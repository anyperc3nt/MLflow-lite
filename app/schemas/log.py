"""Pydantic-схемы для логирования параметров и метрик."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ParamLog(BaseModel):
    """Один параметр для логирования."""

    key: str = Field(min_length=1, max_length=250)
    value: str = Field(max_length=500)


class ParamBatch(BaseModel):
    """Батч параметров."""

    params: List[ParamLog] = Field(min_length=1, max_length=200)


class ParamRead(BaseModel):
    """Возвращаемое представление параметра."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str


class MetricEntry(BaseModel):
    """Одна точка метрики."""

    key: str = Field(min_length=1, max_length=250)
    value: float
    step: int = Field(default=0, ge=0)


class MetricBatch(BaseModel):
    """Батч метрик для логирования за один HTTP-запрос."""

    metrics: List[MetricEntry] = Field(min_length=1, max_length=1000)


class MetricRead(BaseModel):
    """Возвращаемое представление метрики."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    value: float
    step: int
