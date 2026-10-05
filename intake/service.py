import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError
from common.labs_model import Labs

from common.schemas import (AnalysisResult, AnemiaClass, DeficiencyCause,
                            IdentifiedCase, Sex)

from intake.auth import CurrentUser, Role
from intake.crypto import (KeyRing, PiiCipher, normalize_oms, normalize_text,
                           oms_blind_index)
from intake.errors import AccessDenied, NotFound, Unprocessable
from intake.repository import Analysis, Doctor, Patient, Repository
from intake.schemas import (AnalysisListItem, AnalysisPage, AnalysisRequest,
                            AnalysisStatus, AnalysisStatusResponse,
                            ClinicalSummary, Contacts, LastAnalysis,
                            PatientCreate, PatientListItem, PatientPage,
                            PatientProfile, TriageFilter, TriageStatus)

logger = logging.getLogger("intake.service")


def triage_from_result(result: AnalysisResult) -> TriageStatus:
    """anemia — анемия есть; latent — анемии нет, но найден дефицит; normal — ничего нет."""
    if result.anemia_detected:
        return TriageStatus.anemia
    if result.deficiency_cause not in (DeficiencyCause.none, DeficiencyCause.undetermined):
        return TriageStatus.latent
    return TriageStatus.normal


def _enum_or_none(enum_cls: Any, value: Any) -> Any:
    try:
        return enum_cls(value)
    except ValueError:
        return None


