import logging
from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from common.http import sanitized_validation_handler
from intake.audit import AuditAction, AuditStatus, RequestAudit
from intake.auth import CurrentUser, get_current_user
from intake.deps import get_request_audit, get_service, get_settings
from intake.errors import AccessDenied, DuplicateOms, NotFound, Unprocessable
from intake.schemas import (AnalysisAccepted, AnalysisPage, AnalysisRequest,
                            AnalysisStatus, AnalysisStatusResponse, PatientCreate,
                            PatientPage, PatientProfile, TriageFilter)
from intake.service import IntakeService

from intake.auth import DEMO_AUTH_IDS
from intake.schemas import DemoLoginRequest, TokenResponse
from intake.security import create_access_token

from intake.config import IntakeSettings

logger = logging.getLogger("intake")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Medical data intake", docs_url=None, redoc_url=None)
app.add_exception_handler(RequestValidationError, sanitized_validation_handler)

_cors = get_settings().cors_list if False else []   # заполняется в _configure_cors()


def _configure_cors() -> None:
    """CORS включается, только если CORS_ORIGINS задан в intake/.env."""
    try:
        origins = get_settings().cors_list
    except Exception:           # .env нет (генерация OpenAPI, тесты) — CORS не нужен
        return
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins,
                           allow_methods=["GET", "POST"],
                           allow_headers=["Authorization", "Content-Type"])


_configure_cors()


