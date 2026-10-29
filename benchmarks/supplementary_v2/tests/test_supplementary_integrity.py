import os
import sys
import json
import subprocess
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, WORKSPACE_ROOT)

from backend.app.engines.terraform_cli import TerraformCLI
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
V2_DIR = os.path.join(WORKSPACE_ROOT, "benchmarks", "supplementary_v2")
MANIFEST_PATH = os.path.join(V2_DIR, "manifest_v2.json")


@pytest.fixture(scope="module")
def manifest_data():
    assert os.path.isfile(MANIFEST_PATH), f"Manifest file missing: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def test_manifest_schema_and_paths_exist(manifest_data):
    """Verify all 40 manifest entries contain required schema fields and paths exist."""
    required_fields = {
        "fixture_id", "experiment_group", "path", "fixture_type", "control_id",
        "expected_status", "feature", "expected_resource_count", "expected_resolved_value",
        "remediation_action", "remediation_expectation", "manual_only", "notes"
    }
    assert len(manifest_data) == 40, f"Expected 40 manifest entries, got {len(manifest_data)}"

    seen_ids = set()
    for entry in manifest_data:
        missing = required_fields - set(entry.keys())
        assert not missing, f"Entry {entry.get('fixture_id')} missing fields: {missing}"

        # Unique fixture IDs
        fid = entry["fixture_id"]
        assert fid not in seen_ids, f"Duplicate fixture_id: {fid}"
        seen_ids.add(fid)

        # Path exists
        full_path = os.path.join(WORKSPACE_ROOT, entry["path"])
        assert os.path.exists(full_path), f"Fixture path does not exist: {full_path}"

        # Ensure no V1 path is referenced
        assert "supplementary_v2" in entry["path"], f"Accidental V1 path reference: {entry['path']}"
        assert not entry["path"].startswith("benchmarks/terraform/"), f"Points to V1: {entry['path']}"
        assert not entry["path"].startswith("benchmarks/application/"), f"Points to V1: {entry['path']}"


def test_classification_balance(manifest_data):
    """Verify classification corpus has balanced PASS/FAIL pairs across 11 controls."""
    class_rows = [r for r in manifest_data if r["experiment_group"] == "CLASSIFICATION" and r["fixture_type"] == "terraform"]
    assert len(class_rows) == 22, f"Expected 22 Terraform classification fixtures, found {len(class_rows)}"

    pass_rows = [r for r in class_rows if r["expected_status"] == "PASS"]
    fail_rows = [r for r in class_rows if r["expected_status"] == "FAIL"]
    assert len(pass_rows) == 11, f"Expected 11 PASS fixtures, got {len(pass_rows)}"
    assert len(fail_rows) == 11, f"Expected 11 FAIL fixtures, got {len(fail_rows)}"

    pass_ctrls = sorted([r["control_id"] for r in pass_rows])
    fail_ctrls = sorted([r["control_id"] for r in fail_rows])
    assert pass_ctrls == fail_ctrls, f"Mismatched controls in classification pairs: {pass_ctrls} vs {fail_ctrls}"
    assert len(set(pass_ctrls)) == 11, f"Expected 11 unique controls, got {len(set(pass_ctrls))}"


def test_terraform_fixtures_provider_validity(manifest_data):
    """Verify all Terraform fixtures pass offline terraform init, validate, plan, and show."""
    tf_rows = [r for r in manifest_data if r["fixture_type"] == "terraform"]
    assert len(tf_rows) == 32  # 22 classification + 10 semantic

    for row in tf_rows:
        path = os.path.join(WORKSPACE_ROOT, row["path"])
        # If directory (e.g. module fixture), pass dir; if file, pass dir containing it in temp or parent
        if os.path.isdir(path):
            target_dir = path
        else:
            # For isolated execution of single file, we pass its file path or directory
            # TerraformCLI.generate_plan_json handles directories by copying .tf files
            # To isolate each single-file fixture, we test it in its own isolated directory
            import tempfile, shutil
            with tempfile.TemporaryDirectory() as td:
                shutil.copy(path, os.path.join(td, os.path.basename(path)))
                res = TerraformCLI.generate_plan_json(td)
                assert res.success, f"Fixture {row['fixture_id']} failed at stage {res.failure_stage}: {res.stderr}"
                assert res.validation_status == "PASS"
                assert "resource_changes" in res.plan_json
                continue

        res = TerraformCLI.generate_plan_json(target_dir)
        assert res.success, f"Fixture {row['fixture_id']} failed at stage {res.failure_stage}: {res.stderr}"
        assert res.validation_status == "PASS"


def test_semantic_expectations_match_native_output(manifest_data):
    """Verify semantic fixtures match frozen ground truth resource counts and status."""
    sem_rows = [r for r in manifest_data if r["experiment_group"] == "SEMANTIC"]
    assert len(sem_rows) == 10

    for row in sem_rows:
        path = os.path.join(WORKSPACE_ROOT, row["path"])
        import tempfile, shutil
        if os.path.isdir(path):
            res = TerraformCLI.generate_plan_json(path)
        else:
            with tempfile.TemporaryDirectory() as td:
                shutil.copy(path, os.path.join(td, os.path.basename(path)))
                res = TerraformCLI.generate_plan_json(td)

        assert res.success
        rc = res.plan_json.get("resource_changes", [])
        assert len(rc) == row["expected_resource_count"], (
            f"Fixture {row['fixture_id']} resource count mismatch: expected {row['expected_resource_count']}, got {len(rc)}"
        )

        findings = OPAPolicyEvaluator.evaluate_terraform_plan(res.plan_json)
        violating_ctrls = [f["control_id"] for f in findings]
        actual_status = "FAIL" if row["control_id"] in violating_ctrls else "PASS"
        assert actual_status == row["expected_status"], (
            f"Fixture {row['fixture_id']} status mismatch: expected {row['expected_status']}, got {actual_status}"
        )


def test_compilable_java_fixtures_compile(manifest_data):
    """Verify all 8 Java fixtures compile cleanly with javac without external dependencies."""
    java_rows = [r for r in manifest_data if r["fixture_type"] == "java"]
    assert len(java_rows) == 8

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        for row in java_rows:
            src_path = os.path.join(WORKSPACE_ROOT, row["path"])
            proc = subprocess.run(["javac", "-d", td, src_path], capture_output=True, text=True)
            assert proc.returncode == 0, f"Java compilation failed for {row['fixture_id']}:\n{proc.stderr}"
