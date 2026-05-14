# Архитектурные решения

Этот документ объясняет, какие решения были приняты по ходу разработки,
чем они отличаются от референсного `fastapi-taskman` из лекций, и почему.

## Схема данных

```text
users  1 --- N  experiments  1 --- N  runs  1 --- N  params
                                       \
                                        1 --- N  metrics  (time-series по step)

registered_models  1 --- N  model_versions  N --- 1  runs
```

Все «дочерние» сущности удаляются каскадно (`ON DELETE CASCADE` на уровне
SQL плюс `cascade="all, delete-orphan"` в ORM-relationship), за
исключением `model_versions -> runs`, где стоит `RESTRICT` — нельзя
удалить ран, на который ссылается зарегистрированная версия модели.

Ключевые инварианты на уровне БД:

- `UniqueConstraint(owner_id, name)` на `experiments` — нельзя завести
  у одного пользователя два эксперимента с одним именем.
- `UniqueConstraint(run_id, key)` на `params` — параметр логируется
  один раз за ран.
- `UniqueConstraint(run_id, key, step)` на `metrics` — для каждой
  точки time-series ровно одно значение (используется для upsert).
- `UniqueConstraint(registered_model_id, version)` на `model_versions`
  — версии нумеруются последовательно внутри модели.

## Чем отличается от fastapi-taskman из лекций

Референс использует `sqlmodel`, который смешивает Pydantic-схемы и
ORM-таблицы в одном классе. На 7 таблицах и сервисном слое это
становится неудобным. В этом проекте:

1. **SQLAlchemy 2.0 ORM с `Mapped[...]`** — таблицы (`app/models/`) и
   Pydantic-схемы (`app/schemas/`) изолированы. Это даёт чистые типы
   на ответах API и упрощает миграции Alembic.
2. **Сервисный слой `app/services/`** — вся бизнес-логика лежит здесь;
   роутеры тонкие и легко покрываются интеграционными тестами, а
   сервисы — юнитами без HTTP (см. `_pareto_front`).
3. **Метрики как time-series** с upsert по `(run_id, key, step)` через
   `sqlalchemy.dialects.sqlite.insert(...).on_conflict_do_update`.
4. **Инвариант Production** проверяется атомарно в одной транзакции:
   при `set_stage(..., PRODUCTION)` сервис в той же сессии переводит
   текущую Production-версию в Archived. Это правильнее, чем
   контролировать только частичным уникальным индексом — даёт
   осмысленное переходное состояние.

## Бизнес-задача: аналитика

Это часть, где «не CRUD». Три алгоритма:

### Leaderboard

`GET /experiments/{id}/leaderboard?metric=...&top=N&mode=max|min`

Метрика — time-series по step. Чтобы получить «текущее значение
метрики у рана», нужно взять точку с максимальным step. Делаем это
одним SQL через коррелированный подзапрос:

```python
last = (
    select(Metric.run_id, func.max(Metric.step).label("max_step"))
    .where(Metric.key == metric_key)
    .group_by(Metric.run_id)
    .subquery()
)
stmt = (
    select(Metric.run_id, Metric.key, Metric.value, Metric.step)
    .join(Run, Run.id == Metric.run_id)
    .join(last,
          (last.c.run_id == Metric.run_id)
          & (last.c.max_step == Metric.step))
    .where(Run.experiment_id == experiment_id, Metric.key == metric_key)
    .order_by(Metric.value.desc() if mode == OptimizeMode.MAX
              else Metric.value.asc())
    .limit(top)
)
```

Это **тот самый фрагмент, которым можно гордиться в видео**: один
запрос, без выгрузки всей истории в Python, корректно работает на
произвольном количестве точек.

### Compare runs

`POST /runs/compare` с `{"run_ids": [...]}` возвращает таблицу,
объединяющую параметры и последние значения метрик у выбранных ранов.
Внутри — один SQL по `params` и один по подзапросу `max(step)` для
метрик, без N+1.

### Pareto-фронт

`GET /experiments/{id}/pareto?x=...&y=...&x_mode=...&y_mode=...`

Алгоритм O(n log n): нормируем оба критерия на максимизацию (умножаем
на -1 если `MIN`), сортируем по x убыв., сканируем с поддержкой
текущего максимума y. Точка попадает на фронт, если её y строго
больше любого ранее увиденного.

Функция `_pareto_front` написана чистой (без БД) — её юнит-тестируем
напрямую на матричных кейсах (5 unit-тестов в `tests/test_analytics.py`).

## Аутентификация и роли

- bcrypt (`passlib`) для паролей.
- JWT (`PyJWT`) с `sub = email`, `exp`, `iat`.
- Зависимости: `get_current_user` (любой залогиненный),
  `require_admin` (только `UserRole.ADMIN`).
- Admin переводит версии моделей в `Production` и видит/удаляет чужие
  эксперименты. Обычный пользователь — только свои.

## SQLite-специфика

- `PRAGMA foreign_keys=ON` включается на каждое подключение через
  SQLAlchemy event listener (`app/core/db.py`) — без этого SQLite
  игнорирует FK на уровне SQL.
- `render_as_batch=True` для Alembic при `sqlite://` URL —
  стандартное требование для ALTER TABLE миграций под SQLite.
- Upsert метрик через `sqlalchemy.dialects.sqlite.insert(...)
  .on_conflict_do_update(...)` — диалектозависимо, но локализовано
  в одном сервисе.

## Тесты

- Изолированный `test.db` в `tmp_path` на каждый тест через
  переопределение FastAPI-зависимости `get_session` (`tests/conftest.py`).
- 62 теста покрывают:
  - модели и unique-ограничения (8),
  - auth happy/edge (10),
  - experiments CRUD + admin override (9),
  - runs CRUD + lifecycle (8),
  - логирование params/metrics + upsert (7),
  - аналитика — unit на `_pareto_front` + integration на роуты (10),
  - registry + Production-инвариант + admin-only (8),
  - smoke /health и OpenAPI (2).
- Покрытие: **95%** line coverage.
