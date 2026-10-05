"""Контракт внешнего API (PReact). JSON — snake_case."""
import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (AfterValidator, BaseModel, ConfigDict, Field,
                      StringConstraints, field_validator)

from common.labs_model import Labs
from common.schemas import AnalysisResult, AnemiaClass, DeficiencyCause, Sex

Stripped = Annotated[str, StringConstraints(strip_whitespace=True)]


# ───────── анализы ─────────
class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    biomarkers: Labs
    pregnant: bool = False          # по умолчанию false; true допустимо только для пола F


class AnalysisStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class TriageStatus(str, Enum):
    """Триаж по последнему готовому анализу."""
    anemia = "anemia"        # анемия обнаружена
    latent = "latent"        # анемии нет, но есть дефицит (скрытый)
    normal = "normal"        # анемии и дефицитов нет


class AnalysisAccepted(BaseModel):
    analysis_id: UUID
    status: AnalysisStatus


class AnalysisStatusResponse(BaseModel):
    analysis_id: UUID
    status: AnalysisStatus
    result: AnalysisResult | None = None
    error_code: str | None = None
    created_at: datetime | None = None


class AnalysisListItem(BaseModel):
    analysis_id: UUID
    status: AnalysisStatus
    created_at: datetime
    error_code: str | None = None
    triage_status: TriageStatus | None = None
    anemia_class: AnemiaClass | None = None
    deficiency_cause: DeficiencyCause | None = None


class AnalysisPage(BaseModel):
    items: list[AnalysisListItem]
    total: int
    limit: int
    offset: int


# ───────── пациенты ─────────
_PHONE = re.compile(r"^[+0-9()\-\s]{5,32}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_OMS = re.compile(r"^[0-9A-Za-z]{6,32}$")


class Contacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: Stripped | None = Field(None, max_length=32)
    email: Stripped | None = Field(None, max_length=254)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v is not None and not _PHONE.match(v):
            raise ValueError("invalid phone")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        if v is not None and not _EMAIL.match(v):
            raise ValueError("invalid email")
        return v


def _oms_clean(v: str) -> str:
    cleaned = re.sub(r"[\s\-]", "", v)
    if not _OMS.match(cleaned):
        raise ValueError("invalid OMS number")
    return v


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Stripped = Field(min_length=2, max_length=200)
    age: int = Field(ge=18, le=120)
    sex: Sex
    oms: Annotated[Stripped, AfterValidator(_oms_clean)] | None = Field(None, max_length=48)
    contacts: Contacts | None = None
    # Только для администратора: к какому врачу прикрепить. Врач прикрепляется сам.
    doctor_id: UUID | None = None


class LastAnalysis(BaseModel):
    analysis_id: UUID
    created_at: datetime
    triage_status: TriageStatus | None = None
    anemia_class: AnemiaClass | None = None
    deficiency_cause: DeficiencyCause | None = None


class ClinicalSummary(BaseModel):
    triage_status: TriageStatus | None = None     # null — готовых анализов ещё нет
    analyses_total: int
    analyses_in_progress: int
    last_analysis: LastAnalysis | None = None


class PatientProfile(BaseModel):
    patient_id: UUID
    full_name: str | None
    age: int
    sex: Sex
    oms: str | None
    contacts: Contacts | None
    created_at: datetime
    clinical_summary: ClinicalSummary


class PatientListItem(BaseModel):
    patient_id: UUID
    full_name: str | None
    age: int
    sex: Sex
    oms: str | None
    triage_status: TriageStatus | None
    last_analysis_at: datetime | None


class PatientPage(BaseModel):
    items: list[PatientListItem]
    total: int
    limit: int
    offset: int

# ───────── аутентификация ─────────
class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["doctor", "patient", "admin"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    auth_id: UUID
    expires_in: int          # секунды

TriageFilter = Literal["all", "anemia", "latent", "normal"]