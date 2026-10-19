import os
import shutil
import tempfile
import hashlib
import csv
import pytest
import numpy as np

from benchmarks.metrics_calculator import (
    safe_divide,
    calculate_confusion_matrix,
    calculate_native_vs_synthetic_metrics,
    calculate_rl_comparison_metrics,
    calculate_remediation_metrics,
    calculate_fail_closed_metrics,
    calculate_security_metrics,
    calculate_performance_stats,
    normalize_semantic_value,
    check_semantic_agreement,
)
from benchmarks.generate_report import (
    generate_report,
    validate_run_dir as validate_report_run_dir,
    validate_policy_signature,
)
from benchmarks.generate_charts import (
    generate_charts,
    generate_native_vs_synthetic_chart,
    validate_run_dir as validate_charts_run_dir,
)
from benchmarks.runner_rl_baseline import get_smoke_states, get_official_states
from benchmarks.common import get_rl_states


# ==============================================================================
# SECTION 24: METRIC UNIT TESTS
# ==============================================================================

def test_confusion_matrix_known_values():
    """Validates precision, recall, specificity, F1, accuracy, and coverage with known inputs."""
    rows = [
        # 4 TPs (exp=FAIL, act=FAIL)
        {"expected": "FAIL", "actual": "FAIL"},
        {"expected": "FAIL", "actual": "FAIL"},
        {"expected": "FAIL", "actual": "FAIL"},
        {"expected": "FAIL", "actual": "FAIL"},
        # 3 TNs (exp=PASS, act=PASS)
        {"expected": "PASS", "actual": "PASS"},
        {"expected": "PASS", "actual": "PASS"},
        {"expected": "PASS", "actual": "PASS"},
        # 1 FP (exp=PASS, act=FAIL)
        {"expected": "PASS", "actual": "FAIL"},
        # 2 FNs (exp=FAIL, act=PASS)
        {"expected": "FAIL", "actual": "PASS"},
        {"expected": "FAIL", "actual": "PASS"},
        # Non-decisive categories
        {"expected": "FAIL", "actual": "ERROR"},
        {"expected": "PASS", "actual": "UNKNOWN"},
        {"expected": "PASS", "actual": "UNSUPPORTED"},
        {"expected": "PASS", "actual": "NOT_APPLICABLE"},
    ]
    # Total = 14 rows
    # Decisive = 4 + 3 + 1 + 2 = 10
    # TP = 4, TN = 3, FP = 1, FN = 2
    # Precision = 4 / (4 + 1) = 0.8
    # Recall = 4 / (4 + 2) = 4 / 6 = 0.6667
    # Specificity = 3 / (3 + 1) = 0.75
    # F1 = 2 * (0.8 * (4/6)) / (0.8 + (4/6)) = 16/22 = 0.7273
    # Decision Accuracy = (4 + 3) / 10 = 0.7
    # Coverage = 10 / 14 = 0.7143

    m = calculate_confusion_matrix(rows)
    assert m["total"] == 14
    assert m["TP"] == 4
    assert m["TN"] == 3
    assert m["FP"] == 1
    assert m["FN"] == 2
    assert m["ERROR"] == 1
    assert m["UNKNOWN"] == 1
    assert m["UNSUPPORTED"] == 1
    assert m["NOT_APPLICABLE"] == 1

    assert m["precision"] == 0.8
    assert m["recall"] == 0.6667
    assert m["specificity"] == 0.75
    assert m["F1"] == 0.7273
    assert m["decision_accuracy"] == 0.7
    assert m["coverage"] == 0.7143

def test_zero_denominator_safety():
    """Ensures division by zero yields 0.0 without throwing exceptions."""
    assert safe_divide(10.0, 0.0) == 0.0
    assert safe_divide(0.0, 0.0) == 0.0

    empty_m = calculate_confusion_matrix([])
    assert empty_m["total"] == 0
    assert empty_m["precision"] == 0.0
    assert empty_m["recall"] == 0.0
    assert empty_m["specificity"] == 0.0
    assert empty_m["F1"] == 0.0
    assert empty_m["decision_accuracy"] == 0.0
    assert empty_m["coverage"] == 0.0

    # Test no positive cases (TP=0, FP=0)
    tn_only = [{"expected": "PASS", "actual": "PASS"}]
    tn_m = calculate_confusion_matrix(tn_only)
    assert tn_m["precision"] == 0.0
    assert tn_m["recall"] == 0.0
    assert tn_m["specificity"] == 1.0
    assert tn_m["decision_accuracy"] == 1.0

