from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role
from ..rbac import PERMISSIONS, Principal, require_permission
from ..schemas import CreateRoleRequest, RoleOut
from ..services.audit import record_audit

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("/permissions")
def list_permissions(principal: Principal = Depends(require_permission("roles.manage"))) -> dict[str, list[str]]:
    return {"permissions": PERMISSIONS}


@router.get("", response_model=list[RoleOut])
def list_roles(
    principal: Principal = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> list[RoleOut]:
    rows = db.query(Role).filter(Role.workspace_id == principal.workspace_id).order_by(Role.is_system.desc(), Role.name).all()
    return [RoleOut.model_validate(row) for row in rows]


@router.post("", response_model=RoleOut)
def create_role(
    payload: CreateRoleRequest,
    principal: Principal = Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
) -> RoleOut:
    invalid = [p for p in payload.permissions if p not in PERMISSIONS and p != "*"]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid permissions: {', '.join(invalid)}")
    role = Role(
        workspace_id=principal.workspace_id,
        name=payload.name,
        description=payload.description,
        permissions=payload.permissions,
        is_system=False,
    )
    db.add(role)
    db.flush()
    record_audit(db, principal=principal, action="roles.create", target_type="role", target_id=role.id)
    db.commit()
    db.refresh(role)
    return RoleOut.model_validate(role)

