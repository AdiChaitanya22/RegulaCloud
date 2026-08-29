from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import AuditLog

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit Logs"])

@router.get("/logs")
def get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(50).all()
    return [
        {
            "id": f"log-{l.id}",
            "actor": l.actor,
            "action": l.action,
            "resource": f"{l.resource_type}:{l.resource_id or 'global'}",
            "severity": l.severity,
            "current_hash": l.current_hash[:16] + "...",
            "previous_hash": l.previous_hash[:16] + "...",
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if l.timestamp else "Just now"
        }
        for l in logs
    ]
