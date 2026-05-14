"""Тесты роутов /experiments."""
from tests.conftest import auth_headers, login_user, register_user


def _create_experiment(client, token, name="exp-1", description=None):
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = client.post("/experiments", json=payload, headers=auth_headers(token))
    return response


def test_create_experiment_success(client, user_token):
    response = _create_experiment(client, user_token, name="alpha", description="d")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "alpha"
    assert body["description"] == "d"
    assert body["owner_id"] > 0


def test_create_experiment_requires_auth(client):
    response = client.post("/experiments", json={"name": "x"})
    assert response.status_code == 401


def test_create_duplicate_name_returns_409(client, user_token):
    _create_experiment(client, user_token, name="dup")
    response = _create_experiment(client, user_token, name="dup")
    assert response.status_code == 409


def test_two_users_can_have_same_experiment_name(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    assert _create_experiment(client, token_a, name="shared").status_code == 201
    assert _create_experiment(client, token_b, name="shared").status_code == 201


def test_list_returns_only_own_experiments(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    _create_experiment(client, token_a, name="exp-a")
    _create_experiment(client, token_b, name="exp-b")

    body = client.get("/experiments", headers=auth_headers(token_a)).json()
    names = [e["name"] for e in body]
    assert names == ["exp-a"]


def test_get_other_users_experiment_returns_403(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    created = _create_experiment(client, token_a, name="exp-a").json()

    response = client.get(f"/experiments/{created['id']}", headers=auth_headers(token_b))
    assert response.status_code == 403


def test_get_missing_experiment_returns_404(client, user_token):
    response = client.get("/experiments/999", headers=auth_headers(user_token))
    assert response.status_code == 404


def test_patch_experiment_updates_fields(client, user_token):
    created = _create_experiment(client, user_token, name="old").json()
    response = client.patch(
        f"/experiments/{created['id']}",
        json={"name": "new", "description": "updated"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "new"
    assert body["description"] == "updated"


def test_patch_other_users_experiment_returns_403(client):
    register_user(client, email="a@example.com")
    register_user(client, email="b@example.com")
    token_a = login_user(client, email="a@example.com")
    token_b = login_user(client, email="b@example.com")
    created = _create_experiment(client, token_a, name="exp-a").json()

    response = client.patch(
        f"/experiments/{created['id']}",
        json={"name": "hacked"},
        headers=auth_headers(token_b),
    )
    assert response.status_code == 403


def test_delete_own_experiment_returns_204(client, user_token):
    created = _create_experiment(client, user_token, name="to-delete").json()
    response = client.delete(
        f"/experiments/{created['id']}", headers=auth_headers(user_token)
    )
    assert response.status_code == 204
    assert client.get(
        f"/experiments/{created['id']}", headers=auth_headers(user_token)
    ).status_code == 404


def test_admin_can_see_and_delete_others_experiment(client, admin_token):
    register_user(client, email="a@example.com")
    token_a = login_user(client, email="a@example.com")
    created = _create_experiment(client, token_a, name="exp-a").json()

    body = client.get("/experiments", headers=auth_headers(admin_token)).json()
    assert any(e["id"] == created["id"] for e in body)

    response = client.delete(
        f"/experiments/{created['id']}", headers=auth_headers(admin_token)
    )
    assert response.status_code == 204
