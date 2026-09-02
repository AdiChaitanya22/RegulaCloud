from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.app.core.database import get_db
from backend.app.db.models import SystemSetting, AuditLog

router = APIRouter(prefix="/settings", tags=["System Settings"])

DEFAULT_SETTINGS = {
    "awsArn": "arn:aws:iam::123456789012:role/ReguCloudCrossAccount",
    "azureTenant": "4fa38c92-38ef-4122-8321-75bf22e391aa",
    "slackWebhook": "https://example.com/slack-webhook",
    "rulesPci": True,
    "rulesSoc": True,
    "rulesHipaa": False,
    "scanIntervalHours": 1,
    "enforcementMode": "FailClosed"
}

@router.get("")
def get_settings(db: Session = Depends(get_db)):
    setting_row = db.query(SystemSetting).filter(SystemSetting.key == "global_config").first()
    if setting_row and setting_row.value:
        return setting_row.value
    return DEFAULT_SETTINGS

@router.post("")
def save_settings(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    setting_row = db.query(SystemSetting).filter(SystemSetting.key == "global_config").first()
    if not setting_row:
        setting_row = SystemSetting(key="global_config", value=payload)
        db.add(setting_row)
    else:
        setting_row.value = payload
        
    AuditLog.create_entry(
        session=db,
        actor="system.admin",
        action="UPDATE_SYSTEM_SETTINGS",
        resource_type="SETTINGS",
        resource_id="global_config",
        severity="Low",
        details={"updated_keys": list(payload.keys())}
    )
    db.commit()
    return {"status": "SUCCESS", "settings": setting_row.value}
