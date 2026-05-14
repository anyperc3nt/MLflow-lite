"""Модели реестра моделей: RegisteredModel и ModelVersion."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelStage(str, enum.Enum):
    """Стадии жизненного цикла версии модели."""

    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class RegisteredModel(Base):
    """Именованная модель — контейнер для версий."""

    __tablename__ = "registered_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    versions: Mapped[List["ModelVersion"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


class ModelVersion(Base):
    """Версия модели, привязанная к рану."""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "registered_model_id", "version", name="uq_model_versions_model_version"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registered_model_id: Mapped[int] = mapped_column(
        ForeignKey("registered_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[ModelStage] = mapped_column(
        Enum(ModelStage, name="model_stage"),
        nullable=False,
        default=ModelStage.NONE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    model: Mapped["RegisteredModel"] = relationship(back_populates="versions")