def test_distribution_statistics_known_values():
    """Validates mean, median, sample stddev, p95, min, max, and warmup exclusion."""
    # Data: [10, 20, 30, 40, 50], plus warmup=True row with 999
    rows = [
        {"operation": "test_op", "duration_ms": 10.0, "warmup": "false"},
        {"operation": "test_op", "duration_ms": 20.0, "warmup": "false"},
        {"operation": "test_op", "duration_ms": 30.0, "warmup": "false"},
        {"operation": "test_op", "duration_ms": 40.0, "warmup": "false"},
        {"operation": "test_op", "duration_ms": 50.0, "warmup": "false"},
        {"operation": "test_op", "duration_ms": 999.0, "warmup": "true"},  # Must be ignored
    ]
    stats = calculate_performance_stats(rows)
    assert "test_op" in stats
    s = stats["test_op"]
    assert s["n"] == 5
    assert s["mean_ms"] == 30.0
    assert s["median_ms"] == 30.0
    # Sample stddev with ddof=1: sqrt((400 + 100 + 0 + 100 + 400) / 4) = sqrt(250) ≈ 15.8114
    assert s["stddev_ms"] == 15.8114
    # 95th percentile of [10, 20, 30, 40, 50]
    expected_p95 = round(float(np.percentile([10, 20, 30, 40, 50], 95)), 4)
    assert s["p95_ms"] == expected_p95
    assert s["min_ms"] == 10.0
    assert s["max_ms"] == 50.0

# ==============================================================================
# SECTION 25: REPORT ANTI-FABRICATION TEST
# ==============================================================================

def test_report_anti_fabrication():
    """
    Creates temporary CSV data (TP=1, TN=1, FP=1, FN=1), generates report,
    verifies computed metrics, alters rows, re-runs, and verifies metrics changed.
    Proves SUMMARY.md is dynamically calculated rather than hardcoded.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        det_csv = os.path.join(tmp_dir, "detection.csv")

        # Dataset A: TP=1, TN=1, FP=1, FN=1
        rows_a = [
            {"framework": "terraform", "rule_id": "CKV_01", "expected": "FAIL", "actual": "FAIL"},
            {"framework": "terraform", "rule_id": "CKV_02", "expected": "PASS", "actual": "PASS"},
            {"framework": "terraform", "rule_id": "CKV_03", "expected": "PASS", "actual": "FAIL"},
            {"framework": "terraform", "rule_id": "CKV_04", "expected": "FAIL", "actual": "PASS"},
        ]
        with open(det_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["framework", "rule_id", "expected", "actual"])
            writer.writeheader()
            writer.writerows(rows_a)

        generate_report(tmp_dir)
        summary_path = os.path.join(tmp_dir, "SUMMARY.md")
        assert os.path.exists(summary_path)
        with open(summary_path, "r", encoding="utf-8") as f:
            content_a = f.read()

        # In dataset A: TP=1, FP=1 -> precision = 50.0%, accuracy = 50.0%
        assert "50.0%" in content_a

        # Dataset B: Change FP to TN -> TP=1, TN=2, FP=0, FN=1
        # Precision becomes 100.0%, Accuracy becomes 75.0%
        rows_b = [
            {"framework": "terraform", "rule_id": "CKV_01", "expected": "FAIL", "actual": "FAIL"},
            {"framework": "terraform", "rule_id": "CKV_02", "expected": "PASS", "actual": "PASS"},
            {"framework": "terraform", "rule_id": "CKV_03", "expected": "PASS", "actual": "PASS"},
            {"framework": "terraform", "rule_id": "CKV_04", "expected": "FAIL", "actual": "PASS"},
        ]
        with open(det_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["framework", "rule_id", "expected", "actual"])
            writer.writeheader()
            writer.writerows(rows_b)

        generate_report(tmp_dir)
        with open(summary_path, "r", encoding="utf-8") as f:
            content_b = f.read()

        assert "100.0%" in content_b
        assert "75.0%" in content_b
        assert content_a != content_b


# ==============================================================================
# SECTION 26: CHART ANTI-FABRICATION TEST
# ==============================================================================

def test_chart_anti_fabrication():
    """
    Generates chart from temporary CSV dataset A, alters data significantly to dataset B,
    and verifies the resulting PNG byte hashes differ.
    Proves charts are rendered from CSV data rather than static templates.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "native_vs_synthetic.csv")
        charts_dir = os.path.join(tmp_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)

        fieldnames = ["feature", "native_correct", "synthetic_correct", "native_resource_count", "synthetic_resource_count"]

        # Dataset A: Single feature with 100% native correct, 0% synthetic
        rows_a = [
            {"feature": "literal", "native_correct": "True", "synthetic_correct": "False", "native_resource_count": 1, "synthetic_resource_count": 0},
            {"feature": "literal", "native_correct": "True", "synthetic_correct": "False", "native_resource_count": 1, "synthetic_resource_count": 0},
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_a)

        chart_file_a = generate_native_vs_synthetic_chart(tmp_dir, charts_dir)
        assert os.path.exists(chart_file_a)
        with open(chart_file_a, "rb") as f:
            hash_a = hashlib.sha256(f.read()).hexdigest()

        # Dataset B: Multiple different features with inverted correctness and resource counts
        rows_b = [
            {"feature": "module", "native_correct": "False", "synthetic_correct": "True", "native_resource_count": 0, "synthetic_resource_count": 5},
            {"feature": "count", "native_correct": "True", "synthetic_correct": "True", "native_resource_count": 3, "synthetic_resource_count": 3},
            {"feature": "for_each", "native_correct": "False", "synthetic_correct": "False", "native_resource_count": 0, "synthetic_resource_count": 0},
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_b)

        chart_file_b = generate_native_vs_synthetic_chart(tmp_dir, charts_dir)
        with open(chart_file_b, "rb") as f:
            hash_b = hashlib.sha256(f.read()).hexdigest()

        # Hashes must differ because chart rendering reflects changed data
        assert hash_a != hash_b

