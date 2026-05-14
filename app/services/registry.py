"""Бизнес-логика реестра моделей.

Инвариант: у одной модели не может быть более одной версии в стадии
PRODUCTION. Переход в PRODUCTION атомарно архивирует текущую Production.
"""
from __future__ import annotations

from typing import List

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ModelStage, ModelVersion, RegisteredModel, Run, User
from app.services.runs import get_run_for_user


def register_model(
    session: Session, owner: User, name: str, description: str | None
) -> RegisteredModel:
    """Создать новую зарегистрированную модель."""
    model = RegisteredModel(name=name, description=description, owner_id=owner.id)
    session.add(model)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model with name '{name}' already exists",
        ) from exc
    session.refresh(model)
    return model


def _get_model_by_name(session: Session, name: str) -> RegisteredModel:
    model = session.execute(
        select(RegisteredModel).where(RegisteredModel.name == name)
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{name}' not found",
        )
    return model


def list_models(session: Session) -> List[RegisteredModel]:
    return list(
        session.execute(
            select(RegisteredModel).order_by(RegisteredModel.id)
        ).scalars()
    )


def get_model(session: Session, name: str) -> RegisteredModel:
    return _get_model_by_name(session, name)


def register_version(
    session: Session, user: User, name: str, run_id: int
) -> ModelVersion:
    """Зарегистрировать новую версию модели из существующего рана."""
    model = _get_model_by_name(session, name)
    # Проверяем доступ пользователя к рану (повторно используем существующий хелпер).
    get_run_for_user(session, user, run_id)

    next_version = (
        session.execute(
            select(func.coalesce(func.max(ModelVersion.version), 0)).where(
                ModelVersion.registered_model_id == model.id
            )
        ).scalar_one()
        + 1
    )
    version = ModelVersion(
        registered_model_id=model.id,
        version=next_version,
        run_id=run_id,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


def set_stage(
    session: Session, name: str, version_number: int, new_stage: ModelStage
) -> ModelVersion:
    """Изменить стадию версии. При переходе в Production текущую Production
    в той же модели атомарно переводим в Archived.
    """
    model = _get_model_by_name(session, name)
    target = session.execute(
        select(ModelVersion).where(
            ModelVersion.registered_model_id == model.id,
            ModelVersion.version == version_number,
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} of model '{name}' not found",
        )

    if new_stage == ModelStage.PRODUCTION:
        existing = session.execute(
            select(ModelVersion).where(
                ModelVersion.registered_model_id == model.id,
                ModelVersion.stage == ModelStage.PRODUCTION,
                ModelVersion.id != target.id,
            )
        ).scalars().all()
        for prev in existing:
            prev.stage = ModelStage.ARCHIVED

    target.stage = new_stage
    session.commit()
    session.refresh(target)
    return target


def list_versions(session: Session, name: str) -> List[ModelVersion]:
    model = _get_model_by_name(session, name)
    return list(
        session.execute(
            select(ModelVersion)
            .where(ModelVersion.registered_model_id == model.id)
            .order_by(ModelVersion.version)
        ).scalars()
    )
