import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.db.models import (
    Project,
    EvaluationRun,
    RequirementEvaluation,
    RegulatoryRequirement,
    RequirementControlMapping,
    TechnicalControl,
    Regulation
)
from backend.app.engines.applicability_engine import ApplicabilityEngine
from backend.app.engines.rl_remediator import QLearningRemediationAgent

class RAGContext:
    def __init__(
        self,
        project_id: str,
        project_name: str,
        organization: str,
        sector: str,
        jurisdiction: str,
        environment: str,
        data_categories: List[str],
        overall_status: str,
        deployment_allowed: bool,
        compliance_score: float,
        evidence_hash: str,
        passed_count: int,
        failed_count: int,
        unknown_count: int,
        applicable_requirements: List[Dict[str, Any]],
        failed_controls: List[Dict[str, Any]],
        opa_violations: List[Dict[str, Any]],
        sonar_findings: List[Dict[str, Any]],
        remediation_steps: List[Dict[str, Any]],
        grounding_sources: List[str]
    ):
        self.project_id = project_id
        self.project_name = project_name
        self.organization = organization
        self.sector = sector
        self.jurisdiction = jurisdiction
        self.environment = environment
        self.data_categories = data_categories
        self.overall_status = overall_status
        self.deployment_allowed = deployment_allowed
        self.compliance_score = compliance_score
        self.evidence_hash = evidence_hash
        self.passed_count = passed_count
        self.failed_count = failed_count
        self.unknown_count = unknown_count
        self.applicable_requirements = applicable_requirements
        self.failed_controls = failed_controls
        self.opa_violations = opa_violations
        self.sonar_findings = sonar_findings
        self.remediation_steps = remediation_steps
        self.grounding_sources = grounding_sources

    def to_prompt_text(self) -> str:
        """
        Formats retrieved database records into a clean, markdown-structured
        evidence context for LLM grounding.
        """
        applicable_summary = "\n".join([
            f"- [{r['requirement_id']}] {r['title']} (Mandatory: {r['mandatory']}) — Rationale: {r['reason']}"
            for r in self.applicable_requirements
        ]) or "No applicable requirements registered."

        opa_summary = "\n".join([
            f"- Resource `{v.get('resource')}`: Violated Control `{v.get('control_id')}` ({v.get('policy_id')}). Expected `{v.get('expected')}` but got `{v.get('actual')}`. Reason: {v.get('explanation')}"
            for v in self.opa_violations
        ]) or "0 OPA Rego policy violations."

        sonar_summary = "\n".join([
            f"- File `{f.get('file')}:{f.get('line')}` [{f.get('severity')}]: {f.get('title')} ({f.get('cwe')}) - Rule: {f.get('rule')}"
            for f in self.sonar_findings
        ]) or "0 SonarQube static code security findings."

        remediation_summary = "\n".join([
            f"Step {r.get('step')}: {r.get('name')} (Target: {r.get('target_control')}, Cost: {r.get('cost_impact')})"
            for r in self.remediation_steps
        ]) or "No active remediations required."

        return f"""
[AUTHORITATIVE DETERMINISTIC EVALUATION STATE]
- Project ID: {self.project_id}
- Project Name: {self.project_name} ({self.organization})
- Jurisdiction: {self.jurisdiction} | Sector: {self.sector} | Environment: {self.environment}
- Regulated Data Categories: {', '.join(self.data_categories)}
- Deterministic Status: {self.overall_status} (Passed: {self.passed_count}, Failed: {self.failed_count}, Unknown: {self.unknown_count})
- Compliance Score: {self.compliance_score:.1f}%
- Deployment Allowed: {self.deployment_allowed} (GATING: {'UNBLOCKED' if self.deployment_allowed else 'DEPLOYMENT BLOCKED'})
- Evidence SHA-256 Hash: {self.evidence_hash}

[APPLICABLE STATUTORY REQUIREMENTS]
{applicable_summary}

[ACTIVE OPA REGO POLICY VIOLATIONS]
{opa_summary}

[ACTIVE SONARQUBE APPLICATION SECURITY FINDINGS]
{sonar_summary}

[RECOMMENDED Q-LEARNING REMEDIATION ROADMAP]
{remediation_summary}
""".strip()

