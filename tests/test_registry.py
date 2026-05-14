"""Тесты реестра моделей и инварианта Production."""
from tests.conftest import auth_headers, login_user, register_user


def _setup_run(client, token, exp_name="exp"):
    exp = client.post(
        "/experiments", json={"name": exp_name}, headers=auth_headers(token)
    ).json()
    run = client.post(
        f"/experiments/{exp['id']}/runs", headers=auth_headers(token)
    ).json()
    return exp, run


def _register_model(client, token, name="my-model"):
    return client.post(
        "/models", json={"name": name, "description": "d"}, headers=auth_headers(token)
    )


def _create_version(client, token, name, run_id):
    return client.post(
        f"/models/{name}/versions",
        json={"run_id": run_id},
        headers=auth_headers(token),
    )


def test_register_model_success(client, user_token):
    response = _register_model(client, user_token, name="m1")
    assert response.status_code == 201
    assert response.json()["name"] == "m1"


def test_register_model_duplicate_name_returns_409(client, user_token):
    _register_model(client, user_token, name="dup")
    response = _register_model(client, user_token, name="dup")
    assert response.status_code == 409


def test_create_version_auto_increments(client, user_token):
    _, run = _setup_run(client, user_token)
    _register_model(client, user_token, name="m2")
    v1 = _create_version(client, user_token, "m2", run["id"]).json()
    v2 = _create_version(client, user_token, "m2", run["id"]).json()
    assert v1["version"] == 1
    assert v2["version"] == 2
    assert v1["stage"] == "None"


def test_promote_to_production_archives_previous(client, admin_token, user_token):
    _, run = _setup_run(client, user_token)
    _register_model(client, user_token, name="m3")
    v1 = _create_version(client, user_token, "m3", run["id"]).json()
    v2 = _create_version(client, user_token, "m3", run["id"]).json()

    # Сначала переводим v1 в Production (через admin).
    r1 = client.patch(
        f"/models/m3/versions/{v1['version']}/stage",
        json={"stage": "Production"},
        headers=auth_headers(admin_token),
    )
    assert r1.status_code == 200
    assert r1.json()["stage"] == "Production"

    # Перевод v2 в Production должен заархивировать v1.
    r2 = client.patch(
        f"/models/m3/versions/{v2['version']}/stage",
        json={"stage": "Production"},
        headers=auth_headers(admin_token),
    )
    assert r2.status_code == 200
    assert r2.json()["stage"] == "Production"

    detail = client.get(
        "/models/m3", headers=auth_headers(admin_token)
    ).json()
    by_version = {v["version"]: v["stage"] for v in detail["versions"]}
    assert by_version[v1["version"]] == "Archived"
    assert by_version[v2["version"]] == "Production"


def test_non_admin_cannot_change_stage(client, user_token):
    _, run = _setup_run(client, user_token)
    _register_model(client, user_token, name="m4")
    v1 = _create_version(client, user_token, "m4", run["id"]).json()

    response = client.patch(
        f"/models/m4/versions/{v1['version']}/stage",
        json={"stage": "Staging"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 403


def test_create_version_for_unknown_model_returns_404(client, user_token):
    _, run = _setup_run(client, user_token)
    response = _create_version(client, user_token, "ghost", run["id"])
    assert response.status_code == 404


def test_create_version_requires_access_to_run(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    _, run = _setup_run(client, token_a, exp_name="exp-a")
    _register_model(client, token_b, name="m-b")

    response = _create_version(client, token_b, "m-b", run["id"])
    assert response.status_code == 403


def test_set_stage_for_unknown_version_returns_404(client, admin_token, user_token):
    _register_model(client, user_token, name="m5")
    response = client.patch(
        "/models/m5/versions/99/stage",
        json={"stage": "Staging"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 404


def test_list_models_returns_all(client, user_token):
    _register_model(client, user_token, name="alpha")
    _register_model(client, user_token, name="beta")
    response = client.get("/models", headers=auth_headers(user_token))
    assert response.status_code == 200
    names = {m["name"] for m in response.json()}
    assert {"alpha", "beta"} <= names
