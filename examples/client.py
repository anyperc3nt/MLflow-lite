"""Тонкий HTTP-клиент к MLflow-lite для демо-скриптов.

Никакой бизнес-логики — только обёртки вокруг requests/httpx, чтобы
демо-скрипты были читаемыми и устойчивыми к рефакторингу путей.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

import httpx


class MLflowLiteClient:
    """Простой клиент MLflow-lite на httpx.Client."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 10.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        self._token: Optional[str] = None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MLflowLiteClient":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    @property
    def _auth_headers(self) -> dict:
        if self._token is None:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    def signup_or_login(self, email: str, password: str, name: str = "Demo") -> None:
        """Зарегистрироваться (если нужно), затем залогиниться."""
        self._client.post(
            "/auth/signup",
            json={"email": email, "password": password, "name": name},
        )
        response = self._client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        response.raise_for_status()
        self._token = response.json()["access_token"]

    def get_or_create_experiment(self, name: str, description: str = "") -> int:
        """Создать эксперимент с этим именем или вернуть существующий."""
        response = self._client.post(
            "/experiments",
            json={"name": name, "description": description},
            headers=self._auth_headers,
        )
        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code == 409:
            listed = self._client.get(
                "/experiments", headers=self._auth_headers
            ).json()
            for exp in listed:
                if exp["name"] == name:
                    return exp["id"]
        response.raise_for_status()
        raise RuntimeError("unreachable")

    def create_run(self, experiment_id: int) -> int:
        response = self._client.post(
            f"/experiments/{experiment_id}/runs", headers=self._auth_headers
        )
        response.raise_for_status()
        return response.json()["id"]

    def log_params(self, run_id: int, params: dict) -> None:
        if not params:
            return
        response = self._client.post(
            f"/runs/{run_id}/params",
            json={"params": [{"key": k, "value": str(v)} for k, v in params.items()]},
            headers=self._auth_headers,
        )
        response.raise_for_status()

    def log_metrics(
        self, run_id: int, metrics: Iterable[tuple[str, float, int]]
    ) -> None:
        """metrics: iterable of (key, value, step)."""
        batch: List[dict] = [
            {"key": k, "value": float(v), "step": int(s)} for k, v, s in metrics
        ]
        if not batch:
            return
        response = self._client.post(
            f"/runs/{run_id}/metrics",
            json={"metrics": batch},
            headers=self._auth_headers,
        )
        response.raise_for_status()

    def finish_run(self, run_id: int, success: bool = True) -> None:
        new_status = "FINISHED" if success else "FAILED"
        response = self._client.patch(
            f"/runs/{run_id}",
            json={"status": new_status},
            headers=self._auth_headers,
        )
        response.raise_for_status()

    def leaderboard(
        self,
        experiment_id: int,
        metric: str,
        top: int = 10,
        mode: str = "min",
    ) -> List[dict]:
        """Возвращает JSON leaderboard (список объектов с run_id, value, step, ...)."""
        response = self._client.get(
            f"/experiments/{experiment_id}/leaderboard",
            params={"metric": metric, "top": top, "mode": mode},
            headers=self._auth_headers,
        )
        response.raise_for_status()
        return response.json()

    def register_model(self, name: str, description: str = "") -> None:
        """Регистрирует имя модели в реестре. 409 — модель уже есть, игнорируем."""
        response = self._client.post(
            "/models",
            json={"name": name, "description": description or None},
            headers=self._auth_headers,
        )
        if response.status_code not in (201, 409):
            response.raise_for_status()

    def register_model_version(self, model_name: str, run_id: int) -> dict:
        """Регистрирует версию модели, привязанную к рану."""
        response = self._client.post(
            f"/models/{model_name}/versions",
            json={"run_id": run_id},
            headers=self._auth_headers,
        )
        response.raise_for_status()
        return response.json()
