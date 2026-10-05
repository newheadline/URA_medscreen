"""JWT-примитивы. Ничего не знает про БД и FastAPI — только sign/verify."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

ALGORITHM = "HS256"


def create_access_token(secret: str, auth_id: uuid.UUID, role: str, ttl_hours: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(auth_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(secret: str, token: str) -> dict:
    """Бросает InvalidTokenError при любой проблеме."""
    return jwt.decode(token, secret, algorithms=[ALGORITHM])