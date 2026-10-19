import os
import math
from typing import List, Dict, Any, Tuple
import numpy as np

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divides two numbers, handling zero denominators gracefully."""
    if denominator == 0.0 or math.isnan(denominator):
        return default
    return float(numerator / denominator)

def calculate_confusion_matrix(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates TP, TN, FP, FN, ERROR, UNKNOWN, UNSUPPORTED, NOT_APPLICABLE
    and derived classification metrics (precision, recall, specificity, F1, accuracy, coverage).
    Never converts ERROR or UNKNOWN into PASS.
    """
    tp = 0
    tn = 0
    fp = 0
    fn = 0
    err_count = 0
    unk_count = 0
    unsup_count = 0
    na_count = 0

    for r in rows:
        exp = str(r.get("expected", "")).upper()
        act = str(r.get("actual", "")).upper()

        if act == "ERROR":
            err_count += 1
        elif act == "UNKNOWN":
            unk_count += 1
        elif act in ["UNSUPPORTED", "NOT_SUPPORTED"]:
            unsup_count += 1
        elif act in ["NOT_APPLICABLE", "N/A"]:
            na_count += 1
        elif exp == "FAIL" and act == "FAIL":
            tp += 1
        elif exp == "PASS" and act == "PASS":
            tn += 1
        elif exp == "PASS" and act == "FAIL":
            fp += 1
        elif exp == "FAIL" and act == "PASS":
            fn += 1
        else:
            unk_count += 1

    decisive_total = tp + tn + fp + fn
    total = len(rows)

    precision = safe_divide(tp, tp + fp, 0.0)
    recall = safe_divide(tp, tp + fn, 0.0)
    specificity = safe_divide(tn, tn + fp, 0.0)
    
    if (precision + recall) > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    decision_accuracy = safe_divide(tp + tn, decisive_total, 0.0) if decisive_total > 0 else 0.0
    overall_accuracy = safe_divide(tp + tn, total, 0.0)
    coverage = safe_divide(decisive_total, total, 0.0)

    return {
        "total": total,
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "ERROR": err_count,
        "UNKNOWN": unk_count,
        "UNSUPPORTED": unsup_count,
        "NOT_APPLICABLE": na_count,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "F1": round(f1, 4),
        "decision_accuracy": round(decision_accuracy, 4),
        "overall_accuracy": round(overall_accuracy, 4),
        "coverage": round(coverage, 4)
    }

def normalize_semantic_value(val: Any) -> str:
    """Normalizes string/boolean/numeric values for semantic comparison."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("true", "t"):
        return "true"
    if s.lower() in ("false", "f"):
        return "false"
    if s.lower() in ("none", "null", ""):
        return "none"
    if s == "UNRESOLVED":
        return "UNRESOLVED"
    # Attempt numeric normalization e.g. "14" vs 14 vs 14.0
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except ValueError:
        pass
    return s.lower()

def check_semantic_agreement(n_count: int, s_count: int, n_val: Any, s_val: Any) -> bool:
    """
    Evaluates whether synthetic parser semantically agrees with Native Terraform reference oracle.
    Requirements:
    1. Native reference exists and successfully extracted concrete resources (n_count > 0).
    2. Synthetic resource count exactly equals Native resource count (s_count == n_count).
    3. Target resolved values match after normalization (synthetic is not UNRESOLVED).
    """
    if n_count <= 0:
        return False
    if s_count != n_count:
        return False
    norm_n = normalize_semantic_value(n_val)
    norm_s = normalize_semantic_value(s_val)
    if norm_s == "UNRESOLVED":
        return False
    if norm_n != "none":
        return norm_s == norm_n
    return norm_s in ("none", "")

def calculate_native_vs_synthetic_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates policy decision correctness against ground-truth manifest labels, and evaluates
    synthetic semantic agreement using Native Terraform Plan execution as the reference oracle.
    
    NOTE: Native Terraform is NOT an independent security oracle; it is the semantic reference
    for resolved resource counts and attribute values to test whether the synthetic regex parser
    correctly resolves Terraform language constructs (variables, modules, counts, locals).
    """
    total = len(rows)
    native_decision_correct = 0
    synthetic_decision_correct = 0

    native_ref_available_count = 0
    synthetic_sem_agree_count = 0

    features = {}

    for r in rows:
        feat = r.get("feature", "unknown")
        if feat not in features:
            features[feat] = {
                "total": 0,
                "native_dec_correct": 0,
                "synthetic_dec_correct": 0,
                "native_ref_available": 0,
                "synthetic_sem_agreement": 0,
                # Backwards-compatible aliases
                "native_sem_correct": 0,
                "synthetic_sem_correct": 0
            }

        features[feat]["total"] += 1

        exp = str(r.get("expected", "")).upper()
        n_act = str(r.get("native_actual", "")).upper()
        s_act = str(r.get("synthetic_actual", "")).upper()

        n_count = int(r.get("native_resource_count", 0))
        s_count = int(r.get("synthetic_resource_count", 0))

        n_res_val = str(r.get("native_resolved_value", ""))
        s_res_val = str(r.get("synthetic_resolved_value", ""))

        # 1. Independent policy decision correctness against ground truth
        n_dec = (n_act == exp) and (n_act not in ["ERROR", "UNKNOWN"])
        s_dec = (s_act == exp) and (s_act not in ["ERROR", "UNKNOWN"])

        if n_dec:
            native_decision_correct += 1
            features[feat]["native_dec_correct"] += 1

        if s_dec:
            synthetic_decision_correct += 1
            features[feat]["synthetic_dec_correct"] += 1

        # 2. Native Reference Oracle Availability
        n_ref_avail = (n_count > 0 and n_act not in ["ERROR", "UNKNOWN"])
        if n_ref_avail:
            native_ref_available_count += 1
            features[feat]["native_ref_available"] += 1
            features[feat]["native_sem_correct"] += 1

        # 3. Synthetic Semantic Agreement with Native Terraform Oracle
        s_agree = check_semantic_agreement(n_count, s_count, n_res_val, s_res_val)
        if s_agree:
            synthetic_sem_agree_count += 1
            features[feat]["synthetic_sem_agreement"] += 1
            features[feat]["synthetic_sem_correct"] += 1

    native_ref_rate = round(safe_divide(native_ref_available_count, total), 4)
    synthetic_agree_rate = round(safe_divide(synthetic_sem_agree_count, total), 4)

    return {
        "total": total,
        "native_decision_accuracy": round(safe_divide(native_decision_correct, total), 4),
        "synthetic_decision_accuracy": round(safe_divide(synthetic_decision_correct, total), 4),
        "native_reference_available": native_ref_available_count,
        "native_reference_rate": native_ref_rate,
        "synthetic_semantic_agreement_count": synthetic_sem_agree_count,
        "synthetic_semantic_agreement_rate": synthetic_agree_rate,
        # Backwards-compatible aliases
        "native_semantic_accuracy": native_ref_rate,
        "synthetic_semantic_accuracy": synthetic_agree_rate,
        "by_feature": features
    }

