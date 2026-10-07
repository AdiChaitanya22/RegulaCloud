from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, List
from backend.app.core.database import get_db
from backend.app.db.models import Project, EvaluationRun, TechnicalControl, Deployment, AuditLog, RequirementEvaluation
from backend.app.core.auth import require_user
from sqlalchemy import func

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])

@router.get("/stats")
def get_dashboard_stats(current_user=Depends(require_user), db: Session = Depends(get_db)):
    # 1. Scope Projects
    if current_user.role == "ADMIN":
        projects_query = db.query(Project)
    else:
        projects_query = db.query(Project).filter(Project.owner_id == current_user.id)
    
    projects = projects_query.all()
    project_ids = [p.id for p in projects]
    project_count = len(projects)
    
    if project_count == 0:
        return {
            "complianceScore": 0,
            "securityFindings": 0,
            "activeProjects": 0,
            "monitoredControls": db.query(TechnicalControl).count(),
            "deploymentsTotal": 0,
            "deploymentsSuccess": 0,
            "deploymentsBlocked": 0,
            "policyViolations": 0,
            "unsupportedResources": 0,
            "criticalFindings": 0,
            "highFindings": 0,
            "recentActivities": [],
            "trend": [],
            "severityDistribution": [],
            "controlDistribution": []
        }

    # 2. Score & Basic Metrics
    avg_score = round(sum(p.compliance_score for p in projects) / project_count, 1)

    # 3. Deployments
    deployments_query = db.query(Deployment).filter(Deployment.project_id.in_(project_ids))
    deployments = deployments_query.all()
    total_deployments = len(deployments)
    successful_deployments = sum(1 for d in deployments if d.status == "SUCCESS")
    blocked_deployments = sum(1 for d in deployments if d.status == "BLOCKED")

    # 4. Evaluation Runs (Latest per project)
    latest_runs = []
    for pid in project_ids:
        r = db.query(EvaluationRun).filter(EvaluationRun.project_id == pid).order_by(EvaluationRun.evaluated_at.desc()).first()
        if r:
            latest_runs.append(r)
    
    latest_run_ids = [r.id for r in latest_runs]
    failed_controls_count = sum(r.failed_count for r in latest_runs)
    
    # 5. Requirement Evaluations (Control Distribution)
    pass_count = 0
    fail_count = 0
    unknown_count = 0
    not_app_count = 0
    
    critical_findings = 0
    high_findings = 0
    
    if latest_run_ids:
        req_evals = db.query(RequirementEvaluation).filter(RequirementEvaluation.evaluation_run_id.in_(latest_run_ids)).all()
        for re_item in req_evals:
            if re_item.status == "PASS":
                pass_count += 1
            elif re_item.status == "FAIL":
                fail_count += 1
                for f in (re_item.findings or []):
                    if isinstance(f, dict):
                        # Simple proxy for severity
                        if f.get("source") == "OPA" or "RDS" in str(f.get("control_id", "")):
                            critical_findings += 1
                        else:
                            high_findings += 1
            elif re_item.status == "UNKNOWN":
                unknown_count += 1
            elif re_item.status == "NOT_APPLICABLE":
                not_app_count += 1

    # 6. Audit Logs
    audit_query = db.query(AuditLog)
    if current_user.role != "ADMIN":
        # Rough filtering by project_id in details or resource_id, if modeled that way.
        pass # To keep it simple, we will return global audits for now, or filter if project_id exists.
    
    recent_logs = audit_query.order_by(AuditLog.id.desc()).limit(10).all()
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

    # 7. Compliance Trend
    trend = []
    if current_user.role == "ADMIN":
        # Global daily average
        history = db.query(
            func.date(EvaluationRun.evaluated_at).label("dt"), 
            func.avg(EvaluationRun.compliance_score).label("score")
        ).group_by(func.date(EvaluationRun.evaluated_at)).order_by(func.date(EvaluationRun.evaluated_at).asc()).limit(14).all()
        for h in history:
            trend.append({"date": h.dt, "score": round(h.score, 1)})
    else:
        # User projects daily average
        history = db.query(
            func.date(EvaluationRun.evaluated_at).label("dt"), 
            func.avg(EvaluationRun.compliance_score).label("score")
        ).filter(EvaluationRun.project_id.in_(project_ids)).group_by(func.date(EvaluationRun.evaluated_at)).order_by(func.date(EvaluationRun.evaluated_at).asc()).limit(14).all()
        for h in history:
            trend.append({"date": h.dt, "score": round(h.score, 1)})

    # Calculate Unsupported Resources from Native Plan Evidence
    unsupported_resources = 0
    all_controls = db.query(TechnicalControl).all()
    supported_types = set()
    for c in all_controls:
        if c.expected_state and "resource_type" in c.expected_state:
            supported_types.add(c.expected_state["resource_type"])
            
    for r in latest_runs:
        if r.evidence_payload and "native_plan_json" in r.evidence_payload:
            native_plan = r.evidence_payload["native_plan_json"]
            planned_values = native_plan.get("planned_values", {}).get("root_module", {})
            resources = []
            def extract(mod):
                for res in mod.get("resources", []):
                    resources.append(res)
                for child in mod.get("child_modules", []):
                    extract(child)
            extract(planned_values)
            
            for res in resources:
                if res.get("type") not in supported_types:
                    unsupported_resources += 1

    return {
        "complianceScore": avg_score,
        "securityFindings": failed_controls_count,
        "activeProjects": project_count,
        "monitoredControls": db.query(TechnicalControl).count(),
        "deploymentsTotal": total_deployments,
        "deploymentsSuccess": successful_deployments,
        "deploymentsBlocked": blocked_deployments,
        "policyViolations": failed_controls_count,
        "unsupportedResources": unsupported_resources,
        "criticalFindings": critical_findings,
        "highFindings": high_findings,
        "recentActivities": activities,
        "trend": trend,
        "controlDistribution": [
            {"name": "Pass", "value": pass_count},
            {"name": "Fail", "value": fail_count},
            {"name": "Unknown", "value": unknown_count},
            {"name": "Not Applicable", "value": not_app_count}
        ]
    }
