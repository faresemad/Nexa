# apps/accounts/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from core.response import APIResponse
from .serializers import LoginSerializer, UserSerializer
from .models import User


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: None})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.last_login_at = timezone.now()
        user.save()

        refresh = RefreshToken.for_user(user)

        # Get user's workspaces
        workspaces = []
        for wu in user.workspace_users.filter(status="active").select_related(
            "workspace", "role"
        ):
            permissions = list(wu.role.permissions.values_list("key", flat=True))
            workspaces.append(
                {
                    "id": str(wu.workspace.id),
                    "name": wu.workspace.name,
                    "role": wu.role.name,
                    "permissions": permissions,
                }
            )

        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "workspaces": workspaces,
        }

        return APIResponse.success(data=data, message="تم تسجيل الدخول بنجاح")


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return APIResponse.error("Refresh token is required", "VALIDATION_ERROR")

        try:
            refresh = RefreshToken(refresh_token)
            return APIResponse.success(data={"access": str(refresh.access_token)})
        except Exception:
            return APIResponse.error(
                "Invalid or expired refresh token", "INVALID_TOKEN", status=401
            )


class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return APIResponse.success(message="تم تسجيل الخروج بنجاح")
        except Exception:
            return APIResponse.success(message="تم تسجيل الخروج بنجاح")


class MeView(APIView):
    def get(self, request):
        # Get current workspace permissions if workspace header present
        permissions = []
        workspace_id = request.headers.get("X-Workspace-ID")

        if workspace_id:
            workspace_user = request.user.workspace_users.filter(
                workspace_id=workspace_id, status="active"
            ).first()

            if workspace_user:
                permissions = list(
                    workspace_user.role.permissions.values_list("key", flat=True)
                )

        data = {"user": UserSerializer(request.user).data, "permissions": permissions}

        return APIResponse.success(data=data)
