"""Конфигурация приложения, читается из переменных окружения / .env."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./mlflow_lite.db"
    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Опциональный bootstrap-админ. Если оба поля заполнены, при старте
    # сервиса создаётся пользователь с этим email и ролью ADMIN
    # (только если такого пользователя ещё нет в БД).
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None


settings = Settings()
