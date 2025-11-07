import math
import random
from typing import Dict

from .celery_app import celery_app


@celery_app.task(name="app.tasks.estimate_pi")
def estimate_pi(num_samples: int = 1_000_000) -> Dict[str, float]:
    if num_samples <= 0:
        num_samples = 1

    inside = 0
    # Simple Monte Carlo: quarter circle in unit square
    for _ in range(num_samples):
        x = random.random()
        y = random.random()
        if x * x + y * y <= 1.0:
            inside += 1

    pi_estimate = 4.0 * (inside / float(num_samples))
    return {
        "pi": pi_estimate,
        "samples": float(num_samples),
        "inside": float(inside),  # Raw count for aggregation
        "error_abs": abs(math.pi - pi_estimate),
    }


