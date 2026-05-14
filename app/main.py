"""Точка входа FastAPI-приложения MLflow-lite."""
from fastapi import FastAPI

from app.routes import auth as auth_routes

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
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)


app.include_router(auth_routes.router)


@app.get("/health", tags=["Служебное"], summary="Проверка работоспособности")
def health() -> dict:
    """Простой liveness-эндпоинт."""
    return {"status": "ok"}
