"""Хеширование паролей и работа с JWT."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Возвращает bcrypt-хеш пароля."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Сверяет открытый пароль с хешем."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str, expires_delta: timedelta | None = None, extra: dict[str, Any] | None = None
) -> str:
    """Создаёт подписанный JWT с полями sub и exp."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": now}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Декодирует и валидирует JWT, бросает jwt.InvalidTokenError при ошибке."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
