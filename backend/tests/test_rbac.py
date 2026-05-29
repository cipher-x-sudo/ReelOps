from app.rbac import DEFAULT_ROLES, PERMISSIONS, has_permission
from app.rbac import Principal


def test_default_roles_cover_core_permissions():
    owner = set(DEFAULT_ROLES["Owner"]["permissions"])
    admin = set(DEFAULT_ROLES["Admin"]["permissions"])
    assert "*" in owner
    assert set(PERMISSIONS).issubset(admin)
    assert "jobs.create" in DEFAULT_ROLES["Producer"]["permissions"]
    assert "jobs.approve" in DEFAULT_ROLES["Reviewer"]["permissions"]
    assert "jobs.view" in DEFAULT_ROLES["Viewer"]["permissions"]


def test_permission_wildcard_allows_everything():
    principal = Principal(user=None, api_key=None, workspace_id="workspace", permissions={"*"})
    assert has_permission(principal, "users.manage")
    assert has_permission(principal, "jobs.render")