# ==============================================================================
# SECTION 27: INVALID RUN PROTECTION
# ==============================================================================

def test_invalid_run_protection():
    """
    Verifies that attempting generation on directories containing 'INVALID' is strictly refused
    by default, preventing accidental publication of synthetic or fabricated data.
    """
    invalid_dir = "benchmark_results/1791380137-INVALID-SYNTHESIZED"

    # Charts generator must raise ValueError by default
    with pytest.raises(ValueError) as excinfo_charts:
        validate_charts_run_dir(invalid_dir)
    assert "REFUSED" in str(excinfo_charts.value)
    assert "INVALID" in str(excinfo_charts.value)

    # Report generator must raise ValueError by default
    with pytest.raises(ValueError) as excinfo_report:
        validate_report_run_dir(invalid_dir)
    assert "REFUSED" in str(excinfo_report.value)
    assert "INVALID" in str(excinfo_report.value)

    # Both generators should permit execution when allow_invalid=True is explicitly passed
    validate_charts_run_dir(invalid_dir, allow_invalid=True)
    validate_report_run_dir(invalid_dir, allow_invalid=True)

# ==============================================================================
# PHASE 6A.8 CORRECTION TESTS
# ==============================================================================

def test_semantic_agreement_oracle_cases():
    """
    Validates semantic agreement between Synthetic parser and Native Terraform reference oracle:
    CASE 1: Native count=2, Synthetic count=1, same policy decision -> semantic_agreement=False
    CASE 2: Native module count=2, Synthetic count=0, same PASS decision -> semantic_agreement=False
    CASE 3: Native resolved=true, Synthetic resolved=false -> semantic_agreement=False
    CASE 4: Native resolved=true, Synthetic resolved=true, same count -> semantic_agreement=True
    CASE 5: Native resolved=14, Synthetic resolved="14", same count -> semantic_agreement=True after normalization
    """
    # CASE 1: Partial count parse (Native=2, Synthetic=1)
    row_case1 = [{
        "feature": "count",
        "expected": "FAIL",
        "native_actual": "FAIL",
        "synthetic_actual": "FAIL",
        "native_resource_count": 2,
        "synthetic_resource_count": 1,
        "native_resolved_value": "14",
        "synthetic_resolved_value": "14"
    }]
    m1 = calculate_native_vs_synthetic_metrics(row_case1)
    assert m1["native_decision_accuracy"] == 1.0
    assert m1["synthetic_decision_accuracy"] == 1.0
    assert m1["synthetic_semantic_agreement_rate"] == 0.0
    assert not check_semantic_agreement(2, 1, "14", "14")

    # CASE 2: Module missing parse (Native=2, Synthetic=0)
    row_case2 = [{
        "feature": "module",
        "expected": "PASS",
        "native_actual": "PASS",
        "synthetic_actual": "PASS",
        "native_resource_count": 2,
        "synthetic_resource_count": 0,
        "native_resolved_value": "AES256",
        "synthetic_resolved_value": "None"
    }]
    m2 = calculate_native_vs_synthetic_metrics(row_case2)
    assert m2["native_decision_accuracy"] == 1.0
    assert m2["synthetic_decision_accuracy"] == 1.0
    assert m2["synthetic_semantic_agreement_rate"] == 0.0
    assert not check_semantic_agreement(2, 0, "AES256", "None")

    # CASE 3: Value mismatch (Native=true, Synthetic=false)
    assert not check_semantic_agreement(1, 1, True, False)
    assert not check_semantic_agreement(1, 1, "true", "false")

    # CASE 4: Identical boolean values & matching count
    assert check_semantic_agreement(1, 1, True, True)
    assert check_semantic_agreement(1, 1, "true", True)
    assert check_semantic_agreement(1, 1, False, False)

    # CASE 5: Numeric normalization (14 vs "14")
    assert check_semantic_agreement(2, 2, 14, "14")
    assert check_semantic_agreement(1, 1, "180", 180)
    assert normalize_semantic_value(14) == normalize_semantic_value("14") == "14"

