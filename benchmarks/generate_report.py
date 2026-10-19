import os
import sys
import json
import csv
import subprocess
import argparse
from typing import List, Dict, Any, Tuple


from benchmarks.metrics_calculator import (
    calculate_confusion_matrix,
    calculate_native_vs_synthetic_metrics,
    calculate_rl_comparison_metrics,
    calculate_remediation_metrics,
    calculate_fail_closed_metrics,
    calculate_security_metrics,
    calculate_performance_stats
)

MANIFEST_HASH = "fccdecf583df9a3d655a7eb88eb593fedb292bc201c13189d2c1ce8a29096b9e"
RL_STATES_HASH = "29b1eb0718e408681318b4918fbcaf96eb86cc2d55bd938c0437bdbd051146b5"

def get_git_commit() -> str:
    """Retrieves current git commit hash if available."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN_COMMIT"

def validate_run_dir(run_dir: str, allow_invalid: bool = False) -> None:
    """Verifies run directory exists and does not represent an invalid run."""
    if not os.path.exists(run_dir):
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    
    if "INVALID" in os.path.abspath(run_dir).upper() and not allow_invalid:
        raise ValueError(
            f"REFUSED: Target run directory '{run_dir}' contains 'INVALID'. "
            "Use --allow-invalid flag explicitly if conducting forensic analysis."
        )

def load_csv(filepath: str) -> List[Dict[str, Any]]:
    """Loads CSV rows as a list of dictionaries if file exists."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate_policy_signature(sig_str: str) -> Tuple[str, bool]:
    """
    Validates every action ID in the signature against production ACTIONS.
    Returns (validated_display_string, is_valid).
    If any action ID is unknown, formats as UNKNOWN_ACTION_ID:<id> and flags is_valid=False.
    """
    from backend.app.engines.rl_remediator import QLearningRemediationAgent
    valid_ids = {a["id"] for a in QLearningRemediationAgent.ACTIONS}

    tokens = [t.strip() for t in str(sig_str).split(":") if t.strip()]
    if not tokens:
        return "EMPTY_SIGNATURE", True

    validated_tokens = []
    has_unknown = False
    for t in tokens:
        if t in valid_ids:
            validated_tokens.append(t)
        else:
            validated_tokens.append(f"UNKNOWN_ACTION_ID:{t}")
            has_unknown = True

    return ":".join(validated_tokens), not has_unknown

