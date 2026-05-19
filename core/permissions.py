# core/permissions.py
from rest_framework import permissions
from apps.workspaces.models import WorkspaceUser


class HasWorkspacePermission(permissions.BasePermission):
    def __init__(self, permission_key):
        self.permission_key = permission_key

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Super admin can access everything
        if request.user.global_role == "super_admin":
            return True

        workspace_id = request.headers.get("X-Workspace-ID")
        if not workspace_id:
            return False

        try:
            workspace_user = WorkspaceUser.objects.get(
                workspace_id=workspace_id, user=request.user, status="active"
            )

            # Check if user has the required permission through their role
            return workspace_user.role.permissions.filter(
                key=self.permission_key
            ).exists()

        except WorkspaceUser.DoesNotExist:
            return False


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and request.user.global_role == "super_admin"
        )
# core/permissions.py
from rest_framework import permissions
from apps.workspaces.models import WorkspaceUser


class HasWorkspacePermission(permissions.BasePermission):
    def __init__(self, permission_key):
        self.permission_key = permission_key

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Super admin can access everything
        if request.user.global_role == "super_admin":
            return True

        workspace_id = request.headers.get("X-Workspace-ID")
        if not workspace_id:
            return False

        try:
            workspace_user = WorkspaceUser.objects.get(
                workspace_id=workspace_id, user=request.user, status="active"
            )

            # Check if user has the required permission through their role
            return workspace_user.role.permissions.filter(
                key=self.permission_key
            ).exists()

        except WorkspaceUser.DoesNotExist:
            return False


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and request.user.global_role == "super_admin"
        )
