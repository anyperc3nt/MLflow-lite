"""Тесты роутов /experiments/{id}/runs и /runs/{id}."""
from tests.conftest import auth_headers, login_user, register_user


def _create_experiment(client, token, name="exp"):
    return client.post(
        "/experiments", json={"name": name}, headers=auth_headers(token)
    ).json()


def test_create_run_success(client, user_token):
    exp = _create_experiment(client, user_token)
    response = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["experiment_id"] == exp["id"]
    assert body["status"] == "RUNNING"
    assert body["ended_at"] is None


def test_create_run_in_foreign_experiment_returns_403(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    exp = _create_experiment(client, token_a, name="exp-a")

    response = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(token_b)
    )
    assert response.status_code == 403


def test_list_runs_of_experiment(client, user_token):
    exp = _create_experiment(client, user_token)
    client.post(f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token))
    client.post(f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token))
    response = client.get(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_finish_run_sets_status_and_ended_at(client, user_token):
    exp = _create_experiment(client, user_token)
    run = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    ).json()
    response = client.patch(
        f"/runs/{run['id']}",
        json={"status": "FINISHED"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FINISHED"
    assert body["ended_at"] is not None


def test_cannot_finish_run_twice(client, user_token):
    exp = _create_experiment(client, user_token)
    run = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    ).json()
    client.patch(
        f"/runs/{run['id']}",
        json={"status": "FINISHED"},
        headers=auth_headers(user_token),
    )
    response = client.patch(
        f"/runs/{run['id']}",
        json={"status": "FAILED"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 409


def test_cannot_revert_to_running(client, user_token):
    exp = _create_experiment(client, user_token)
    run = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    ).json()
    response = client.patch(
        f"/runs/{run['id']}",
        json={"status": "RUNNING"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 400


def test_get_foreign_run_returns_403(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    exp = _create_experiment(client, token_a, name="exp-a")
    run = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(token_a)
    ).json()

    response = client.get(f"/runs/{run['id']}", headers=auth_headers(token_b))
    assert response.status_code == 403


def test_delete_run_does_not_affect_siblings(client, user_token):
    exp = _create_experiment(client, user_token)
    run1 = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    ).json()
    run2 = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    ).json()

    response = client.delete(f"/runs/{run1['id']}", headers=auth_headers(user_token))
    assert response.status_code == 204

    siblings = client.get(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    ).json()
    assert [r["id"] for r in siblings] == [run2["id"]]


def test_deleting_experiment_cascades_runs(client, user_token):
    exp = _create_experiment(client, user_token)
    run = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(user_token)
    ).json()
    response = client.delete(
        f"/experiments/{exp['id']}", headers=auth_headers(user_token)
    )
    assert response.status_code == 204
    assert client.get(f"/runs/{run['id']}", headers=auth_headers(user_token)).status_code == 404
