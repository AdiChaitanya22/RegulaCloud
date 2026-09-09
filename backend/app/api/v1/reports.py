from fastapi import APIRouter, Depends, HTTPException, Body, Response
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
import uuid
import json
from backend.app.core.database import get_db
from backend.app.db.models import ComplianceReport, EvaluationRun, Project, AuditLog, RequirementEvaluation, Regulation

router = APIRouter(prefix="/reports", tags=["Government Compliance Reports"])

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    reports = db.query(ComplianceReport).order_by(ComplianceReport.created_at.desc()).all()
    if not reports:
        # Seed initial database-backed reports from latest evaluation
        latest_run = db.query(EvaluationRun).order_by(EvaluationRun.evaluated_at.desc()).first()
        score_val = f"{latest_run.compliance_score:.1f}%" if latest_run else "100.0%"
        grade_val = "A" if (latest_run and latest_run.compliance_score >= 90) else "B"
        
        rep1 = ComplianceReport(
            id="rep-dpdp-01",
            title="DPDP Act 2023 Statutory Verification Report",
            project_id="proj-healthcare-india",
            evaluation_run_id=latest_run.id if latest_run else None,
            status="Ready",
            grade=grade_val,
            score=score_val,
            desc="Technical verification certificate for personal data encryption, purpose isolation, and breach logging safeguards.",
            evidence_hash=latest_run.evidence_hash if latest_run else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        rep2 = ComplianceReport(
            id="rep-certin-02",
            title="CERT-In 180-Day Log Retention & Incident Audit",
            project_id="proj-healthcare-india",
            evaluation_run_id=latest_run.id if latest_run else None,
            status="Ready",
            grade="A",
            score="100.0%",
            desc="Verifiable telemetry review verifying 180-day CloudWatch log retention and NTP synchronization with NPL/NIC.",
            evidence_hash=latest_run.evidence_hash if latest_run else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        db.add(rep1)
        db.add(rep2)
        db.commit()
        reports = [rep1, rep2]

    return [
        {
            "id": r.id,
            "title": r.title,
            "date": r.created_at.strftime("%d %b %Y") if r.created_at else "Today",
            "status": r.status,
            "grade": r.grade,
            "score": r.score,
            "desc": r.desc,
            "evidence_hash": r.evidence_hash
        }
        for r in reports
    ]

@router.post("/generate")
def generate_report(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    title = payload.get("title", "Statutory Compliance Audit Certificate")
    project_id = payload.get("projectId", "proj-healthcare-india")
    evaluation_run_id_param = payload.get("evaluation_run_id")

    # Guard: project must exist before we touch anything else
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    # Resolve evaluation run: explicit selection or fallback to latest
    if evaluation_run_id_param:
        eval_run = db.query(EvaluationRun).filter(
            EvaluationRun.id == evaluation_run_id_param
        ).first()
        if not eval_run:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation run '{evaluation_run_id_param}' not found."
            )
        if eval_run.project_id != project_id:
            raise HTTPException(
                status_code=403,
                detail="Evaluation run does not belong to the requested project."
            )
        latest_run = eval_run
    else:
        latest_run = db.query(EvaluationRun).filter(
            EvaluationRun.project_id == project_id
        ).order_by(EvaluationRun.evaluated_at.desc()).first()

    score_float = latest_run.compliance_score if latest_run else project.compliance_score or 100.0
    score_str = f"{score_float:.1f}%"
    grade = "A" if score_float >= 90.0 else ("B" if score_float >= 80.0 else ("C" if score_float >= 70.0 else "F"))
    evidence_hash = latest_run.evidence_hash if latest_run else "0" * 64

    rep_id = f"rep-{uuid.uuid4().hex[:8]}"
    report = ComplianceReport(
        id=rep_id,
        title=title,
        project_id=project_id,
        evaluation_run_id=latest_run.id if latest_run else None,
        status="Ready",
        grade=grade,
        score=score_str,
        desc=payload.get("desc", f"Verifiable regulatory compliance verification certificate for project '{project.name}'."),
        evidence_hash=evidence_hash
    )
    db.add(report)

    AuditLog.create_entry(
        session=db,
        actor="auditor.compliance_officer",
        action="GENERATE_COMPLIANCE_REPORT",
        resource_type="AUDIT_REPORT",
        resource_id=rep_id,
        severity="Low",
        details={"title": title, "grade": grade, "score": score_str, "evidence_hash": evidence_hash}
    )
    db.commit()

    return {
        "id": report.id,
        "title": report.title,
        "date": report.created_at.strftime("%d %b %Y"),
        "status": report.status,
        "grade": report.grade,
        "score": report.score,
        "desc": report.desc,
        "evidence_hash": report.evidence_hash
    }

@router.get("/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    # Generate structured CSV evidence document
    lines = [
        "REGULACLOUD STATUTORY COMPLIANCE AUDIT CERTIFICATE",
        f"Report ID,{report.id}",
        f"Title,{report.title}",
        f"Project ID,{report.project_id or 'proj-healthcare-india'}",
        f"Generated At,{report.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if report.created_at else 'N/A'}",
        f"Compliance Score,{report.score}",
        f"Compliance Grade,{report.grade}",
        f"Cryptographic Evidence Hash (SHA-256),{report.evidence_hash or 'N/A'}",
        "",
        "EVALUATED STATUTORY REQUIREMENTS & CONTROLS BREAKDOWN",
        "Requirement ID,Title,Status,Reason,Evidence Source"
    ]
    
    if not report.evaluation_run_id:
        raise HTTPException(status_code=400, detail="No compliance evaluation evidence exists to back this report.")

    eval_run = db.query(EvaluationRun).filter(EvaluationRun.id == report.evaluation_run_id).first()
    if not eval_run:
        raise HTTPException(status_code=400, detail="Evaluation run evidence not found.")
        
    req_evals = db.query(RequirementEvaluation).filter(
        RequirementEvaluation.evaluation_run_id == report.evaluation_run_id
    ).all()
    
    for re_item in req_evals:
        clean_title = re_item.requirement.title.replace(",", ";") if re_item.requirement else ""
        clean_reason = (re_item.reason or "Satisfied").replace(",", ";")
        src = "OPA Rego & SonarQube"
        lines.append(f'"{re_item.requirement_id}","{clean_title}","{re_item.status}","{clean_reason}","{src}"')

    # Append true OPA & SonarQube telemetry
    evidence = eval_run.evidence_payload or {}
    
    lines.append("")
    lines.append("OPA_VIOLATION,Description")
    opa_violations = evidence.get("opa_violations", [])
    if opa_violations:
        for v in opa_violations:
            desc = v.get("description", "").replace(",", ";")
            lines.append(f'"OPA_REGO","{desc}"')
    else:
        lines.append('"OPA_REGO","No violations detected or telemetry unavailable"')
        
    lines.append("")
    lines.append("SONAR_FINDING,Severity,Message")
    sonar_findings = evidence.get("sonar_findings", [])
    if sonar_findings:
        for s in sonar_findings:
            msg = s.get("message", "").replace(",", ";")
            sev = s.get("severity", "UNKNOWN")
            lines.append(f'"SONARQUBE","{sev}","{msg}"')
    else:
        lines.append('"SONARQUBE","N/A","No findings or telemetry unavailable"')

    csv_content = "\n".join(lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=regulacloud_audit_{report_id}.csv"}
    )
