"""Хранилище соответствий case_token → patient_id (шифртекст).
В проде: отдельная БД/роль, недоступна контуру анализа."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, LargeBinary, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class VaultRecord(Base):
    __tablename__ = "vault"

    case_token: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_ref_enc: Mapped[bytes] = mapped_column(LargeBinary)   # BYTEA в PostgreSQL
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Vault:
    def __init__(self, url: str):
        self.engine = create_engine(url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)   # прототип; в проде — Alembic

    def put(self, case_token: str, patient_ref_enc: bytes) -> None:
        with Session(self.engine) as s:
            s.add(VaultRecord(case_token=case_token, patient_ref_enc=patient_ref_enc))
            s.commit()

    def get(self, case_token: str) -> VaultRecord | None:
        with Session(self.engine) as s:
            return s.get(VaultRecord, case_token)
