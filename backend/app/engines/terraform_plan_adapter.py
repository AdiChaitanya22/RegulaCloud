from typing import Dict, Any, List

class TerraformPlanAdapter:
    """
    Adapts Native Terraform Plan JSON (planned_values) to the canonical RegulaCloud 
    resource_changes structure expected by the existing OPA policies.
    """

    @classmethod
    def adapt(cls, native_plan: Dict[str, Any]) -> Dict[str, Any]:
        if not native_plan or "planned_values" not in native_plan:
            return {"resource_changes": []}

        planned_values = native_plan.get("planned_values", {})
        root_module = planned_values.get("root_module", {})
        
        adapted_changes = []
        cls._extract_resources(root_module, adapted_changes)

        return {"resource_changes": adapted_changes}

    @classmethod
    def _extract_resources(cls, module_node: Dict[str, Any], results: List[Dict[str, Any]]):
        # Extract from current module
        for res in module_node.get("resources", []):
            if res.get("mode") == "managed":
                adapted_res = {
                    "address": res.get("address"),
                    "type": res.get("type"),
                    "name": res.get("name"),
                    "provider_name": res.get("provider_name"),
                    "change": {
                        "actions": ["create"], # Always evaluated as creation for offline static analysis
                        "after": res.get("values", {})
                    }
                }
                results.append(adapted_res)

        # Recurse into child modules
        for child in module_node.get("child_modules", []):
            cls._extract_resources(child, results)
