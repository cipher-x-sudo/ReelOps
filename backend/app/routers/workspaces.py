from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, UserWorkspaceRole, Workspace
from ..rbac import DEFAULT_ROLES, Principal, require_permission
from ..schemas import CreateWorkspaceRequest, WorkspaceOut
from ..services.audit import record_audit

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    principal: Principal = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> list[WorkspaceOut]:
    if "*" in principal.permissions:
        rows = db.query(Workspace).order_by(Workspace.name).all()
    else:
        memberships = db.query(UserWorkspaceRole).filter(UserWorkspaceRole.user_id == principal.actor_user_id).all()
        ids = [m.workspace_id for m in memberships]
        rows = db.query(Workspace).filter(Workspace.id.in_(ids)).order_by(Workspace.name).all()
    return [WorkspaceOut.model_validate(row) for row in rows]


@router.post("", response_model=WorkspaceOut)
def create_workspace(
    payload: CreateWorkspaceRequest,
    principal: Principal = Depends(require_permission("workspaces.manage")),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    workspace = Workspace(name=payload.name, slug=payload.slug)
    db.add(workspace)
    db.flush()
    for name, role_def in DEFAULT_ROLES.items():
        db.add(
            Role(
                workspace_id=workspace.id,
                name=name,
                description=str(role_def["description"]),
                permissions=list(role_def["permissions"]),
                is_system=True,
            )
        )
    record_audit(db, principal=principal, action="workspaces.create", target_type="workspace", target_id=workspace.id)
    db.commit()
    db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)

