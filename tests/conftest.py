"""Общие фикстуры pytest: изолированная SQLite-БД и TestClient с override."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base, get_session
from app.main import app

# Импорт моделей нужен, чтобы Base.metadata знал обо всех таблицах при create_all.
from app.models import models as _models  # noqa: F401  pylint: disable=unused-import


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Путь к изолированному файлу SQLite на каждый тест."""
    return tmp_path / "test.db"


@pytest.fixture()
def engine(db_path: Path):
    """Свежий engine на файл, схема создаётся через Base.metadata.create_all."""
    url = f"sqlite:///{db_path}"
    eng = create_engine(url, connect_args={"check_same_thread": False}, future=True)
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
