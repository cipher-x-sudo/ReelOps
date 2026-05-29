from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, User, UserWorkspaceRole, Workspace
from ..rbac import Principal, require_permission
from ..schemas import CreateUserRequest, UpdateUserRequest, UserOut
from ..security import hash_password
from ..services.audit import record_audit

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    principal: Principal = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    memberships = db.query(UserWorkspaceRole).filter(UserWorkspaceRole.workspace_id == principal.workspace_id).all()
    user_ids = [m.user_id for m in memberships]
    rows = db.query(User).filter(User.id.in_(user_ids)).order_by(User.email).all()
    return [UserOut.model_validate(row) for row in rows]


@router.post("", response_model=UserOut)
def create_user(
    payload: CreateUserRequest,
    principal: Principal = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> UserOut:
    workspace = db.get(Workspace, payload.workspace_id)
    role = db.get(Role, payload.role_id)
    if not workspace or not role or role.workspace_id != workspace.id:
        raise HTTPException(status_code=400, detail="Invalid workspace or role")
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    user = User(
        email=payload.email.lower(),
        name=payload.name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(UserWorkspaceRole(user_id=user.id, workspace_id=workspace.id, role_id=role.id))
    record_audit(db, principal=principal, action="users.create", target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    principal: Principal = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.name is not None:
        user.name = payload.name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.workspace_id and payload.role_id:
        role = db.get(Role, payload.role_id)
        if not role or role.workspace_id != payload.workspace_id:
            raise HTTPException(status_code=400, detail="Invalid role for workspace")
        membership = (
            db.query(UserWorkspaceRole)
            .filter(UserWorkspaceRole.user_id == user.id, UserWorkspaceRole.workspace_id == payload.workspace_id)
            .first()
        )
        if membership:
            membership.role_id = payload.role_id
        else:
            db.add(UserWorkspaceRole(user_id=user.id, workspace_id=payload.workspace_id, role_id=payload.role_id))
    record_audit(db, principal=principal, action="users.update", target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)