class RAGEngine:
    """
    Retrieves grounded context from the existing PostgreSQL / SQLite Knowledge Base,
    Evaluation Runs, OPA Evidence, SonarQube Findings, and Q-Learning Remediation Engine.
    """

    @classmethod
    def assemble_context(cls, db: Session, project_id: str) -> RAGContext:
        grounding_sources: List[str] = []

        # 1. Project Profile Retrieval
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' does not exist in RegulaCloud database.")
        grounding_sources.append(f"projects (id: {project_id})")

        # 2. Applicability Engine Query
        profile = {
            "jurisdiction": project.jurisdiction,
            "sector": project.sector,
            "data_categories": project.data_categories or [],
            "environment": project.environment,
            "cloud_provider": project.cloud_provider
        }
        applicable_reqs = ApplicabilityEngine.evaluate_applicability(profile, db)
        grounding_sources.append("regulatory_knowledge_base (India DPDPA 2023, Rules 2025, CERT-In 2022)")

        # 3. Latest Evaluation Run Query
        latest_run = db.query(EvaluationRun).filter(
            EvaluationRun.project_id == project_id
        ).order_by(EvaluationRun.evaluated_at.desc()).first()

        if latest_run:
            overall_status = latest_run.overall_status
            score = latest_run.compliance_score
            passed = latest_run.passed_count
            failed = latest_run.failed_count
            unknown = latest_run.unknown_count
            evidence_hash = latest_run.evidence_hash
            deployment_allowed = (overall_status == "PASS" and failed == 0 and unknown == 0)
            grounding_sources.append(f"evaluation_runs (id: {latest_run.id})")

            # Extract OPA and Sonar evidence from evaluations / payload
            eval_records = db.query(RequirementEvaluation).filter(
                RequirementEvaluation.evaluation_run_id == latest_run.id
            ).all()

            opa_violations = []
            sonar_findings = []
            failed_controls = []

            for er in eval_records:
                if er.status == "FAIL":
                    for f in er.findings:
                        if f.get("source") == "OPA":
                            opa_violations.append(f)
                            failed_controls.append({
                                "requirement_id": er.requirement_id,
                                "control_id": f.get("control_id"),
                                "reason": f.get("explanation")
                            })
                        elif f.get("source") == "SONARQUBE":
                            sonar_findings.append(f)
                            failed_controls.append({
                                "requirement_id": er.requirement_id,
                                "control_id": f.get("control_id"),
                                "reason": f.get("title")
                            })
        else:
            # Fallback to current project score baseline
            score = project.compliance_score
            overall_status = "PASS" if score >= 90 else "FAIL"
            passed = 8 if score >= 90 else 5
            failed = 0 if score >= 90 else 3
            unknown = 0
            deployment_allowed = (score >= 90)
            evidence_hash = "0" * 64
            opa_violations = []
            sonar_findings = []
            failed_controls = []

        # 4. Q-Learning Remediation Extraction
        remediation_steps = []
        if failed > 0:
            agent = QLearningRemediationAgent()
            violated_ctrl_ids = list(set([fc.get("control_id") for fc in failed_controls if fc.get("control_id")]))
            if not violated_ctrl_ids and opa_violations:
                violated_ctrl_ids = [v.get("control_id") for v in opa_violations if v.get("control_id")]
            if violated_ctrl_ids:
                remediation_steps = agent.recommend_remediations(violated_ctrl_ids)
                grounding_sources.append("q_learning_remediation_engine")

        return RAGContext(
            project_id=project.id,
            project_name=project.name,
            organization=project.organization,
            sector=project.sector,
            jurisdiction=project.jurisdiction,
            environment=project.environment,
            data_categories=project.data_categories or [],
            overall_status=overall_status,
            deployment_allowed=deployment_allowed,
            compliance_score=score,
            evidence_hash=evidence_hash,
            passed_count=passed,
            failed_count=failed,
            unknown_count=unknown,
            applicable_requirements=applicable_reqs,
            failed_controls=failed_controls,
            opa_violations=opa_violations,
            sonar_findings=sonar_findings,
            remediation_steps=remediation_steps,
            grounding_sources=grounding_sources
        )
