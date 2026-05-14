"""Роуты CRUD для ранов."""
from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.schemas.run import RunRead, RunStatusUpdate
from app.services import runs as svc

router = APIRouter(tags=["Раны"])


@router.post(
    "/experiments/{experiment_id}/runs",
    status_code=status.HTTP_201_CREATED,
    response_model=RunRead,
    summary="Создать ран в эксперименте",
)
def create(
    experiment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.create_run(session, current_user, experiment_id)


@router.get(
    "/experiments/{experiment_id}/runs",
    response_model=List[RunRead],
    summary="Список ранов эксперимента",
)
def list_runs(
    experiment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.list_runs_for_experiment(session, current_user, experiment_id)


@router.get(
    "/runs/{run_id}",
    response_model=RunRead,
    summary="Получить ран по id",
)
def get_one(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.get_run_for_user(session, current_user, run_id)


@router.patch(
    "/runs/{run_id}",
    response_model=RunRead,
    summary="Завершить ран (FINISHED / FAILED)",
)
def update_status(
    run_id: int,
    payload: RunStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.update_run_status(session, current_user, run_id, payload.status)


@router.delete(
    "/runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить ран",
)
def delete(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    svc.delete_run(session, current_user, run_id)
