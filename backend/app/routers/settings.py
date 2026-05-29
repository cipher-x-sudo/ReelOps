from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import AppSetting
from ..rbac import Principal, require_permission
from ..services.audit import record_audit

router = APIRouter(prefix="/api/settings", tags=["settings"])


SAFE_ENV_KEYS = [
    "flow2api_base_url",
    "llm_provider",
    "llm_model",
    "tts_provider",
    "tts_voice",
    "render_mode",
]


@router.get("")
def get_settings(
    principal: Principal = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
):
    rows = db.query(AppSetting).filter(AppSetting.workspace_id == principal.workspace_id).all()
    configured = {row.key: row.value for row in rows}
    env_defaults = {key: getattr(settings, key) for key in SAFE_ENV_KEYS}
    return {"env_defaults": env_defaults, "workspace": configured}


@router.put("/{key}")
def put_setting(
    key: str,
    value: dict,
    principal: Principal = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
):
    row = db.query(AppSetting).filter(AppSetting.workspace_id == principal.workspace_id, AppSetting.key == key).first()
    if not row:
        row = AppSetting(workspace_id=principal.workspace_id, key=key, value=value)
        db.add(row)
    else:
        row.value = value
    record_audit(db, principal=principal, action="settings.update", target_type="setting", target_id=key)
    db.commit()
    return {"ok": True, "key": key, "value": value}

