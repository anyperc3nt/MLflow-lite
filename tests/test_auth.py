"""Тесты роутов /auth/signup, /auth/login, /auth/me."""
from tests.conftest import auth_headers, login_user, register_user


def test_signup_success(client):
    response = client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": "password123", "name": "New"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "user"
    assert "id" in body
    assert "hashed_password" not in body


def test_signup_duplicate_email_returns_409(client):
    register_user(client, email="dup@example.com")
    response = client.post(
        "/auth/signup",
        json={"email": "dup@example.com", "password": "password123", "name": "Other"},
    )
    assert response.status_code == 409


def test_signup_rejects_short_password(client):
    response = client.post(
        "/auth/signup",
        json={"email": "x@example.com", "password": "short", "name": "X"},
    )
    assert response.status_code == 422


def test_signup_rejects_invalid_email(client):
    response = client.post(
        "/auth/signup",
        json={"email": "not-an-email", "password": "password123", "name": "X"},
    )
    assert response.status_code == 422


def test_login_success(client):
    register_user(client)
    response = client.post(
        "/auth/login", data={"username": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


def test_login_wrong_password(client):
    register_user(client)
    response = client.post(
        "/auth/login", data={"username": "user@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        "/auth/login", data={"username": "ghost@example.com", "password": "password123"}
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_token_returns_current_user(client):
    register_user(client)
    token = login_user(client)
    response = client.get("/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_me_with_invalid_token(client):
    response = client.get("/auth/me", headers=auth_headers("not-a-valid-jwt"))
    assert response.status_code == 401
