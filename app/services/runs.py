"""Бизнес-логика управления ранами."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Run, RunStatus, User, UserRole
from app.services.experiments import get_experiment_for_user


def create_run(session: Session, user: User, experiment_id: int) -> Run:
    """Создать ран в эксперименте пользователя."""
    get_experiment_for_user(session, user, experiment_id)
    run = Run(experiment_id=experiment_id)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def list_runs_for_experiment(session: Session, user: User, experiment_id: int) -> List[Run]:
    """Список ранов внутри эксперимента (с проверкой доступа)."""
    get_experiment_for_user(session, user, experiment_id)
    stmt = select(Run).where(Run.experiment_id == experiment_id).order_by(Run.id)
    return list(session.execute(stmt).scalars())


def get_run_for_user(session: Session, user: User, run_id: int) -> Run:
    """Получить ран и проверить, что пользователь имеет к нему доступ."""
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )
    if user.role != UserRole.ADMIN and run.experiment.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this run",
        )
    return run


def update_run_status(
    session: Session, user: User, run_id: int, new_status: RunStatus
) -> Run:
    """Изменить статус рана. Переход возможен только из RUNNING."""
    run = get_run_for_user(session, user, run_id)
    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run already in terminal status {run.status.value}",
        )
    if new_status == RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition run back to RUNNING",
        )
    run.status = new_status
    run.ended_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(run)
    return run


def delete_run(session: Session, user: User, run_id: int) -> None:
    """Удалить ран (каскадно удаляются его метрики и параметры)."""
    run = get_run_for_user(session, user, run_id)
    session.delete(run)
    session.commit()
