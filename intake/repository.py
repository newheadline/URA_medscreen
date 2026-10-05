from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import (JSON, BigInteger, Boolean, DateTime, Integer, LargeBinary,
                        String, create_engine, func, select, update)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from intake.errors import DuplicateOms
from intake.schemas import AnalysisStatus

# JSONB в PostgreSQL, обычный JSON в SQLite (для тестов)
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "Patients"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(1), nullable=False)
    auth_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), unique=True)
    full_name_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    oms_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    oms_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    contacts_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Doctor(Base):
    __tablename__ = "Doctors"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    specialty: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, unique=True)


class DoctorPatient(Base):
    __tablename__ = "Doctor_n_patients"

    doctor_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    patient_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Analysis(Base):
    __tablename__ = "Analyses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    biomarkers: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    predictions: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    doctor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    case_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    triage_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    patient_age: Mapped[int] = mapped_column(Integer, nullable=False)
    patient_sex: Mapped[str] = mapped_column(String(1), nullable=False)
    pregnant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "Audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    role: Mapped[str | None] = mapped_column(String(32))
    client_ip: Mapped[str | None] = mapped_column(String(45))
    action_type: Mapped[str] = mapped_column(String(48), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    execution_status: Mapped[str] = mapped_column(String(16), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    digital_signature_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


@dataclass(frozen=True)
class RegistryRow:
    patient: Patient
    last_analysis_at: datetime | None
    triage_status: str | None          # по последнему DONE-анализу


@dataclass(frozen=True)
class PatientSummary:
    total: int
    in_progress: int
    latest_done: Analysis | None


class Repository:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)

    # ───────── пользователи ─────────
    def get_patient_by_auth_id(self, auth_id: UUID) -> Patient | None:
        with Session(self.engine) as session:
            return session.scalar(select(Patient).where(Patient.auth_id == auth_id))

    def get_patient(self, patient_id: UUID) -> Patient | None:
        with Session(self.engine) as session:
            return session.get(Patient, patient_id)

    def get_doctor(self, doctor_id: UUID) -> Doctor | None:
        with Session(self.engine) as session:
            return session.get(Doctor, doctor_id)

    def get_doctor_by_auth_id(self, auth_id: UUID) -> Doctor | None:
        with Session(self.engine) as session:
            return session.scalar(select(Doctor).where(Doctor.auth_id == auth_id))

    def doctor_has_patient(self, doctor_id: UUID, patient_id: UUID) -> bool:
        """ABAC-проверка: прикреплён ли пациент к врачу (таблица Doctor_n_patients)."""
        with Session(self.engine) as session:
            return session.get(DoctorPatient, (doctor_id, patient_id)) is not None

    # ───────── пациенты ─────────
    def create_patient(self, patient: Patient, attach_to_doctor: UUID | None) -> Patient:
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(patient)
            try:
                session.flush()
                if attach_to_doctor is not None:
                    session.add(DoctorPatient(
                        doctor_id=attach_to_doctor, patient_id=patient.id,
                        created_at=patient.created_at))
                session.commit()
            except IntegrityError:
                session.rollback()
                if patient.oms_hash is not None and session.scalar(
                        select(Patient.id).where(Patient.oms_hash == patient.oms_hash)):
                    raise DuplicateOms()
                raise
        return patient

    def list_registry(self, doctor_id: UUID) -> list[RegistryRow]:
        """Все пациенты врача + триаж по последнему готовому анализу.
        ФИО/ОМС в БД зашифрованы, поэтому поиск по ним делает сервис в памяти
        по этому (врачебному) набору."""
        mine = select(DoctorPatient.patient_id).where(DoctorPatient.doctor_id == doctor_id)
        rn = func.row_number().over(
            partition_by=Analysis.user_id,
            order_by=(Analysis.created_at.desc(), Analysis.id.desc()))
        latest = (
            select(Analysis.user_id.label("pid"), Analysis.created_at.label("at"),
                   Analysis.triage_status.label("triage"), rn.label("rn"))
            .where(Analysis.status == AnalysisStatus.DONE.value, Analysis.user_id.in_(mine))
            .subquery())
        stmt = (
            select(Patient, latest.c.at, latest.c.triage)
            .join(DoctorPatient, DoctorPatient.patient_id == Patient.id)
            .outerjoin(latest, (latest.c.pid == Patient.id) & (latest.c.rn == 1))
            .where(DoctorPatient.doctor_id == doctor_id))
        with Session(self.engine) as session:
            return [RegistryRow(p, at, triage) for p, at, triage in session.execute(stmt)]

    def patient_summary(self, patient_id: UUID) -> PatientSummary:
        with Session(self.engine) as session:
            total = session.scalar(
                select(func.count()).select_from(Analysis).where(Analysis.user_id == patient_id)) or 0
            in_progress = session.scalar(
                select(func.count()).select_from(Analysis).where(
                    Analysis.user_id == patient_id,
                    Analysis.status.in_([AnalysisStatus.RECEIVED.value,
                                         AnalysisStatus.PROCESSING.value]))) or 0
            latest = session.scalar(
                select(Analysis)
                .where(Analysis.user_id == patient_id,
                       Analysis.status == AnalysisStatus.DONE.value)
                .order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(1))
            return PatientSummary(total, in_progress, latest)

    # ───────── анализы ─────────
    def create_analysis(
        self,
        patient_id: UUID,
        doctor_id: UUID | None,
        biomarkers: dict,
        patient_age: int,
        patient_sex: str,
        pregnant: bool | None,
    ) -> Analysis:
        now = datetime.now(timezone.utc)
        analysis = Analysis(
            id=uuid4(), biomarkers=biomarkers, predictions=None,
            user_id=patient_id, doctor_id=doctor_id,
            status=AnalysisStatus.RECEIVED.value, error_code=None, case_token=None,
            model_version=None, triage_status=None,
            patient_age=patient_age, patient_sex=patient_sex, pregnant=pregnant,
            created_at=now, updated_at=now)
        with Session(self.engine) as session:
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
        return analysis

    def get_analysis(self, analysis_id: UUID, patient_id: UUID) -> Analysis | None:
        """Анализ ТОЛЬКО если он принадлежит указанному пациенту: нельзя получить
        чужой анализ, подставив его id в путь другого пациента."""
        with Session(self.engine) as session:
            return session.scalar(select(Analysis).where(
                Analysis.id == analysis_id, Analysis.user_id == patient_id))

    def list_analyses(self, patient_id: UUID, limit: int, offset: int) -> tuple[list[Analysis], int]:
        with Session(self.engine) as session:
            total = session.scalar(
                select(func.count()).select_from(Analysis).where(Analysis.user_id == patient_id)) or 0
            rows = list(session.scalars(
                select(Analysis).where(Analysis.user_id == patient_id)
                .order_by(Analysis.created_at.desc(), Analysis.id.desc())
                .limit(limit).offset(offset)))
            return rows, total

    # ───────── воркер ─────────
    def claim_next(self, stale_seconds: int) -> Analysis | None:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(seconds=stale_seconds)
        with Session(self.engine) as session:
            query = (
                select(Analysis)
                .where(
                    (Analysis.status == AnalysisStatus.RECEIVED.value)
                    | (
                        (Analysis.status == AnalysisStatus.PROCESSING.value)
                        & (Analysis.updated_at < stale_before)
                    )
                )
                .order_by(Analysis.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            analysis = session.scalar(query)
            if analysis is None:
                return None
            analysis.status = AnalysisStatus.PROCESSING.value
            analysis.error_code = None
            analysis.updated_at = now
            session.commit()
            session.refresh(analysis)
            return analysis

    def mark_done(self, analysis_id: UUID, result: dict, case_token: str,
                  model_version: str, triage_status: str) -> None:
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            session.execute(
                update(Analysis).where(Analysis.id == analysis_id).values(
                    predictions=result, case_token=case_token,
                    model_version=model_version, triage_status=triage_status,
                    status=AnalysisStatus.DONE.value, error_code=None, updated_at=now))
            session.commit()

    def mark_failed(self, analysis_id: UUID, error_code: str) -> None:
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            session.execute(
                update(Analysis).where(Analysis.id == analysis_id).values(
                    status=AnalysisStatus.FAILED.value, error_code=error_code,
                    updated_at=now))
            session.commit()