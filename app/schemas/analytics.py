"""Pydantic-схемы аналитики."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class OptimizeMode(str, Enum):
    """Направление оптимизации метрики."""

    MAX = "max"
    MIN = "min"


class LeaderboardEntry(BaseModel):
    """Строка leaderboard."""

    run_id: int
    metric_key: str
    value: float
    step: int


class CompareRequest(BaseModel):
    """Запрос на сравнение нескольких ранов."""

    run_ids: List[int] = Field(min_length=2, max_length=20)


class CompareCell(BaseModel):
    """Значение параметра/метрики у конкретного рана."""

    value: Optional[str] = None


class CompareResponse(BaseModel):
    """Сводная таблица сравнения ранов."""

    run_ids: List[int]
    params: Dict[str, Dict[int, Optional[str]]]
    metrics: Dict[str, Dict[int, Optional[float]]]


class ParetoPoint(BaseModel):
    """Точка Парето-фронта."""

    run_id: int
    x: float
    y: float
