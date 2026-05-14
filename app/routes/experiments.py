"""Роуты CRUD для экспериментов."""
from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.schemas.experiment import ExperimentCreate, ExperimentRead, ExperimentUpdate
from app.services import experiments as svc

router = APIRouter(prefix="/experiments", tags=["Эксперименты"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ExperimentRead,
    summary="Создать эксперимент",
)
def create(
    payload: ExperimentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.create_experiment(session, current_user, payload)


@router.get(
    "",
    response_model=List[ExperimentRead],
    summary="Список экспериментов пользователя",
)
def list_all(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.list_experiments(session, current_user)


@router.get(
    "/{experiment_id}",
    response_model=ExperimentRead,
    summary="Получить эксперимент по id",
)
def get_one(
    experiment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.get_experiment_for_user(session, current_user, experiment_id)


@router.patch(
    "/{experiment_id}",
    response_model=ExperimentRead,
    summary="Обновить эксперимент",
)
def update(
    experiment_id: int,
    payload: ExperimentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.update_experiment(session, current_user, experiment_id, payload)


@router.delete(
    "/{experiment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить эксперимент",
)
def delete(
    experiment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    svc.delete_experiment(session, current_user, experiment_id)
