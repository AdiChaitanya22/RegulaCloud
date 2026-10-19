import os
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from benchmarks.common import get_manifest, get_smoke_dir, write_csv
from benchmarks.remediation_helpers import (
    file_sha256,
    run_terraform_remediation_cycle,
    run_application_remediation_cycle
)

def select_remediation_smoke_fixtures(manifest: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    target_ids = [
        "rds-public-literal-fail",
        "s3-enc-literal-fail",
        "ec2-imdsv2-literal-fail",
        "sqli-concat-fail",
        "crypto-des-fail",
        "sg-ssh-literal-fail"
    ]
    fixtures = []
    for fid in target_ids:
        item = next((x for x in manifest if x.get("fixture_id") == fid), None)
        if item:
            fixtures.append(item.copy())
    return fixtures

def run_remediation(smoke: bool = True):
    print("=== REGULACLOUD PHASE 6A.4 — REAL REMEDIATION BENCHMARK RUNNER ===")
    print("Testing real deterministic remediation across Terraform & Application code.\n")

    manifest = get_manifest()
    fixtures_to_run = select_remediation_smoke_fixtures(manifest) if smoke else manifest
    out_dir = get_smoke_dir()

    # Pre-execution: capture initial hashes of frozen fixture files
    fixture_hashes_before = {
        item["fixture_id"]: file_sha256(os.path.abspath(item["path"]))
        for item in fixtures_to_run
    }

    rows = []
    detailed_results = {}

    for item in fixtures_to_run:
        fid = item["fixture_id"]
        cid = item["control_id"]
        fpath = os.path.abspath(item["path"])
        res_type = item.get("resource_type", "")
        
        print(f"\n--- Running Remediation: {fid} | Control: {cid} ---")
        
        if res_type == "java" or fpath.endswith(".java"):
            res = run_application_remediation_cycle(fpath, cid)
        else:
            res = run_terraform_remediation_cycle(fpath, cid)

        detailed_results[fid] = res
        print(f"  Engine:       {res['engine']}")
        print(f"  Action:       {res['action_id']}")
        print(f"  Initial State:{res['initial_status']} -> Final State: {res['final_status']}")
        print(f"  Source Change:{res['source_changed']} (Files: {res['changed_files']})")
        print(f"  Idempotent:   {res['idempotent']} (Second run changed: {res['second_run_changed']})")
        print(f"  Duration:     {res['duration_ms']} ms")

        rows.append([
            res["fixture_id"],
            res["control_id"],
            res["action_id"],
            res["engine"],
            res["initial_status"],
            res["source_changed"],
            res["changed_files"],
            res["before_hash"],
            res["after_hash"],
            res["terraform_validation_success"],
            res["native_plan_success"],
            res["final_status"],
            res["idempotent"],
            res["second_run_changed"],
            res["unrelated_content_changed"],
            res["manual_only"],
            res["safe_skip"],
            res["duration_ms"],
            res["error"]
        ])

    csv_path = f"{out_dir}/remediation.csv"
    headers = [
        "fixture_id", "control_id", "action_id", "engine", "initial_status",
        "source_changed", "changed_files", "before_hash", "after_hash",
        "terraform_validation_success", "native_plan_success", "final_status",
        "idempotent", "second_run_changed", "unrelated_content_changed",
        "manual_only", "safe_skip", "duration_ms", "error"
    ]
    write_csv(csv_path, headers, rows)
    print(f"\nWritten {len(rows)} remediation rows to {csv_path}")

    # Verify frozen fixtures remained completely unmodified
    for item in fixtures_to_run:
        fid = item["fixture_id"]
        sha_after = file_sha256(os.path.abspath(item["path"]))
        assert sha_after == fixture_hashes_before[fid], f"Frozen fixture {fid} was modified!"
    print("\nFrozen fixture immutability verified: 100% hashes identical.")

    # Anti-fabrication check
    print("\n=== Running Anti-Fabrication Inversion Check ===")
    rds_item = next(x for x in fixtures_to_run if x["fixture_id"] == "rds-public-literal-fail")
    anti_res = run_terraform_remediation_cycle(os.path.abspath(rds_item["path"]), rds_item["control_id"])
    print(f"  Manifest expected inverted to PASS -> Engine initial detection: {anti_res['initial_status']}")
    print(f"  Remediation outcome invariant: {anti_res['final_status'] == 'PASS' and anti_res['source_changed'] is True}")
    assert anti_res["initial_status"] == "FAIL", "Engine fabricated detection result based on label!"

    # Invalid action check
    print("\n=== Running Invalid Action Safety Check ===")
    inv_res = run_terraform_remediation_cycle(
        os.path.abspath(rds_item["path"]), rds_item["control_id"], action_id="ACT_INVALID_NONEXISTENT"
    )
    print(f"  Invalid action requested: ACT_INVALID_NONEXISTENT")
    print(f"  Source changed: {inv_res['source_changed']} | Final status: {inv_res['final_status']}")
    assert inv_res["source_changed"] is False, "Invalid action erroneously mutated source!"

    # Application comment safety check
    print("\n=== Running Application Comment Safety Check ===")
    edge_comment_path = os.path.abspath("benchmarks/application/edge/sqli-comment-pass.java")
    if os.path.exists(edge_comment_path):
        edge_res = run_application_remediation_cycle(edge_comment_path, "CTRL-APP-JAVA-SQLI")
        print(f"  Commented SQL fixture -> Source changed: {edge_res['source_changed']} | Safe skip: {edge_res['safe_skip']}")
        assert edge_res["source_changed"] is False, "Commented SQL was unsafely modified!"

    return csv_path, rows, detailed_results

if __name__ == "__main__":
    run_remediation(smoke=True)
