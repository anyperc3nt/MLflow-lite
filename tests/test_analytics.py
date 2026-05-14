"""Тесты аналитики: unit на Pareto + integration на роуты."""
from app.schemas.analytics import OptimizeMode
from app.services.analytics import _pareto_front
from tests.conftest import auth_headers


# --------------------------- unit-тесты Pareto ----------------------------


def test_pareto_empty():
    assert _pareto_front([], OptimizeMode.MAX, OptimizeMode.MAX) == []


def test_pareto_max_max_all_dominated_except_one():
    # Точка (1, 5.0, 5.0) доминирует все остальные.
    points = [(1, 5.0, 5.0), (2, 1.0, 1.0), (3, 3.0, 2.0)]
    front = _pareto_front(points, OptimizeMode.MAX, OptimizeMode.MAX)
    assert [p[0] for p in front] == [1]


def test_pareto_max_max_classic_front():
    # (1, 5, 1), (2, 3, 3), (3, 1, 5) — все на фронте; (4, 2, 2) — доминируема (2).
    points = [(1, 5.0, 1.0), (2, 3.0, 3.0), (3, 1.0, 5.0), (4, 2.0, 2.0)]
    front = _pareto_front(points, OptimizeMode.MAX, OptimizeMode.MAX)
    assert sorted(p[0] for p in front) == [1, 2, 3]


def test_pareto_min_min_inverts_axes():
    # Минимизируем оба: лучшая точка — (3, 1, 1).
    points = [(1, 5.0, 5.0), (2, 4.0, 6.0), (3, 1.0, 1.0)]
    front = _pareto_front(points, OptimizeMode.MIN, OptimizeMode.MIN)
    assert [p[0] for p in front] == [3]


def test_pareto_mixed_modes_min_x_max_y():
    # Минимизируем x, максимизируем y. На фронте: (1, 1, 10), (2, 2, 12).
    # (3, 1, 5) доминируется точкой (1, 1, 10).
    points = [(1, 1.0, 10.0), (2, 2.0, 12.0), (3, 1.0, 5.0), (4, 3.0, 11.0)]
    front = _pareto_front(points, OptimizeMode.MIN, OptimizeMode.MAX)
    ids = sorted(p[0] for p in front)
    assert ids == [1, 2]


# --------------------------- integration-тесты роутов ---------------------


def _setup_runs(client, token, exp_name="exp"):
    exp = client.post(
        "/experiments", json={"name": exp_name}, headers=auth_headers(token)
    ).json()
    runs = []
    for _ in range(3):
        runs.append(
            client.post(
                f"/experiments/{exp['id']}/runs", headers=auth_headers(token)
            ).json()
        )
    return exp, runs


def _log_metric_series(client, token, run_id, key, values):
    client.post(
        f"/runs/{run_id}/metrics",
        json={
            "metrics": [
                {"key": key, "value": v, "step": i} for i, v in enumerate(values)
            ]
        },
        headers=auth_headers(token),
    )


def test_leaderboard_returns_last_step_value_sorted(client, user_token):
    exp, runs = _setup_runs(client, user_token)
    # У каждого рана последняя точка — её и нужно учитывать.
    _log_metric_series(client, user_token, runs[0]["id"], "val_loss", [1.0, 0.5, 0.3])
    _log_metric_series(client, user_token, runs[1]["id"], "val_loss", [0.9, 0.7, 0.6])
    _log_metric_series(client, user_token, runs[2]["id"], "val_loss", [1.5, 0.2, 0.1])

    response = client.get(
        f"/experiments/{exp['id']}/leaderboard",
        params={"metric": "val_loss", "top": 3, "mode": "min"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 200
    body = response.json()
    # Сортировка по value asc: 0.1 (runs[2]), 0.3 (runs[0]), 0.6 (runs[1]).
    assert [row["run_id"] for row in body] == [runs[2]["id"], runs[0]["id"], runs[1]["id"]]
    assert [row["value"] for row in body] == [0.1, 0.3, 0.6]
    # Step должен быть последним.
    assert all(row["step"] == 2 for row in body)


def test_leaderboard_top_limits_rows(client, user_token):
    exp, runs = _setup_runs(client, user_token)
    for run, val in zip(runs, [0.5, 0.4, 0.3]):
        _log_metric_series(client, user_token, run["id"], "acc", [val])

    response = client.get(
        f"/experiments/{exp['id']}/leaderboard",
        params={"metric": "acc", "top": 2, "mode": "max"},
        headers=auth_headers(user_token),
    )
    body = response.json()
    assert len(body) == 2
    assert body[0]["value"] == 0.5


def test_compare_requires_at_least_two_runs(client, user_token):
    exp, runs = _setup_runs(client, user_token)
    response = client.post(
        "/runs/compare",
        json={"run_ids": [runs[0]["id"]]},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 422
    _ = exp


def test_pareto_endpoint_returns_front(client, user_token):
    exp, runs = _setup_runs(client, user_token)
    # (loss, size) — минимизируем loss, минимизируем size.
    pairs = [(0.5, 100.0), (0.3, 200.0), (0.7, 50.0), (0.4, 150.0)]
    for run, (loss, size) in zip(runs + [runs[0]], pairs[: len(runs)]):
        _log_metric_series(client, user_token, run["id"], "loss", [loss])
        _log_metric_series(client, user_token, run["id"], "size", [size])

    response = client.get(
        f"/experiments/{exp['id']}/pareto",
        params={"x": "loss", "y": "size", "x_mode": "min", "y_mode": "min"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 200
    front = response.json()
    # Все три точки попадают на фронт: ни одна не доминирует другую.
    assert len(front) == 3


def test_pareto_rejects_same_x_y(client, user_token):
    exp, _ = _setup_runs(client, user_token)
    response = client.get(
        f"/experiments/{exp['id']}/pareto",
        params={"x": "loss", "y": "loss"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 400
