import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "mcpi-worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_routes={"app.tasks.*": {"queue": "default"}},
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
