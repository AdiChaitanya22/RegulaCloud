from fastapi import APIRouter, Body
from typing import List, Dict, Any
from backend.app.engines.rl_remediator import QLearningRemediationAgent

router = APIRouter(prefix="/remediation", tags=["RL Remediation Optimizer"])

agent = QLearningRemediationAgent()
# Pre-train simulator in background
agent.train_simulator(episodes=300)

@router.post("/optimize")
def optimize_remediation(payload: Dict[str, Any] = Body(...)):
    # Accept active_violations (list of control ID strings) or opa_violations
    # (list of structured OPA violation dicts) as equivalent inputs.
    # Falls back to the hardcoded default only when neither key supplies violations.
    _raw = payload.get("active_violations") or [
        v.get("control_id", v) if isinstance(v, dict) else v
        for v in payload.get("opa_violations", [])
    ]
    active_violations: List[str] = _raw or [
        "CTRL-AWS-RDS-NO-PUBLIC",
        "CTRL-AWS-S3-ENC",
        "CTRL-AWS-LOG-180D",
    ]

    recommendations = agent.recommend_remediations(active_violations)

    # Derive top-level action_ids from recommendations — single source of truth
    action_ids = [rec["action_id"] for rec in recommendations if rec.get("action_id")]

    return {
        "model_type": "Tabular Q-Learning (Model-Free RL)",
        "objective": "Minimize compliance violation duration with optimal cost-complexity tradeoff",
        "total_steps_required": len(recommendations),
        "action_ids": action_ids,
        "recommendations": recommendations,
        "policy_explanation": (
            "The Q-learning policy prioritizes mandatory database boundary isolation (POL-DPDP-NET-01) "
            "and cryptographic storage enforcement first due to high statutory non-compliance penalties (+100 reward), "
            "followed by CERT-In 180-day logging retention configuration."
        )
    }
