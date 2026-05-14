"""Pydantic-схемы для экспериментов."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ExperimentCreate(BaseModel):
    """Тело запроса на создание эксперимента."""

    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class ExperimentUpdate(BaseModel):
    """Частичное обновление эксперимента."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class ExperimentRead(BaseModel):
    """Публичное представление эксперимента."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
