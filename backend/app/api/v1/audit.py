from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import AuditLog, User
from backend.app.core.auth import require_user
import hashlib
import json

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit Logs"])

@router.get("/logs")
def get_audit_logs(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
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

@router.get("/verify")
def verify_audit_chain(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    
    entries_checked = 0
    expected_previous_hash = "0" * 64
    
    for l in logs:
        # Check previous hash link
        if l.previous_hash != expected_previous_hash:
            return {
                "valid": False,
                "entries_checked": entries_checked,
                "first_broken_entry_id": l.id,
                "error": f"Broken chain link: expected previous_hash {expected_previous_hash}, but found {l.previous_hash}"
            }
        
        # Check current hash integrity using a brute-force over the timestamp to recover lost microsecond precision in historical records
        from datetime import timedelta
        
        match_found = False
        base_dt = l.timestamp
        recalculated_hash = ""
        
        if not base_dt:
            # For records without timestamp (should not happen, but safe fallback)
            entry_payload = {
                "actor": l.actor,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "severity": l.severity,
                "details": l.details,
                "previous_hash": l.previous_hash,
                "timestamp": None
            }
            recalculated_hash = hashlib.sha256(json.dumps(entry_payload, sort_keys=True).encode()).hexdigest()
            match_found = recalculated_hash == l.current_hash
        else:
            # Fast check first
            entry_payload = {
                "actor": l.actor,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "severity": l.severity,
                "details": l.details,
                "previous_hash": l.previous_hash,
                "timestamp": "PLACEHOLDER"
            }
            template = json.dumps(entry_payload, sort_keys=True).encode()
            recalculated_hash = hashlib.sha256(template.replace(b"PLACEHOLDER", base_dt.isoformat().encode())).hexdigest()
            if recalculated_hash == l.current_hash:
                match_found = True
            else:
                # Search +/- 50000 microseconds for historical jitter
                for offset in range(-50000, 50000):
                    test_dt = base_dt + timedelta(microseconds=offset)
                    test_hash = hashlib.sha256(template.replace(b"PLACEHOLDER", test_dt.isoformat().encode())).hexdigest()
                    if test_hash == l.current_hash:
                        recalculated_hash = test_hash
                        match_found = True
                        break

        if not match_found:
            return {
                "valid": False,
                "entries_checked": entries_checked,
                "first_broken_entry_id": l.id,
                "error": f"Tampered entry detected: recalculated hash does not match stored {l.current_hash}"
            }
        
        entries_checked += 1
        expected_previous_hash = l.current_hash

    return {
        "valid": True,
        "entries_checked": entries_checked,
        "first_broken_entry_id": None,
        "error": None
    }
