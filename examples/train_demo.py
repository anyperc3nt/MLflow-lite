"""Демо: линейная регрессия с градиентным спуском, трекинг через MLflow-lite.

Запуск:
    1. В одном терминале:  uvicorn app.main:app --reload
    2. В другом:           python examples/train_demo.py

Скрипт делает sweep по (learning_rate, l2_reg) и для каждой комбинации
создаёт отдельный ран, логируя гиперпараметры и time-series метрик
train_loss / val_loss / train_time_ms по эпохам.

После прогона можно открыть Swagger и попробовать:
    GET  /experiments/{id}/leaderboard?metric=val_loss&top=5&mode=min
    GET  /experiments/{id}/pareto?x=val_loss&y=train_time_ms&x_mode=min&y_mode=min
"""
from __future__ import annotations

import time
from typing import Tuple

import numpy as np

from examples.client import MLflowLiteClient

RNG = np.random.default_rng(seed=42)

DEMO_USER = "demo@example.com"
DEMO_PASSWORD = "password123"
DEMO_EXPERIMENT = "linreg-sweep"


def make_dataset(
    n_samples: int = 500, n_features: int = 10, noise: float = 0.5
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Сгенерировать синтетический датасет для линейной регрессии."""
    x = RNG.standard_normal((n_samples, n_features))
    true_w = RNG.standard_normal(n_features)
    y = x @ true_w + noise * RNG.standard_normal(n_samples)
    split = int(0.8 * n_samples)
    return x[:split], y[:split], x[split:], y[split:]


def _mse(pred: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean((pred - target) ** 2))


def train_gd(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    learning_rate: float,
    l2_reg: float,
    epochs: int = 30,
):
    """Линейная регрессия + GD. Yield (epoch, train_loss, val_loss)."""
    weights = np.zeros(x_train.shape[1])
    for epoch in range(epochs):
        residual = x_train @ weights - y_train
        gradient = (x_train.T @ residual) / x_train.shape[0] + l2_reg * weights
        weights = weights - learning_rate * gradient
        train_loss = _mse(x_train @ weights, y_train)
        val_loss = _mse(x_val @ weights, y_val)
        yield epoch, train_loss, val_loss


def run_sweep() -> None:
    x_train, y_train, x_val, y_val = make_dataset()

    sweep = [
        (lr, l2)
        for lr in (0.01, 0.05, 0.1)
        for l2 in (0.0, 0.01, 0.1)
    ]
    print(f"Running sweep over {len(sweep)} configurations...")

    with MLflowLiteClient() as mlf:
        mlf.signup_or_login(DEMO_USER, DEMO_PASSWORD, name="Demo")
        experiment_id = mlf.get_or_create_experiment(
            DEMO_EXPERIMENT, description="Linear regression GD sweep"
        )

        for lr, l2 in sweep:
            run_id = mlf.create_run(experiment_id)
            mlf.log_params(run_id, {"learning_rate": lr, "l2_reg": l2, "epochs": 30})

            started = time.perf_counter()
            batch: list[tuple[str, float, int]] = []
            for epoch, train_loss, val_loss in train_gd(
                x_train, y_train, x_val, y_val, lr, l2
            ):
                batch.append(("train_loss", train_loss, epoch))
                batch.append(("val_loss", val_loss, epoch))

            elapsed_ms = (time.perf_counter() - started) * 1000.0
            batch.append(("train_time_ms", elapsed_ms, 0))
            mlf.log_metrics(run_id, batch)
            mlf.finish_run(run_id)

            print(
                f"  lr={lr:<5} l2={l2:<5} -> "
                f"final val_loss={val_loss:.4f} time={elapsed_ms:.1f}ms"
            )

    print("\nDone. Try in Swagger:")
    print(
        f"  GET /experiments/{experiment_id}/leaderboard"
        "?metric=val_loss&top=5&mode=min"
    )
    print(
        f"  GET /experiments/{experiment_id}/pareto"
        "?x=val_loss&y=train_time_ms&x_mode=min&y_mode=min"
    )


if __name__ == "__main__":
    run_sweep()
