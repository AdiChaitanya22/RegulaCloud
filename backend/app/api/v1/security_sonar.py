from fastapi import APIRouter, Body
from typing import Dict, Any
from backend.app.engines.sonarqube_client import SonarQubeClient

router = APIRouter(prefix="/security", tags=["SonarQube Security Scanner"])

client = SonarQubeClient()

@router.get("/findings")
def get_security_findings(project_key: str = "proj-healthcare-india"):
    findings = client.fetch_project_findings(project_key)
    return findings

@router.post("/scan")
def trigger_security_scan(payload: Dict[str, Any] = Body(...)):
    project_id = payload.get("projectId", "proj-healthcare-india")
    findings = client.fetch_project_findings(project_id)
    return findings
