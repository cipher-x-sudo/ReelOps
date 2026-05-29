from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, User, UserWorkspaceRole, Workspace
from ..rbac import Principal, get_current_principal
from ..schemas import LoginRequest, MeResponse, MembershipOut, RoleOut, TokenResponse, UserOut, WorkspaceOut
from ..security import create_access_token, verify_password
from ..services.audit import record_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id)
    membership = db.query(UserWorkspaceRole).filter(UserWorkspaceRole.user_id == user.id).first()
    record_audit(
        db,
        principal=None,
        action="auth.login",
        target_type="user",
        target_id=user.id,
        workspace_id=membership.workspace_id if membership else None,
    )
    db.commit()
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)) -> MeResponse:
    if not principal.user:
        raise HTTPException(status_code=400, detail="API keys do not have a user profile")
    memberships = []
    rows = db.query(UserWorkspaceRole).filter(UserWorkspaceRole.user_id == principal.user.id).all()
    for row in rows:
        workspace = db.get(Workspace, row.workspace_id)
        role = db.get(Role, row.role_id)
        if workspace and role:
            memberships.append(
                MembershipOut(
                    workspace=WorkspaceOut.model_validate(workspace),
                    role=RoleOut.model_validate(role),
                )
            )
    return MeResponse(user=UserOut.model_validate(principal.user), memberships=memberships)

