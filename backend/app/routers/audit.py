from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog
from ..rbac import Principal, require_permission

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_logs(
    principal: Principal = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.workspace_id == principal.workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": row.id,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "details": row.details,
            "created_at": row.created_at,
        }
        for row in rows
    ]

