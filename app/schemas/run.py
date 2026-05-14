"""Pydantic-схемы для ранов."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import RunStatus


class RunCreate(BaseModel):
    """Тело запроса на создание рана — пустое, всё определяется experiment_id из URL."""


class RunStatusUpdate(BaseModel):
    """Изменение статуса рана: FINISHED или FAILED."""

    status: RunStatus


class RunRead(BaseModel):
    """Публичное представление рана."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    status: RunStatus
    started_at: datetime
    ended_at: Optional[datetime]
