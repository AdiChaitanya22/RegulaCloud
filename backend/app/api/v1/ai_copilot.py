from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.ai import AIChatRequest, AIChatResponse, DeterministicStateSnapshot
from backend.app.engines.rag_engine import RAGEngine
from backend.app.engines.guardrails import GuardrailEngine, LEGAL_DISCLAIMER
from backend.app.engines.llm_client import LLMClient
from backend.app.db.models import AuditLog

router = APIRouter(prefix="/ai", tags=["Grounded AI Copilot"])

llm_client = LLMClient()

@router.post("/chat", response_model=AIChatResponse)
def chat_with_copilot(
    req: AIChatRequest = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # 1. Retrieve Grounded Context from KB & Evaluation Vault
        context = RAGEngine.assemble_context(db, req.project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context retrieval error: {str(e)}")

    # 2. Extract Citations & Build State Snapshot
    citations = GuardrailEngine.build_citations(context)
    deterministic_snapshot = DeterministicStateSnapshot(
        project_id=context.project_id,
        project_name=context.project_name,
        overall_status=context.overall_status,
        deployment_allowed=context.deployment_allowed,
        compliance_score=context.compliance_score,
        passed_count=context.passed_count,
        failed_count=context.failed_count,
        unknown_count=context.unknown_count,
        evidence_hash=context.evidence_hash
    )

    # 3. Generate Grounded AI Response
    history_dicts = [{"role": m.role, "content": m.content} for m in req.conversation_history] if req.conversation_history else []
    gen_result = llm_client.generate_response(
        user_message=req.message,
        context=context,
        history=history_dicts
    )

    # 4. Record Audit Log Entry (Phase 10)
    AuditLog.create_entry(
        session=db,
        actor="ai_copilot.user",
        action="AI_COPILOT_QUERY",
        resource_type="PROJECT_EVALUATION",
        resource_id=req.project_id,
        severity="Low",
        details={
            "query": req.message[:150],
            "overall_status": context.overall_status,
            "score": context.compliance_score,
            "provider": gen_result.get("provider"),
            "evidence_hash": context.evidence_hash
        }
    )

    return AIChatResponse(
        reply=gen_result["reply"],
        deterministic_state=deterministic_snapshot,
        citations=citations,
        disclaimer=LEGAL_DISCLAIMER,
        llm_provider_used=gen_result.get("provider", "DETERMINISTIC_GROUNDED_ENGINE"),
        grounding_sources_used=context.grounding_sources
    )
