import logging
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from uuid import UUID

from fastapi import Header, HTTPException, status
from jwt.exceptions import InvalidTokenError

from intake.config import IntakeSettings
from intake.security import decode_access_token

logger = logging.getLogger("intake.auth")


class Role(str, Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"


# Фиксированные UUID демо-пользователей. Должны совпадать с db/seed_demo.sql.
DEMO_AUTH_IDS: dict[str, UUID] = {
    "doctor":  UUID("11111111-1111-1111-1111-111111111111"),
    "patient": UUID("22222222-2222-2222-2222-222222222222"),
    "admin":   UUID("33333333-3333-3333-3333-333333333333"),
}


@dataclass(frozen=True)
class CurrentUser:
    auth_id: UUID
    role: Role


@lru_cache
def _settings() -> IntakeSettings:
    return IntakeSettings()  # pyright: ignore[reportCallIssue]


async def get_current_user(
    authorization: str | None = Header(None),
) -> CurrentUser:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(_settings().jwt_secret.get_secret_value(), token)
    except InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {e}")

    try:
        auth_id = UUID(payload["sub"])
        role = Role(payload["role"])
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token payload")

    return CurrentUser(auth_id=auth_id, role=role)