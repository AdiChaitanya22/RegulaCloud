import os
import sys
import json
import pytest
from collections import Counter

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, WORKSPACE_ROOT)

from backend.app.engines.rl_remediator import QLearningRemediationAgent
STATES_PATH = os.path.join(WORKSPACE_ROOT, "benchmarks", "supplementary_v2", "rl", "states_v2.json")


@pytest.fixture(scope="module")
def states_data():
    assert os.path.isfile(STATES_PATH), f"RL states file missing: {STATES_PATH}"
    with open(STATES_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def test_rl_total_states_and_uniqueness(states_data):
    """Verify exactly 30 states exist and all binary states are strictly unique."""
    assert len(states_data) == 30, f"Expected 30 RL states, got {len(states_data)}"

    seen_ids = set()
    binary_tuples = set()
    for state in states_data:
        sid = state["state_id"]
        assert sid not in seen_ids, f"Duplicate state_id: {sid}"
        seen_ids.add(sid)

        bstate = tuple(state["binary_state"])
        assert len(bstate) == 11, f"Binary state must be 11-dimensional, got {len(bstate)}"
        assert bstate not in binary_tuples, f"Duplicate binary state vector: {bstate}"
        binary_tuples.add(bstate)

    assert len(binary_tuples) == 30, "Found duplicate active-action state sets"


def test_rl_valid_indices_and_action_ids(states_data):
    """Verify all indices are within 0..10 and action IDs match production QLearningRemediationAgent."""
    prod_actions = QLearningRemediationAgent.ACTIONS
    assert len(prod_actions) == 11, f"Expected 11 production actions, found {len(prod_actions)}"

    for state in states_data:
        indices = state["active_action_indices"]
        assert all(0 <= i < 11 for i in indices), f"Invalid action index in {state['state_id']}: {indices}"
        assert len(indices) == len(set(indices)), f"Duplicate indices within state {state['state_id']}"

        # Verify action IDs match production actions exactly
        expected_action_ids = [prod_actions[i]["id"] for i in indices]
        assert state["active_action_ids"] == expected_action_ids, (
            f"Action ID mismatch in {state['state_id']}: expected {expected_action_ids}, got {state['active_action_ids']}"
        )

        # Verify active controls match
        expected_ctrls = [prod_actions[i]["target_control"] for i in indices]
        assert state["active_controls"] == expected_ctrls, (
            f"Control ID mismatch in {state['state_id']}: expected {expected_ctrls}, got {state['active_controls']}"
        )

        # Verify binary_state consistency
        for i in range(11):
            expected_bit = 1 if i in indices else 0
            assert state["binary_state"][i] == expected_bit, (
                f"Binary state bit mismatch at index {i} in {state['state_id']}"
            )


def test_rl_density_distribution(states_data):
    """Verify exact density distribution: single=5, dual=10, multi_3_to_5=10, dense_6_to_9=5."""
    counts = Counter(s["density_class"] for s in states_data)
    assert counts["single"] == 5, f"Expected 5 single states, got {counts['single']}"
    assert counts["dual"] == 10, f"Expected 10 dual states, got {counts['dual']}"
    assert counts["multi_3_to_5"] == 10, f"Expected 10 multi states (3-5), got {counts['multi_3_to_5']}"
    assert counts["dense_6_to_9"] == 5, f"Expected 5 dense states (6-9), got {counts['dense_6_to_9']}"

    # Verify active indices count strictly corresponds to declared density class
    for s in states_data:
        k = len(s["active_action_indices"])
        dclass = s["density_class"]
        if dclass == "single":
            assert k == 1
        elif dclass == "dual":
            assert k == 2
        elif dclass == "multi_3_to_5":
            assert 3 <= k <= 5
        elif dclass == "dense_6_to_9":
            assert 6 <= k <= 9
        else:
            pytest.fail(f"Unknown density class: {dclass}")


def test_rl_action_coverage(states_data):
    """Verify across the 30-state corpus every production action appears at least once."""
    action_freq = Counter()
    for s in states_data:
        for idx in s["active_action_indices"]:
            action_freq[idx] += 1

    for idx in range(11):
        assert action_freq[idx] > 0, f"Action index {idx} has 0 occurrences across V2 corpus!"

    # Ensure no invented actions
    assert set(action_freq.keys()) == set(range(11))
