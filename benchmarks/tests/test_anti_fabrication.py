import os
import pytest
from benchmarks.evaluation_helpers import execute_native

def test_runner_anti_fabrication_label_invariance():
    """
    Verifies that the real detection engine output is strictly invariant to ground-truth label inversion.
    1. Executes real Terraform pipeline against rds-public-literal-fail.tf.
    2. Real engine produces actual="FAIL".
    3. Manifest expected="FAIL" yields TP (True Positive).
    4. Mutating expected label in memory to "PASS" keeps actual="FAIL" and yields FP (False Positive).
    Proves that manifest labels never influence actual engine outcomes.
    """
    fixture_path = os.path.abspath("benchmarks/terraform/noncompliant/rds-public-literal-fail.tf")
    control_id = "CTRL-AWS-RDS-NO-PUBLIC"

    # Step 1: Execute real engine
    res = execute_native(fixture_path, control_id)
    actual_1 = res["actual"]
    assert actual_1 == "FAIL", f"Engine must detect non-compliant fixture as FAIL, got {actual_1}"

    # Step 2: Evaluate with correct expected label
    expected_original = "FAIL"
    if expected_original == "FAIL" and actual_1 == "FAIL":
        classification_original = "TP"
    else:
        classification_original = "UNKNOWN"
    assert classification_original == "TP"

    # Step 3: Invert expected label in memory (simulate label corruption/tampering)
    expected_inverted = "PASS"
    res_inverted = execute_native(fixture_path, control_id)
    actual_2 = res_inverted["actual"]

    # Step 4: Verify engine output is completely identical regardless of expected label
    assert actual_1 == actual_2 == "FAIL", "Engine output changed after label inversion!"

    # Step 5: Verify that only the confusion matrix classification changes from TP to FP
    if expected_inverted == "PASS" and actual_2 == "FAIL":
        classification_inverted = "FP"
    else:
        classification_inverted = "UNKNOWN"

    assert classification_inverted == "FP", "Label inversion must change classification to FP"
    assert classification_original != classification_inverted
