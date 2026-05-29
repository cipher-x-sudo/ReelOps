from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import ApiKey, Role, User, UserWorkspaceRole
from .security import API_KEY_PREFIX, decode_access_token, hash_api_key

PERMISSIONS = [
    "workspaces.manage",
    "users.manage",
    "roles.manage",
    "settings.manage",
    "niches.manage",
    "jobs.view",
    "jobs.create",
    "jobs.approve",
    "jobs.render",
    "exports.download",
    "api_keys.manage",
]

DEFAULT_ROLES: dict[str, dict[str, object]] = {
    "Owner": {"description": "Full system access.", "permissions": ["*"]},
    "Admin": {"description": "Manage users, settings, niches, and jobs.", "permissions": PERMISSIONS},
    "Producer": {
        "description": "Create jobs, run generation, select assets, render and export reels.",
        "permissions": ["jobs.view", "jobs.create", "jobs.render", "exports.download"],
    },
    "Reviewer": {
        "description": "Review and approve scripts, prompts, assets, and renders.",
        "permissions": ["jobs.view", "jobs.approve", "exports.download"],
    },
    "Viewer": {"description": "Read-only access to jobs and exports.", "permissions": ["jobs.view", "exports.download"]},
}


@dataclass
class Principal:
    user: Optional[User]
    api_key: Optional[ApiKey]
    workspace_id: str
    permissions: set[str]

    @property
    def actor_user_id(self) -> Optional[str]:
        return self.user.id if self.user else None

    @property
    def api_key_id(self) -> Optional[str]:
        return self.api_key.id if self.api_key else None


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


def _resolve_user_principal(db: Session, token: str, requested_workspace_id: Optional[str]) -> Principal:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    query = db.query(UserWorkspaceRole).filter(UserWorkspaceRole.user_id == user.id)
    if requested_workspace_id:
        query = query.filter(UserWorkspaceRole.workspace_id == requested_workspace_id)
    membership = query.first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace membership")

    role = db.get(Role, membership.role_id)
    permissions = set(role.permissions or []) if role else set()
    return Principal(user=user, api_key=None, workspace_id=membership.workspace_id, permissions=permissions)


def _resolve_api_key_principal(db: Session, token: str) -> Principal:
    key_hash = hash_api_key(token)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)).first()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    permissions = set(api_key.permissions or [])
    return Principal(user=None, api_key=api_key, workspace_id=api_key.workspace_id, permissions=permissions)


def get_current_principal(
    authorization: Optional[str] = Header(None),
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    db: Session = Depends(get_db),
) -> Principal:
    token = _extract_bearer(authorization)
    if token.startswith(f"{API_KEY_PREFIX}_"):
        return _resolve_api_key_principal(db, token)
    return _resolve_user_principal(db, token, workspace_id)


def has_permission(principal: Principal, permission: str) -> bool:
    return "*" in principal.permissions or permission in principal.permissions


def require_permission(permission: str) -> Callable:
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not has_permission(principal, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")
        return principal

    return dependency

