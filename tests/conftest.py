"""Общие фикстуры pytest: изолированная SQLite-БД и TestClient с override."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Импорт пакета моделей нужен, чтобы Base.metadata знал обо всех таблицах при create_all.
import app.models as _models  # noqa: F401  pylint: disable=unused-import

from app.core.db import Base, get_session
from app.main import app


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Путь к изолированному файлу SQLite на каждый тест."""
    return tmp_path / "test.db"


@pytest.fixture()
def engine(db_path: Path):
    """Свежий engine на файл со StaticPool, чтобы все сессии в тесте
    работали через одно подключение и видели свежие коммиты.
    """
    url = f"sqlite:///{db_path}"
    eng = create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture()
def db_session(session_factory) -> Iterator[Session]:
    """ORM-сессия для unit-тестов, работающих с БД напрямую."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory) -> Iterator[TestClient]:
    """TestClient с переопределённой зависимостью get_session."""

    def _override_get_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def register_user(
    client: TestClient,
    email: str = "user@example.com",
    password: str = "password123",
    name: str = "Test User",
) -> dict:
    """Хелпер: создать пользователя через POST /auth/signup."""
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_user(
    client: TestClient,
    email: str = "user@example.com",
    password: str = "password123",
) -> str:
    """Хелпер: залогиниться через POST /auth/login, вернуть JWT."""
    response = client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_token(client: TestClient) -> str:
    """Фикстура: зарегистрированный пользователь + готовый JWT-токен."""
    register_user(client)
    return login_user(client)


@pytest.fixture()
def admin_token(client: TestClient, session_factory) -> str:
    """Фикстура: пользователь с ролью ADMIN + готовый JWT.

    Создаётся напрямую через ORM (минуя /auth/signup), чтобы атомарно
    выставить роль ADMIN и не зависеть от двух раздельных HTTP-вызовов.
    """
    from app.auth.security import get_password_hash
    from app.models import User, UserRole

    session = session_factory()
    try:
        user = User(
            email="admin@example.com",
            hashed_password=get_password_hash("password123"),
            name="Admin",
            role=UserRole.ADMIN,
        )
        session.add(user)
        session.commit()
    finally:
        session.close()
    return login_user(client, email="admin@example.com")