def test_official_rl_state_isolation():
    """
    Verifies that the official RL baseline runner mode strictly isolates the 30 frozen states
    and refuses/excludes development-only synthetic states (state_multi, state_healthcare_b).
    """
    frozen_states = get_rl_states()
    frozen_ids = [s["state_id"] for s in frozen_states]
    assert len(frozen_states) == 30

    # Official mode (smoke=False)
    official_states = get_official_states()
    assert len(official_states) == 30
    official_ids = [s["state_id"] for s in official_states]
    assert official_ids == frozen_ids
    assert "state_multi" not in official_ids
    assert "state_healthcare_b" not in official_ids
    assert all(s["state_source"] == "FROZEN_CORPUS" for s in official_states)

    # Smoke mode (smoke=True)
    smoke_states = get_smoke_states()
    assert len(smoke_states) == 3
    smoke_ids = [s["state_id"] for s in smoke_states]
    assert "state_multi" in smoke_ids
    assert "state_healthcare_b" in smoke_ids

    # Verify development-only states are explicitly labeled
    for s in smoke_states:
        if s["state_id"] in ("state_multi", "state_healthcare_b"):
            assert s["state_source"] == "DEVELOPMENT_ONLY"
        else:
            assert s["state_source"] == "FROZEN_CORPUS"

def test_policy_signature_validation():
    """
    Verifies policy signature validation against production ACTIONS:
    - Known actions are preserved and displayed exactly.
    - Unknown actions are flagged with UNKNOWN_ACTION_ID:<id> and trigger integrity error.
    """
    valid_sig = "ACT_ENABLE_RDS_ENC:ACT_DISABLE_RDS_PUBLIC:ACT_DISABLE_RDS_PUBLIC"
    disp_valid, is_valid = validate_policy_signature(valid_sig)
    assert is_valid is True
    assert disp_valid == valid_sig

    single_action = "ACT_ENABLE_RDS_ENC"
    disp_single, is_single_valid = validate_policy_signature(single_action)
    assert is_single_valid is True
    assert disp_single == "ACT_ENABLE_RDS_ENC"

    corrupted_sig = "ACT_ENABLE_RDS_ENC:ACT_FAKE_ACTION:ACT_ENABLE_RDS_BACKUP"
    disp_corrupted, is_corrupted_valid = validate_policy_signature(corrupted_sig)
    assert is_corrupted_valid is False
    assert "UNKNOWN_ACTION_ID:ACT_FAKE_ACTION" in disp_corrupted
    assert "UNKNOWN_ACTION_ID:ACT_ENABLE_RDS_BACKUP" in disp_corrupted
    assert disp_corrupted == "ACT_ENABLE_RDS_ENC:UNKNOWN_ACTION_ID:ACT_FAKE_ACTION:UNKNOWN_ACTION_ID:ACT_ENABLE_RDS_BACKUP"

