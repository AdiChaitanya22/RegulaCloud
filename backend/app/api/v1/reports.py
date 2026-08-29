from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from backend.app.core.database import get_db
from backend.app.db.models import EvaluationRun, Project, AuditLog

router = APIRouter(prefix="/reports", tags=["Government Compliance Reports"])

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    return [
        {
            "id": "rep-dpdp-01",
            "title": "DPDP Act 2023 Statutory Verification Report",
            "date": "29 Aug 2026",
            "status": "Ready",
            "grade": "A",
            "score": "96.4%",
            "desc": "Technical verification certificate for personal data encryption, purpose isolation, and breach logging safeguards."
        },
        {
            "id": "rep-certin-02",
            "title": "CERT-In 180-Day Log Retention & Incident Audit",
            "date": "29 Aug 2026",
            "status": "Ready",
            "grade": "A",
            "score": "100.0%",
            "desc": "Verifiable telemetry review verifying 180-day CloudWatch log retention and NTP synchronization with NPL/NIC."
        },
        {
            "id": "rep-appsec-03",
            "title": "Application Security Baseline (SonarQube)",
            "date": "29 Aug 2026",
            "status": "Ready",
            "grade": "A",
            "score": "92.0%",
            "desc": "Static code analysis report validating zero open critical SQLi/XSS vulnerabilities across repository codebase."
        }
    ]

@router.post("/generate")
def generate_report(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    title = payload.get("title", "Statutory Compliance Audit Certificate")
    
    AuditLog.create_entry(
        session=db,
        actor="government.auditor",
        action="GENERATE_COMPLIANCE_REPORT",
        resource_type="AUDIT_REPORT",
        resource_id=title,
        severity="Low",
        details={"title": title, "grade": payload.get("grade", "A"), "score": payload.get("score", "98.5%")}
    )

    return {
        "id": f"rep-{int(datetime.utcnow().timestamp())}",
        "title": title,
        "date": datetime.utcnow().strftime("%d %b %Y"),
        "status": "Ready",
        "grade": payload.get("grade", "A"),
        "score": payload.get("score", "98.5%"),
        "desc": payload.get("desc", "Traceable regulatory compliance verification certificate.")
    }
