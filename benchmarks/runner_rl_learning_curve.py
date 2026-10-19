import os
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from benchmarks.common import get_smoke_dir, write_csv
from backend.app.engines.rl_remediator import QLearningRemediationAgent
from benchmarks.rl_helpers import (
    train_isolated_agent,
    simulate_remediation,
    map_violations_to_binary_state,
    select_action
)
from benchmarks.runner_rl_baseline import get_smoke_states

def compute_policy_signature(agent: QLearningRemediationAgent, eval_states: List[Any], actions: List[Dict[str, Any]]) -> str:
    """
    Computes a deterministic policy signature across evaluation states by
    recording the greedy action selected at the initial state.
    Used for assessing POLICY STABILITY across training episode scales.
    """
    signature_tokens = []
    for s_tuple in eval_states:
        val_indices = [i for i, b in enumerate(s_tuple) if b == 1]
        best_idx = select_action("Q_LEARNING", s_tuple, val_indices, actions, q_agent=agent)
        signature_tokens.append(actions[best_idx]["id"])
    return ":".join(signature_tokens)

def run_rl_learning_curve(smoke: bool = True):
    print("=== REGULACLOUD PHASE 6A.3 — RL LEARNING CURVE BENCHMARK RUNNER ===")
    print("Evaluating training progression and POLICY STABILITY across episode scales.\n")

    actions = QLearningRemediationAgent.ACTIONS
    eval_state_items = get_smoke_states()
    eval_binary_states = [
        map_violations_to_binary_state(s["active_violations"], actions)
        for s in eval_state_items
    ]

    out_dir = get_smoke_dir()
    episode_counts = [50, 300] if smoke else [50, 300, 1000, 2000]
    seeds = [42, 123]

    rows = []
    headers = [
        "episode_count",
        "seed",
        "terminal_success_rate",
        "mean_reward",
        "training_time_ms",
        "policy_signature",
        "error"
    ]

    for ep in episode_counts:
        print(f"--- Training Episode Scale: {ep} ---")
        for s in seeds:
            agent, train_time_ms = train_isolated_agent(seed=s, episodes=ep)
            
            rewards = []
            terminal_successes = []
            for st in eval_binary_states:
                res = simulate_remediation("Q_LEARNING", st, actions, seed=s, q_agent=agent)
                rewards.append(res["cumulative_reward"])
                terminal_successes.append(1 if res["automatic_terminal_success"] else 0)

            term_rate = round(sum(terminal_successes) / len(terminal_successes) * 100, 1)
            mean_rew = round(sum(rewards) / len(rewards), 2)
            pol_sig = compute_policy_signature(agent, eval_binary_states, actions)

            print(f"  Episodes={ep:<4} | Seed={s:<3} | SuccessRate={term_rate}% | MeanReward={mean_rew:<7.2f} | TrainTime={train_time_ms}ms | Signature={pol_sig}")

            rows.append([
                ep,
                s,
                f"{term_rate}%",
                mean_rew,
                train_time_ms,
                pol_sig,
                "None"
            ])

    csv_path = f"{out_dir}/rl_learning_curve.csv"
    write_csv(csv_path, headers, rows)
    print(f"\nWritten {len(rows)} learning curve rows to {csv_path}")

    # Assess policy stability
    sig_50_42 = next(r[5] for r in rows if r[0] == 50 and r[1] == 42)
    sig_300_42 = next(r[5] for r in rows if r[0] == 300 and r[1] == 42)
    print("\n=== POLICY STABILITY ANALYSIS ===")
    print(f"  Seed 42 (50 eps)  Signature: {sig_50_42}")
    print(f"  Seed 42 (300 eps) Signature: {sig_300_42}")
    print(f"  Policy Signature Invariant: {sig_50_42 == sig_300_42}")

    return csv_path, rows

if __name__ == "__main__":
    run_rl_learning_curve(smoke=True)
