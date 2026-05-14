"""Pydantic-схемы реестра моделей."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import ModelStage


class RegisteredModelCreate(BaseModel):
    """Регистрация нового имени модели."""

    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class RegisteredModelRead(BaseModel):
    """Публичное представление зарегистрированной модели."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime


class ModelVersionCreate(BaseModel):
    """Регистрация новой версии модели из существующего рана."""

    run_id: int


class ModelVersionRead(BaseModel):
    """Публичное представление версии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    registered_model_id: int
    version: int
    run_id: int
    stage: ModelStage
    created_at: datetime


class StageUpdate(BaseModel):
    """Запрос на смену стадии версии."""

    stage: ModelStage


class RegisteredModelDetail(RegisteredModelRead):
    """Модель + список её версий."""

    versions: List[ModelVersionRead] = []