def load_rl_comparison_csv(filepath: str) -> List[Dict[str, Any]]:
    """Loads rl_comparison.csv handling unquoted comma-separated action lists and optional state_source gracefully."""
    if not os.path.exists(filepath):
        return []
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        has_source = "state_source" in header
        source_idx = header.index("state_source") if has_source else -1
        strat_idx = header.index("strategy") if "strategy" in header else (2 if has_source else 1)
        seed_idx = header.index("seed") if "seed" in header else (3 if has_source else 2)

        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) == len(header):
                records.append(dict(zip(header, parts)))
            elif len(parts) > len(header):
                rec = {
                    "state_id": parts[0],
                    "state_source": parts[source_idx] if has_source and len(parts) > source_idx else "UNKNOWN",
                    "strategy": parts[strat_idx],
                    "seed": parts[seed_idx],
                    "initial_state": parts[seed_idx + 1] if len(parts) > seed_idx + 1 else "",
                    "final_state": parts[-12],
                    "automatic_terminal_success": parts[-11],
                    "steps": parts[-10],
                    "remediation_cost": parts[-9],
                    "complexity": parts[-8],
                    "cumulative_reward": parts[-7],
                    "runtime_ms": parts[-6],
                    "training_episodes": parts[-5],
                    "alpha": parts[-4],
                    "gamma": parts[-3],
                    "epsilon": parts[-2],
                    "error": parts[-1]
                }
                records.append(rec)
    return records


