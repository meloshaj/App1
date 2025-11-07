import argparse
import math
import random
import sys
from typing import Dict, List, Tuple


def verify_result_structure(result: Dict) -> Tuple[bool, str]:
    required_keys = {"pi", "samples", "inside", "error_abs"}
    missing = required_keys.difference(result.keys())
    if missing:
        return False, f"missing keys: {sorted(missing)}"
    if not isinstance(result["pi"], (int, float)):
        return False, "'pi' must be numeric"
    if not isinstance(result["samples"], (int, float)):
        return False, "'samples' must be numeric"
    if not isinstance(result["inside"], (int, float)):
        return False, "'inside' must be numeric"
    if not isinstance(result["error_abs"], (int, float)):
        return False, "'error_abs' must be numeric"
    # internal consistency: pi = 4.0 * inside / samples
    samples_val = float(result["samples"])
    inside_val = float(result["inside"])
    if samples_val > 0:
        expected_pi = 4.0 * (inside_val / samples_val)
        if abs(result["pi"] - expected_pi) > 1e-6:
            return False, f"'pi' inconsistent: expected {expected_pi:.6f} from inside/samples, got {result['pi']:.6f}"
    # internal consistency: error_abs ~= |pi - math.pi|
    if abs(abs(result["pi"] - math.pi) - float(result["error_abs"])) > 1e-6:
        return False, "'error_abs' inconsistent with 'pi'"
    return True, "ok"


def run_trials(samples: int, trials: int) -> List[float]:
    # Late import to use the local package
    from .tasks import estimate_pi

    estimates: List[float] = []
    for i in range(trials):
        # Diverse seeds per trial while still reproducible when --seed is given
        random.random()  # advance state a bit
        result = estimate_pi(samples)
        ok, msg = verify_result_structure(result)
        if not ok:
            raise AssertionError(f"Bad result structure for samples={samples}: {msg}")
        # samples is returned as float in the task; compare numerically
        if int(result["samples"]) != int(samples if samples > 0 else 1):
            raise AssertionError(
                f"Returned samples mismatch: got {result['samples']} expected {samples}"
            )
        estimates.append(float(result["pi"]))
    return estimates


def within_tolerance(value: float, target: float, tol: float) -> bool:
    return abs(value - target) <= tol


def choose_tolerance(samples: int) -> float:
    # Heuristic tolerances for mean over several trials
    if samples >= 1_000_000:
        return 0.004
    if samples >= 100_000:
        return 0.01
    if samples >= 10_000:
        return 0.03
    return 0.08


def verify_estimation(sample_sizes: List[int], trials: int) -> int:
    failures = []

    # Edge case: non-positive coerces to 1
    from .tasks import estimate_pi
    edge = estimate_pi(0)
    if int(edge["samples"]) != 1:
        failures.append("num_samples<=0 should coerce to 1")

    print("Running Monte Carlo π verification...")
    for n in sample_sizes:
        tol = choose_tolerance(n)
        estimates = run_trials(n, trials)
        mean_est = sum(estimates) / len(estimates)
        err = abs(mean_est - math.pi)
        ok = within_tolerance(mean_est, math.pi, tol)
        status = "PASS" if ok else "FAIL"
        print(
            f"samples={n:>9}  trials={trials}  mean={mean_est:.6f}  err={err:.6f}  tol={tol:.3f}  {status}"
        )
        if not ok:
            failures.append(f"samples={n} mean error {err:.6f} > tol {tol:.3f}")

    if failures:
        print("\nVerification FAILED:")
        for f in failures:
            print(" - " + f)
        return 1

    print("\nVerification PASSED: estimation behaves within expected bounds.")
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify Monte Carlo π estimation task.")
    parser.add_argument(
        "--samples",
        type=int,
        nargs="*",
        default=[10_000, 100_000],
        help="Sample sizes to test (default: 10000 100000)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Trials per sample size (default: 5)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Random seed for reproducibility (default: 12345)",
    )
    args = parser.parse_args(argv)

    random.seed(args.seed)
    return verify_estimation(args.samples, args.trials)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


