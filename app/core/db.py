"""SQLAlchemy engine, sessionmaker и FastAPI-зависимость для сессии."""
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _connection_record):  # pragma: no cover
    """Включаем enforcement внешних ключей для каждого подключения SQLite."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI-зависимость, выдающая SQLAlchemy-сессию."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
