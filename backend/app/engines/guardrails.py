from typing import List, Dict, Any, Tuple
from backend.app.schemas.ai import Citation, DeterministicStateSnapshot
from backend.app.engines.rag_engine import RAGContext

LEGAL_DISCLAIMER = (
    "RegulaCloud provides technical compliance verification and explanation. "
    "It does not provide legal advice or legal certification."
)

SYSTEM_PROMPT = """You are RegulaCloud AI Copilot, a technical cloud compliance assistant for government regulators and cloud architects.

CRITICAL OPERATIONAL RULES:
1. AUTHORITY BOUNDARY: You are an explanatory copilot only. The deterministic compliance engine results in the provided context are authoritative, absolute, and immutable.
2. ZERO OVERRIDE PRIVILEGE: You have NO authority to approve deployments, change compliance scores, or override OPA/SonarQube decisions. If asked to approve a deployment, state clearly that approval is governed solely by the deterministic compliance gate and authorized administrator signature.
3. GROUNDING OBLIGATION: Answer questions using ONLY the provided [AUTHORITATIVE DETERMINISTIC EVALUATION STATE], [APPLICABLE STATUTORY REQUIREMENTS], [ACTIVE OPA REGO POLICY VIOLATIONS], and [RECOMMENDED Q-LEARNING REMEDIATION ROADMAP].
4. FAIL-CLOSED INTEGRITY: If deterministic status is FAIL or UNKNOWN, you must NEVER claim the deployment is compliant, approved, or unblocked.
5. CITATIONS: Clearly cite the regulation name, statutory section, and technical control ID for every technical point discussed.
6. NO LEGAL ADVICE: Frame all explanations as technical verification against codified rules."""

