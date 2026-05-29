from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import AuditLog
from ..rbac import Principal


def record_audit(
    db: Session,
    *,
    principal: Optional[Principal],
    action: str,
    target_type: str = "",
    target_id: str = "",
    details: Optional[dict[str, Any]] = None,
    workspace_id: Optional[str] = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=principal.actor_user_id if principal else None,
            api_key_id=principal.api_key_id if principal else None,
            workspace_id=workspace_id or (principal.workspace_id if principal else None),
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )
    )

