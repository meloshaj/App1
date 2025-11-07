## MCPI Demo — FastAPI + Celery + Redis (Monte Carlo π)

This is a minimal demo showing how to orchestrate background work with Celery and Redis, expose an HTTP API with FastAPI, and present results in a small web UI. The Monte Carlo method estimates π (pi) by sampling random points.

### Project Structure

```
app/
  __init__.py
  main.py              # FastAPI app (UI + API)
  celery_app.py        # Celery configuration
  tasks.py             # Celery task: Monte Carlo π estimation
  static/
    app.js             # Frontend logic (batch flow, polling, table)
    styles.css         # Styles
  templates/
    index.html         # Simple UI
Dockerfile
docker-compose.yml
requirements.txt
README.md
```

### Prerequisites

- Docker and Docker Compose (recommended), or
- Python 3.11+, pip, and a running Redis instance
- Windows, macOS, or Linux supported

---

## Quick Start (Docker Compose)

This is the easiest way to run everything locally.

0) Ensure you are in the project directory `C:\mcpi-demo` on Windows:

Windows (cmd):

```bat
cd C:\mcpi-demo
```

Windows (PowerShell):

```powershell
Set-Location C:\mcpi-demo
```

1) Build and start the stack:

```bash
docker compose up --build
```

2) Open the app in your browser:

```
http://localhost:8000
```

3) Use the form to start a batch:

- Total samples: total number of random samples to process (will be split across tasks)
- Number of tasks: how many Celery jobs to start in parallel (samples are divided evenly)
- Display digits: formatting precision in the UI

Example: With 1,000,000 total samples and 4 tasks, each task processes 250,000 samples.

4) Stop the stack when finished:

```bash
docker compose down
```

Notes:

- The compose file starts three services: `redis`, `api` (FastAPI), and `worker` (Celery). They use the same `REDIS_URL` internally.
- The API is available at `http://localhost:8000` and serves the UI at `/`.

### Scaling workers (parallelism)

Increase Celery workers to process more tasks concurrently. Replace `2` with your desired number (e.g., `3`, `4`, etc.):

```bash
docker compose up -d --build --scale worker=2
```

Check containers:

```bash
docker compose ps
```

Optionally raise per-worker concurrency (example):

```bash
docker compose exec worker celery -A app.celery_app.celery_app worker -Q default -l info -c 8
```

---

## Local Development (without Docker)

You will run Redis, the Celery worker, and the FastAPI server directly.

### 1) Create and activate a virtual environment

Windows (cmd):

```bat
python -m venv .venv
.venv\Scripts\activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux (bash/zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Start Redis

- With Docker:

```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

- Or use a local Redis install listening on `localhost:6379`.

### 4) Set environment and run services

Ensure both API and worker see the same `REDIS_URL`.

Windows (PowerShell):

```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
```

Windows (cmd):

```bat
set REDIS_URL=redis://localhost:6379/0
```

macOS/Linux (bash/zsh):

```bash
export REDIS_URL=redis://localhost:6379/0
```

Start the Celery worker (terminal 1):

```bash
celery -A app.celery_app.celery_app worker -Q default -l info
```

Start the API (terminal 2):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open the app:

```
http://localhost:8000
```

---

## API Reference

Base URL (local): `http://localhost:8000`

- POST `/api/pi/start`
  - Body: `{ "samples": number }` (optional; default `1000000`)
  - Response: `{ "task_id": string }`

- GET `/api/pi/status/{task_id}`
  - Response when pending:
    ```json
    { "task_id": "...", "state": "PENDING", "ready": false }
    ```
  - Response when complete (example):
    ```json
    {
      "task_id": "...",
      "state": "SUCCESS",
      "ready": true,
      "result": {
        "pi": 3.14159,
        "samples": 1000000.0,
        "inside": 785398.0,
        "error_abs": 0.00000
      }
    }
    ```

- POST `/api/pi/batch/start`
  - Body: `{ "samples": number, "tasks": number }`
    - `samples`: Total number of samples to process (will be split across tasks)
    - `tasks`: Number of parallel tasks to create
  - Response: `{ "task_ids": string[] }`
  - Behavior: The total samples are divided evenly across the specified number of tasks. If the division has a remainder, the extra samples are distributed to the first tasks.

Batch computation:

- The backend splits the total samples across tasks: `samples_per_task = total_samples // num_tasks`
- Each task processes its allocated samples and returns: `{ "pi": float, "samples": float, "inside": float, "error_abs": float }`
  - `inside`: Raw count of points inside the quarter circle (used for aggregation)

UI behavior:

- The UI submits a batch, polls all task IDs via `/api/pi/status/{id}`, and aggregates results by combining raw counts (`inside` + `samples`) from all tasks.
- The final π estimate is computed from the aggregated counts: `π = 4.0 * (total_inside / total_samples)`
- This aggregation method is statistically superior to averaging individual task estimates.
- The table displays individual task results, while the metrics show the combined estimate.

---

## Verification (estimation correctness)

You can run a verification script that exercises `app/tasks.py::estimate_pi` across multiple sample sizes and checks that the mean estimate is within a reasonable tolerance of π.

Run with Docker Compose (inside the API container):

```bash
docker compose exec api python -m app.verify_estimation --samples 10000 100000 --trials 5 --seed 12345
```

Run locally (without Docker):

```bash
python -m app.verify_estimation --samples 10000 100000 --trials 5 --seed 12345
```

Flags:

- `--samples`: list of sample sizes to test (default: `10000 100000`)
- `--trials`: trials per sample size (default: `5`)
- `--seed`: RNG seed to make runs reproducible (default: `12345`)

Exit code is non-zero if verification fails.

---

## Troubleshooting

- UI not loading? Confirm the API is running and listening on `:8000`.
- Jobs never complete? Ensure `worker` is running and `REDIS_URL` matches for both API and worker.
- Redis connection errors? Verify Redis is reachable at `redis://localhost:6379/0` (local) or the compose network URL.
- CORS or fetch errors in console? Access the UI via the same host/port (`http://localhost:8000`).
- Nothing appears in the results table? Check worker logs for exceptions.

Logs to check:

- Celery worker terminal for task execution and queue activity
- API server terminal for request handling and tracebacks
- Browser DevTools console/network for frontend fetch errors

---

## Development Notes

- The static files are served at `/static` and templates from `app/templates` via FastAPI.
- The task `estimate_pi` is defined in `app/tasks.py` and routed to the `default` queue in `app/celery_app.py`.
- Default sample counts and digits are adjustable in the UI.
- Batch computation demonstrates distributed computation: total work is split across tasks, and results are aggregated by combining raw counts for optimal statistical accuracy.
- The table with task results has a scrollable container (max-height: 500px) to handle many tasks without extending the page.
