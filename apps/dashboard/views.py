# apps/dashboard/views.py
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Q, Avg
from core.response import APIResponse
from apps.social.models import Comment, Post
from apps.crm.models import Lead
from apps.campaigns.models import Campaign
from datetime import timedelta


class OpportunitiesView(APIView):
    def get(self, request):
        """Get today's opportunities dashboard"""
        workspace = request.workspace
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        # Unreplied comments
        unreplied_comments = Comment.objects.filter(
            workspace=workspace,
            is_replied=False,
            status="new",
            created_time__gte=seven_days_ago,
        )
        unreplied_count = unreplied_comments.count()
        unreplied_top = unreplied_comments.order_by("-created_time")[:5]

        # Price questions
        price_questions = Comment.objects.filter(
            workspace=workspace, ai_intent="price", is_replied=False
        )
        price_questions_count = price_questions.count()
        price_questions_top = price_questions.order_by("-ai_lead_score")[:5]

        # Hot leads
        hot_leads = Lead.objects.filter(
            workspace=workspace,
            score__gte=70,
            stage__in=["new_lead", "interested", "asked_price"],
        )
        hot_leads_count = hot_leads.count()
        hot_leads_top = hot_leads.order_by("-score")[:5]

        # Stalled conversations
        stalled = Lead.objects.filter(
            workspace=workspace,
            next_follow_up_at__lt=now,
            stage__in=["follow_up_needed", "offer_sent"],
        )
        stalled_count = stalled.count()
        stalled_top = stalled.order_by("next_follow_up_at")[:5]

        # Old unreplied comments (recovery)
        old_comments = Comment.objects.filter(
            workspace=workspace, is_replied=False, created_time__lt=seven_days_ago
        )
        old_comments_count = old_comments.count()
        old_comments_top = old_comments.order_by("-ai_lead_score")[:5]

        # Today's metrics
        today_start = now.replace(hour=0, minute=0, second=0)
        comments_today = Comment.objects.filter(
            workspace=workspace, created_time__gte=today_start
        ).count()

        leads_today = Lead.objects.filter(
            workspace=workspace, created_at__gte=today_start
        ).count()

        campaigns_running = Campaign.objects.filter(
            workspace=workspace, status="running"
        ).count()

        data = {
            "unreplied_comments": {
                "count": unreplied_count,
                "label": "تعليقات بدون رد",
                "items": self._serialize_comments(unreplied_top),
                "action": {
                    "text": "عرض الكل",
                    "link": "/comments?status=new&is_replied=false",
                },
            },
            "price_questions": {
                "count": price_questions_count,
                "label": "استفسارات الأسعار",
                "items": self._serialize_comments(price_questions_top),
                "action": {"text": "عرض الكل", "link": "/comments?intent=price"},
            },
            "hot_leads": {
                "count": hot_leads_count,
                "label": "عملاء محتملين",
                "items": self._serialize_leads(hot_leads_top),
                "action": {"text": "عرض الكل", "link": "/leads/hot"},
            },
            "stalled_conversations": {
                "count": stalled_count,
                "label": "محادثات متوقفة",
                "items": self._serialize_leads(stalled_top),
                "action": {"text": "متابعة", "link": "/leads?stage=follow_up_needed"},
            },
            "old_comments": {
                "count": old_comments_count,
                "label": "تعليقات قديمة",
                "items": self._serialize_comments(old_comments_top),
                "action": {"text": "استرداد", "link": "/comments?days_old=7"},
            },
            "summary": {
                "comments_today": comments_today,
                "leads_today": leads_today,
                "campaigns_running": campaigns_running,
                "avg_response_time": self._calculate_avg_response_time(workspace),
            },
        }

        return APIResponse.success(data=data)

    def _serialize_comments(self, comments):
        return [
            {
                "id": str(c.id),
                "message": c.message[:100],
                "user_name": c.facebook_user_name,
                "intent": c.ai_intent,
                "score": c.ai_lead_score,
                "created_time": c.created_time,
            }
            for c in comments
        ]

    def _serialize_leads(self, leads):
        return [
            {
                "id": str(l.id),
                "name": l.contact.name,
                "stage": l.stage,
                "score": l.score,
                "next_follow_up": l.next_follow_up_at,
            }
            for l in leads
        ]

    def _calculate_avg_response_time(self, workspace):
        # Calculate average time between comment creation and reply
        avg_time = Comment.objects.filter(
            workspace=workspace, is_replied=True, reply_sent_at__isnull=False
        ).aggregate(avg_hours=Avg(Expr(F("reply_sent_at") - F("created_time"))))
        return avg_time.get("avg_hours", 0)
