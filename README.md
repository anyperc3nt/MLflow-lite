# MLflow-lite

Учебный REST-сервис для трекинга ML-экспериментов и лёгкого реестра моделей —
упрощённое подмножество MLflow на FastAPI + SQLAlchemy + JWT.

Итоговый проект курса «Разработка Web-приложения на FastAPI» (МФТИ, Цифровая
кафедра).

## Возможности

- Аутентификация по JWT (OAuth2PasswordBearer), роли `user` / `admin`.
- CRUD по экспериментам и ранам, логирование параметров, метрик (со `step`,
  как time-series) и тегов.
- Мини-реестр моделей: регистрация версии из существующего рана и переходы
  стадий `None` / `Staging` / `Production` / `Archived` с инвариантом «не более
  одной Production-версии у модели».
- Аналитика поверх ранов: **leaderboard** (top-N по метрике), **compare runs**
  (diff параметров и метрик), **Pareto-фронт** по двум метрикам.

## Стек

- Python 3.12
- FastAPI, SQLAlchemy 2.0, Alembic
- SQLite (БД создаётся автоматически при первом запуске)
- pytest + TestClient, pylint

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

alembic upgrade head
uvicorn app.main:app --reload
```

Swagger UI: <http://127.0.0.1:8000/docs>.

## Тесты и линт

```bash
pytest --cov=app
pylint app > pylint.txt
```

## Автор

Alex Kuruts, студент Цифровой кафедры МФТИ.
