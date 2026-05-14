"""Pydantic-схемы для пользователей и токенов."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole


class UserCreate(BaseModel):
    """Тело запроса на регистрацию."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class UserRead(BaseModel):
    """Публичное представление пользователя."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    """JWT-токен в стандартном для OAuth2 формате."""

    access_token: str
    token_type: str = "bearer"
