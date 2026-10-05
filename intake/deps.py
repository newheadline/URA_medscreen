"""Сборка зависимостей. Общая для main.py, worker.py и модуля авторизации
(auth.py может звать get_audit_trail() для записи AUTH_LOGIN)."""
from functools import lru_cache

from fastapi import Depends, Request

from intake.audit import AuditTrail, RequestAudit
from intake.config import IntakeSettings
from intake.crypto import KeyRing, PiiCipher
from intake.repository import Repository
from intake.service import IntakeService


@lru_cache
def get_settings() -> IntakeSettings:
    return IntakeSettings()  # pyright: ignore[reportCallIssue]


@lru_cache
def get_repository() -> Repository:
    return Repository(get_settings().database_url)


@lru_cache
def get_keyring() -> KeyRing:
    return KeyRing(get_settings().data_master_key.get_secret_value())


@lru_cache
def get_audit_trail() -> AuditTrail:
    return AuditTrail(get_repository().engine, get_keyring().hmac_key("audit-chain"))


def get_service(
    repository: Repository = Depends(get_repository),
    keyring: KeyRing = Depends(get_keyring),
) -> IntakeService:
    return IntakeService(repository, PiiCipher(keyring), keyring)


def get_request_audit(
    request: Request,
    trail: AuditTrail = Depends(get_audit_trail),
) -> RequestAudit:
    return RequestAudit(trail, request)
