from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.app.core.database import get_db
from backend.app.db.models import Project, EvaluationRun, TechnicalControl, Deployment, AuditLog, RequirementEvaluation
from backend.app.core.auth import require_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])

@router.get("/stats")
def get_dashboard_stats(current_user=Depends(require_user), db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    project_count = len(projects)
    
    # 1. Real Compliance Score
    if projects:
        avg_score = round(sum(p.compliance_score for p in projects) / len(projects), 1)
    else:
        avg_score = 100.0

    # 2. Real Latest Evaluation Stats
    latest_run = db.query(EvaluationRun).order_by(EvaluationRun.evaluated_at.desc()).first()
    failed_controls_count = latest_run.failed_count if latest_run else 0
    passed_controls_count = latest_run.passed_count if latest_run else 0
    
    # 3. Monitored Controls
    total_controls = db.query(TechnicalControl).count()
    
    # 4. Deployments Stats
    deployments = db.query(Deployment).all()
    total_deployments = len(deployments)
    successful_deployments = sum(1 for d in deployments if d.status == "SUCCESS")
    blocked_deployments = sum(1 for d in deployments if d.status == "BLOCKED")
    
    # 5. Recent Activities from Audit Log
    recent_logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(6).all()
    activities = []
    for l in recent_logs:
        act_type = "success" if "SUCCESS" in l.action or "PASS" in l.action else ("alert" if l.severity in ["Critical", "High"] else "scan")
        activities.append({
            "id": f"act-{l.id}",
            "event": l.action.replace("_", " ").title(),
            "details": f"Target {l.resource_type}:{l.resource_id or 'global'}. Severity: {l.severity}.",
            "time": l.timestamp.strftime("%H:%M UTC") if l.timestamp else "Recently",
            "type": act_type
        })
        
    if not activities:
        activities = [
            {"id": "act-init", "event": "System Baseline Online", "details": "Continuous compliance gate active.", "time": "Just now", "type": "success"}
        ]

    # 6. Real Severity Distribution
    critical_findings = 0
    high_findings = 0
    medium_findings = 0
    if latest_run and latest_run.failed_count > 0:
        req_evals = db.query(RequirementEvaluation).filter(
            RequirementEvaluation.evaluation_run_id == latest_run.id,
            RequirementEvaluation.status == "FAIL"
        ).all()
        for re_item in req_evals:
            for f in (re_item.findings or []):
                if isinstance(f, dict):
                    if f.get("source") == "OPA" or "RDS" in str(f.get("control_id", "")):
                        critical_findings += 1
                    else:
                        high_findings += 1
    
    # 7. Compliance Trend (Historical Runs)
    history_runs = db.query(EvaluationRun).order_by(EvaluationRun.evaluated_at.asc()).limit(6).all()
    trend = []
    for r in history_runs:
        trend.append({
            "date": r.evaluated_at.strftime("%d %b"),
            "score": round(r.compliance_score, 1)
        })
    if not trend:
        trend = [{"date": datetime.utcnow().strftime("%d %b"), "score": avg_score}]

    return {
        "complianceScore": avg_score,
        "securityFindings": failed_controls_count,
        "activeProjects": project_count,
        "monitoredControls": total_controls,
        "deploymentsTotal": total_deployments,
        "deploymentsSuccess": successful_deployments,
        "deploymentsBlocked": blocked_deployments,
        "policyViolations": failed_controls_count,
        "criticalFindings": critical_findings,
        "highFindings": high_findings,
        "recentActivities": activities,
        "trend": trend
    }
