from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.app.core.database import get_db
from backend.app.db.models import Project, EvaluationRun, RequirementEvaluation, TechnicalControl
from backend.app.core.auth import require_user
from backend.app.engines.terraform_plan_adapter import TerraformPlanAdapter

router = APIRouter(prefix="/projects", tags=["Infrastructure Topology"])

RESOURCE_CATEGORIES = {
    "aws_db_instance": "DATABASE",
    "aws_dynamodb_table": "DATABASE",
    "aws_s3_bucket": "STORAGE",
    "aws_ebs_volume": "STORAGE",
    "aws_instance": "COMPUTE",
    "aws_vpc": "NETWORK",
    "aws_subnet": "NETWORK",
    "aws_security_group": "SECURITY",
    "aws_lb": "NETWORK",
    "aws_kms_key": "SECURITY",
    "aws_secretsmanager_secret": "SECURITY",
    "aws_waf": "SECURITY",
    "aws_cloudwatch_log_group": "LOGGING",
    "aws_cloudtrail": "LOGGING",
    "aws_iam_role": "IDENTITY",
    "aws_iam_policy": "IDENTITY",
    "aws_iam_user": "IDENTITY",
    "aws_lambda_function": "SERVERLESS",
    "aws_sqs_queue": "MESSAGING",
    "aws_sns_topic": "MESSAGING"
}

def sanitize_attributes(attrs: dict) -> dict:
    if not isinstance(attrs, dict):
        return attrs
    sanitized = {}
    sensitive_keys = ["password", "secret", "token", "access_key", "secret_key", "private_key", "connection", "key_material"]
    for k, v in attrs.items():
        if any(sec in k.lower() for sec in sensitive_keys):
            sanitized[k] = "********"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_attributes(v)
        else:
            sanitized[k] = v
    return sanitized

def extract_resources_recursive(module: dict, base_address: str = "") -> list:
    resources = []
    # Current module resources
    for r in module.get("resources", []):
        resources.append(r)
    # Child modules
    for child in module.get("child_modules", []):
        resources.extend(extract_resources_recursive(child, child.get("address", "")))
    return resources

def extract_edges(configuration_module: dict) -> list:
    edges = []
    for r in configuration_module.get("resources", []):
        source_addr = r.get("address")
        for expr_key, expr_val in r.get("expressions", {}).items():
            if isinstance(expr_val, dict) and "references" in expr_val:
                for ref in expr_val["references"]:
                    # Basic cleanup: if reference is like aws_vpc.main.id, we just want aws_vpc.main
                    # But the reference array usually contains both "aws_vpc.main" and "aws_vpc.main.id"
                    # We will add it directly. The frontend/backend can filter out non-resource refs.
                    if "." in ref and not ref.startswith("var.") and not ref.startswith("local.") and not ref.startswith("data."):
                        # Extract resource address (e.g. aws_vpc.main from aws_vpc.main.id)
                        parts = ref.split(".")
                        if len(parts) >= 2:
                            target_addr = f"{parts[0]}.{parts[1]}"
                            if target_addr != source_addr:
                                edges.append({
                                    "source": source_addr,
                                    "target": target_addr,
                                    "type": "REFERENCE"
                                })
    # Recurse child modules in config
    for child in configuration_module.get("module_calls", {}).values():
        if "module" in child:
            edges.extend(extract_edges(child["module"]))
    return edges

