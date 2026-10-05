"""Неизменяемый журнал аудита.

Три слоя защиты (от слабого к сильному):
  1. БД: триггеры запрещают UPDATE/DELETE/TRUNCATE, права на них отозваны (db/schema.sql).
  2. Приложение: каждая запись содержит HMAC-SHA256(prev_hash + поля записи), ключ
     только у приложения. Администратор БД может отключить триггеры, но не может
     подделать цепочку без ключа: verify() покажет первую испорченную запись.
  3. Снаружи (НЕ реализовано здесь): периодически выгружать head_hash во внешнее
     хранилище с защитой от перезаписи (Object Lock, SIEM, бумажный носитель) —
     только так обнаруживается обрезка ХВОСТА журнала.

Журнал fail-closed: если запись не удалась — запрос завершается ошибкой.
Действие без следа в системе с ПДн недопустимо."""
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from fastapi import Request
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from intake.repository import AuditLog

GENESIS_HASH = "0" * 64
AUDIT_LOCK_KEY = 0x4D534155        # «MSAU»: сериализует запись цепочки в PostgreSQL


class AuditAction(str, Enum):
    # Из требований фронтенда
    AUTH_LOGIN = "AUTH_LOGIN"
    PATIENT_READ = "PATIENT_READ"
    ANALYSIS_CREATE = "ANALYSIS_CREATE"
    REPORT_EXPORT_PDF = "REPORT_EXPORT_PDF"
    CADES_SIGN_CREATED = "CADES_SIGN_CREATED"
    # Добавлены бэкендом (в списке фронтенда их нет)
    PATIENT_LIST = "PATIENT_LIST"
    PATIENT_CREATE = "PATIENT_CREATE"
    ANALYSIS_LIST = "ANALYSIS_LIST"
    ANALYSIS_READ = "ANALYSIS_READ"
    ME_READ = "ME_READ"
    ANALYSIS_PROCESSED = "ANALYSIS_PROCESSED"      # системное: воркер


class AuditStatus(str, Enum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    ERROR = "ERROR"


class AuditWriteError(RuntimeError):
    pass


def _ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compute_signature(key: bytes, prev_hash: str, *, ts: datetime,
                      user_id: uuid.UUID | None, role: str | None,
                      client_ip: str | None, action: str,
                      resource_id: str | None, status: str) -> str:
    payload = json.dumps(
        [_ts(ts), str(user_id) if user_id else None, role, client_ip,
         action, resource_id, status],
        ensure_ascii=False, separators=(",", ":"))
    return hmac.new(key, f"{prev_hash}|{payload}".encode(), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class AuditVerification:
    ok: bool
    checked: int
    first_bad_id: int | None
    head_id: int | None          # для внешнего якоря
    head_hash: str | None


class AuditTrail:
    def __init__(self, engine: Engine, hmac_key: bytes, max_retries: int = 8):
        self.engine = engine
        self._key = hmac_key
        self._retries = max_retries

    def record(self, *, action: AuditAction, status: AuditStatus,
               user_id: uuid.UUID | None = None, role: str | None = None,
               client_ip: str | None = None,
               resource_id: uuid.UUID | str | None = None) -> None:
        ip = client_ip[:45] if client_ip else None
        res = str(resource_id) if resource_id else None
        for _ in range(self._retries):
            try:
                with Session(self.engine) as s, s.begin():
                    if self.engine.dialect.name == "postgresql":
                        s.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                                  {"k": AUDIT_LOCK_KEY})
                    prev = s.scalar(select(AuditLog.digital_signature_hash)
                                    .order_by(AuditLog.id.desc()).limit(1)) or GENESIS_HASH
                    ts = datetime.now(timezone.utc)
                    sig = compute_signature(
                        self._key, prev, ts=ts, user_id=user_id, role=role,
                        client_ip=ip, action=action.value, resource_id=res,
                        status=status.value)
                    s.add(AuditLog(
                        timestamp_utc=ts, user_id=user_id, role=role, client_ip=ip,
                        action_type=action.value, resource_id=res,
                        execution_status=status.value, prev_hash=prev,
                        digital_signature_hash=sig))
                return
            except IntegrityError:      # параллельная запись заняла prev_hash — пробуем ещё раз
                continue
        raise AuditWriteError("could not append audit record")

    def verify(self) -> AuditVerification:
        prev, n, head_id = GENESIS_HASH, 0, None
        with Session(self.engine) as s:
            for row in s.scalars(select(AuditLog).order_by(AuditLog.id)).yield_per(1000):
                expected = compute_signature(
                    self._key, prev, ts=row.timestamp_utc, user_id=row.user_id,
                    role=row.role, client_ip=row.client_ip, action=row.action_type,
                    resource_id=row.resource_id, status=row.execution_status)
                if row.prev_hash != prev or row.digital_signature_hash != expected:
                    return AuditVerification(False, n, row.id, head_id, prev)
                prev, head_id, n = row.digital_signature_hash, row.id, n + 1
        return AuditVerification(True, n, None, head_id, prev if n else None)


class RequestAudit:
    """AuditTrail, привязанный к текущему HTTP-запросу (берёт client_ip)."""

    def __init__(self, trail: AuditTrail, request: Request):
        self._trail = trail
        self._ip = request.client.host if request.client else None

    def record(self, *, user_id: uuid.UUID | None, role: str | None,
               action: AuditAction, status: AuditStatus,
               resource_id: uuid.UUID | str | None = None) -> None:
        self._trail.record(action=action, status=status, user_id=user_id,
                           role=role, client_ip=self._ip, resource_id=resource_id)
