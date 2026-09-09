from datetime import datetime
import hashlib
import json
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="USER") # ADMIN, USER, AUDITOR
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Regulation(Base):
    __tablename__ = "regulations"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    jurisdiction = Column(String(64), nullable=False, default="India")
    version = Column(String(32), nullable=False, default="1.0")
    effective_date = Column(String(64), nullable=True)
    official_source_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    requirements = relationship("RegulatoryRequirement", back_populates="regulation", cascade="all, delete-orphan")


class RegulatoryRequirement(Base):
    __tablename__ = "regulatory_requirements"

    id = Column(String(64), primary_key=True, index=True) # e.g. DPDP-2023-SEC8.5
    regulation_id = Column(String(64), ForeignKey("regulations.id"), nullable=False)
    title = Column(String(255), nullable=False)
    requirement_text = Column(Text, nullable=False)
    version = Column(String(32), nullable=False, default="1.0")
    mandatory = Column(Boolean, nullable=False, default=True)
    applicability_conditions = Column(JSON, nullable=False, default=dict) # Dict of conditions
    status = Column(String(32), nullable=False, default="APPROVED") # DRAFT, APPROVED, DEPRECATED
    approved_by = Column(String(128), nullable=True, default="Regulatory Compliance Reviewer")
    official_source = Column(String(255), nullable=True)
    policy_reference = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    regulation = relationship("Regulation", back_populates="requirements")
    control_mappings = relationship("RequirementControlMapping", back_populates="requirement", cascade="all, delete-orphan")


class TechnicalControl(Base):
    __tablename__ = "technical_controls"

    id = Column(String(64), primary_key=True, index=True) # e.g. CTRL-AWS-S3-ENC
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False) # Cryptography, AccessControl, AuditLogging, CodeSecurity
    description = Column(Text, nullable=False)
    verification_source = Column(String(64), nullable=False) # OPA_TERRAFORM, SONARQUBE, AWS_API
    expected_state = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    requirement_mappings = relationship("RequirementControlMapping", back_populates="control", cascade="all, delete-orphan")


class RequirementControlMapping(Base):
    __tablename__ = "requirement_control_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String(64), ForeignKey("regulatory_requirements.id"), nullable=False)
    control_id = Column(String(64), ForeignKey("technical_controls.id"), nullable=False)
    mapping_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    requirement = relationship("RegulatoryRequirement", back_populates="control_mappings")
    control = relationship("TechnicalControl", back_populates="requirement_mappings")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False)
    sector = Column(String(64), nullable=False) # Healthcare, Finance, Education, Government, E-Commerce
    jurisdiction = Column(String(64), nullable=False, default="India")
    data_categories = Column(JSON, nullable=False, default=list) # ["personal_data", "financial_data"]
    environment = Column(String(32), nullable=False, default="production")
    cloud_provider = Column(String(32), nullable=False, default="AWS")
    aws_region = Column(String(32), nullable=False, default="ap-south-1")
    compliance_score = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="Protected") # Protected, Review, At Risk
    owner = Column(String(128), nullable=False, default="admin@regulacloud.gov.in")
    infrastructure_path = Column(String(255), nullable=True)
    application_source_path = Column(String(255), nullable=True)
    hcl_content = Column(Text, nullable=True)
    regulatory_scope = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    trigger_type = Column(String(32), nullable=False) # PRE_DEPLOY, MANUAL_SCAN, DRIFT_DETECTED
    overall_status = Column(String(32), nullable=False) # PASS, FAIL, UNKNOWN
    compliance_score = Column(Float, nullable=False)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    unknown_count = Column(Integer, default=0)
    not_applicable_count = Column(Integer, default=0)
    evidence_payload = Column(JSON, nullable=False, default=dict)
    remediation_plan = Column(JSON, nullable=True, default=list)
    evidence_hash = Column(String(64), nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    evaluations = relationship("RequirementEvaluation", back_populates="run", cascade="all, delete-orphan")


class RequirementEvaluation(Base):
    __tablename__ = "requirement_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_run_id = Column(String(64), ForeignKey("evaluation_runs.id"), nullable=False)
    requirement_id = Column(String(64), ForeignKey("regulatory_requirements.id"), nullable=False)
    status = Column(String(32), nullable=False) # PASS, FAIL, UNKNOWN, NOT_APPLICABLE
    reason = Column(Text, nullable=True)
    findings = Column(JSON, nullable=False, default=list)

    run = relationship("EvaluationRun", back_populates="evaluations")
    requirement = relationship("RegulatoryRequirement")


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    evaluation_run_id = Column(String(64), ForeignKey("evaluation_runs.id"), nullable=True)
    status = Column(String(32), nullable=False, default="AWAITING_APPROVAL") # AWAITING_APPROVAL, DEPLOYING, SUCCESS, FAILED, BLOCKED
    terraform_plan_json = Column(JSON, nullable=True)
    applied_by = Column(String(128), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    logs = Column(JSON, default=list)


class DriftEvent(Base):
    __tablename__ = "drift_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    resource_id = Column(String(255), nullable=False)
    control_id = Column(String(64), ForeignKey("technical_controls.id"), nullable=False)
    expected_state = Column(JSON, nullable=False)
    actual_state = Column(JSON, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(128), nullable=False)
    action = Column(String(128), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=True)
    severity = Column(String(32), nullable=False, default="Low")
    details = Column(JSON, nullable=True, default=dict)
    previous_hash = Column(String(64), nullable=True)
    current_hash = Column(String(64), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    @classmethod
    def create_entry(cls, session, actor: str, action: str, resource_type: str, resource_id: str, severity: str, details: dict):
        last_entry = session.query(cls).order_by(cls.id.desc()).first()
        prev_hash = last_entry.current_hash if last_entry else "0" * 64
        
        now = datetime.utcnow()
        entry_payload = {
            "actor": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "severity": severity,
            "details": details,
            "previous_hash": prev_hash,
            "timestamp": now.isoformat()
        }
        computed_hash = hashlib.sha256(json.dumps(entry_payload, sort_keys=True).encode()).hexdigest()
        
        log = cls(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            severity=severity,
            details=details,
            previous_hash=prev_hash,
            current_hash=computed_hash,
            timestamp=now
        )
        session.add(log)
        session.commit()
        return log


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=True)
    evaluation_run_id = Column(String(64), ForeignKey("evaluation_runs.id"), nullable=True)
    status = Column(String(32), default="Ready") # Ready, Generating, Archived
    grade = Column(String(8), default="A")
    score = Column(String(16), default="100.0%")
    desc = Column(Text, nullable=True)
    report_data = Column(JSON, nullable=True)
    evidence_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True, index=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

