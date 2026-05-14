# MLflow-lite

Учебный REST-сервис для трекинга ML-экспериментов и лёгкого реестра
моделей — упрощённое подмножество MLflow на FastAPI + SQLAlchemy + JWT.

Итоговый проект курса «Разработка Web-приложения на FastAPI»
(Цифровая кафедра МФТИ).

## Что умеет

- Аутентификация по JWT (OAuth2PasswordBearer), роли `user` и `admin`.
- CRUD по экспериментам и ранам, логирование параметров и метрик
  (со `step`, как time-series). Метрики поддерживают upsert по
  `(run_id, key, step)` — повторная отправка той же точки обновляет
  её значение, что позволяет тренировочным скриптам перезапускаться
  без 409.
- Мини-реестр моделей: регистрация версий из существующего рана,
  переходы стадий `None` / `Staging` / `Production` / `Archived` с
  инвариантом «не более одной Production-версии у модели» —
  атомарный переход в Production архивирует предыдущую.
- Аналитика поверх ранов:
  - **leaderboard** — top-N по последнему значению выбранной метрики;
  - **compare runs** — таблица параметров и последних метрик у
    нескольких ранов;
  - **Pareto-фронт** — недоминируемые раны по двум метрикам
    (любая комбинация `min`/`max`).

## Стек

- Python 3.12
- FastAPI, SQLAlchemy 2.0 (ORM `Mapped[...]`), Alembic
- SQLite (БД создаётся автоматически при первом запуске)
- pytest + TestClient + pytest-cov, pylint

## Структура проекта

```text
app/
  core/                  настройки и SQLAlchemy engine
  auth/                  пароли, JWT, get_current_user, require_admin
  models/                ORM-модели (User, Experiment, Run, Param,
                         Metric, RegisteredModel, ModelVersion)
  schemas/               Pydantic-схемы (Create/Read/Update)
  services/              бизнес-логика (experiments, runs, logging,
                         analytics, registry)
  routes/                FastAPI-роутеры (тонкие)
  main.py                сборка приложения
migrations/              Alembic, миграции 0001_core и 0002_registry
tests/                   pytest + TestClient, 68 тестов
examples/                демо-скрипт + httpx-клиент
```

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

## Демо-скрипт (как это используют на практике)

```bash
pip install -r examples/requirements-demo.txt
# в одном терминале:
uvicorn app.main:app --reload
# в другом:
PYTHONPATH=. python examples/train_demo.py
```

Скрипт делает sweep по `(learning_rate, l2_reg)` на 9 ранов,
логирует параметры и метрики по эпохам, после чего в Swagger можно
посмотреть leaderboard и Pareto-фронт.

Подробнее — в [examples/README.md](examples/README.md).

## Тесты, покрытие и линт

```bash
PYTHONPATH=. pytest --cov=app
PYTHONPATH=. pylint app > pylint.txt
```

Актуальные метрики:

- **62 теста**, все проходят (pytest + TestClient)
- **95% line coverage** (минимум по критерию — 70%)
- **pylint: 10.00/10** (см. `pylint.txt`)

## Соответствие критериям

| Критерий | Покрытие |
|---|---|
| ≥3 связанные таблицы | 7 таблиц с FK-связями и каскадным удалением |
| ≥12 эндпоинтов | **20** эндпоинтов в 5 группах (см. Swagger) |
| Аутентификация и валидация | JWT, OAuth2PasswordBearer, Pydantic |
| Бизнес-задача | 3 алгоритма аналитики + инвариант Production |
| Тесты ≥70% | 62 теста, **95% покрытия** |
| pylint | **10.00/10** |
| Поэтапная git-история | 10 осмысленных коммитов в `main` |

См. также [ARCHITECTURE.md](ARCHITECTURE.md) — обзор решений и
сравнение с референсным `fastapi-taskman` из лекций.

## Автор

Alex Kuruts, студент Цифровой кафедры МФТИ.
