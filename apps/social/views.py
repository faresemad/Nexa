# apps/social/views.py (partial)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema
from core.response import APIResponse
from services.facebook import FacebookService
from .models import SocialPage
from tasks.facebook_sync import sync_page_posts_task, sync_all_page_data


class FacebookLoginView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Generate Facebook OAuth URL"""
        base_url = "https://www.facebook.com/v18.0/dialog/oauth"
        params = {
            "client_id": settings.FACEBOOK_APP_ID,
            "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
            "scope": "pages_read_engagement,pages_manage_posts,pages_manage_metadata,pages_messaging",
            "response_type": "code",
            "state": str(request.user.id),  # To verify on callback
        }

        oauth_url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

        return APIResponse.success(data={"url": oauth_url})


class FacebookCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handle Facebook OAuth callback"""
        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code:
            return APIResponse.error("Authorization code missing", "VALIDATION_ERROR")

        # Exchange code for access token
        url = f"{FacebookService.BASE_URL}/oauth/access_token"
        params = {
            "client_id": settings.FACEBOOK_APP_ID,
            "client_secret": settings.FACEBOOK_APP_SECRET,
            "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
            "code": code,
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            return APIResponse.error("Failed to get access token", "FACEBOOK_API_ERROR")

        data = response.json()
        short_lived_token = data.get("access_token")

        # Get long-lived token
        long_lived_token, expires_in = FacebookService.get_long_lived_token(
            short_lived_token
        )

        # Store token temporarily (in cache) for page selection
        cache_key = f"fb_token_{request.user.id}"
        cache.set(cache_key, long_lived_token, timeout=3600)

        return APIResponse.success(
            data={"message": "تم ربط حساب فيسبوك بنجاح", "expires_in": expires_in}
        )


class FacebookPagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of Facebook pages managed by user"""
        cache_key = f"fb_token_{request.user.id}"
        user_token = cache.get(cache_key)

        if not user_token:
            return APIResponse.error(
                "Facebook token expired, please reconnect", "FACEBOOK_TOKEN_EXPIRED"
            )

        pages = FacebookService.get_user_pages(user_token)

        # Check which pages are already connected
        connected_page_ids = SocialPage.objects.filter(
            workspace=request.workspace, status="connected"
        ).values_list("facebook_page_id", flat=True)

        for page in pages:
            page["already_connected"] = page["id"] in connected_page_ids

        return APIResponse.success(data=pages)


class ConnectPageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Connect a Facebook page to workspace"""
        page_id = request.data.get("page_id")
        page_name = request.data.get("page_name")
        page_access_token = request.data.get("access_token")

        if not all([page_id, page_access_token]):
            return APIResponse.error(
                "Page ID and access token required", "VALIDATION_ERROR"
            )

        # Check plan limit
        PlanLimitGuard.check_limit(request.workspace, "pages")

        # Check if already connected
        if SocialPage.objects.filter(
            facebook_page_id=page_id, workspace=request.workspace
        ).exists():
            return APIResponse.error("Page already connected", "VALIDATION_ERROR")

        # Encrypt and save page
        encrypted_token = FacebookService.encrypt_token(page_access_token)

        social_page = SocialPage.objects.create(
            workspace=request.workspace,
            platform="facebook",
            facebook_page_id=page_id,
            facebook_page_name=page_name,
            page_access_token_encrypted=encrypted_token,
            status="connected",
        )

        # Trigger initial sync
        sync_all_page_data.delay(str(social_page.id))

        return APIResponse.success(
            data={"page_id": str(social_page.id), "message": "تم ربط الصفحة بنجاح"}
        )


class DisconnectPageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, page_id):
        """Disconnect a Facebook page"""
        try:
            page = SocialPage.objects.get(id=page_id, workspace=request.workspace)
            page.status = "disconnected"
            page.soft_delete()

            return APIResponse.success(message="تم فصل الصفحة بنجاح")
        except SocialPage.DoesNotExist:
            return APIResponse.error("Page not found", "NOT_FOUND")
