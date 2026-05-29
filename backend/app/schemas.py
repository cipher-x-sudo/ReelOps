from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    name: str
    description: str
    permissions: list[str]
    is_system: bool


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    name: str
    is_active: bool
    created_at: datetime


class MembershipOut(BaseModel):
    workspace: WorkspaceOut
    role: RoleOut


class MeResponse(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = ""
    password: str = Field(min_length=8)
    workspace_id: str
    role_id: str


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)
    workspace_id: Optional[str] = None
    role_id: Optional[str] = None


class CreateRoleRequest(BaseModel):
    name: str
    description: str = ""
    permissions: list[str]


class CreateWorkspaceRequest(BaseModel):
    name: str
    slug: str


class NicheOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    title: str
    source_path: str
    source_type: str
    config: dict[str, Any]
    needs_review: bool


class UpdateNicheConfigRequest(BaseModel):
    config: dict[str, Any]
    needs_review: bool = False


class CreateJobRequest(BaseModel):
    niche_id: str
    title: str = ""
    platform: str = "multi-platform"
    language: str = "English"
    options: dict[str, Any] = Field(default_factory=dict)


class AdvanceJobRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    step_key: str
    decision: str = Field(pattern="^(approved|rejected|changes_requested)$")
    notes: str = ""


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    niche_id: Optional[str]
    title: str
    platform: str
    language: str
    status: str
    current_step: str
    payload: dict[str, Any]
    artifacts: dict[str, Any]
    error_message: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class ApiKeyCreateRequest(BaseModel):
    name: str
    permissions: list[str]


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    permissions: list[str]

