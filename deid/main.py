import hmac
import logging
from functools import lru_cache
from typing import AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError

from common.http import sanitized_validation_handler
from common.schemas import AnalysisResult, DeidentifiedCase, IdentifiedCase
from deid.config import DeidSettings
from deid.security import Crypto
from deid.service import Deidentifier
from deid.vault import Vault

# ВАЖНО: тела запросов не логируем — только case_token.
logger = logging.getLogger("deid")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Deidentification service", docs_url=None, redoc_url=None)


app.add_exception_handler(RequestValidationError, sanitized_validation_handler)


@lru_cache
def _settings() -> DeidSettings:
    # значения подтягиваются из .env/окружения; pyright этого не видит
    return DeidSettings()  # pyright: ignore[reportCallIssue]


@lru_cache
def _deidentifier() -> Deidentifier:
    s = _settings()
    return Deidentifier(Crypto(s.vault_enc_key.get_secret_value()), Vault(s.vault_db_url))


async def analysis_client(
    s: DeidSettings = Depends(_settings),
) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        base_url=s.analysis_url, timeout=30,
        headers={"X-API-Key": s.analysis_api_key.get_secret_value()},
    ) as client:
        yield client


def require_service_key(
    x_api_key: str = Header(...),
    s: DeidSettings = Depends(_settings),
) -> None:
    # В проде вместо общего ключа — mTLS между сервисами
    if not hmac.compare_digest(x_api_key, s.service_api_key.get_secret_value()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid service key")


@app.post("/v1/process", response_model=AnalysisResult,
          dependencies=[Depends(require_service_key)])
async def process(
    case: IdentifiedCase,
    deid: Deidentifier = Depends(_deidentifier),
    client: httpx.AsyncClient = Depends(analysis_client),
) -> AnalysisResult:
    anon: DeidentifiedCase = await run_in_threadpool(deid.run, case)

    # Дальше уходит только обезличенный набор
    try:
        r = await client.post(
            "/v1/analyze",
            content=anon.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        result = AnalysisResult.model_validate(r.json())
    except (httpx.HTTPError, ValueError):
        logger.error("analysis failed case=%s", anon.case_token)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "analysis contour error")

    if result.case_token != anon.case_token:
        logger.error("token mismatch case=%s", anon.case_token)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "token mismatch")

    logger.info("processed case=%s", anon.case_token)
    return result

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "deid", "version": "0.1-draft"}