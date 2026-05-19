# config/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Auth
    path("api/auth/", include("apps.accounts.urls")),
    # Facebook OAuth
    path("api/auth/facebook/", include("apps.social.facebook_urls")),
    # Workspace
    path("api/workspaces/", include("apps.workspaces.urls")),
    # Dashboard
    path("api/dashboard/", include("apps.dashboard.urls")),
    # Social Pages
    path("api/social/", include("apps.social.urls")),
    # CRM
    path("api/crm/", include("apps.crm.urls")),
    # Campaigns
    path("api/campaigns/", include("apps.campaigns.urls")),
    # AI
    path("api/ai/", include("apps.ai_services.urls")),
    # Reports
    path("api/reports/", include("apps.reports.urls")),
    # Activity Logs
    path("api/activity-logs/", include("apps.activity_logs.urls")),
    # Webhooks
    path("api/webhooks/", include("apps.webhooks.urls")),
    # Admin Panel
    path("api/admin/", include("apps.admin_panel.urls")),
]
