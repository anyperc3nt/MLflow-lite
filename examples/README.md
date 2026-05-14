# Demo: tracking a real training loop

This folder contains a small example that uses MLflow-lite from a real
training script, not just Swagger. It demonstrates how the service is
intended to be used in practice.

## Setup

```bash
# In repo root, with .venv activated:
pip install -r examples/requirements-demo.txt

# Start the API in another terminal:
alembic upgrade head
uvicorn app.main:app --reload
```

## Run the demo

```bash
PYTHONPATH=. python examples/train_demo.py
```

The script will:

1. Sign up `demo@example.com` (or login if already exists).
2. Create (or reuse) an experiment named `linreg-sweep`.
3. Sweep `(learning_rate, l2_reg)` over 9 combinations and create
   one run per combination.
4. For each run, log hyperparameters and a time-series of
   `train_loss` / `val_loss` per epoch, plus a single
   `train_time_ms` data point.
5. Mark each run as `FINISHED`.

After the run, open <http://127.0.0.1:8000/docs> and try:

- `GET /experiments/{id}/leaderboard?metric=val_loss&top=5&mode=min`
- `GET /experiments/{id}/pareto?x=val_loss&y=train_time_ms&x_mode=min&y_mode=min`
- `POST /runs/compare` with a couple of run ids to see params/metric diffs.

## Files

- [client.py](client.py) - thin httpx wrapper around the API
- [train_demo.py](train_demo.py) - numpy gradient descent sweep
- [requirements-demo.txt](../examples/requirements-demo.txt) - numpy + httpx