@app.middleware("http")
async def no_store(request: Request, call_next):
    """Ответы содержат медицинские данные: запрещаем кэширование браузером/прокси."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="access denied")


class _Ctx:
    def __init__(self, resource_id: UUID | None):
        self.resource_id = resource_id


@contextmanager
def audited(audit: RequestAudit, user: CurrentUser, action: AuditAction,
            resource_id: UUID | None = None) -> Iterator[_Ctx]:
    """Каждое обращение к данным пишется в журнал аудита: SUCCESS / DENIED / ERROR.
    Запрос чужого пациента (IDOR) → 403 и запись DENIED с id запрошенного ресурса."""
    ctx = _Ctx(resource_id)

    def rec(st: AuditStatus) -> None:
        audit.record(user_id=user.auth_id, role=user.role.value, action=action,
                     status=st, resource_id=ctx.resource_id)

    try:
        yield ctx
    except AccessDenied:
        rec(AuditStatus.DENIED)
        logger.warning("security: access denied action=%s user=%s resource=%s",
                       action.value, user.auth_id, ctx.resource_id)
        raise _forbidden()
    except NotFound:
        rec(AuditStatus.ERROR)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    except DuplicateOms:
        rec(AuditStatus.ERROR)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "duplicate_oms")
    except Unprocessable as e:
        rec(AuditStatus.ERROR)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, e.code)
    except HTTPException:
        raise
    except Exception:
        rec(AuditStatus.ERROR)
        raise
    else:
        rec(AuditStatus.SUCCESS)


Limit = Query(50, ge=1, le=100, description="Размер страницы")
Offset = Query(0, ge=0)
ERR = {401: {"description": "not authenticated"}, 403: {"description": "access denied"}}


# ───────────────────────── 3.1 Пациенты ─────────────────────────
@app.get("/api/v1/patients", response_model=PatientPage, responses=ERR, tags=["patients"])
def list_patients(
    search: str | None = Query(None, max_length=100, description="Подстрока ФИО или номера ОМС"),
    triage: TriageFilter = Query("all", description="all | anemia | latent | normal"),
    limit: int = Limit, offset: int = Offset,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> PatientPage:
    """Реестр пациентов, прикреплённых к авторизованному врачу."""
    with audited(audit, user, AuditAction.PATIENT_LIST):
        return service.registry(user, search, triage, limit, offset)


@app.post("/api/v1/patients", response_model=PatientProfile, status_code=201,
          responses={**ERR, 400: {"description": "duplicate_oms"},
                     422: {"description": "validation / business rule"}}, tags=["patients"])
def create_patient(
    body: PatientCreate,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> PatientProfile:
    """Регистрация пациента врачом (прикрепляется автоматически) или администратором."""
    with audited(audit, user, AuditAction.PATIENT_CREATE) as ctx:
        profile = service.register_patient(user, body)
        ctx.resource_id = profile.patient_id
        return profile


@app.get("/api/v1/patients/{patient_id}", response_model=PatientProfile,
         responses={**ERR, 404: {"description": "not found"}}, tags=["patients"])
def get_patient(
    patient_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> PatientProfile:
    """Профиль пациента + сводный клинический статус. Чужой пациент → 403 и запись в журнал."""
    with audited(audit, user, AuditAction.PATIENT_READ, patient_id):
        return service.patient_profile(user, patient_id)


@app.get("/api/v1/me", response_model=PatientProfile, responses=ERR, tags=["me"])
def get_me(
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> PatientProfile:
    """Собственный профиль (только роль patient)."""
    with audited(audit, user, AuditAction.ME_READ):
        return service.my_profile(user)


# ───────────────────────── 3.2 Анализы ─────────────────────────
@app.get("/api/v1/patients/{patient_id}/analyses", response_model=AnalysisPage,
         responses=ERR, tags=["analyses"])
def list_patient_analyses(
    patient_id: UUID, limit: int = Limit, offset: int = Offset,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> AnalysisPage:
    with audited(audit, user, AuditAction.ANALYSIS_LIST, patient_id):
        return service.list_for_doctor(user, patient_id, limit, offset)


@app.post("/api/v1/patients/{patient_id}/analyses", response_model=AnalysisAccepted,
          status_code=status.HTTP_202_ACCEPTED,
          responses={**ERR, 422: {"description": "validation / pregnancy_requires_female"}},
          tags=["analyses"])
def create_patient_analysis(
    patient_id: UUID, request: AnalysisRequest, response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> AnalysisAccepted:
    """Принять анализ на ИИ-скрининг. ML в запросе не выполняется: воркер обработает
    асинхронно; состояние — GET .../analyses/{analysis_id}."""
    with audited(audit, user, AuditAction.ANALYSIS_CREATE, patient_id) as ctx:
        analysis = service.create_for_doctor(user, patient_id, request)
        ctx.resource_id = analysis.id
        logger.info("analysis received id=%s", analysis.id)
        response.headers["Location"] = (
            f"/api/v1/patients/{patient_id}/analyses/{analysis.id}")
        return AnalysisAccepted(analysis_id=analysis.id,
                                status=AnalysisStatus(analysis.status))


@app.get("/api/v1/patients/{patient_id}/analyses/{analysis_id}",
         response_model=AnalysisStatusResponse,
         responses={**ERR, 404: {"description": "analysis not found"}}, tags=["analyses"])
def get_patient_analysis(
    patient_id: UUID, analysis_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> AnalysisStatusResponse:
    with audited(audit, user, AuditAction.ANALYSIS_READ, analysis_id):
        return service.get_for_doctor(user, patient_id, analysis_id)


@app.get("/api/v1/me/analyses", response_model=AnalysisPage, responses=ERR, tags=["me"])
def list_my_analyses(
    limit: int = Limit, offset: int = Offset,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> AnalysisPage:
    with audited(audit, user, AuditAction.ANALYSIS_LIST):
        return service.list_mine(user, limit, offset)

@app.post("/api/v1/me/analyses", response_model=AnalysisAccepted,
          status_code=status.HTTP_202_ACCEPTED,
          responses={**ERR, 422: {"description": "validation / pregnancy_requires_female"}},
          tags=["me"])
def create_my_analysis(
    request: AnalysisRequest, response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> AnalysisAccepted:
    """Пациент загружает свой анализ. Воркер обработает асинхронно."""
    with audited(audit, user, AuditAction.ANALYSIS_CREATE) as ctx:
        analysis = service.create_mine(user, request)
        ctx.resource_id = analysis.id
        response.headers["Location"] = f"/api/v1/me/analyses/{analysis.id}"
        return AnalysisAccepted(analysis_id=analysis.id,
                                status=AnalysisStatus(analysis.status))

@app.get("/api/v1/me/analyses/{analysis_id}", response_model=AnalysisStatusResponse,
         responses={**ERR, 404: {"description": "analysis not found"}}, tags=["me"])
def get_my_analysis(
    analysis_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: IntakeService = Depends(get_service),
    audit: RequestAudit = Depends(get_request_audit),
) -> AnalysisStatusResponse:
    with audited(audit, user, AuditAction.ANALYSIS_READ, analysis_id):
        return service.get_mine(user, analysis_id)

# ───────────────────────── 3.0 Аутентификация ─────────────────────────
@app.post("/api/v1/auth/demo-login", response_model=TokenResponse, tags=["auth"])
def demo_login(
    body: DemoLoginRequest,
    s: IntakeSettings = Depends(get_settings),
) -> TokenResponse:
    """DEMO ONLY. Отдаёт валидный JWT для seed-пользователя по роли.
    В проде этот эндпоинт должен быть выключен (DEMO_LOGIN_ENABLED=false)."""
    if not s.demo_login_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    auth_id = DEMO_AUTH_IDS.get(body.role)
    if auth_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown demo role")
    token = create_access_token(
        s.jwt_secret.get_secret_value(), auth_id, body.role, s.jwt_ttl_hours
    )
    logger.info("demo-login role=%s auth_id=%s", body.role, auth_id)
    return TokenResponse(
        access_token=token, role=body.role, auth_id=auth_id,
        expires_in=s.jwt_ttl_hours * 3600,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