@router.get("/{project_id}/infrastructure/topology")
def get_infrastructure_topology(project_id: str, current_user=Depends(require_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if current_user.role != "ADMIN" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    latest_run = db.query(EvaluationRun).filter(EvaluationRun.project_id == project_id).order_by(EvaluationRun.evaluated_at.desc()).first()
    if not latest_run:
        return {
            "status": "NO_EVALUATION",
            "message": "No infrastructure evaluation is available yet. Run compliance evaluation to generate the native infrastructure model."
        }

    # Stale check
    is_stale = project.infrastructure_hash != latest_run.infrastructure_hash

    # Extract Native Plan
    evidence = latest_run.evidence_payload or {}
    native_plan = evidence.get("native_plan_json", {})
    if not native_plan:
        return {
            "status": "UNSUPPORTED_SOURCE",
            "message": "Topology requires native Terraform Plan JSON evidence."
        }

    planned_values = native_plan.get("planned_values", {})
    root_module = planned_values.get("root_module", {})
    all_plan_resources = extract_resources_recursive(root_module)

    config_root = native_plan.get("configuration", {}).get("root_module", {})
    raw_edges = extract_edges(config_root)
    
    # Deduplicate edges
    unique_edges = {}
    for e in raw_edges:
        key = f"{e['source']}->{e['target']}"
        unique_edges[key] = e
    edges = list(unique_edges.values())

    # Get compliance overlay
    req_evals = db.query(RequirementEvaluation).filter(RequirementEvaluation.evaluation_run_id == latest_run.id).all()
    
    # Map findings to resources
    resource_compliance = {}
    for re in req_evals:
        for f in (re.findings or []):
            if isinstance(f, dict) and "resource" in f:
                res_addr = f["resource"]
                if res_addr not in resource_compliance:
                    resource_compliance[res_addr] = {"controls": [], "status": "PASS", "failed_count": 0}
                
                res_status = f.get("result", "PASS")
                resource_compliance[res_addr]["controls"].append({
                    "control_id": f.get("control_id"),
                    "status": res_status
                })
                
                if res_status == "FAIL":
                    resource_compliance[res_addr]["status"] = "FAIL"
                    resource_compliance[res_addr]["failed_count"] += 1
                elif res_status == "UNKNOWN" and resource_compliance[res_addr]["status"] != "FAIL":
                    resource_compliance[res_addr]["status"] = "UNKNOWN"

    # Pre-calculate supported resource types
    all_controls = db.query(TechnicalControl).all()
    supported_types = set()
    for c in all_controls:
        exp = c.expected_state or {}
        if "resource_type" in exp:
            supported_types.add(exp["resource_type"])

    # Build node list
    nodes = []
    supported_count = 0
    passed_count = 0
    failed_count = 0
    unknown_count = 0

    for r in all_plan_resources:
        r_addr = r.get("address")
        r_type = r.get("type")
        is_supported = r_type in supported_types
        
        comp_data = resource_compliance.get(r_addr, {})
        status = comp_data.get("status", "PASS") if is_supported else "UNSUPPORTED"
        
        if is_supported:
            supported_count += 1
            if status == "PASS": passed_count += 1
            elif status == "FAIL": failed_count += 1
            elif status == "UNKNOWN": unknown_count += 1

        node = {
            "id": r_addr,
            "address": r_addr,
            "type": r_type,
            "name": r.get("name"),
            "provider": r.get("provider_name"),
            "module": r_addr.split(".aws_")[0] if ".aws_" in r_addr and r_addr.startswith("module.") else None,
            "category": RESOURCE_CATEGORIES.get(r_type, "OTHER"),
            "region": "ap-south-1", # Approximation or parsed from provider config
            "compliance_status": status,
            "supported": is_supported,
            "control_count": len(comp_data.get("controls", [])),
            "failed_control_count": comp_data.get("failed_count", 0),
            "attributes": sanitize_attributes(r.get("values", {})),
            "controls": comp_data.get("controls", [])
        }
        nodes.append(node)

    # Filter edges to only include nodes that exist
    valid_node_ids = {n["id"] for n in nodes}
    valid_edges = [e for e in edges if e["source"] in valid_node_ids and e["target"] in valid_node_ids]

    total_resources = len(nodes)
    unsupported_count = total_resources - supported_count
    coverage_pct = (supported_count / total_resources * 100) if total_resources > 0 else 100.0

    return {
        "project_id": project.id,
        "project_name": project.name,
        "evaluation_run_id": latest_run.id,
        "evaluation_source": "TERRAFORM_NATIVE_PLAN",
        "infrastructure_hash": project.infrastructure_hash,
        "plan_hash": latest_run.plan_hash,
        "stale": is_stale,
        "resources": nodes,
        "edges": valid_edges,
        "coverage": {
            "total_resources": total_resources,
            "supported_resources": supported_count,
            "unsupported_resources": unsupported_count,
            "resource_coverage_percent": round(coverage_pct, 1),
            "controls_evaluated": sum(n["control_count"] for n in nodes),
            "resources_passed": passed_count,
            "resources_failed": failed_count,
            "resources_unknown": unknown_count
        }
    }
