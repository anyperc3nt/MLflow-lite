"""Роуты логирования параметров и метрик."""
from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.schemas.log import MetricBatch, MetricRead, ParamBatch, ParamRead
from app.services import logging_service as svc

router = APIRouter(tags=["Логирование"])


@router.post(
    "/runs/{run_id}/params",
    status_code=status.HTTP_201_CREATED,
    response_model=List[ParamRead],
    summary="Залогировать гиперпараметры рана",
)
def log_params(
    run_id: int,
    payload: ParamBatch,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.log_params(session, current_user, run_id, payload.params)


@router.post(
    "/runs/{run_id}/metrics",
    status_code=status.HTTP_201_CREATED,
    summary="Залогировать батч точек метрик (upsert по key+step)",
)
def log_metrics(
    run_id: int,
    payload: MetricBatch,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    accepted = svc.log_metrics_batch(session, current_user, run_id, payload.metrics)
    return {"accepted": accepted}


@router.get(
    "/runs/{run_id}/params",
    response_model=List[ParamRead],
    summary="Получить параметры рана",
)
def list_params(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.list_params(session, current_user, run_id)


@router.get(
    "/runs/{run_id}/metrics",
    response_model=List[MetricRead],
    summary="Получить все точки метрик рана",
)
def list_metrics(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.list_metrics(session, current_user, run_id)
