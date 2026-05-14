"""Тесты логирования параметров и метрик."""
from tests.conftest import auth_headers, login_user, register_user


def _setup_run(client, token, exp_name="exp"):
    exp = client.post(
        "/experiments", json={"name": exp_name}, headers=auth_headers(token)
    ).json()
    run = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(token)
    ).json()
    return exp, run


def test_log_params_success(client, user_token):
    _, run = _setup_run(client, user_token)
    response = client.post(
        f"/runs/{run['id']}/params",
        json={"params": [{"key": "lr", "value": "0.01"}, {"key": "depth", "value": "5"}]},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert {p["key"] for p in body} == {"lr", "depth"}


def test_duplicate_param_key_returns_409(client, user_token):
    _, run = _setup_run(client, user_token)
    client.post(
        f"/runs/{run['id']}/params",
        json={"params": [{"key": "lr", "value": "0.01"}]},
        headers=auth_headers(user_token),
    )
    response = client.post(
        f"/runs/{run['id']}/params",
        json={"params": [{"key": "lr", "value": "0.02"}]},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 409


def test_log_metrics_batch_success(client, user_token):
    _, run = _setup_run(client, user_token)
    batch = [
        {"key": "loss", "value": 1.0 - 0.1 * i, "step": i} for i in range(10)
    ]
    response = client.post(
        f"/runs/{run['id']}/metrics",
        json={"metrics": batch},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 201
    assert response.json() == {"accepted": 10}

    listed = client.get(
        f"/runs/{run['id']}/metrics", headers=auth_headers(user_token)
    ).json()
    assert len(listed) == 10
    assert listed[0]["key"] == "loss"
    assert listed[-1]["step"] == 9


def test_metrics_upsert_overwrites_existing_step(client, user_token):
    _, run = _setup_run(client, user_token)
    client.post(
        f"/runs/{run['id']}/metrics",
        json={"metrics": [{"key": "loss", "value": 1.0, "step": 0}]},
        headers=auth_headers(user_token),
    )
    response = client.post(
        f"/runs/{run['id']}/metrics",
        json={"metrics": [{"key": "loss", "value": 0.5, "step": 0}]},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 201

    listed = client.get(
        f"/runs/{run['id']}/metrics", headers=auth_headers(user_token)
    ).json()
    assert len(listed) == 1
    assert listed[0]["value"] == 0.5


def test_cannot_log_to_finished_run(client, user_token):
    _, run = _setup_run(client, user_token)
    client.patch(
        f"/runs/{run['id']}",
        json={"status": "FINISHED"},
        headers=auth_headers(user_token),
    )
    response = client.post(
        f"/runs/{run['id']}/metrics",
        json={"metrics": [{"key": "loss", "value": 0.1, "step": 0}]},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 409


def test_cannot_log_to_foreign_run(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    _, run = _setup_run(client, token_a, exp_name="exp-a")

    response = client.post(
        f"/runs/{run['id']}/metrics",
        json={"metrics": [{"key": "loss", "value": 0.1, "step": 0}]},
        headers=auth_headers(token_b),
    )
    assert response.status_code == 403


def test_metrics_validation_rejects_negative_step(client, user_token):
    _, run = _setup_run(client, user_token)
    response = client.post(
        f"/runs/{run['id']}/metrics",
        json={"metrics": [{"key": "loss", "value": 0.1, "step": -1}]},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 422


def test_metrics_validation_rejects_empty_batch(client, user_token):
    _, run = _setup_run(client, user_token)
    response = client.post(
        f"/runs/{run['id']}/metrics",
        json={"metrics": []},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 422
