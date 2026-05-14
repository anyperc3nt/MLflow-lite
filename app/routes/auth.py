"""Роуты аутентификации: signup, login, me."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token, get_password_hash, verify_password
from app.core.db import get_session
from app.models import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRead,
    summary="Регистрация нового пользователя",
)
def signup(
    payload: UserCreate,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        name=payload.name,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {payload.email} already exists",
        ) from exc
    session.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Вход и получение JWT")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
) -> Token:
    user = session.execute(select(User).where(User.email == form_data.username)).scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.email)
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Текущий пользователь по токену",
)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
