from __future__ import annotations

from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine
from .models import Role, User, UserWorkspaceRole, Workspace
from .rbac import DEFAULT_ROLES
from .security import hash_password


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def seed_defaults(db: Session) -> None:
    workspace = db.query(Workspace).filter(Workspace.slug == "default").first()
    if not workspace:
        workspace = Workspace(name="Default Workspace", slug="default")
        db.add(workspace)
        db.flush()

    roles_by_name: dict[str, Role] = {}
    for role_name, role_def in DEFAULT_ROLES.items():
        role = (
            db.query(Role)
            .filter(Role.workspace_id == workspace.id, Role.name == role_name)
            .first()
        )
        if not role:
            role = Role(
                workspace_id=workspace.id,
                name=role_name,
                description=str(role_def["description"]),
                permissions=list(role_def["permissions"]),
                is_system=True,
            )
            db.add(role)
            db.flush()
        roles_by_name[role_name] = role

    admin = db.query(User).filter(User.email == settings.admin_user.lower()).first()
    if not admin:
        admin = User(
            email=settings.admin_user.lower(),
            name="ReelOps Owner",
            password_hash=hash_password(settings.admin_password),
            is_active=True,
        )
        db.add(admin)
        db.flush()

    existing_membership = (
        db.query(UserWorkspaceRole)
        .filter(UserWorkspaceRole.user_id == admin.id, UserWorkspaceRole.workspace_id == workspace.id)
        .first()
    )
    if not existing_membership:
        db.add(UserWorkspaceRole(user_id=admin.id, workspace_id=workspace.id, role_id=roles_by_name["Owner"].id))

    db.commit()

