"""ORM-модели MLflow-lite.

Модели сгруппированы в одном файле, чтобы избежать циклических импортов
между взаимно-связанными сущностями (User, Experiment, Run, ...).
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    """Роли пользователей."""

    USER = "user"
    ADMIN = "admin"


class RunStatus(str, enum.Enum):
    """Статусы рана."""

    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class User(Base):
    """Пользователь сервиса."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.USER
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    experiments: Mapped[List["Experiment"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Experiment(Base):
    """ML-эксперимент — контейнер для ранов."""

    __tablename__ = "experiments"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_experiments_owner_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="experiments")
    runs: Mapped[List["Run"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class Run(Base):
    """Отдельный прогон обучения внутри эксперимента."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), nullable=False, default=RunStatus.RUNNING
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment: Mapped["Experiment"] = relationship(back_populates="runs")
    params: Mapped[List["Param"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    metrics: Mapped[List["Metric"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Param(Base):
    """Гиперпараметр рана (логируется один раз)."""

    __tablename__ = "params"
    __table_args__ = (UniqueConstraint("run_id", "key", name="uq_params_run_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(250), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    run: Mapped["Run"] = relationship(back_populates="params")


class Metric(Base):
    """Точка метрики (time-series по step внутри рана)."""

    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("run_id", "key", "step", name="uq_metrics_run_key_step"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    run: Mapped["Run"] = relationship(back_populates="metrics")
