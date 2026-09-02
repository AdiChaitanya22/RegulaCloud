from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.engines.compliance_engine import ComplianceEngine
from backend.app.schemas.compliance import ComplianceEvaluateRequest, ComplianceEvaluationResponse
from backend.app.db.models import EvaluationRun, Project, Regulation, RegulatoryRequirement, RequirementEvaluation

router = APIRouter(prefix="/compliance", tags=["Compliance Engine"])

@router.get("/summary")
def get_compliance_summary(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    if not projects:
        return {
            "overallScore": 0.0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "notEvaluated": 0,
            "frameworks": []
        }
    
    total_passed = 0
    total_failed = 0
    total_unknown = 0
    total_na = 0
    scores = []
    
    # Collect latest evaluation run for each project
    latest_run_ids = []
    for p in projects:
        latest_run = db.query(EvaluationRun).filter(
            EvaluationRun.project_id == p.id
        ).order_by(EvaluationRun.evaluated_at.desc()).first()
        
        if latest_run:
            latest_run_ids.append(latest_run.id)
            total_passed += latest_run.passed_count
            total_failed += latest_run.failed_count
            total_unknown += latest_run.unknown_count
            total_na += latest_run.not_applicable_count
            scores.append(latest_run.compliance_score)
        else:
            scores.append(p.compliance_score or 0.0)
            
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    
    # Dynamic Framework Breakdown
    regulations = db.query(Regulation).all()
    frameworks = []
    for reg in regulations:
        req_ids = [r.id for r in reg.requirements]
        if not req_ids or not latest_run_ids:
            frameworks.append({
                "name": reg.name,
                "score": 100 if total_failed == 0 else 85,
                "status": "Compliant" if total_failed == 0 else "Review Required"
            })
            continue
            
        evals = db.query(RequirementEvaluation).filter(
            RequirementEvaluation.evaluation_run_id.in_(latest_run_ids),
            RequirementEvaluation.requirement_id.in_(req_ids)
        ).all()
        
        if evals:
            reg_passed = sum(1 for e in evals if e.status == "PASS")
            reg_total = len(evals)
            reg_score = round((reg_passed / reg_total) * 100.0, 1) if reg_total > 0 else 100.0
        else:
            reg_score = 100.0
            
        frameworks.append({
            "name": reg.name,
            "score": int(reg_score),
            "status": "Compliant" if reg_score >= 90.0 else ("Review Required" if reg_score >= 70.0 else "Non-Compliant")
        })

    return {
        "overallScore": avg_score,
        "passed": total_passed,
        "failed": total_failed,
        "warnings": total_unknown,
        "notEvaluated": total_na,
        "frameworks": frameworks
    }

@router.post("/evaluate", response_model=ComplianceEvaluationResponse)
def evaluate_compliance(req: ComplianceEvaluateRequest, db: Session = Depends(get_db)):
    try:
        result = ComplianceEngine.evaluate_compliance(
            db=db,
            project_id=req.project_id,
            hcl_code=req.hcl_code,
            sonar_project_key=req.sonar_project_key,
            trigger_type=req.trigger_type
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance evaluation failure: {str(e)}")

@router.get("/history/{project_id}")
def get_evaluation_history(project_id: str, db: Session = Depends(get_db)):
    runs = db.query(EvaluationRun).filter(
        EvaluationRun.project_id == project_id
    ).order_by(EvaluationRun.evaluated_at.desc()).limit(10).all()
    return runs
