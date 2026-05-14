"""Создание bootstrap-администратора при старте приложения.

Если в `.env` заполнены `ADMIN_EMAIL` и `ADMIN_PASSWORD`, при старте
проверяется наличие пользователя с этим email; если его нет —
создаётся с ролью ADMIN. Повторные запуски ничего не делают.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.auth.security import get_password_hash
from app.core.config import settings
from app.core.db import SessionLocal
from app.models import User, UserRole

logger = logging.getLogger(__name__)


def ensure_admin_user() -> None:
    """Создать админа из настроек, если задан и ещё не существует."""
    email = settings.admin_email
    password = settings.admin_password
    if not email or not password:
        return

    with SessionLocal() as session:
        existing = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("Bootstrap admin %s already exists, skipping", email)
            return

        admin = User(
            email=email,
            hashed_password=get_password_hash(password),
            name="Admin",
            role=UserRole.ADMIN,
        )
        session.add(admin)
        session.commit()
        logger.info("Bootstrap admin %s created", email)
