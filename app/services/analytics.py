"""Аналитика по ранам: leaderboard, compare runs, Pareto-фронт.

Метрика — time-series по `step`, поэтому везде, где нужно "значение метрики
у рана", берётся точка с максимальным `step` (через коррелированный
подзапрос, чтобы не загружать всю историю в Python).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Experiment, Metric, Param, Run, User, UserRole
from app.schemas.analytics import (
    CompareResponse,
    LeaderboardEntry,
    OptimizeMode,
    ParetoPoint,
)
from app.services.experiments import get_experiment_for_user


def _last_metric_subquery(metric_key: str):
    """Подзапрос: для каждого run_id максимальный step заданной метрики."""
    return (
        select(Metric.run_id, func.max(Metric.step).label("max_step"))
        .where(Metric.key == metric_key)
        .group_by(Metric.run_id)
        .subquery()
    )


def leaderboard(
    session: Session,
    user: User,
    experiment_id: int,
    metric_key: str,
    top: int,
    mode: OptimizeMode,
) -> List[LeaderboardEntry]:
    """Top-N ранов эксперимента по последнему значению метрики."""
    get_experiment_for_user(session, user, experiment_id)
    if top <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="`top` must be positive",
        )

    last = _last_metric_subquery(metric_key)
    stmt = (
        select(Metric.run_id, Metric.key, Metric.value, Metric.step)
        .join(Run, Run.id == Metric.run_id)
        .join(last, (last.c.run_id == Metric.run_id) & (last.c.max_step == Metric.step))
        .where(Run.experiment_id == experiment_id, Metric.key == metric_key)
        .order_by(Metric.value.desc() if mode == OptimizeMode.MAX else Metric.value.asc())
        .limit(top)
    )
    rows = session.execute(stmt).all()
    return [
        LeaderboardEntry(run_id=row.run_id, metric_key=row.key, value=row.value, step=row.step)
        for row in rows
    ]


def _last_metrics_for_runs(session: Session, run_ids: List[int]) -> Dict[Tuple[int, str], float]:
    """Для каждого (run_id, metric_key) вернуть значение на максимальном step."""
    if not run_ids:
        return {}
    last_step = (
        select(Metric.run_id, Metric.key, func.max(Metric.step).label("max_step"))
        .where(Metric.run_id.in_(run_ids))
        .group_by(Metric.run_id, Metric.key)
        .subquery()
    )
    stmt = (
        select(Metric.run_id, Metric.key, Metric.value)
        .join(
            last_step,
            (last_step.c.run_id == Metric.run_id)
            & (last_step.c.key == Metric.key)
            & (last_step.c.max_step == Metric.step),
        )
        .where(Metric.run_id.in_(run_ids))
    )
    return {(row.run_id, row.key): row.value for row in session.execute(stmt).all()}


def compare_runs(session: Session, user: User, run_ids: List[int]) -> CompareResponse:
    """Сравнить параметры и (последние значения) метрик у нескольких ранов."""
    unique_ids = list(dict.fromkeys(run_ids))
    if len(unique_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 distinct run_ids are required",
        )

    runs = (
        session.execute(select(Run).where(Run.id.in_(unique_ids))).scalars().all()
    )
    found_ids = {run.id for run in runs}
    missing = [rid for rid in unique_ids if rid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runs not found: {missing}",
        )

    if user.role != UserRole.ADMIN:
        owners = {
            row.id: row.owner_id
            for row in session.execute(
                select(Experiment.id, Experiment.owner_id).where(
                    Experiment.id.in_({run.experiment_id for run in runs})
                )
            ).all()
        }
        for run in runs:
            if owners.get(run.experiment_id) != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No access to run {run.id}",
                )

    params_rows = session.execute(
        select(Param.run_id, Param.key, Param.value).where(Param.run_id.in_(unique_ids))
    ).all()
    params: Dict[str, Dict[int, Optional[str]]] = {}
    for run_id, key, value in params_rows:
        params.setdefault(key, {rid: None for rid in unique_ids})[run_id] = value

    last_metrics = _last_metrics_for_runs(session, unique_ids)
    metrics: Dict[str, Dict[int, Optional[float]]] = {}
    for (run_id, key), value in last_metrics.items():
        metrics.setdefault(key, {rid: None for rid in unique_ids})[run_id] = value

    return CompareResponse(run_ids=unique_ids, params=params, metrics=metrics)


def _pareto_front(
    points: List[Tuple[int, float, float]],
    x_mode: OptimizeMode,
    y_mode: OptimizeMode,
) -> List[Tuple[int, float, float]]:
    """Парето-фронт для двумерных точек.

    Алгоритм O(n log n): нормируем оба критерия "на максимизацию" умножением
    на -1 при необходимости, сортируем по x убыв., затем сканируем
    с поддержкой текущего максимума y. Точка попадает на фронт, если её y
    строго больше любого ранее увиденного y.
    """
    if not points:
        return []
    sx = 1.0 if x_mode == OptimizeMode.MAX else -1.0
    sy = 1.0 if y_mode == OptimizeMode.MAX else -1.0
    transformed = [(rid, sx * x, sy * y) for rid, x, y in points]
    transformed.sort(key=lambda t: (-t[1], -t[2]))

    front: List[Tuple[int, float, float]] = []
    best_y = float("-inf")
    for rid, tx, ty in transformed:
        if ty > best_y:
            front.append((rid, tx / sx, ty / sy))
            best_y = ty
    return front


def pareto(
    session: Session,
    user: User,
    experiment_id: int,
    x_key: str,
    y_key: str,
    x_mode: OptimizeMode,
    y_mode: OptimizeMode,
) -> List[ParetoPoint]:
    """Парето-фронт по двум метрикам внутри эксперимента."""
    get_experiment_for_user(session, user, experiment_id)
    if x_key == y_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x and y metrics must be different",
        )

    run_ids = [
        row[0]
        for row in session.execute(
            select(Run.id).where(Run.experiment_id == experiment_id)
        ).all()
    ]
    last_metrics = _last_metrics_for_runs(session, run_ids)
    points: List[Tuple[int, float, float]] = []
    for rid in run_ids:
        x_val = last_metrics.get((rid, x_key))
        y_val = last_metrics.get((rid, y_key))
        if x_val is not None and y_val is not None:
            points.append((rid, x_val, y_val))

    front = _pareto_front(points, x_mode, y_mode)
    return [ParetoPoint(run_id=rid, x=x, y=y) for rid, x, y in front]
