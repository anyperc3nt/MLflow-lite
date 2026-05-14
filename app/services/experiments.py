"""Бизнес-логика управления экспериментами."""
from __future__ import annotations

from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Experiment, User, UserRole
from app.schemas.experiment import ExperimentCreate, ExperimentUpdate


def create_experiment(session: Session, owner: User, payload: ExperimentCreate) -> Experiment:
    """Создать эксперимент с владельцем `owner`."""
    experiment = Experiment(
        name=payload.name, description=payload.description, owner_id=owner.id
    )
    session.add(experiment)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Experiment with name '{payload.name}' already exists for this user",
        ) from exc
    session.refresh(experiment)
    return experiment


def list_experiments(session: Session, user: User) -> List[Experiment]:
    """Список экспериментов, видимых пользователю.

    Обычный пользователь видит только свои; админ — все.
    """
    stmt = select(Experiment).order_by(Experiment.id)
    if user.role != UserRole.ADMIN:
        stmt = stmt.where(Experiment.owner_id == user.id)
    return list(session.execute(stmt).scalars())


def get_experiment_for_user(session: Session, user: User, experiment_id: int) -> Experiment:
    """Вернуть эксперимент, если он принадлежит пользователю (или пользователь admin).

    Поднимает 404, если эксперимента нет, и 403, если он не доступен пользователю.
    """
    experiment = session.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )
    if user.role != UserRole.ADMIN and experiment.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this experiment",
        )
    return experiment


def update_experiment(
    session: Session, user: User, experiment_id: int, payload: ExperimentUpdate
) -> Experiment:
    """Обновить эксперимент. Только владелец или admin."""
    experiment = get_experiment_for_user(session, user, experiment_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(experiment, field, value)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment with this name already exists for this user",
        ) from exc
    session.refresh(experiment)
    return experiment


def delete_experiment(session: Session, user: User, experiment_id: int) -> None:
    """Удалить эксперимент (каскадно удаляются все его раны)."""
    experiment = get_experiment_for_user(session, user, experiment_id)
    session.delete(experiment)
    session.commit()
