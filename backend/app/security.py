from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt

from .config import settings

JWT_ALGORITHM = "HS256"
API_KEY_PREFIX = "rop"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    expires_at = datetime.utcnow() + timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {"sub": user_id, "exp": expires_at, "typ": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])


def new_api_key() -> str:
    return f"{API_KEY_PREFIX}_{secrets.token_urlsafe(32)}"


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def api_key_prefix(value: str) -> str:
    return value[:16]

