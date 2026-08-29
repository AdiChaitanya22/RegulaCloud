from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ComplianceEvaluateRequest(BaseModel):
    project_id: str
    hcl_code: Optional[str] = None
    sonar_project_key: Optional[str] = None
    trigger_type: str = "PRE_DEPLOY"

class FindingDetail(BaseModel):
    source: str
    control_id: str
    resource: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    rule: Optional[str] = None
    title: Optional[str] = None
    actual: Optional[str] = None
    expected: Optional[str] = None
    explanation: Optional[str] = None

class RequirementEvaluationResponse(BaseModel):
    requirement_id: str
    title: str
    regulation_id: str
    status: str # PASS, FAIL, UNKNOWN, NOT_APPLICABLE
    mandatory: bool
    reason: Optional[str] = None
    findings: List[Dict[str, Any]] = Field(default_factory=list)

class ComplianceEvaluationResponse(BaseModel):
    evaluation_run_id: str
    project_id: str
    overall_status: str # PASS, FAIL, REVIEW_REQUIRED
    compliance_score: float
    deployment_allowed: bool
    passed_count: int
    failed_count: int
    unknown_count: int
    not_applicable_count: int
    evidence_hash: str
    evaluations: List[RequirementEvaluationResponse]
    opa_violations: List[Dict[str, Any]]
    sonar_findings: List[Dict[str, Any]]
