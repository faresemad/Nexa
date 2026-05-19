# apps/social/comment_views.py
from rest_framework.views import APIView
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from core.response import APIResponse
from core.permissions import HasWorkspacePermission
from services.facebook import FacebookService
from services.ai_analyzer import AIAnalyzer
from services.lead_converter import LeadConverter
from services.plan_guard import PlanLimitGuard
from .models import Comment, SocialPage
from .serializers import CommentSerializer


class CommentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List comments with advanced filtering"""
        queryset = Comment.objects.filter(
            workspace=request.workspace, deleted_at__isnull=True
        )

        # Apply filters
        status_filter = request.GET.get("status")
        intent_filter = request.GET.get("intent")
        sentiment_filter = request.GET.get("sentiment")
        lead_score_min = request.GET.get("lead_score_min")
        lead_score_max = request.GET.get("lead_score_max")
        has_phone = request.GET.get("has_phone")
        assigned_to = request.GET.get("assigned_to")
        post_id = request.GET.get("post_id")
        page_id = request.GET.get("social_page_id")
        search = request.GET.get("search")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if intent_filter:
            queryset = queryset.filter(ai_intent=intent_filter)
        if sentiment_filter:
            queryset = queryset.filter(ai_sentiment=sentiment_filter)
        if lead_score_min:
            queryset = queryset.filter(ai_lead_score__gte=int(lead_score_min))
        if lead_score_max:
            queryset = queryset.filter(ai_lead_score__lte=int(lead_score_max))
        if has_phone == "true":
            queryset = queryset.filter(ai_extracted_phone__isnull=False)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        if page_id:
            queryset = queryset.filter(post__social_page_id=page_id)
        if search:
            queryset = queryset.filter(message__icontains=search)
        if date_from:
            queryset = queryset.filter(created_time__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_time__lte=date_to)

        queryset = queryset.select_related("post", "assigned_to", "reply_by").order_by(
            "-created_time"
        )

        return APIResponse.paginated(queryset, request, CommentSerializer)


class CommentDetailView(APIView):
    def get(self, request, comment_id):
        """Get comment details with AI analysis and lead info"""
        try:
            comment = Comment.objects.select_related(
                "post", "assigned_to", "lead", "reply_by"
            ).get(id=comment_id, workspace=request.workspace)

            return APIResponse.success(data=CommentSerializer(comment).data)
        except Comment.DoesNotExist:
            return APIResponse.error("Comment not found", "NOT_FOUND")


class CommentAIReplyView(APIView):
    def post(self, request, comment_id):
        """Generate AI reply for comment"""
        try:
            comment = Comment.objects.get(id=comment_id, workspace=request.workspace)
        except Comment.DoesNotExist:
            return APIResponse.error("Comment not found", "NOT_FOUND")

        # Check plan limits
        PlanLimitGuard.check_limit(request.workspace, "ai_replies")

        # Generate AI reply
        tone = request.data.get("tone", "professional")
        result = AIAnalyzer.generate_reply(
            comment.message,
            comment.ai_intent or "general",
            comment.ai_sentiment or "neutral",
            tone,
        )

        return APIResponse.success(
            data={"reply": result["reply"], "tokens_used": result["tokens_used"]}
        )


class CommentReplyView(APIView):
    def post(self, request, comment_id):
        """Reply to comment (manual or AI-generated)"""
        try:
            comment = Comment.objects.select_related("post__social_page").get(
                id=comment_id, workspace=request.workspace
            )
        except Comment.DoesNotExist:
            return APIResponse.error("Comment not found", "NOT_FOUND")

        message = request.data.get("message")
        is_ai_reply = request.data.get("is_ai_reply", False)

        if not message:
            return APIResponse.error("Reply message required", "VALIDATION_ERROR")

        # Send reply to Facebook
        try:
            page = comment.post.social_page
            token = FacebookService.decrypt_token(page.page_access_token_encrypted)

            result = FacebookService.reply_to_comment(
                comment.facebook_comment_id, token, message
            )

            # Update comment
            comment.is_replied = True
            comment.reply_text = message
            comment.reply_facebook_id = result.get("id")
            comment.reply_sent_at = timezone.now()
            comment.reply_by = request.user
            comment.reply_is_ai_generated = is_ai_reply
            comment.status = "replied"
            comment.save()

            # Log activity
            ActivityLog.objects.create(
                workspace=request.workspace,
                user=request.user,
                action="reply_comment",
                entity_type="comment",
                entity_id=comment.id,
                description=f"Replied to comment {comment.facebook_comment_id}",
            )

            return APIResponse.success(
                data={"reply_id": result.get("id"), "message": "تم إرسال الرد بنجاح"}
            )

        except FacebookAPIError as e:
            return APIResponse.error(str(e), "FACEBOOK_API_ERROR")


class CommentConvertToLeadView(APIView):
    def post(self, request, comment_id):
        """Manually convert comment to lead"""
        try:
            comment = Comment.objects.get(id=comment_id, workspace=request.workspace)
        except Comment.DoesNotExist:
            return APIResponse.error("Comment not found", "NOT_FOUND")

        if comment.is_converted_to_lead:
            return APIResponse.error(
                "Comment already converted to lead", "VALIDATION_ERROR"
            )

        lead = LeadConverter.convert_comment_to_lead(comment, request.user)

        return APIResponse.success(
            data={"lead_id": str(lead.id), "message": "تم تحويل التعليق إلى عميل محتمل"}
        )


class CommentBulkActionView(APIView):
    def post(self, request):
        """Bulk action on comments"""
        action = request.data.get("action")
        comment_ids = request.data.get("comment_ids", [])

        if not comment_ids:
            return APIResponse.error("Comment IDs required", "VALIDATION_ERROR")

        comments = Comment.objects.filter(
            id__in=comment_ids, workspace=request.workspace
        )

        if action == "bulk_reply":
            message = request.data.get("message")
            # Queue bulk reply task
            from tasks.ai_tasks import bulk_reply_comments

            bulk_reply_comments.delay(
                [str(c.id) for c in comments], message, str(request.user.id)
            )

        elif action == "bulk_convert":
            for comment in comments:
                if not comment.is_converted_to_lead and comment.ai_lead_score >= 70:
                    LeadConverter.convert_comment_to_lead(comment, request.user)

        elif action == "assign":
            assigned_to_id = request.data.get("assigned_to_id")
            comments.update(assigned_to_id=assigned_to_id)

        return APIResponse.success(
            message=f"تم تنفيذ الإجراء على {comments.count()} تعليق"
        )
