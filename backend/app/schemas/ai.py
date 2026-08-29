from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AIChatMessage(BaseModel):
    role: str = "user" # user, assistant, system
    content: str

class AIChatRequest(BaseModel):
    project_id: str
    message: str
    conversation_history: Optional[List[AIChatMessage]] = Field(default_factory=list)

class Citation(BaseModel):
    type: str # REGULATION, EVIDENCE, REMEDIATION
    reference_id: str
    label: str
    target_control: Optional[str] = None
    target_resource: Optional[str] = None

class DeterministicStateSnapshot(BaseModel):
    project_id: str
    project_name: str
    overall_status: str # PASS, FAIL, REVIEW_REQUIRED
    deployment_allowed: bool
    compliance_score: float
    passed_count: int
    failed_count: int
    unknown_count: int
    evidence_hash: str

class AIChatResponse(BaseModel):
    reply: str
    deterministic_state: DeterministicStateSnapshot
    citations: List[Citation] = Field(default_factory=list)
    disclaimer: str = (
        "RegulaCloud provides technical compliance verification and explanation. "
        "It does not provide legal advice or legal certification."
    )
    llm_provider_used: str
    grounding_sources_used: List[str] = Field(default_factory=list)
