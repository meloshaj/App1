from fastapi import FastAPI, Request
from fastapi import Body
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---- PI endpoints ----
@app.post("/api/pi/start")
def start_pi_job(payload: dict = Body(default={})):
    from .tasks import estimate_pi

    num_samples = payload.get("samples", 1_000_000)
    try:
        num_samples = int(num_samples)
    except Exception:
        num_samples = 1_000_000

    task = estimate_pi.delay(num_samples)
    return {"task_id": task.id}


@app.get("/api/pi/status/{task_id}")
def pi_status(task_id: str):
    from .celery_app import celery_app
    async_result = celery_app.AsyncResult(task_id)

    data = {
        "task_id": task_id,
        "state": async_result.state,
        "ready": async_result.ready(),
    }
    if async_result.ready():
        try:
            data["result"] = async_result.get(timeout=1)
        except Exception as exc:
            return JSONResponse(status_code=500, content={"error": str(exc)})

    return data


@app.post("/api/pi/batch/start")
def start_pi_batch(payload: dict = Body(default={})): 
    from .tasks import estimate_pi

    total_samples = payload.get("samples", 1_000_000)
    num_tasks = payload.get("tasks", 4)

    try:
        total_samples = int(total_samples)
    except Exception:
        total_samples = 1_000_000

    try:
        num_tasks = max(1, int(num_tasks))
    except Exception:
        num_tasks = 4

    # Split total_samples across num_tasks for distributed computation
    samples_per_task = total_samples // num_tasks
    remainder = total_samples % num_tasks
    
    # Distribute tasks with samples_per_task, adding extra samples to first tasks if remainder exists
    task_ids = []
    for i in range(num_tasks):
        # Add one extra sample to first 'remainder' tasks to account for division remainder
        task_samples = samples_per_task + (1 if i < remainder else 0)
        task_ids.append(estimate_pi.delay(task_samples).id)
    
    return {"task_ids": task_ids}


