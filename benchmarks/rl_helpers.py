import os
import sys
import time
import random
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.engines.rl_remediator import QLearningRemediationAgent

SEVERITY_RANK = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3
}

def get_action_severity(action: Dict[str, Any]) -> str:
    """
    Determines severity from control/action mapping semantics.
    Controls with NO-PUBLIC, CRITICAL, or INJECTION are ranked Critical;
    all other compliance controls are ranked High.
    """
    tc = action.get("target_control", "")
    aid = action.get("id", "")
    if "NO-PUBLIC" in tc or "CRITICAL" in tc or "INJECTION" in tc or "CRITICAL" in aid:
        return "Critical"
    return "High"

def map_violations_to_binary_state(violations: List[str], actions: List[Dict[str, Any]]) -> Tuple[int, ...]:
    """
    Maps active violation representations to a concrete binary tuple state of length len(actions).
    Supports 'violation_X' indexed labels as well as canonical control IDs.
    """
    state = [0] * len(actions)
    for v in violations:
        if v.startswith("violation_") and v[len("violation_"):].isdigit():
            idx = int(v[len("violation_"):])
            if 0 <= idx < len(actions):
                state[idx] = 1
        else:
            for idx, a in enumerate(actions):
                if a["target_control"] == v or a["id"] == v:
                    state[idx] = 1
    return tuple(state)

def format_binary_state(state: Tuple[int, ...]) -> str:
    return "".join(str(b) for b in state)

def step_env(
    current_state: Tuple[int, ...],
    action_idx: int,
    actions: List[Dict[str, Any]]
) -> Tuple[Tuple[int, ...], int, int, float, bool]:
    """
    Standard state transition and reward calculation matching production rl_remediator.py.
    Returns: (next_state, cost_penalty, complexity_penalty, step_reward, is_successful)
    """
    next_state_list = list(current_state)
    cost = actions[action_idx]["cost_penalty"]
    comp = actions[action_idx]["complexity_penalty"]
    
    if next_state_list[action_idx] == 1:
        next_state_list[action_idx] = 0
        step_reward = 50.0 - float(cost + comp)
        is_successful = True
    else:
        step_reward = -10.0
        is_successful = False

    if sum(next_state_list) == 0:
        step_reward += 100.0

    return tuple(next_state_list), cost, comp, step_reward, is_successful

def select_action(
    strategy: str,
    current_state: Tuple[int, ...],
    valid_indices: List[int],
    actions: List[Dict[str, Any]],
    rng: Optional[random.Random] = None,
    q_agent: Optional[QLearningRemediationAgent] = None
) -> int:
    """
    Deterministic/stochastic action selection according to strategy specifications:
    - FIXED_ORDER: First valid action by declaration order.
    - SEVERITY_FIRST: Highest severity valid action (Critical > High > Medium > Low), tie-break by declaration order.
    - LOWEST_COST_FIRST: Valid action with lowest cost_penalty, tie-break by declaration order.
    - RANDOM: Uniformly sampled among valid actions using local seeded RNG.
    - Q_LEARNING: Argmax over masked Q-values from isolated trained agent.
    """
    if strategy == "FIXED_ORDER":
        return min(valid_indices)

    elif strategy == "SEVERITY_FIRST":
        # Sort by severity rank ascending (0 is Critical), then declaration order
        sorted_indices = sorted(
            valid_indices,
            key=lambda idx: (SEVERITY_RANK.get(get_action_severity(actions[idx]), 99), idx)
        )
        return sorted_indices[0]

    elif strategy == "LOWEST_COST_FIRST":
        # Sort by cost_penalty ascending, then declaration order
        sorted_indices = sorted(
            valid_indices,
            key=lambda idx: (actions[idx]["cost_penalty"], idx)
        )
        return sorted_indices[0]

    elif strategy == "RANDOM":
        if rng is None:
            raise ValueError("RANDOM strategy requires a seeded local RNG instance.")
        return rng.choice(valid_indices)

    elif strategy == "Q_LEARNING":
        if q_agent is None:
            raise ValueError("Q_LEARNING strategy requires an isolated trained Q-learning agent.")
        q_row = q_agent._get_q_row(current_state)
        masked_q = q_row.copy()
        for i in range(len(actions)):
            if i not in valid_indices:
                masked_q[i] = -9999.0
        best_idx = int(np.argmax(masked_q))
        return best_idx

    else:
        raise ValueError(f"Unknown RL strategy: {strategy}")

def simulate_remediation(
    strategy: str,
    initial_state: Tuple[int, ...],
    actions: List[Dict[str, Any]],
    seed: Optional[int] = None,
    q_agent: Optional[QLearningRemediationAgent] = None
) -> Dict[str, Any]:
    """
    Simulates remediation sequence using the common environment and metric calculations.
    """
    start_time = time.perf_counter()
    rng = random.Random(seed) if seed is not None else None

    current_state = initial_state
    selected_actions = []
    total_cost = 0
    total_complexity = 0
    cumulative_reward = 0.0
    successful_actions = 0
    skipped_actions = 0
    steps = 0

    max_steps = len(actions) * 2

    while sum(current_state) > 0 and steps < max_steps:
        valid_indices = [i for i, bit in enumerate(current_state) if bit == 1]
        if not valid_indices:
            break

        chosen_idx = select_action(
            strategy,
            current_state,
            valid_indices,
            actions,
            rng=rng,
            q_agent=q_agent
        )

        next_state, cost, comp, step_reward, is_successful = step_env(
            current_state,
            chosen_idx,
            actions
        )

        selected_actions.append(actions[chosen_idx]["id"])
        total_cost += cost
        total_complexity += comp
        cumulative_reward += step_reward
        steps += 1

        if is_successful:
            successful_actions += 1
        else:
            skipped_actions += 1

        current_state = next_state

    runtime_ms = round((time.perf_counter() - start_time) * 1000, 3)
    terminal_success = (sum(current_state) == 0)

    return {
        "strategy": strategy,
        "seed": seed if seed is not None else "None",
        "initial_state": format_binary_state(initial_state),
        "selected_actions": selected_actions,
        "successful_actions": successful_actions,
        "skipped_actions": skipped_actions,
        "final_state": format_binary_state(current_state),
        "automatic_terminal_success": terminal_success,
        "steps": steps,
        "remediation_cost": total_cost,
        "complexity": total_complexity,
        "cumulative_reward": round(cumulative_reward, 2),
        "runtime_ms": runtime_ms,
        "error": "None"
    }

def train_isolated_agent(
    seed: int,
    episodes: int = 500,
    alpha: float = 0.2,
    gamma: float = 0.9,
    epsilon: float = 0.2
) -> Tuple[QLearningRemediationAgent, float]:
    """
    Trains a clean, isolated QLearningRemediationAgent instance with local seed.
    Returns the trained agent and training duration in milliseconds.
    """
    start_time = time.perf_counter()
    agent = QLearningRemediationAgent(alpha=alpha, gamma=gamma, epsilon=epsilon)
    np.random.seed(seed)
    agent.train_simulator(episodes=episodes)
    train_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return agent, train_time_ms
