# core/middleware.py
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from apps.workspaces.models import Workspace


class WorkspaceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip middleware for non-API paths
        if not request.path.startswith("/api/"):
            return None

        # Skip for auth endpoints and webhooks
        skip_paths = ["/api/auth/", "/api/webhooks/"]
        if any(request.path.startswith(path) for path in skip_paths):
            return None

        workspace_id = request.headers.get("X-Workspace-ID")

        if not workspace_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "X-Workspace-ID header is required",
                    "errorCode": "WORKSPACE_REQUIRED",
                },
                status=400,
            )

        try:
            workspace = Workspace.objects.get(id=workspace_id)
            request.workspace = workspace
        except Workspace.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Workspace not found",
                    "errorCode": "NOT_FOUND",
                },
                status=404,
            )

        # Verify user has access to workspace
        if request.user.is_authenticated:
            if not request.user.is_super_admin:
                has_access = request.user.workspace_users.filter(
                    workspace_id=workspace_id, status="active"
                ).exists()

                if not has_access:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Access denied to this workspace",
                            "errorCode": "FORBIDDEN",
                        },
                        status=403,
                    )


class ActivityLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Log API activity (implemented via signal)
        return response
