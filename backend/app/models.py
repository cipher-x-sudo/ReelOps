from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(180), unique=True, nullable=False)
    slug = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=new_id)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(180), nullable=False, default="")
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    memberships = relationship("UserWorkspaceRole", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_role_workspace_name"),)

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    description = Column(Text, nullable=False, default="")
    permissions = Column(JSON, nullable=False, default=list)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class UserWorkspaceRole(Base):
    __tablename__ = "user_workspace_roles"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id", name="uq_user_workspace_role"),)

    id = Column(String(36), primary_key=True, default=new_id)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="memberships")
    role = relationship("Role")
    workspace = relationship("Workspace")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(180), nullable=False)
    key_prefix = Column(String(20), nullable=False, index=True)
    key_hash = Column(String(64), nullable=False, unique=True)
    permissions = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(120), nullable=False, index=True)
    target_type = Column(String(80), nullable=False, default="")
    target_id = Column(String(80), nullable=False, default="")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class Niche(Base):
    __tablename__ = "niches"

    id = Column(String(36), primary_key=True, default=new_id)
    slug = Column(String(160), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    source_path = Column(Text, nullable=False)
    source_type = Column(String(20), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    needs_review = Column(Boolean, default=True, nullable=False)
    imported_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ReelJob(Base):
    __tablename__ = "reel_jobs"

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    niche_id = Column(String(36), ForeignKey("niches.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    platform = Column(String(80), nullable=False, default="multi-platform")
    language = Column(String(80), nullable=False, default="English")
    status = Column(String(40), nullable=False, default="draft")
    current_step = Column(String(80), nullable=False, default="topic")
    payload = Column(JSON, nullable=False, default=dict)
    artifacts = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    niche = relationship("Niche")


class ReelJobStep(Base):
    __tablename__ = "reel_job_steps"

    id = Column(String(36), primary_key=True, default=new_id)
    job_id = Column(String(36), ForeignKey("reel_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_key = Column(String(80), nullable=False)
    status = Column(String(40), nullable=False, default="pending")
    input = Column(JSON, nullable=False, default=dict)
    output = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ReelApproval(Base):
    __tablename__ = "reel_approvals"

    id = Column(String(36), primary_key=True, default=new_id)
    job_id = Column(String(36), ForeignKey("reel_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_key = Column(String(80), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision = Column(String(40), nullable=False)
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)


class ReelAsset(Base):
    __tablename__ = "reel_assets"

    id = Column(String(36), primary_key=True, default=new_id)
    job_id = Column(String(36), ForeignKey("reel_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(50), nullable=False)
    label = Column(String(180), nullable=False, default="")
    status = Column(String(40), nullable=False, default="draft")
    uri = Column(Text, nullable=False, default="")
    asset_metadata = Column("metadata", JSON, nullable=False, default=dict)
    selected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("workspace_id", "key", name="uq_setting_workspace_key"),)

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(120), nullable=False)
    value = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