class IntakeService:
    def __init__(self, repository: Repository, cipher: PiiCipher, keyring: KeyRing):
        self.repository = repository
        self.cipher = cipher
        self.keyring = keyring

    # ───────── доступ ─────────
    def _doctor(self, user: CurrentUser) -> Doctor:
        if user.role != Role.doctor:
            raise AccessDenied("not a doctor")
        doctor = self.repository.get_doctor_by_auth_id(user.auth_id)
        if doctor is None:
            raise AccessDenied("doctor profile not found")
        return doctor

    def _doctor_with_patient(self, user: CurrentUser, patient_id: UUID) -> tuple[Doctor, Patient]:
        """ABAC/IDOR: врач работает только с пациентами из Doctor_n_patients.
        Несуществующий и чужой пациент неотличимы (оба → AccessDenied), чтобы
        нельзя было перебором выяснять, какие id существуют."""
        doctor = self._doctor(user)
        if not self.repository.doctor_has_patient(doctor.id, patient_id):
            raise AccessDenied("patient is not attached to doctor")
        patient = self.repository.get_patient(patient_id)
        if patient is None:
            raise AccessDenied("patient not found")
        return doctor, patient

    def _patient_self(self, user: CurrentUser) -> Patient:
        if user.role != Role.patient:
            raise AccessDenied("not a patient")
        patient = self.repository.get_patient_by_auth_id(user.auth_id)
        if patient is None:
            raise AccessDenied("patient profile not found")
        return patient

    # ───────── пациенты ─────────
    def register_patient(self, user: CurrentUser, req: PatientCreate) -> PatientProfile:
        attach: UUID | None
        if user.role == Role.doctor:
            doctor = self._doctor(user)
            if req.doctor_id not in (None, doctor.id):
                raise Unprocessable("doctor_id_not_allowed")
            attach = doctor.id
        elif user.role == Role.admin:
            attach = req.doctor_id
            if attach is not None and self.repository.get_doctor(attach) is None:
                raise Unprocessable("unknown_doctor")
        else:
            raise AccessDenied("role cannot register patients")

        oms = normalize_oms(req.oms) if req.oms else None
        contacts = req.contacts.model_dump(exclude_none=True) if req.contacts else {}
        patient = Patient(
            id=uuid4(), age=req.age, sex=req.sex.value, auth_id=None,
            full_name_enc=self.cipher.enc_str(req.full_name),
            oms_enc=self.cipher.enc_str(oms) if oms else None,
            oms_hash=oms_blind_index(self.keyring, oms) if oms else None,
            contacts_enc=self.cipher.enc_json(contacts) if contacts else None,
            created_by=user.auth_id, created_at=datetime.now(timezone.utc))
        self.repository.create_patient(patient, attach)       # DuplicateOms при повторе ОМС
        return self._profile(patient)

    def registry(self, user: CurrentUser, search: str | None, triage: TriageFilter,
                 limit: int, offset: int) -> PatientPage:
        doctor = self._doctor(user)
        rows = self.repository.list_registry(doctor.id)

        items: list[tuple[str, PatientListItem]] = []
        q_text = normalize_text(search) if search else ""
        q_oms = normalize_oms(search) if search else ""
        for row in rows:
            if triage != "all" and row.triage_status != triage:
                continue
            name = self.cipher.dec_str(row.patient.full_name_enc) if row.patient.full_name_enc else None
            oms = self.cipher.dec_str(row.patient.oms_enc) if row.patient.oms_enc else None
            if search:
                hit = bool(name and q_text in normalize_text(name)) or bool(oms and q_oms in oms)
                if not hit:
                    continue
            items.append((normalize_text(name or ""), PatientListItem(
                patient_id=row.patient.id, full_name=name, age=row.patient.age,
                sex=Sex(row.patient.sex), oms=oms,
                triage_status=_enum_or_none(TriageStatus, row.triage_status),
                last_analysis_at=row.last_analysis_at)))
        items.sort(key=lambda kv: kv[0])
        page = [i for _, i in items][offset: offset + limit]
        return PatientPage(items=page, total=len(items), limit=limit, offset=offset)

    def patient_profile(self, user: CurrentUser, patient_id: UUID) -> PatientProfile:
        _, patient = self._doctor_with_patient(user, patient_id)
        return self._profile(patient)

    def my_profile(self, user: CurrentUser) -> PatientProfile:
        return self._profile(self._patient_self(user))

    def _profile(self, patient: Patient) -> PatientProfile:
        summary = self.repository.patient_summary(patient.id)
        last = summary.latest_done
        preds = last.predictions if last is not None else None
        last_analysis = None
        if last is not None:
            last_analysis = LastAnalysis(
                analysis_id=last.id, created_at=last.created_at,
                triage_status=_enum_or_none(TriageStatus, last.triage_status),
                anemia_class=_enum_or_none(AnemiaClass, (preds or {}).get("anemia_class")),
                deficiency_cause=_enum_or_none(DeficiencyCause, (preds or {}).get("deficiency_cause")))
        contacts = (Contacts.model_validate(self.cipher.dec_json(patient.contacts_enc))
                    if patient.contacts_enc else None)
        return PatientProfile(
            patient_id=patient.id,
            full_name=self.cipher.dec_str(patient.full_name_enc) if patient.full_name_enc else None,
            age=patient.age, sex=Sex(patient.sex),
            oms=self.cipher.dec_str(patient.oms_enc) if patient.oms_enc else None,
            contacts=contacts, created_at=patient.created_at,
            clinical_summary=ClinicalSummary(
                triage_status=last_analysis.triage_status if last_analysis else None,
                analyses_total=summary.total, analyses_in_progress=summary.in_progress,
                last_analysis=last_analysis))

    # ───────── анализы ─────────
    def create_for_doctor(self, user: CurrentUser, patient_id: UUID,
                          request: AnalysisRequest) -> Analysis:
        doctor, patient = self._doctor_with_patient(user, patient_id)
        if request.pregnant and patient.sex != Sex.female.value:
            raise Unprocessable("pregnancy_requires_female")
        return self.repository.create_analysis(
            patient_id=patient.id, doctor_id=doctor.id,
            biomarkers=request.biomarkers.model_dump(exclude_none=True),
            patient_age=patient.age, patient_sex=patient.sex, pregnant=request.pregnant)
    def create_mine(self, user: CurrentUser, request: AnalysisRequest) -> Analysis:
        patient = self._patient_self(user)
        if request.pregnant and patient.sex != Sex.female.value:
            raise Unprocessable("pregnancy_requires_female")
        return self.repository.create_analysis(
            patient_id=patient.id, doctor_id=None,     # ← пациента создал сам пациент
            biomarkers=request.biomarkers.model_dump(exclude_none=True),
            patient_age=patient.age, patient_sex=patient.sex, pregnant=request.pregnant)

    def list_for_doctor(self, user: CurrentUser, patient_id: UUID,
                        limit: int, offset: int) -> AnalysisPage:
        _, patient = self._doctor_with_patient(user, patient_id)
        return self._page(patient.id, limit, offset)

    def list_mine(self, user: CurrentUser, limit: int, offset: int) -> AnalysisPage:
        return self._page(self._patient_self(user).id, limit, offset)

    def get_for_doctor(self, user: CurrentUser, patient_id: UUID,
                       analysis_id: UUID) -> AnalysisStatusResponse:
        _, patient = self._doctor_with_patient(user, patient_id)
        return self._status(self._analysis_of(patient.id, analysis_id))

    def get_mine(self, user: CurrentUser, analysis_id: UUID) -> AnalysisStatusResponse:
        patient = self._patient_self(user)
        return self._status(self._analysis_of(patient.id, analysis_id))

    def _analysis_of(self, patient_id: UUID, analysis_id: UUID) -> Analysis:
        analysis = self.repository.get_analysis(analysis_id, patient_id)
        if analysis is None:
            raise NotFound("analysis")
        return analysis

    def _page(self, patient_id: UUID, limit: int, offset: int) -> AnalysisPage:
        rows, total = self.repository.list_analyses(patient_id, limit, offset)
        items = []
        for a in rows:
            preds = a.predictions or {}
            items.append(AnalysisListItem(
                analysis_id=a.id, status=AnalysisStatus(a.status), created_at=a.created_at,
                error_code=a.error_code,
                triage_status=_enum_or_none(TriageStatus, a.triage_status),
                anemia_class=_enum_or_none(AnemiaClass, preds.get("anemia_class")),
                deficiency_cause=_enum_or_none(DeficiencyCause, preds.get("deficiency_cause"))))
        return AnalysisPage(items=items, total=total, limit=limit, offset=offset)

    @staticmethod
    def _status(analysis: Analysis) -> AnalysisStatusResponse:
        result, error_code = None, analysis.error_code
        if analysis.status == AnalysisStatus.DONE.value:
            try:
                result = AnalysisResult.model_validate(analysis.predictions)
            except ValidationError:
                logger.error("stored result does not match contract id=%s", analysis.id)
                error_code = "STORED_RESULT_INVALID"
        return AnalysisStatusResponse(
            analysis_id=analysis.id, status=AnalysisStatus(analysis.status),
            result=result, error_code=error_code, created_at=analysis.created_at)

    def build_identified_case(self, analysis: Analysis) -> IdentifiedCase:
        return IdentifiedCase(
            patient_id=str(analysis.user_id),
            age_years=analysis.patient_age,
            sex=Sex(analysis.patient_sex),
            pregnant=analysis.pregnant,
            labs=Labs.model_validate(analysis.biomarkers)
        )
