# services/plan_guard.py
from django.utils import timezone
from core.exceptions import PlanLimitExceeded


class PlanLimitGuard:
    @staticmethod
    def check_limit(workspace, feature_key, increment=1):
        """Check if workspace has reached plan limit for a feature"""
        from apps.workspaces.models import UsageLog, FeatureFlag

        # Check if feature is enabled
        feature_flag = FeatureFlag.objects.filter(
            workspace=workspace, feature_key=feature_key, is_enabled=True
        ).first()

        if not feature_flag and feature_key != "ai_analysis":
            raise PlanLimitExceeded("هذه الميزة غير مفعلة في باقتك")

        # Get subscription
        subscription = workspace.subscriptions.filter(
            status__in=["active", "trial"]
        ).first()

        if not subscription:
            raise PlanLimitExceeded("لا يوجد اشتراك نشط")

        plan = subscription.plan

        # Get current period
        now = timezone.now()
        period_start = now.replace(day=1, hour=0, minute=0, second=0)

        # Get current usage
        current_usage = UsageLog.objects.filter(
            workspace=workspace, feature_key=feature_key, period_start__gte=period_start
        ).count()

        # Check limits based on feature
        limits = {
            "ai_replies": plan.max_ai_replies_per_month,
            "ai_analysis": plan.max_comments_sync_per_month,
            "campaigns": plan.max_campaigns_per_month,
            "pages": plan.max_pages,
            "users": plan.max_users,
            "leads": plan.max_leads,
        }

        limit = limits.get(feature_key)
        if limit and current_usage >= limit:
            raise PlanLimitExceeded(f"تم تجاوز الحد المسموح به ({limit}) في باقتك")

        # Log usage
        UsageLog.objects.create(
            workspace=workspace,
            feature_key=feature_key,
            usage_type=feature_key,
            usage_count=increment,
            period_start=period_start,
            period_end=period_start + timezone.timedelta(days=30),
        )

        return True