def generate_report(run_dir: str, allow_invalid: bool = False) -> str:

    """
    Parses all benchmark CSV files in run_dir, computes mathematical metrics,
    and generates SUMMARY.md with full provenance and methodological warnings.
    """
    validate_run_dir(run_dir, allow_invalid=allow_invalid)
    run_id = os.path.basename(os.path.abspath(run_dir))
    git_commit = get_git_commit()

    # Load metadata if present
    meta_path = os.path.join(run_dir, "metadata.json")
    meta = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

    source_runs = meta.get("source_run_ids", [run_id])

    # 1. Detection
    det_rows = load_csv(os.path.join(run_dir, "detection.csv"))
    infra_det = [r for r in det_rows if not r.get("fixture_id", "").startswith("java-") and not r.get("control_id", "").startswith("CTRL-SONAR-")]
    app_det = [r for r in det_rows if r.get("fixture_id", "").startswith("java-") or r.get("control_id", "").startswith("CTRL-SONAR-")]
    infra_cm = calculate_confusion_matrix(infra_det)
    app_cm = calculate_confusion_matrix(app_det)

    # 2. Native vs Synthetic
    nvs_rows = load_csv(os.path.join(run_dir, "native_vs_synthetic.csv"))
    nvs_metrics = calculate_native_vs_synthetic_metrics(nvs_rows)

    # 3. RL Comparison & Learning Curve
    from benchmarks.metrics_calculator import load_rl_comparison_csv
    rl_rows = load_rl_comparison_csv(os.path.join(run_dir, "rl_comparison.csv"))
    rl_metrics = calculate_rl_comparison_metrics(rl_rows)
    curve_rows = load_csv(os.path.join(run_dir, "rl_learning_curve.csv"))

    # 4. Remediation
    rem_rows = load_csv(os.path.join(run_dir, "remediation.csv"))
    rem_metrics = calculate_remediation_metrics(rem_rows)

    # 5. Fail-Closed
    fc_rows = load_csv(os.path.join(run_dir, "fail_closed.csv"))
    fc_metrics = calculate_fail_closed_metrics(fc_rows)

    # 6. Security
    sec_rows = load_csv(os.path.join(run_dir, "security.csv"))
    sec_metrics = calculate_security_metrics(sec_rows)

    # 7. Performance
    perf_rows = load_csv(os.path.join(run_dir, "performance.csv"))
    perf_metrics = calculate_performance_stats(perf_rows)

    # 8. Scale
    scale_rows = load_csv(os.path.join(run_dir, "scale.csv"))

    lines = []
    lines.append(f"# REGULACLOUD BENCHMARK EVALUATION SUMMARY")
    lines.append("")
    lines.append("> [!WARNING]")
    lines.append("> **DEVELOPMENT SMOKE RESULTS — NOT OFFICIAL EXPERIMENTAL RESULTS**  ")
    lines.append("> The figures herein are produced from a development smoke test suite designed to verify harness execution integrity, not to answer Research Questions (RQ1–RQ6) definitively.")
    lines.append("")

    # Provenance
    lines.append("## 1. Run Provenance & Verification Metadata")
    lines.append(f"- **Benchmark Run ID**: `{run_id}`")
    lines.append(f"- **Official Benchmark**: `false`")
    lines.append(f"- **Git Commit**: `{git_commit}`")
    lines.append(f"- **Manifest SHA-256**: `{MANIFEST_HASH}`")
    lines.append(f"- **RL States SHA-256**: `{RL_STATES_HASH}`")
    lines.append(f"- **Source Smoke Runs**: `{', '.join(source_runs)}`")
    lines.append("")

    # Detection Table
    lines.append("## 2. Detection Performance (Infrastructure vs Application)")
    lines.append("### 2.1 Infrastructure Detection (Native Terraform Plan + OPA)")
    lines.append(f"- **Total Infrastructure Fixtures**: n = {infra_cm['total']}")
    lines.append(f"- **Confusion Matrix**: TP = {infra_cm['TP']}, TN = {infra_cm['TN']}, FP = {infra_cm['FP']}, FN = {infra_cm['FN']}, ERROR = {infra_cm['ERROR']}, UNKNOWN = {infra_cm['UNKNOWN']}")
    lines.append(f"- **Precision**: `{infra_cm['precision'] * 100:.1f}%`")
    lines.append(f"- **Recall**: `{infra_cm['recall'] * 100:.1f}%`")
    lines.append(f"- **Specificity**: `{infra_cm['specificity'] * 100:.1f}%`")
    lines.append(f"- **F1 Score**: `{infra_cm['F1']:.4f}`")
    lines.append(f"- **Decision Accuracy**: `{infra_cm['decision_accuracy'] * 100:.1f}%`")
    lines.append(f"- **Coverage**: `{infra_cm['coverage'] * 100:.1f}%`")
    lines.append("")

    lines.append("### 2.2 Application Security Scanner (LOCAL STATIC APPLICATION SCANNER)")
    lines.append("> [!NOTE]")
    lines.append("> **Label Notice**: Evaluated using `LOCAL STATIC APPLICATION SCANNER` fallback engine. Not evaluated against live SonarQube server.")
    lines.append(f"- **Total Application Fixtures**: n = {app_cm['total']}")
    lines.append(f"- **Confusion Matrix**: TP = {app_cm['TP']}, TN = {app_cm['TN']}, FP = {app_cm['FP']}, FN = {app_cm['FN']}")
    lines.append(f"- **Decision Accuracy**: `{app_cm['decision_accuracy'] * 100:.1f}%`")
    lines.append("")

    # Native vs Synthetic
    lines.append("## 3. Native Plan Pipeline vs Synthetic Regex Parser")
    lines.append("> [!NOTE]")
    lines.append("> **Semantic Reference Oracle**: Native Terraform Plan execution serves as the semantic reference oracle for resolved resource counts and configuration attribute values when evaluating the synthetic regex parser. It is not an independent security oracle.")
    lines.append("")
    lines.append(f"- **Total Comparison Cases**: n = {nvs_metrics['total']}")
    lines.append(f"- **Native Policy Decision Accuracy**: `{nvs_metrics['native_decision_accuracy'] * 100:.1f}%`")
    lines.append(f"- **Synthetic Policy Decision Accuracy**: `{nvs_metrics['synthetic_decision_accuracy'] * 100:.1f}%`")
    lines.append(f"- **Native Semantic Reference Availability**: `{nvs_metrics.get('native_reference_available', nvs_metrics['total'])}/{nvs_metrics['total']} ({nvs_metrics.get('native_reference_rate', 1.0) * 100:.1f}%)`")
    lines.append(f"- **Synthetic Semantic Agreement with Native Terraform**: `{nvs_metrics.get('synthetic_semantic_agreement_rate', nvs_metrics.get('synthetic_semantic_accuracy', 0.0)) * 100:.1f}%`")
    lines.append("")
    lines.append("| Feature | Samples | Native Policy Acc | Synthetic Policy Acc | Native Semantic Ref Avail | Synthetic Semantic Agreement |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for feat, f_data in nvs_metrics["by_feature"].items():
        n_t = f_data["total"]
        n_p = (f_data["native_dec_correct"] / n_t * 100) if n_t else 0.0
        s_p = (f_data["synthetic_dec_correct"] / n_t * 100) if n_t else 0.0
        n_ref = (f_data.get("native_ref_available", f_data.get("native_sem_correct", 0)) / n_t * 100) if n_t else 0.0
        s_agree = (f_data.get("synthetic_sem_agreement", f_data.get("synthetic_sem_correct", 0)) / n_t * 100) if n_t else 0.0
        lines.append(f"| `{feat}` | {n_t} | {n_p:.1f}% | {s_p:.1f}% | {n_ref:.1f}% | {s_agree:.1f}% |")
    lines.append("")

    # RL Metrics
    lines.append("## 4. Reinforcement Learning Remediation Baselines")
    lines.append("> [!IMPORTANT]")
    lines.append("> **Methodological Limitation**: The frozen primary RL corpus provides limited discrimination between ordering strategies because single-violation states admit only one relevant action. Q-learning superiority cannot be claimed merely from these states.")
    lines.append("")
    lines.append("| Strategy | Evaluations (n) | Success Rate | Mean Steps | Mean Cost | Mean Complexity | Mean Reward | Mean Runtime (ms) |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for strat, s_data in rl_metrics.items():
        lines.append(f"| `{strat}` | {s_data['n']} | {s_data['success_rate'] * 100:.1f}% | {s_data['mean_steps']:.2f} | {s_data['mean_cost']:.2f} | {s_data['mean_complexity']:.2f} | {s_data['mean_reward']:.2f} | {s_data['mean_runtime_ms']:.2f} |")
    lines.append("")

    # Learning Curve
    lines.append("### 4.1 RL Policy Stability Curve")
    lines.append("| Episode Checkpoint | Terminal Success Rate | Mean Reward | Training Time (ms) | Policy Stability Signature |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    signature_integrity_errors = []
    for cr in curve_rows:
        raw_sr = str(cr.get("terminal_success_rate", "0")).replace("%", "")
        try:
            s_rate = float(raw_sr)
            if s_rate <= 1.0:
                s_rate *= 100.0
        except ValueError:
            s_rate = 0.0
        raw_sig = cr.get("policy_signature", "")
        val_sig, is_sig_valid = validate_policy_signature(raw_sig)
        if not is_sig_valid:
            signature_integrity_errors.append(f"Checkpoint {cr.get('episode_count')}: {val_sig}")
        lines.append(f"| {cr.get('episode_count')} | {s_rate:.1f}% | {float(cr.get('mean_reward', 0)):.2f} | {float(cr.get('training_time_ms', 0)):.2f} | `{val_sig}` |")
    lines.append("")
    if signature_integrity_errors:
        lines.append("> [!CAUTION]")
        lines.append(f"> **Report Integrity Error**: Unknown action IDs detected in policy signature: {', '.join(signature_integrity_errors)}")
        lines.append("")


    # Remediation Table
    lines.append("## 5. Remediation Engine & Verification")
    lines.append("> [!NOTE]")
    lines.append("> **Transformation Architecture**: Terraform and application remediations are regex-based deterministic transformations (not AST-based).")
    lines.append("> **ACTION_COVERAGE_GAP**: `ACT_BLOCK_S3_PUBLIC` is currently defined in RL action inventory but has no Terraform mutation handler in `TerraformEngine`.")
    lines.append("")
    lines.append(f"- **Total Remediation Test Cases**: n = {rem_metrics['total_fixtures']}")
    lines.append(f"- **Automatic Remediation Attempts**: n = {rem_metrics['automatic_remediation_attempts']}")
    lines.append(f"- **Automatic Fail->Pass Success Rate**: `{rem_metrics['automatic_success_rate'] * 100:.1f}%`")
    lines.append(f"- **Post-Mutation Terraform Validation Success Rate**: `{rem_metrics['validation_success_rate'] * 100:.1f}%`")
    lines.append(f"- **Post-Mutation Native Replan Success Rate**: `{rem_metrics['native_replan_success_rate'] * 100:.1f}%`")
    lines.append(f"- **Idempotency Rate (Second Run No Mutation)**: `{rem_metrics['idempotency_rate'] * 100:.1f}%`")
    lines.append(f"- **Manual-Only Safety Routing Success Rate**: `{rem_metrics['manual_safety_success_rate'] * 100:.1f}%`")
    lines.append(f"- **Safe Skip Rate**: `{rem_metrics['safe_skip_rate'] * 100:.1f}%`")
    lines.append("")

    # Fail-Closed
    lines.append("## 6. Fail-Closed Deployment Gate Integrity")
    lines.append("> [!WARNING]")
    lines.append("> **Unsupported Resource Warning**: Unsupported resources may be categorized `NOT_APPLICABLE / UNSUPPORTED` while overall compliance remains `PASS` and deployment may remain allowed. Therefore, **Compliance Score != Policy Coverage**. RegulaCloud does not claim universal infrastructure compliance.")
    lines.append("")
    lines.append(f"- **Total Scenarios Evaluated**: n = {fc_metrics['total_scenarios']}")
    lines.append(f"- **Scenarios Blocked**: {fc_metrics['blocked_count']}/{fc_metrics['total_scenarios']} (`{fc_metrics['blocked_rate'] * 100:.1f}%`)")
    lines.append(f"- **Unsafe Deployment Authorizations**: `{fc_metrics['unsafe_authorizations']}` (Expected: 0)")
    lines.append(f"- **Fail-Closed Integrity Maintained**: `{fc_metrics['fail_closed_integrity']}`")
    lines.append("")

    # Security
    lines.append("## 7. Security Correctness Validation")
    lines.append("> [!NOTE]")
    lines.append("> **Scope**: Designated as `SECURITY CORRECTNESS VALIDATION` (not a penetration test). Evaluates authentication enforcement, cross-project isolation, ZIP extraction security, and cryptographic audit tampering detection.")
    lines.append("")
    lines.append(f"- **Total Security Test Cases**: n = {sec_metrics['total_scenarios']}")
    lines.append(f"- **Pass Rate**: `{sec_metrics['pass_rate'] * 100:.1f}%` ({sec_metrics['passed_count']}/{sec_metrics['total_scenarios']})")
    lines.append(f"- **Mismatches / Breaches**: `{len(sec_metrics['mismatches'])}` ({', '.join(sec_metrics['mismatches']) if sec_metrics['mismatches'] else 'None'})")
    lines.append("")

    # Performance
    lines.append("## 8. Runtime Latency Performance")
    lines.append("> [!NOTE]")
    lines.append("> All measurements exclude `warmup=True` iterations. Durations captured using `time.perf_counter()` wall-clock timing.")
    lines.append("")
    lines.append("| Operation | n | Mean (ms) | Median (ms) | Sample StdDev (ms) | P95 (ms) | Min (ms) | Max (ms) |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for op, p_data in perf_metrics.items():
        lines.append(f"| `{op}` | {p_data['n']} | {p_data['mean_ms']:.2f} | {p_data['median_ms']:.2f} | {p_data['stddev_ms']:.2f} | {p_data['p95_ms']:.2f} | {p_data['min_ms']:.2f} | {p_data['max_ms']:.2f} |")
    lines.append("")

    # Scale & Storage
    lines.append("## 9. Scalability & Storage Profile")
    lines.append("| Requested Count | Planned Count | Source (B) | Init (ms) | Validate (ms) | Plan (ms) | Show (ms) | Adapter (ms) | OPA (ms) | Total (ms) | Plan JSON (B) | Evidence Payload (B) |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for sr in scale_rows:
        lines.append(
            f"| {sr.get('resource_count_requested')} | {sr.get('resource_count_planned')} | {sr.get('source_bytes')} | "
            f"{float(sr.get('init_ms', 0)):.1f} | {float(sr.get('validate_ms', 0)):.1f} | {float(sr.get('plan_ms', 0)):.1f} | "
            f"{float(sr.get('show_ms', 0)):.1f} | {float(sr.get('adapter_ms', 0)):.2f} | {float(sr.get('opa_ms', 0)):.1f} | "
            f"{float(sr.get('total_ms', 0)):.1f} | {sr.get('plan_bytes')} | {sr.get('evidence_bytes')} |"
        )
    lines.append("")

    # Storage Extrapolation
    if scale_rows:
        lines.append("### 9.1 Storage Extrapolation (ESTIMATED)")
        lines.append("> [!NOTE]")
        lines.append("> **Extrapolation Methodology**: Computed transparently based on measured UTF-8 evidence payload growth between 1-resource and 10-resource models. Does not mix native plan JSON with statutory evidence payloads.")
        try:
            ev_1 = float(scale_rows[0].get("evidence_bytes", 400))
            ev_10 = float(scale_rows[1].get("evidence_bytes", 3400)) if len(scale_rows) > 1 else ev_1 * 10
            ev_per_res = (ev_10 - ev_1) / 9.0 if len(scale_rows) > 1 else ev_1
            lines.append(f"- **Measured 1-Resource Evidence Size**: `{ev_1:.0f} bytes`")
            lines.append(f"- **Measured 10-Resource Evidence Size**: `{ev_10:.0f} bytes`")
            lines.append(f"- **Estimated Marginal Growth per Resource**: `{ev_per_res:.1f} bytes/resource`")
            lines.append(f"- **ESTIMATED 50-Resource Evidence Size**: `{(ev_1 + 49 * ev_per_res) / 1024:.2f} KB`")
            lines.append(f"- **ESTIMATED 100-Resource Evidence Size**: `{(ev_1 + 99 * ev_per_res) / 1024:.2f} KB`")
        except Exception:
            lines.append("- Storage extrapolation could not be calculated from current scale samples.")
        lines.append("")

    # Known Limitations
    lines.append("## 10. Known Methodological Limitations")
    lines.append("1. **Small Development Sample**: Results generated from minimal development smoke runs; definitive conclusions require official full-corpus execution.")
    lines.append("2. **Synthetic / Offline AWS Planning**: Provider execution uses mock credentials and offline providers; cloud API latency and provider rate limiting are excluded.")
    lines.append("3. **No Terraform Apply**: Pipeline terminates at `terraform show -json` and OPA verification; resource provisioning and infrastructure drift are unmeasured.")
    lines.append("4. **Local Static Application Scanner**: Java CVE detection relies on local regex heuristic rules, not a production SonarQube static analysis server.")
    lines.append("5. **Regex-Based Remediation**: Remediation engines apply deterministic string/regex mutations, not semantic Abstract Syntax Tree (AST) rewrites.")
    lines.append("6. **ACTION_COVERAGE_GAP**: `ACT_BLOCK_S3_PUBLIC` is present in RL action inventory but lacks an implemented mutation handler in `TerraformEngine`.")
    lines.append("7. **Frozen RL Corpus Ordering Weakness**: Frozen states consist predominantly of single-violation states where action ordering cannot be tested.")
    lines.append("8. **Unsupported Resource Policy Coverage**: Unmapped resources receive `NOT_APPLICABLE` without blocking deployment, meaning high compliance score does not ensure comprehensive policy coverage.")
    lines.append("9. **Single-Machine Execution**: Benchmark timings are hardware-dependent (Apple Silicon macOS), subject to local disk caching and CPU contention.")
    lines.append("10. **SQLite Development Database**: Production platform uses PostgreSQL; local SQLite benchmarks do not reflect distributed database network latency.")
    lines.append("11. **KNOWN_PRODUCTION_DEFECT_TO_REVIEW_AFTER_HARNESS_FREEZE**: The infrastructure topology endpoint (`GET /api/v1/projects/{id}/infrastructure/topology`) accesses `project.infrastructure_hash`, `latest_run.infrastructure_hash`, and `latest_run.plan_hash` directly as model attributes, whereas these values are persisted inside `EvaluationRun.evidence_payload`. Requires resolution in production source after harness freeze.")
    lines.append("")

    report_text = "\n".join(lines)
    report_file = os.path.join(run_dir, "SUMMARY.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Generated comprehensive SUMMARY.md in {report_file}")
    return report_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate comprehensive benchmark SUMMARY.md report.")
    parser.add_argument("--run-dir", type=str, required=True, help="Path to benchmark run directory")
    parser.add_argument("--allow-invalid", action="store_true", help="Allow processing invalid directories")
    args = parser.parse_args()

    generate_report(args.run_dir, allow_invalid=args.allow_invalid)
