"""Точка входа FastAPI-приложения MLflow-lite."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.bootstrap import ensure_admin_user
from app.routes import analytics as analytics_routes
from app.routes import auth as auth_routes
from app.routes import experiments as experiments_routes
from app.routes import logging as logging_routes
from app.routes import registry as registry_routes
from app.routes import runs as runs_routes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown-хуки приложения."""
    ensure_admin_user()
    yield


app = FastAPI(
    title="MLflow-lite",
    description=(
        "Учебный REST-сервис для трекинга ML-экспериментов и лёгкого реестра "
        "моделей — упрощённое подмножество MLflow."
    ),
    version="0.1.0",
    contact={
        "name": "Цифровая кафедра МФТИ",
        "url": "https://mipt.ru",
    },
    lifespan=lifespan,
)


app.include_router(auth_routes.router)
app.include_router(experiments_routes.router)
app.include_router(runs_routes.router)
app.include_router(logging_routes.router)
app.include_router(analytics_routes.router)
app.include_router(registry_routes.router)


@app.get("/health", tags=["Служебное"], summary="Проверка работоспособности")
def health() -> dict:
    """Простой liveness-эндпоинт."""
    return {"status": "ok"}
