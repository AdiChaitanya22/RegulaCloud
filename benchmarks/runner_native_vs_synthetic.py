import os
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from benchmarks.common import get_manifest, get_smoke_dir, write_csv
from benchmarks.evaluation_helpers import (
    execute_native,
    execute_synthetic,
    extract_feature
)

def select_smoke_fixtures(manifest: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    target_ids = [
        "rds-public-literal-fail",
        "rds-public-variable-fail",
        "rds-enc-local-pass",
        "s3-enc-module-pass",
        "cw-ret-count-fail"
    ]
    fixtures = []
    for fid in target_ids:
        item = next((x for x in manifest if x.get("fixture_id") == fid), None)
        if item:
            fixtures.append(item.copy())
    return fixtures

def run_native_vs_synthetic(smoke: bool = True):
    manifest = get_manifest()
    out_dir = get_smoke_dir()
    
    if smoke:
        fixtures_to_run = select_smoke_fixtures(manifest)
    else:
        fixtures_to_run = manifest

    rows = []
    print(f"=== Starting Native vs Synthetic Benchmark (Total Fixtures: {len(fixtures_to_run)}) ===")

    for item in fixtures_to_run:
        fixture_id = item["fixture_id"]
        control_id = item["control_id"]
        fixture_path = os.path.abspath(item["path"])
        feature = extract_feature(item.get("benchmark_tags", []))
        expected = item["expected_status"]
        
        print(f"\n--- Fixture: {fixture_id} | Control: {control_id} | Feature: {feature} ---")
        
        # 1. Native Execution
        nat_res = execute_native(fixture_path, control_id)
        native_actual = nat_res["actual"]
        native_duration_ms = nat_res["duration_ms"]
        native_error = nat_res["error"]
        native_resolved_val = nat_res["resolved_value"]
        native_res_count = nat_res["resource_count"]
        
        # 2. Synthetic Execution
        syn_res = execute_synthetic(fixture_path, control_id)
        synthetic_actual = syn_res["actual"]
        synthetic_duration_ms = syn_res["duration_ms"]
        synthetic_error = syn_res["error"]
        synthetic_resolved_val = syn_res["resolved_value"]
        synthetic_res_count = syn_res["resource_count"]
        
        # 3. Independent Correctness Evaluation
        native_correct = (native_actual == expected) if native_actual not in ["ERROR", "UNKNOWN"] else False
        synthetic_correct = (synthetic_actual == expected) if synthetic_actual not in ["ERROR", "UNKNOWN"] else False
        
        print(f"  Native:    Actual={native_actual:<5} Correct={str(native_correct):<5} Resources={native_res_count} Resolved={native_resolved_val} Dur={native_duration_ms}ms Err={native_error}")
        print(f"  Synthetic: Actual={synthetic_actual:<5} Correct={str(synthetic_correct):<5} Resources={synthetic_res_count} Resolved={synthetic_resolved_val} Dur={synthetic_duration_ms}ms Err={synthetic_error}")

        rows.append([
            fixture_id,
            control_id,
            feature,
            expected,
            native_actual,
            synthetic_actual,
            native_correct,
            synthetic_correct,
            native_resolved_val,
            synthetic_resolved_val,
            native_res_count,
            synthetic_res_count,
            native_duration_ms,
            synthetic_duration_ms,
            native_error,
            synthetic_error
        ])

    csv_path = f"{out_dir}/native_vs_synthetic.csv"
    headers = [
        "fixture_id",
        "control_id",
        "feature",
        "expected",
        "native_actual",
        "synthetic_actual",
        "native_correct",
        "synthetic_correct",
        "native_resolved_value",
        "synthetic_resolved_value",
        "native_resource_count",
        "synthetic_resource_count",
        "native_duration_ms",
        "synthetic_duration_ms",
        "native_error",
        "synthetic_error"
    ]
    write_csv(csv_path, headers, rows)
    print(f"\nWritten {len(rows)} rows to {csv_path}")

    # Anti-fabrication check on rds-public-literal-fail
    print("\n=== Running Anti-Fabrication Inversion Verification ===")
    test_item = next((x for x in fixtures_to_run if x["fixture_id"] == "rds-public-literal-fail"), fixtures_to_run[0])
    orig_expected = test_item["expected_status"]
    inverted_expected = "PASS" if orig_expected == "FAIL" else "FAIL"
    
    t_path = os.path.abspath(test_item["path"])
    t_ctrl = test_item["control_id"]
    
    n_res_orig = execute_native(t_path, t_ctrl)
    s_res_orig = execute_synthetic(t_path, t_ctrl)
    
    n_correct_orig = (n_res_orig["actual"] == orig_expected)
    s_correct_orig = (s_res_orig["actual"] == orig_expected)
    
    n_correct_inv = (n_res_orig["actual"] == inverted_expected)
    s_correct_inv = (s_res_orig["actual"] == inverted_expected)
    
    print(f"Anti-fabrication Fixture: {test_item['fixture_id']}")
    print(f"Original Expected: {orig_expected} -> Native Actual: {n_res_orig['actual']}, Synthetic Actual: {s_res_orig['actual']}")
    print(f"Original Correctness -> Native: {n_correct_orig}, Synthetic: {s_correct_orig}")
    print(f"Inverted Expected: {inverted_expected} -> Native Actual: {n_res_orig['actual']}, Synthetic Actual: {s_res_orig['actual']}")
    print(f"Inverted Correctness -> Native: {n_correct_inv}, Synthetic: {s_correct_inv}")
    assert n_res_orig["actual"] == "FAIL", "Native engine output changed or unexpected!"
    assert s_res_orig["actual"] == "FAIL", "Synthetic engine output changed or unexpected!"
    assert n_correct_orig != n_correct_inv, "Correctness must flip when expected flips!"
    print("Anti-fabrication verified: Engine outputs are invariant to ground-truth label inversion.")

    return csv_path, rows

if __name__ == "__main__":
    run_native_vs_synthetic(smoke=True)
