from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ApiKey
from ..rbac import PERMISSIONS, Principal, require_permission
from ..schemas import ApiKeyCreateRequest, ApiKeyCreateResponse
from ..security import api_key_prefix, hash_api_key, new_api_key
from ..services.audit import record_audit

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


@router.get("")
def list_api_keys(
    principal: Principal = Depends(require_permission("api_keys.manage")),
    db: Session = Depends(get_db),
):
    rows = db.query(ApiKey).filter(ApiKey.workspace_id == principal.workspace_id).order_by(ApiKey.created_at.desc()).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "key_prefix": row.key_prefix,
            "permissions": row.permissions,
            "is_active": row.is_active,
            "created_at": row.created_at,
            "last_used_at": row.last_used_at,
        }
        for row in rows
    ]


@router.post("", response_model=ApiKeyCreateResponse)
def create_api_key(
    payload: ApiKeyCreateRequest,
    principal: Principal = Depends(require_permission("api_keys.manage")),
    db: Session = Depends(get_db),
) -> ApiKeyCreateResponse:
    invalid = [p for p in payload.permissions if p not in PERMISSIONS and p != "*"]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid permissions: {', '.join(invalid)}")
    plaintext = new_api_key()
    row = ApiKey(
        workspace_id=principal.workspace_id,
        name=payload.name,
        key_prefix=api_key_prefix(plaintext),
        key_hash=hash_api_key(plaintext),
        permissions=payload.permissions,
        created_by_user_id=principal.actor_user_id,
    )
    db.add(row)
    db.flush()
    record_audit(db, principal=principal, action="api_keys.create", target_type="api_key", target_id=row.id)
    db.commit()
    return ApiKeyCreateResponse(id=row.id, name=row.name, key=plaintext, key_prefix=row.key_prefix, permissions=row.permissions)

