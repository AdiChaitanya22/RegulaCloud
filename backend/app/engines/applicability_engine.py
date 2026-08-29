from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models import RegulatoryRequirement, Regulation

class ApplicabilityResult:
    def __init__(self, requirement_id: str, regulation_id: str, regulation_name: str, title: str, mandatory: bool, reason: str, requirement_text: str):
        self.requirement_id = requirement_id
        self.regulation_id = regulation_id
        self.regulation_name = regulation_name
        self.title = title
        self.mandatory = mandatory
        self.reason = reason
        self.requirement_text = requirement_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "regulation_id": self.regulation_id,
            "regulation_name": self.regulation_name,
            "title": self.title,
            "mandatory": self.mandatory,
            "reason": self.reason,
            "requirement_text": self.requirement_text
        }

class ApplicabilityEngine:
    """
    Deterministic, explainable applicability engine that checks regulatory conditions
    against a target project profile (jurisdiction, sector, data categories, cloud provider, environment).
    """

    @staticmethod
    def evaluate_applicability(project_profile: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        target_jurisdiction = project_profile.get("jurisdiction", "India")
        target_sector = project_profile.get("sector", "")
        target_data_categories = set(project_profile.get("data_categories", []))
        target_env = project_profile.get("environment", "production")
        target_provider = project_profile.get("cloud_provider", "AWS")

        all_requirements = db.query(RegulatoryRequirement).join(Regulation).filter(
            RegulatoryRequirement.status == "APPROVED"
        ).all()

        applicable_list: List[Dict[str, Any]] = []

        for req in all_requirements:
            conds = req.applicability_conditions or {}
            reasons = []
            is_applicable = True

            # 1. Check Jurisdiction
            req_jurisdiction = conds.get("jurisdiction")
            if req_jurisdiction:
                if req_jurisdiction.lower() != target_jurisdiction.lower():
                    is_applicable = False
                else:
                    reasons.append(f"Jurisdiction matches '{target_jurisdiction}'")

            # 2. Check Data Categories
            cat_includes = conds.get("data_categories_include")
            if cat_includes and is_applicable:
                required_set = set(cat_includes)
                intersection = target_data_categories.intersection(required_set)
                if not intersection:
                    is_applicable = False
                else:
                    reasons.append(f"Processes regulated data category: {list(intersection)}")

            # 3. Check Sector (if specified in conditions)
            sec_cond = conds.get("sector")
            if sec_cond and is_applicable:
                if isinstance(sec_cond, list):
                    if target_sector not in sec_cond:
                        is_applicable = False
                    else:
                        reasons.append(f"Project sector '{target_sector}' is in regulated sectors {sec_cond}")
                elif isinstance(sec_cond, str):
                    if target_sector != sec_cond:
                        is_applicable = False
                    else:
                        reasons.append(f"Project sector matches '{target_sector}'")

            # 4. Check Environment (e.g. production vs staging)
            env_cond = conds.get("environment")
            if env_cond and is_applicable:
                if env_cond.lower() != target_env.lower():
                    is_applicable = False
                else:
                    reasons.append(f"Active in '{target_env}' deployment stage")

            # 5. Check Cloud Provider if specified
            provider_cond = conds.get("cloud_provider")
            if provider_cond and is_applicable:
                if provider_cond.lower() != target_provider.lower():
                    is_applicable = False
                else:
                    reasons.append(f"Cloud provider '{target_provider}' requires targeted technical controls")

            if is_applicable:
                reg_name = req.regulation.name if req.regulation else "Unknown Regulation"
                explanation = "Applies because: " + "; ".join(reasons) if reasons else "Universally applicable baseline requirement."
                applicable_list.append(
                    ApplicabilityResult(
                        requirement_id=req.id,
                        regulation_id=req.regulation_id,
                        regulation_name=reg_name,
                        title=req.title,
                        mandatory=req.mandatory,
                        reason=explanation,
                        requirement_text=req.requirement_text
                    ).to_dict()
                )

        return applicable_list
