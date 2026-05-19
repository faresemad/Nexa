# tasks/metrics_tasks.py
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Q
from apps.social.models import Comment
from apps.crm.models import Lead
from apps.dashboard.models import DashboardMetrics


@shared_task(queue="metrics")
def update_dashboard_metrics():
    """Update dashboard metrics for all workspaces"""
    today = timezone.now().date()

    # Process metrics per workspace
    from apps.workspaces.models import Workspace

    workspaces = Workspace.objects.filter(status="active")

    for workspace in workspaces:
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)

        metrics, _ = DashboardMetrics.objects.get_or_create(
            workspace=workspace, metric_date=today
        )

        # Calculate metrics
        metrics.unreplied_comments_count = Comment.objects.filter(
            workspace=workspace,
            is_replied=False,
            status="new",
            created_time__gte=seven_days_ago,
        ).count()

        metrics.price_questions_count = Comment.objects.filter(
            workspace=workspace, ai_intent="price", is_replied=False
        ).count()

        metrics.hot_leads_count = Lead.objects.filter(
            workspace=workspace,
            score__gte=70,
            stage__in=["new_lead", "interested", "asked_price"],
        ).count()

        metrics.comments_replied_count = Comment.objects.filter(
            workspace=workspace, is_replied=True, reply_sent_at__date=today
        ).count()

        metrics.leads_generated_count = Lead.objects.filter(
            workspace=workspace, created_at__date=today
        ).count()

        metrics.save()

    return {"workspaces_processed": workspaces.count()}


@shared_task(queue="logs")
def cleanup_old_logs():
    """Clean up logs older than 90 days"""
    cutoff = timezone.now() - timezone.timedelta(days=90)

    from apps.activity_logs.models import ActivityLog
    from apps.activity_logs.models import APILog
    from apps.activity_logs.models import ErrorLog

    ActivityLog.objects.filter(created_at__lt=cutoff).delete()
    APILog.objects.filter(created_at__lt=cutoff).delete()
    ErrorLog.objects.filter(created_at__lt=cutoff).delete()

    return {"success": True}
