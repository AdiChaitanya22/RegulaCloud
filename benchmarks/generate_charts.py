import os
import sys
import csv
import argparse
from typing import List, Dict, Any

# Configure headless matplotlib backend before importing pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def validate_run_dir(run_dir: str, allow_invalid: bool = False) -> None:
    """Verifies run directory exists and does not represent an invalid run."""
    if not os.path.exists(run_dir):
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    
    if "INVALID" in os.path.abspath(run_dir).upper() and not allow_invalid:
        raise ValueError(
            f"REFUSED: Target run directory '{run_dir}' contains 'INVALID'. "
            "Use --allow-invalid flag explicitly if conducting forensic analysis."
        )

def read_csv_safely(filepath: str, required_cols: List[str] = None) -> List[Dict[str, Any]]:
    """Reads a CSV file and validates required columns."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if required_cols:
            missing = [c for c in required_cols if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"CSV {filepath} missing required columns: {missing}")
        return list(reader)

from benchmarks.metrics_calculator import check_semantic_agreement, load_rl_comparison_csv

def generate_native_vs_synthetic_chart(run_dir: str, charts_dir: str) -> str:
    """Renders native_vs_synthetic_correctness.png distinguishing policy decision correctness from synthetic semantic agreement."""
    csv_path = os.path.join(run_dir, "native_vs_synthetic.csv")
    rows = read_csv_safely(csv_path, ["feature", "native_correct", "synthetic_correct", "native_resource_count", "synthetic_resource_count"])
    if not rows:
        return ""

    features = []
    native_dec_acc = []
    synth_dec_acc = []
    synth_sem_agree = []

    # Group by feature
    feat_map = {}
    for r in rows:
        f = r["feature"]
        if f not in feat_map:
            feat_map[f] = {"n_tot": 0, "n_dec": 0, "s_dec": 0, "s_agree": 0}
        feat_map[f]["n_tot"] += 1
        if str(r.get("native_correct", "")).lower() == "true":
            feat_map[f]["n_dec"] += 1
        if str(r.get("synthetic_correct", "")).lower() == "true":
            feat_map[f]["s_dec"] += 1
        
        # Semantic agreement check with Native reference oracle
        n_cnt = int(r.get("native_resource_count", 0))
        s_cnt = int(r.get("synthetic_resource_count", 0))
        n_res = r.get("native_resolved_value", "")
        s_res = r.get("synthetic_resolved_value", "")
        if check_semantic_agreement(n_cnt, s_cnt, n_res, s_res):
            feat_map[f]["s_agree"] += 1

    for f, d in feat_map.items():
        features.append(f)
        native_dec_acc.append((d["n_dec"] / d["n_tot"]) * 100)
        synth_dec_acc.append((d["s_dec"] / d["n_tot"]) * 100)
        synth_sem_agree.append((d["s_agree"] / d["n_tot"]) * 100)

    x = np.arange(len(features))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width, native_dec_acc, width, label="Native Policy Decision Acc (%)", color="#1f77b4")
    ax.bar(x, synth_dec_acc, width, label="Synthetic Policy Decision Acc (%)", color="#aec7e8")
    ax.bar(x + width, synth_sem_agree, width, label="Synthetic Semantic Agreement with Native (%)", color="#2ca02c")

    ax.set_ylabel("Accuracy / Agreement Rate (%)")
    ax.set_title(f"Native vs Synthetic Policy Correctness & Semantic Agreement by Feature (n = {len(rows)})")
    ax.set_xticks(x)
    ax.set_xticklabels(features, rotation=15)
    ax.set_ylim(0, 115)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    out_file = os.path.join(charts_dir, "native_vs_synthetic_correctness.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file


def parse_pct_value(val: Any) -> float:
    """Parses percentage string or float safely to 0-100 range."""
    s = str(val).strip().replace("%", "")
    try:
        f = float(s)
        return f if f > 1.0 else f * 100.0
    except ValueError:
        return 0.0

def generate_rl_strategy_cost_chart(run_dir: str, charts_dir: str) -> str:
    """Renders rl_strategy_cost.png comparing mean remediation cost per strategy."""
    csv_path = os.path.join(run_dir, "rl_comparison.csv")
    rows = load_rl_comparison_csv(csv_path)
    if not rows:
        return ""

    strat_costs = {}
    for r in rows:
        s = r.get("strategy", "UNKNOWN")
        if s not in strat_costs:
            strat_costs[s] = []
        try:
            strat_costs[s].append(float(r["remediation_cost"]))
        except (ValueError, KeyError):
            pass

    strategies = list(strat_costs.keys())
    means = [np.mean(strat_costs[s]) for s in strategies]
    stds = [np.std(strat_costs[s]) if len(strat_costs[s]) > 1 else 0.0 for s in strategies]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(strategies, means, yerr=stds, capsize=5, color="#ff7f0e", alpha=0.85)
    ax.set_ylabel("Mean Remediation Cost (Penalty Units)")
    ax.set_title(f"Remediation Cost by Strategy (n = {len(rows)} evaluations)")
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1, f"{val:.1f}", ha="center", va="bottom", fontsize=9)

    out_file = os.path.join(charts_dir, "rl_strategy_cost.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file

def generate_rl_strategy_steps_chart(run_dir: str, charts_dir: str) -> str:
    """Renders rl_strategy_steps.png comparing mean steps to compliance per strategy."""
    csv_path = os.path.join(run_dir, "rl_comparison.csv")
    rows = load_rl_comparison_csv(csv_path)
    if not rows:
        return ""

    strat_steps = {}
    for r in rows:
        s = r.get("strategy", "UNKNOWN")
        if s not in strat_steps:
            strat_steps[s] = []
        try:
            strat_steps[s].append(float(r["steps"]))
        except (ValueError, KeyError):
            pass

    strategies = list(strat_steps.keys())
    means = [np.mean(strat_steps[s]) for s in strategies]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(strategies, means, color="#17becf", alpha=0.85)
    ax.set_ylabel("Mean Steps to Resolution")
    ax.set_title(f"Action Steps by Strategy (n = {len(rows)} evaluations)")
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05, f"{val:.2f}", ha="center", va="bottom", fontsize=9)

    out_file = os.path.join(charts_dir, "rl_strategy_steps.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file

def generate_rl_learning_curve_chart(run_dir: str, charts_dir: str) -> str:
    """Renders rl_learning_curve.png displaying training episodes vs mean reward & success rate."""
    csv_path = os.path.join(run_dir, "rl_learning_curve.csv")
    rows = read_csv_safely(csv_path, ["episode_count", "mean_reward", "terminal_success_rate"])
    if not rows:
        return ""

    episodes = [int(r["episode_count"]) for r in rows]
    rewards = [float(r["mean_reward"]) for r in rows]
    success_rates = [parse_pct_value(r["terminal_success_rate"]) for r in rows]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    color = "tab:blue"
    ax1.set_xlabel("Training Episodes")
    ax1.set_ylabel("Mean Reward", color=color)
    ax1.plot(episodes, rewards, color=color, marker="o", linewidth=2, label="Mean Reward")
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2 = ax1.twinx()
    color = "tab:green"
    ax2.set_ylabel("Terminal Success Rate (%)", color=color)
    ax2.plot(episodes, success_rates, color=color, marker="s", linestyle="--", linewidth=2, label="Success Rate")
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.set_ylim(0, 110)

    plt.title(f"Q-Learning Policy Stability Curve ({len(rows)} Checkpoints)")
    out_file = os.path.join(charts_dir, "rl_learning_curve.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file

def generate_scale_runtime_chart(run_dir: str, charts_dir: str) -> str:
    """Renders runtime_vs_resource_count.png showing execution latency vs resource count."""
    csv_path = os.path.join(run_dir, "scale.csv")
    rows = read_csv_safely(csv_path, ["resource_count_requested", "total_ms", "plan_ms", "show_ms"])
    if not rows:
        return ""

    counts = [int(r["resource_count_requested"]) for r in rows]
    total_sec = [float(r["total_ms"]) / 1000.0 for r in rows]
    plan_sec = [float(r["plan_ms"]) / 1000.0 for r in rows]
    show_sec = [float(r["show_ms"]) / 1000.0 for r in rows]

    x = np.arange(len(counts))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width, plan_sec, width, label="terraform plan (s)", color="#9467bd")
    ax.bar(x, show_sec, width, label="terraform show (s)", color="#bcbd22")
    ax.bar(x + width, total_sec, width, label="Total Pipeline (s)", color="#d62728")

    ax.set_xlabel("Resource Count")
    ax.set_ylabel("Execution Time (Seconds)")
    ax.set_title("Terraform Pipeline Latency vs Resource Count (Offline Mock Provider)")
    ax.set_xticks(x)
    ax.set_xticklabels([str(c) for c in counts])
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    out_file = os.path.join(charts_dir, "runtime_vs_resource_count.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file

def generate_remediation_chart(run_dir: str, charts_dir: str) -> str:
    """Renders remediation_success.png displaying automatic vs manual outcomes and idempotency."""
    csv_path = os.path.join(run_dir, "remediation.csv")
    rows = read_csv_safely(csv_path, ["action_id", "initial_status", "final_status", "idempotent", "manual_only"])
    if not rows:
        return ""

    total = len(rows)
    auto_rows = [r for r in rows if str(r.get("manual_only", "")).lower() != "true"]
    manual_rows = [r for r in rows if str(r.get("manual_only", "")).lower() == "true"]

    auto_resolved = sum(1 for r in auto_rows if r.get("initial_status") == "FAIL" and r.get("final_status") == "PASS")
    idempotent_count = sum(1 for r in auto_rows if str(r.get("idempotent", "")).lower() == "true")
    manual_safe = sum(1 for r in manual_rows if str(r.get("source_changed", "")).lower() != "true")

    categories = [
        f"Auto Fail->Pass\n({auto_resolved}/{len(auto_rows)})",
        f"Idempotent Pass\n({idempotent_count}/{len(auto_rows)})",
        f"Manual Safety Safe\n({manual_safe}/{len(manual_rows)})"
    ]
    rates = [
        (auto_resolved / len(auto_rows) * 100) if auto_rows else 0.0,
        (idempotent_count / len(auto_rows) * 100) if auto_rows else 0.0,
        (manual_safe / len(manual_rows) * 100) if manual_rows else 100.0
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(categories, rates, color=["#2ca02c", "#1f77b4", "#ff7f0e"], alpha=0.85)
    ax.set_ylabel("Success Rate (%)")
    ax.set_title(f"Deterministic Remediation & Manual Safety (n = {total} cases)")
    ax.set_ylim(0, 115)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    for bar, val in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{val:.1f}%", ha="center", va="bottom", fontsize=10)

    out_file = os.path.join(charts_dir, "remediation_success.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file

def generate_all_charts(run_dir: str, allow_invalid: bool = False) -> List[str]:
    """Generates all verified PNG charts from real source CSV data in run_dir."""
    validate_run_dir(run_dir, allow_invalid=allow_invalid)
    charts_dir = os.path.join(run_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)

    generated = []
    print(f"Generating charts for run directory: {run_dir}...")

    chart_funcs = [
        generate_native_vs_synthetic_chart,
        generate_rl_strategy_cost_chart,
        generate_rl_strategy_steps_chart,
        generate_rl_learning_curve_chart,
        generate_scale_runtime_chart,
        generate_remediation_chart
    ]

    for fn in chart_funcs:
        out = fn(run_dir, charts_dir)
        if out and os.path.exists(out):
            size = os.path.getsize(out)
            generated.append(out)
            print(f"  ✓ Rendered {os.path.basename(out)} ({size} bytes)")

    print(f"Successfully generated {len(generated)} genuine matplotlib charts in {charts_dir}")
    return generated

generate_charts = generate_all_charts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate genuine matplotlib benchmark charts.")
    parser.add_argument("--run-dir", type=str, required=True, help="Path to benchmark run directory")
    parser.add_argument("--allow-invalid", action="store_true", help="Allow processing invalid directories")
    args = parser.parse_args()

    generate_all_charts(args.run_dir, allow_invalid=args.allow_invalid)
