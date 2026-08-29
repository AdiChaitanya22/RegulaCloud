from fastapi import APIRouter, Body
from typing import Dict, Any
from backend.app.engines.terraform_engine import TerraformEngine
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator

router = APIRouter(prefix="/terraform", tags=["Terraform & OPA"])

@router.post("/generate")
def generate_terraform(params: Dict[str, Any] = Body(...)):
    hcl = TerraformEngine.generate_compliant_hcl(params)
    plan_json = TerraformEngine.hcl_to_plan_json(hcl)
    return {
        "hcl": hcl,
        "plan_json": plan_json
    }

@router.post("/plan-and-opa-eval")
def plan_and_opa_eval(payload: Dict[str, Any] = Body(...)):
    hcl_code = payload.get("hcl_code", "")
    plan_json = payload.get("plan_json")
    
    if not plan_json and hcl_code:
        plan_json = TerraformEngine.hcl_to_plan_json(hcl_code)
    elif not plan_json:
        default_hcl = TerraformEngine.generate_compliant_hcl({})
        plan_json = TerraformEngine.hcl_to_plan_json(default_hcl)

    violations = OPAPolicyEvaluator.evaluate_terraform_plan(plan_json)
    
    return {
        "plan_summary": {
            "resources_count": len(plan_json.get("resource_changes", []))
        },
        "violations_count": len(violations),
        "status": "FAIL" if violations else "PASS",
        "violations": violations
    }