class GuardrailEngine:
    """
    Enforces compliance safety boundaries, anti-jailbreak checks,
    and structured citation extraction.
    """

    @classmethod
    def get_system_prompt(cls) -> str:
        return SYSTEM_PROMPT

    @classmethod
    def build_citations(cls, context: RAGContext) -> List[Citation]:
        citations: List[Citation] = []
        
        # 1. Statutory Regulation Citations
        for req in context.applicable_requirements:
            citations.append(Citation(
                type="REGULATION",
                reference_id=req["requirement_id"],
                label=f"{req['regulation_name']} - {req['title']}",
                target_control=None,
                target_resource=None
            ))

        # 2. Empirical OPA Evidence Citations
        for v in context.opa_violations:
            citations.append(Citation(
                type="EVIDENCE",
                reference_id=v.get("policy_id", "OPA-POLICY"),
                label=f"OPA: {v.get('resource')} ({v.get('control_id')})",
                target_control=v.get("control_id"),
                target_resource=v.get("resource")
            ))

        # 3. SonarQube Evidence Citations
        for f in context.sonar_findings:
            citations.append(Citation(
                type="EVIDENCE",
                reference_id=f.get("cwe", "CWE-MISC"),
                label=f"SonarQube: {f.get('file')}:{f.get('line')} ({f.get('title')})",
                target_control=None,
                target_resource=f.get("file")
            ))

        # 4. Remediation Citations
        for r in context.remediation_steps:
            citations.append(Citation(
                type="REMEDIATION",
                reference_id=f"STEP-{r.get('step')}",
                label=f"Remediation: {r.get('name')}",
                target_control=r.get("target_control"),
                target_resource=None
            ))

        return citations

    @classmethod
    def generate_deterministic_grounded_response(cls, user_message: str, context: RAGContext) -> str:
        """
        Generates a 100% grounded response derived strictly from DB evidence
        when no external LLM API key is configured.
        """
        q = user_message.lower()

        # 1. Approval / Gate Override Request
        if any(w in q for w in ["approve", "authorize", "override", "unblock", "certify", "allow deploy"]):
            if not context.deployment_allowed:
                return (
                    f"⛔ **Deployment Approval Prohibited**: As an AI Copilot, I have zero authority to approve deployments or override compliance decisions.\n\n"
                    f"The authoritative deterministic compliance engine evaluated this project as **{context.overall_status}** ({context.compliance_score:.1f}% compliance score). "
                    f"Deployment is currently **STRICTLY BLOCKED** because {context.failed_count} mandatory statutory controls failed.\n\n"
                    f"To unblock deployment, all failed controls must be remediated in Terraform/SonarQube and re-evaluated by the deterministic engine."
                )
            else:
                return (
                    f"ℹ️ **Deployment Gate Status**: Deterministic compliance is verified at **{context.compliance_score:.1f}% (PASS)**. "
                    f"However, formal deployment authorization requires a cryptographic administrator signature in the Deploy center. AI cannot autonomously trigger AWS rollout."
                )

        # 2. Empirical Evidence Inquiry
        if any(w in q for w in ["evidence", "telemetry", "hash", "what evidence"]):
            opa_lines = "\n".join([
                f"- OPA Resource `{v.get('resource')}`: Failed `{v.get('control_id')}` -> {v.get('explanation')}"
                for v in context.opa_violations
            ]) or "- 0 OPA Rego policy violations."

            sonar_lines = "\n".join([
                f"- SonarQube Finding `{f.get('file')}:{f.get('line')}`: [{f.get('severity')}] {f.get('title')} ({f.get('cwe')})"
                for f in context.sonar_findings
            ]) or "- 0 SonarQube static code security findings."

            return (
                f"🧾 **Empirical Verification Evidence for {context.project_name}**:\n\n"
                f"**Deterministic State**: {context.overall_status} ({context.compliance_score:.1f}% Score)\n"
                f"**Cryptographic Evidence Hash**: `{context.evidence_hash}`\n\n"
                f"**OPA Rego Plan Inspection Results**:\n{opa_lines}\n\n"
                f"**Static Application Security (SonarQube) Findings**:\n{sonar_lines}\n\n"
                f"*All evidence hashes are immutably signed into the PostgreSQL audit ledger.*"
            )

        # 3. Technical Controls Inquiry
        if any(w in q for w in ["control", "controls", "technical control"]):
            ctrl_lines = []
            for v in context.opa_violations:
                ctrl_lines.append(f"- OPA Control **`{v.get('control_id')}`** (Policy: `{v.get('policy_id')}` on `{v.get('resource')}`): {v.get('explanation')}")
            for fc in context.failed_controls:
                if fc.get("control_id") not in [v.get("control_id") for v in context.opa_violations]:
                    ctrl_lines.append(f"- Code Security Control **`{fc.get('control_id')}`** (Requirement: `{fc.get('requirement_id')}`): {fc.get('reason')}")
            
            if ctrl_lines:
                return f"🔍 **Failed Technical Controls ({len(ctrl_lines)})**:\n\n" + "\n".join(ctrl_lines)
            return "✅ **All Technical Controls Passed**: 0 active OPA or SonarQube control violations."

        # 4. Remediation Inquiry
        if any(w in q for w in ["remediation", "fix", "rl", "q-learning", "recommend", "optimize"]):
            if context.remediation_steps:
                steps_text = "\n".join([
                    f"**Step {r.get('step')}: {r.get('name')}**\n- Target Control: `{r.get('target_control')}`\n- Impact: {r.get('cost_impact')} | Complexity: {r.get('complexity')}\n"
                    for r in context.remediation_steps
                ])
                return (
                    f"🤖 **Q-Learning Remediation Optimizer Recommendations**:\n\n{steps_text}"
                    f"\n*The Q-learning policy prioritizes database isolation and KMS encryption first due to statutory penalty weights (+100 reward for mandatory compliance).*"
                )
            return "✅ No active remediation required. All cloud infrastructure conforms to approved regulatory baselines."

        # 5. Applicable Regulations Inquiry
        if any(w in q for w in ["regulation", "regulations", "act", "law", "applicable", "dpdp", "cert-in"]):
            req_lines = [
                f"- **{r['requirement_id']}** ({r['regulation_name']}): *{r['title']}* (Mandatory: `{r['mandatory']}`) — {r['reason']}"
                for r in context.applicable_requirements
            ]
            return (
                f"📋 **Applicable Regulatory Corpus for {context.project_name}** ({context.jurisdiction}, {context.sector}):\n\n"
                + "\n".join(req_lines)
            )

        # 6. Why is deployment blocked?
        if any(w in q for w in ["blocked", "why", "fail", "gate", "reason"]):
            if not context.deployment_allowed:
                reasons = []
                for idx, v in enumerate(context.opa_violations, 1):
                    reasons.append(f"{idx}. **{v.get('resource')}** — Violated `{v.get('control_id')}`: {v.get('explanation')}")
                
                violations_text = "\n".join(reasons) if reasons else "Mandatory statutory controls failed verification."
                return (
                    f"🚨 **Deployment is Blocked**: Project **{context.project_name}** evaluated to **{context.overall_status}** with a compliance score of **{context.compliance_score:.1f}%**.\n\n"
                    f"**Statutory Violations Causing Deployment Block**:\n{violations_text}\n\n"
                    f"**Evidence Hash**: `{context.evidence_hash}`\n\n"
                    f"**Required Action**: Execute the {len(context.remediation_steps)}-step Q-learning remediation roadmap in the Deploy Center to restore compliance."
                )
            else:
                return (
                    f"✅ **Deployment is Not Blocked**: Project **{context.project_name}** has passed all mandatory statutory controls with a compliance score of **{context.compliance_score:.1f}% (PASS)**. "
                    f"Evidence hash `{context.evidence_hash}` is recorded in the cryptographic audit ledger."
                )

        # Default Grounded Overview
        return (
            f"I am RegulaCloud AI Copilot for **{context.project_name}**.\n\n"
            f"- **Jurisdiction**: {context.jurisdiction} ({context.sector})\n"
            f"- **Current Compliance State**: **{context.overall_status}** ({context.compliance_score:.1f}% score)\n"
            f"- **Deployment Gate**: {'🟢 UNBLOCKED' if context.deployment_allowed else '🔴 DEPLOYMENT BLOCKED'}\n"
            f"- **Active Violations**: {context.failed_count} controls\n\n"
            f"You can ask me about applicable regulations, specific failed controls, empirical evidence, or Q-learning remediation steps."
        )
