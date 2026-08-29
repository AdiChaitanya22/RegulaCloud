from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.app.core.database import get_db
from backend.app.engines.applicability_engine import ApplicabilityEngine
from backend.app.db.models import Regulation, RegulatoryRequirement, TechnicalControl, RequirementControlMapping

router = APIRouter(prefix="/applicability", tags=["Applicability Engine"])

@router.post("/evaluate")
def evaluate_applicability(project_profile: Dict[str, Any], db: Session = Depends(get_db)):
    applicable_reqs = ApplicabilityEngine.evaluate_applicability(project_profile, db)
    return {
        "jurisdiction": project_profile.get("jurisdiction", "India"),
        "sector": project_profile.get("sector", "General"),
        "applicable_count": len(applicable_reqs),
        "applicable_requirements": applicable_reqs
    }

@router.get("/traceability-matrix")
def get_traceability_matrix(db: Session = Depends(get_db)):
    regulations = db.query(Regulation).all()
    matrix = []

    for reg in regulations:
        reg_item = {
            "regulation_id": reg.id,
            "regulation_name": reg.name,
            "version": reg.version,
            "requirements": []
        }
        for req in reg.requirements:
            req_dict = {
                "requirement_id": req.id,
                "title": req.title,
                "mandatory": req.mandatory,
                "status": req.status,
                "controls": []
            }
            mappings = db.query(RequirementControlMapping).filter(
                RequirementControlMapping.requirement_id == req.id
            ).all()
            for m in mappings:
                ctrl = db.query(TechnicalControl).filter(TechnicalControl.id == m.control_id).first()
                if ctrl:
                    req_dict["controls"].append({
                        "control_id": ctrl.id,
                        "name": ctrl.name,
                        "verification_source": ctrl.verification_source,
                        "mapping_rationale": m.mapping_rationale
                    })
            reg_item["requirements"].append(req_dict)
        matrix.append(reg_item)

    return matrix
