"""Роуты реестра моделей."""
from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_admin
from app.core.db import get_session
from app.models import User
from app.schemas.registry import (
    ModelVersionCreate,
    ModelVersionRead,
    RegisteredModelCreate,
    RegisteredModelDetail,
    RegisteredModelRead,
    StageUpdate,
)
from app.services import registry as svc

router = APIRouter(prefix="/models", tags=["Реестр моделей"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisteredModelRead,
    summary="Зарегистрировать новую модель",
)
def create_model(
    payload: RegisteredModelCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.register_model(session, current_user, payload.name, payload.description)


@router.get(
    "",
    response_model=List[RegisteredModelRead],
    summary="Список зарегистрированных моделей",
)
def list_models(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.list_models(session)


@router.get(
    "/{name}",
    response_model=RegisteredModelDetail,
    summary="Получить модель и её версии",
)
def get_model(
    name: str,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    model = svc.get_model(session, name)
    versions = svc.list_versions(session, name)
    return RegisteredModelDetail(
        id=model.id,
        name=model.name,
        description=model.description,
        owner_id=model.owner_id,
        created_at=model.created_at,
        versions=[ModelVersionRead.model_validate(v) for v in versions],
    )


@router.post(
    "/{name}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=ModelVersionRead,
    summary="Зарегистрировать новую версию модели из рана",
)
def create_version(
    name: str,
    payload: ModelVersionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.register_version(session, current_user, name, payload.run_id)


@router.patch(
    "/{name}/versions/{version}/stage",
    response_model=ModelVersionRead,
    summary="Изменить стадию версии (только admin)",
)
def update_stage(
    name: str,
    version: int,
    payload: StageUpdate,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
):
    return svc.set_stage(session, name, version, payload.stage)
