"""Логирование параметров и метрик к ранам.

Метрики поддерживают upsert по (run_id, key, step) — повторная отправка
обновляет значение, что позволяет демо-скрипту перезапускаться без 409.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Metric, Param, Run, RunStatus, User
from app.schemas.log import MetricEntry, ParamLog
from app.services.runs import get_run_for_user


def _ensure_run_active(run: Run) -> None:
    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot log to run in terminal status {run.status.value}",
        )


def log_params(session: Session, user: User, run_id: int, params: List[ParamLog]) -> List[Param]:
    """Залогировать набор параметров. Дубликаты по key вызывают 409."""
    run = get_run_for_user(session, user, run_id)
    _ensure_run_active(run)

    for entry in params:
        session.add(Param(run_id=run.id, key=entry.key, value=entry.value))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more param keys already logged for this run",
        ) from exc

    stmt = select(Param).where(Param.run_id == run.id).order_by(Param.id)
    return list(session.execute(stmt).scalars())


def log_metrics_batch(
    session: Session, user: User, run_id: int, metrics: List[MetricEntry]
) -> int:
    """Залогировать батч метрик с upsert по (run_id, key, step).

    Возвращает количество принятых записей (включая обновлённые).
    """
    run = get_run_for_user(session, user, run_id)
    _ensure_run_active(run)

    now = datetime.now(timezone.utc)
    rows = [
        {
            "run_id": run.id,
            "key": entry.key,
            "value": entry.value,
            "step": entry.step,
            "timestamp": now,
        }
        for entry in metrics
    ]

    # SQLite-specific INSERT ... ON CONFLICT(run_id, key, step) DO UPDATE.
    stmt = sqlite_insert(Metric).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["run_id", "key", "step"],
        set_={"value": stmt.excluded.value, "timestamp": stmt.excluded.timestamp},
    )
    session.execute(stmt)
    session.commit()
    return len(rows)


def list_params(session: Session, user: User, run_id: int) -> List[Param]:
    run = get_run_for_user(session, user, run_id)
    stmt = select(Param).where(Param.run_id == run.id).order_by(Param.id)
    return list(session.execute(stmt).scalars())


def list_metrics(session: Session, user: User, run_id: int) -> List[Metric]:
    run = get_run_for_user(session, user, run_id)
    stmt = (
        select(Metric)
        .where(Metric.run_id == run.id)
        .order_by(Metric.key, Metric.step)
    )
    return list(session.execute(stmt).scalars())
