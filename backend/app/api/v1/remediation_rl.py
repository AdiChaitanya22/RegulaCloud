from fastapi import APIRouter, Body
from typing import List, Dict, Any
from backend.app.engines.rl_remediator import QLearningRemediationAgent

router = APIRouter(prefix="/remediation", tags=["RL Remediation Optimizer"])

agent = QLearningRemediationAgent()
# Pre-train simulator in background
agent.train_simulator(episodes=300)

@router.post("/optimize")
def optimize_remediation(payload: Dict[str, Any] = Body(...)):
    active_violations: List[str] = payload.get("active_violations", [
        "CTRL-AWS-RDS-NO-PUBLIC",
        "CTRL-AWS-S3-ENC",
        "CTRL-AWS-LOG-180D"
    ])
    
    recommendations = agent.recommend_remediations(active_violations)
    
    return {
        "model_type": "Tabular Q-Learning (Model-Free RL)",
        "objective": "Minimize compliance violation duration with optimal cost-complexity tradeoff",
        "total_steps_required": len(recommendations),
        "recommendations": recommendations,
        "policy_explanation": (
            "The Q-learning policy prioritizes mandatory database boundary isolation (POL-DPDP-NET-01) "
            "and cryptographic storage enforcement first due to high statutory non-compliance penalties (+100 reward), "
            "followed by CERT-In 180-day logging retention configuration."
        )
    }
