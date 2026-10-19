import math
from typing import List, Dict, Any
import numpy as np

def mean(data: List[float]) -> float:
    """Calculates the arithmetic mean of a dataset."""
    if not data:
        return 0.0
    return float(np.mean(data))

def median(data: List[float]) -> float:
    """Calculates the median (50th percentile) of a dataset."""
    if not data:
        return 0.0
    return float(np.median(data))

def stddev(data: List[float]) -> float:
    """Calculates the sample standard deviation (ddof=1) of a dataset."""
    if len(data) <= 1:
        return 0.0
    return float(np.std(data, ddof=1))

def p95(data: List[float]) -> float:
    """Calculates the 95th percentile of a dataset."""
    if not data:
        return 0.0
    return float(np.percentile(data, 95))

def calculate_summary_stats(data: List[float]) -> Dict[str, float]:
    """Computes mean, median, sample stddev, and p95 for a list of floats."""
    if not data:
        return {"mean": 0.0, "median": 0.0, "stddev": 0.0, "p95": 0.0}
    return {
        "mean": round(mean(data), 4),
        "median": round(median(data), 4),
        "stddev": round(stddev(data), 4),
        "p95": round(p95(data), 4)
    }

def verify_stats_helpers() -> bool:
    """Verifies stats helper functions against known deterministic input."""
    known = [10.0, 20.0, 30.0, 40.0, 50.0]
    res = calculate_summary_stats(known)
    assert res["mean"] == 30.0, f"Mean mismatch: {res['mean']}"
    assert res["median"] == 30.0, f"Median mismatch: {res['median']}"
    assert abs(res["stddev"] - 15.8114) < 1e-3, f"Stddev mismatch: {res['stddev']}"
    assert abs(res["p95"] - 48.0) < 1e-3, f"P95 mismatch: {res['p95']}"
    return True

if __name__ == "__main__":
    verify_stats_helpers()
    print("Stats helper verification PASSED.")
