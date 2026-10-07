import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.db.models import (
    RegulatoryRequirement,
    RequirementControlMapping,
    TechnicalControl,
    EvaluationRun,
    RequirementEvaluation,
    Project
)
from backend.app.engines.applicability_engine import ApplicabilityEngine
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
from backend.app.engines.sonarqube_client import SonarQubeClient
from backend.app.engines.terraform_engine import TerraformEngine
from backend.app.core.hashing import compute_application_hash, compute_infrastructure_hash

class ComplianceEngine:
    """
    Central authoritative deterministic compliance engine.
    Calculates PASS, FAIL, UNKNOWN, NOT_APPLICABLE states and computes verifiable evidence hashes.
    """

    @classmethod
    def evaluate_compliance(
        cls,
        db: Session,
        project_id: str,
        hcl_code: str = None,
        tfplan_json: Dict[str, Any] = None,
        sonar_project_key: str = None,
        trigger_type: str = "PRE_DEPLOY"
    ) -> Dict[str, Any]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        # 1. Applicability Engine Evaluation
        project_profile = {
            "jurisdiction": project.jurisdiction,
            "sector": project.sector,
            "data_categories": project.data_categories or [],
            "environment": project.environment,
            "cloud_provider": project.cloud_provider
        }
        applicable_reqs = ApplicabilityEngine.evaluate_applicability(project_profile, db)
        applicable_req_ids = {r["requirement_id"]: r for r in applicable_reqs}

        # 2. Collect Evidence
        # Evidence A: OPA / Terraform Plan Evaluation
        hcl_code_to_use = hcl_code or project.hcl_content
        if not tfplan_json and hcl_code_to_use:
            tfplan_json = TerraformEngine.hcl_to_plan_json(hcl_code_to_use)
        elif not tfplan_json:
            # Generate default plan for project
            default_hcl = TerraformEngine.generate_compliant_hcl({
                "aws_region": project.aws_region,
                "environment": project.environment
            })
            tfplan_json = TerraformEngine.hcl_to_plan_json(default_hcl)

        opa_violations = OPAPolicyEvaluator.evaluate_terraform_plan(tfplan_json)

        # Evidence B: SonarQube Code Security Evidence
        sonar_client = SonarQubeClient()
        sonar_findings = sonar_client.fetch_project_findings(
            sonar_project_key or project.id, 
            application_source_path=project.application_source_path
        )

        # 3. Deterministic Evaluation of All Requirements
        all_db_reqs = db.query(RegulatoryRequirement).all()
        
        req_evaluations: List[Dict[str, Any]] = []
        passed_count = 0
        failed_count = 0
        unknown_count = 0
        not_applicable_count = 0
        is_deployment_blocked = False

        for req in all_db_reqs:
            if req.id not in applicable_req_ids:
                req_evaluations.append({
                    "requirement_id": req.id,
                    "title": req.title,
                    "regulation_id": req.regulation_id,
                    "status": "NOT_APPLICABLE",
                    "mandatory": req.mandatory,
                    "reason": "Not applicable to current project profile or jurisdiction scope.",
                    "findings": []
                })
                not_applicable_count += 1
                continue

            app_info = applicable_req_ids[req.id]
            mappings = db.query(RequirementControlMapping).filter(
                RequirementControlMapping.requirement_id == req.id
            ).all()

            if not mappings:
                req_evaluations.append({
                    "requirement_id": req.id,
                    "title": req.title,
                    "regulation_id": req.regulation_id,
                    "status": "UNKNOWN",
                    "mandatory": req.mandatory,
                    "reason": "No approved technical control mapping exists for this requirement.",
                    "findings": []
                })
                unknown_count += 1
                if req.mandatory:
                    is_deployment_blocked = True
                continue

            req_status = "PASS"
            req_findings = []
            reasons = []

            for m in mappings:
                control = db.query(TechnicalControl).filter(TechnicalControl.id == m.control_id).first()
                if not control:
                    continue

                if control.verification_source == "OPA_TERRAFORM":
                    matching_opa = [v for v in opa_violations if v.get("control_id") == control.id]
                    if matching_opa:
                        req_status = "FAIL"
                        for v in matching_opa:
                            req_findings.append({
                                "source": "OPA",
                                "control_id": control.id,
                                "resource": v.get("resource"),
                                "actual": v.get("actual"),
                                "expected": v.get("expected"),
                                "explanation": v.get("explanation")
                            })
                            reasons.append(v.get("explanation"))
                    else:
                        # Fail-closed check
                        expected_state = control.expected_state or {}
                        required_resource_type = expected_state.get("resource_type")
                        
                        if required_resource_type:
                            import re
                            hcl_resources = set(re.findall(r'resource\s+"([^"]+)"', hcl_code_to_use or ""))
                            parsed_resources = set(r.get("type") for r in tfplan_json.get("resource_changes", []))
                            
                            if required_resource_type not in hcl_resources:
                                req_status = "FAIL"
                                reasons.append(f"Required safeguard resource '{required_resource_type}' is missing from the infrastructure.")
                                req_findings.append({
                                    "source": "OPA",
                                    "control_id": control.id,
                                    "resource": "global",
                                    "actual": "missing",
                                    "expected": required_resource_type,
                                    "explanation": f"Required safeguard '{required_resource_type}' is missing."
                                })
                            elif required_resource_type not in parsed_resources:
                                req_status = "UNKNOWN"
                                reasons.append(f"Resource '{required_resource_type}' exists but could not be parsed for evaluation.")
                                req_findings.append({
                                    "source": "OPA",
                                    "control_id": control.id,
                                    "resource": "global",
                                    "actual": "unparseable",
                                    "expected": required_resource_type,
                                    "explanation": f"Required policy could not be evaluated for '{required_resource_type}'."
                                })

                elif control.verification_source == "SONARQUBE":
                    if sonar_findings is None:
                        req_status = "UNKNOWN"
                        reasons.append("SonarQube verification service is unavailable. Empirical application security evidence could not be verified.")
                    else:
                        # Check for Critical/Blocker vulnerabilities and statutory CWE flaws (SQLi, XSS, Weak Crypto)
                        critical_sonar = [
                            f for f in sonar_findings 
                            if f.get("severity") in ["Critical", "Blocker"] or f.get("cwe") in ["CWE-89", "CWE-79", "CWE-327"]
                        ]
                        if critical_sonar:
                            req_status = "FAIL"
                            for cs in critical_sonar:
                                req_findings.append({
                                    "source": "SONARQUBE",
                                    "control_id": control.id,
                                    "file": cs.get("file"),
                                    "line": cs.get("line"),
                                    "rule": cs.get("rule"),
                                    "title": cs.get("title")
                                })
                                reasons.append(f"SonarQube finding: {cs.get('title')} at {cs.get('file')}:{cs.get('line')}")

            if req_status == "FAIL":
                failed_count += 1
                if req.mandatory:
                    is_deployment_blocked = True
            elif req_status == "UNKNOWN":
                unknown_count += 1
                if req.mandatory:
                    is_deployment_blocked = True
            else:
                passed_count += 1

            req_evaluations.append({
                "requirement_id": req.id,
                "title": req.title,
                "regulation_id": req.regulation_id,
                "status": req_status,
                "mandatory": req.mandatory,
                "reason": "; ".join(reasons) if reasons else app_info["reason"],
                "findings": req_findings
            })

        # Check for unmapped resources
        import re
        hcl_resources = set(re.findall(r'resource\s+"([^"]+)"', hcl_code_to_use or ""))
        parsed_resources = set(r.get("type") for r in tfplan_json.get("resource_changes", []))
        
        required_resource_types = set()
        for req in all_db_reqs:
            if req.id in applicable_req_ids:
                mappings = db.query(RequirementControlMapping).filter(RequirementControlMapping.requirement_id == req.id).all()
                for m in mappings:
                    control = db.query(TechnicalControl).filter(TechnicalControl.id == m.control_id).first()
                    if control and control.verification_source == "OPA_TERRAFORM":
                        rtype = (control.expected_state or {}).get("resource_type")
                        if rtype:
                            required_resource_types.add(rtype)

        unsupported_resources = hcl_resources - required_resource_types
        for ur in unsupported_resources:
            req_evaluations.append({
                "requirement_id": f"UNSUPPORTED-{ur.upper()}",
                "title": f"Unsupported Resource: {ur}",
                "regulation_id": "SYSTEM",
                "status": "NOT_APPLICABLE",
                "mandatory": False,
                "reason": f"Resource '{ur}' has no applicable policy.",
                "findings": []
            })
            not_applicable_count += 1

        # Calculate compliance score
        applicable_total = passed_count + failed_count + unknown_count
        score = (passed_count / applicable_total * 100.0) if applicable_total > 0 else 100.0
        overall_status = "FAIL" if is_deployment_blocked else ("PASS" if failed_count == 0 and unknown_count == 0 else "REVIEW_REQUIRED")

        # 4. Generate Cryptographic Evidence Hash
        infra_hash = compute_infrastructure_hash(hcl_code_to_use or "")
        app_hash = compute_application_hash(project.application_source_path)

        evidence_payload = {
            "project_id": project_id,
            "score": score,
            "overall_status": overall_status,
            "deployment_allowed": not is_deployment_blocked,
            "passed": passed_count,
            "failed": failed_count,
            "unknown": unknown_count,
            "hcl_code": hcl_code_to_use or "",
            "infrastructure_hash": infra_hash,
            "application_source_hash": app_hash,
            "opa_violations": opa_violations,
            "sonar_findings": sonar_findings or [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        evidence_hash = hashlib.sha256(json.dumps(evidence_payload, sort_keys=True).encode()).hexdigest()

        # 5. Persist Evaluation Run to Database
        import uuid
        run_id = f"eval-run-{uuid.uuid4().hex[:8]}"
        run = EvaluationRun(
            id=run_id,
            project_id=project_id,
            trigger_type=trigger_type,
            overall_status=overall_status,
            compliance_score=score,
            passed_count=passed_count,
            failed_count=failed_count,
            unknown_count=unknown_count,
            not_applicable_count=not_applicable_count,
            evidence_payload=evidence_payload,
            evidence_hash=evidence_hash
        )
        db.add(run)
        db.flush()

        for re_item in req_evaluations:
            db.add(RequirementEvaluation(
                evaluation_run_id=run_id,
                requirement_id=re_item["requirement_id"],
                status=re_item["status"],
                reason=re_item["reason"],
                findings=re_item["findings"]
            ))

        # Update project score
        project.compliance_score = score
        project.status = "Protected" if overall_status == "PASS" else ("At Risk" if overall_status == "FAIL" else "Review")
        db.commit()

        return {
            "evaluation_run_id": run_id,
            "project_id": project_id,
            "overall_status": overall_status,
            "compliance_score": score,
            "deployment_allowed": not is_deployment_blocked,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "unknown_count": unknown_count,
            "not_applicable_count": not_applicable_count,
            "evidence_hash": evidence_hash,
            "evaluations": req_evaluations,
            "opa_violations": opa_violations,
            "sonar_findings": sonar_findings or []
        }