def calculate_rl_comparison_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes average steps, cost, complexity, and cumulative reward per strategy.
    """
    by_strategy = {}
    for r in rows:
        strat = r.get("strategy", "UNKNOWN")
        if strat not in by_strategy:
            by_strategy[strat] = {
                "count": 0,
                "terminal_success_count": 0,
                "steps": [],
                "costs": [],
                "complexities": [],
                "rewards": [],
                "runtimes": []
            }

        by_strategy[strat]["count"] += 1
        if str(r.get("automatic_terminal_success", "")).lower() == "true":
            by_strategy[strat]["terminal_success_count"] += 1

        try:
            by_strategy[strat]["steps"].append(float(r.get("steps", 0)))
        except ValueError:
            pass
        try:
            by_strategy[strat]["costs"].append(float(r.get("remediation_cost", 0)))
        except ValueError:
            pass
        try:
            by_strategy[strat]["complexities"].append(float(r.get("complexity", 0)))
        except ValueError:
            pass
        try:
            by_strategy[strat]["rewards"].append(float(r.get("cumulative_reward", 0)))
        except ValueError:
            pass
        try:
            by_strategy[strat]["runtimes"].append(float(r.get("runtime_ms", 0)))
        except ValueError:
            pass

    results = {}
    for strat, data in by_strategy.items():
        n = data["count"]
        results[strat] = {
            "n": n,
            "success_rate": round(safe_divide(data["terminal_success_count"], n), 4),
            "mean_steps": round(float(np.mean(data["steps"])), 2) if data["steps"] else 0.0,
            "mean_cost": round(float(np.mean(data["costs"])), 2) if data["costs"] else 0.0,
            "mean_complexity": round(float(np.mean(data["complexities"])), 2) if data["complexities"] else 0.0,
            "mean_reward": round(float(np.mean(data["rewards"])), 2) if data["rewards"] else 0.0,
            "mean_runtime_ms": round(float(np.mean(data["runtimes"])), 2) if data["runtimes"] else 0.0
        }

    return results

def calculate_remediation_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates detailed automatic remediation, validation, replan, idempotency,
    and manual safety rates from remediation.csv.
    """
    total = len(rows)
    auto_attempts = 0
    auto_fail_to_pass = 0
    validation_successes = 0
    replan_successes = 0
    idempotent_count = 0
    manual_safety_success = 0
    safe_skips = 0

    for r in rows:
        is_manual = str(r.get("manual_only", "")).lower() == "true"
        is_skip = str(r.get("safe_skip", "")).lower() == "true"
        init_st = str(r.get("initial_status", "")).upper()
        fin_st = str(r.get("final_status", "")).upper()
        src_chg = str(r.get("source_changed", "")).lower() == "true"
        val_succ = str(r.get("terraform_validation_success", "")).lower() == "true"
        plan_succ = str(r.get("native_plan_success", "")).lower() == "true"
        idemp = str(r.get("idempotent", "")).lower() == "true"

        if is_manual:
            if not src_chg and is_skip:
                manual_safety_success += 1
        else:
            auto_attempts += 1
            if init_st == "FAIL" and fin_st == "PASS":
                auto_fail_to_pass += 1
            if val_succ:
                validation_successes += 1
            if plan_succ:
                replan_successes += 1
            if idemp:
                idempotent_count += 1

        if is_skip:
            safe_skips += 1

    return {
        "total_fixtures": total,
        "automatic_remediation_attempts": auto_attempts,
        "automatic_fail_to_pass": auto_fail_to_pass,
        "automatic_success_rate": round(safe_divide(auto_fail_to_pass, auto_attempts), 4),
        "validation_success_rate": round(safe_divide(validation_successes, auto_attempts), 4),
        "native_replan_success_rate": round(safe_divide(replan_successes, auto_attempts), 4),
        "idempotency_rate": round(safe_divide(idempotent_count, auto_attempts), 4),
        "manual_safety_success_rate": round(safe_divide(manual_safety_success, total - auto_attempts), 4) if (total - auto_attempts) > 0 else 1.0,
        "safe_skip_rate": round(safe_divide(safe_skips, total), 4)
    }

def calculate_fail_closed_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates fail-closed safety rate, distinguishing compliance from authorization."""
    total = len(rows)
    blocked_count = 0
    unsafe_authorizations = 0

    for r in rows:
        exp_auth = str(r.get("expected_authorized", "")).lower() == "true"
        act_auth = str(r.get("actual_authorized", "")).lower() == "true"
        is_blocked = str(r.get("blocked", "")).lower() == "true"

        if is_blocked:
            blocked_count += 1
        
        # Unsafe authorization: authorization was granted when expected was false
        if not exp_auth and act_auth:
            unsafe_authorizations += 1

    return {
        "total_scenarios": total,
        "blocked_count": blocked_count,
        "blocked_rate": round(safe_divide(blocked_count, total), 4),
        "unsafe_authorizations": unsafe_authorizations,
        "fail_closed_integrity": (unsafe_authorizations == 0)
    }

def calculate_security_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates security validation pass rate and identifies any mismatches."""
    total = len(rows)
    passed_count = sum(1 for r in rows if str(r.get("passed", "")).lower() == "true")
    mismatches = [r["scenario"] for r in rows if str(r.get("passed", "")).lower() != "true"]

    return {
        "total_scenarios": total,
        "passed_count": passed_count,
        "pass_rate": round(safe_divide(passed_count, total), 4),
        "mismatches": mismatches
    }

def calculate_performance_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes n, mean, median, sample stddev, p95, min, max per operation,
    strictly excluding warmup=True iterations.
    """
    by_op = {}
    for r in rows:
        is_warmup = str(r.get("warmup", "")).lower() == "true"
        if is_warmup:
            continue

        op = r.get("operation", "UNKNOWN")
        if op not in by_op:
            by_op[op] = []
        try:
            dur = float(r.get("duration_ms", 0))
            by_op[op].append(dur)
        except ValueError:
            pass

    results = {}
    for op, data in by_op.items():
        n = len(data)
        if n == 0:
            continue
        arr = np.array(data, dtype=float)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0
        p95_val = float(np.percentile(arr, 95))
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))

        results[op] = {
            "n": n,
            "mean_ms": round(mean_val, 4),
            "median_ms": round(median_val, 4),
            "stddev_ms": round(std_val, 4),
            "p95_ms": round(p95_val, 4),
            "min_ms": round(min_val, 4),
            "max_ms": round(max_val, 4)
        }

    return results
