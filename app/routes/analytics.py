"""Роуты аналитики: leaderboard, compare, pareto."""
from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.schemas.analytics import (
    CompareRequest,
    CompareResponse,
    LeaderboardEntry,
    OptimizeMode,
    ParetoPoint,
)
from app.services import analytics as svc

router = APIRouter(tags=["Аналитика"])


@router.get(
    "/experiments/{experiment_id}/leaderboard",
    response_model=List[LeaderboardEntry],
    summary="Top-N ранов по последнему значению метрики",
)
def leaderboard(
    experiment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    metric: str = Query(..., min_length=1, max_length=250),
    top: int = Query(default=10, ge=1, le=100),
    mode: OptimizeMode = Query(default=OptimizeMode.MAX),
):
    return svc.leaderboard(session, current_user, experiment_id, metric, top, mode)


@router.post(
    "/runs/compare",
    response_model=CompareResponse,
    summary="Сравнить параметры и последние метрики нескольких ранов",
)
def compare(
    payload: CompareRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.compare_runs(session, current_user, payload.run_ids)


@router.get(
    "/experiments/{experiment_id}/pareto",
    response_model=List[ParetoPoint],
    summary="Парето-фронт по двум метрикам",
)
def pareto(
    experiment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    x: str = Query(..., min_length=1, max_length=250),
    y: str = Query(..., min_length=1, max_length=250),
    x_mode: OptimizeMode = Query(default=OptimizeMode.MAX),
    y_mode: OptimizeMode = Query(default=OptimizeMode.MAX),
):
    return svc.pareto(session, current_user, experiment_id, x, y, x_mode, y_mode)
