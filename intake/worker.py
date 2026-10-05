import asyncio
import logging

import httpx
from pydantic import ValidationError

from common.schemas import AnalysisResult, IdentifiedCase
from intake.audit import AuditAction, AuditStatus, AuditTrail
from intake.config import IntakeSettings
from intake.crypto import KeyRing, PiiCipher
from intake.repository import Repository
from intake.service import IntakeService, triage_from_result


logger = logging.getLogger("intake.worker")


class AnalysisWorker:
    def __init__(self, settings: IntakeSettings, repository: Repository,
                 trail: AuditTrail | None = None,
                 http_client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.repository = repository
        self.trail = trail
        self._http = http_client          # подмена в тестах
        keyring = KeyRing(settings.data_master_key.get_secret_value())
        self.service = IntakeService(repository, PiiCipher(keyring), keyring)

    def _audit(self, analysis_id, ok: bool) -> None:
        if self.trail is not None:
            self.trail.record(
                action=AuditAction.ANALYSIS_PROCESSED,
                status=AuditStatus.SUCCESS if ok else AuditStatus.ERROR,
                role="system", resource_id=analysis_id)

    async def run_once(self) -> bool:
        analysis = self.repository.claim_next(
            self.settings.worker_stale_seconds
        )
        if analysis is None:
            return False

        try:
            case = self.service.build_identified_case(analysis)
            result = await self._send_to_deid(case)
            self.repository.mark_done(
                analysis_id=analysis.id,
                result=result.model_dump(mode="json"),
                case_token=result.case_token,
                model_version=result.model_version,
                triage_status=triage_from_result(result).value,
            )
            logger.info("analysis completed id=%s", analysis.id)
            self._audit(analysis.id, True)
        except httpx.HTTPStatusError as e:
            code = "DEID_REJECTED" if e.response.status_code == 422 else "DEID_UNAVAILABLE"
            logger.error("deid returned %s id=%s", e.response.status_code, analysis.id)
            self.repository.mark_failed(analysis.id, code)
            self._audit(analysis.id, False)
        except httpx.HTTPError:
            logger.exception("deid unavailable id=%s", analysis.id)
            self.repository.mark_failed(analysis.id, "DEID_UNAVAILABLE")
            self._audit(analysis.id, False)
        except (ValueError, ValidationError):
            logger.exception("invalid analysis result id=%s", analysis.id)
            self.repository.mark_failed(analysis.id, "INVALID_ANALYSIS_RESULT")
            self._audit(analysis.id, False)
        except Exception:
            logger.exception("unexpected analysis failure id=%s", analysis.id)
            self.repository.mark_failed(analysis.id, "PROCESSING_ERROR")
            self._audit(analysis.id, False)

        return True

    async def _send_to_deid(
        self,
        case: IdentifiedCase,
    ) -> AnalysisResult:
        async def call(client: httpx.AsyncClient) -> AnalysisResult:
            response = await client.post(
                "/v1/process",
                content=case.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return AnalysisResult.model_validate(response.json())

        if self._http is not None:
            return await call(self._http)
        async with httpx.AsyncClient(
            base_url=self.settings.deid_url,
            timeout=60,
            headers={
                "X-API-Key": self.settings.deid_api_key.get_secret_value(),
            },
        ) as client:
            return await call(client)

    async def run_forever(self) -> None:
        while True:
            processed = await self.run_once()
            if not processed:
                await asyncio.sleep(self.settings.worker_poll_seconds)


async def main() -> None:
    settings = IntakeSettings()  # pyright: ignore[reportCallIssue]
    repository = Repository(settings.database_url)
    keyring = KeyRing(settings.data_master_key.get_secret_value())
    trail = AuditTrail(repository.engine, keyring.hmac_key("audit-chain"))
    worker = AnalysisWorker(settings, repository, trail)
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
