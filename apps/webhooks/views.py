# apps/webhooks/views.py
import hashlib
import hmac
import json
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from tasks.facebook_sync import sync_post_comments_task
from tasks.ai_tasks import analyze_comment_task
from apps.social.models import SocialPage, Comment, Post


class FacebookWebhookView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """Verify webhook with Facebook"""
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        verify_token = settings.FACEBOOK_APP_SECRET  # Use app secret as verify token

        if mode == "subscribe" and token == verify_token:
            return HttpResponse(challenge)
        else:
            return HttpResponse("Verification failed", status=403)

    def post(self, request):
        """Handle Facebook webhook events"""
        # Verify signature
        signature = request.headers.get("X-Hub-Signature-256")
        if not self._verify_signature(request.body, signature):
            return HttpResponse("Invalid signature", status=403)

        data = json.loads(request.body)

        # Process entries
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})

                if field == "feed":
                    self._handle_feed_event(value)

        return HttpResponse("OK")

    def _verify_signature(self, body, signature):
        """Verify Facebook webhook signature"""
        if not signature:
            return False

        expected_signature = hmac.new(
            settings.FACEBOOK_APP_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    def _handle_feed_event(self, value):
        """Handle feed events (new comments, posts)"""
        item = value.get("item")
        verb = value.get("verb")

        if verb == "add":
            if "comment" in item:
                self._handle_new_comment(value)
            elif "post" in item:
                self._handle_new_post(value)

    def _handle_new_comment(self, value):
        """Process new comment from webhook"""
        comment_id = value.get("comment_id")
        post_id = value.get("post_id")
        from_id = value.get("from", {}).get("id")
        message = value.get("message", "")

        # Find the post in our database
        try:
            post = Post.objects.get(
                facebook_post_id=post_id,
                social_page__facebook_page_id=value.get("page_id"),
            )

            # Create comment
            comment, created = Comment.objects.update_or_create(
                workspace=post.workspace,
                facebook_comment_id=comment_id,
                defaults={
                    "post": post,
                    "facebook_user_id": from_id,
                    "facebook_user_name": value.get("from", {}).get("name", ""),
                    "message": message,
                    "created_time": timezone.now(),
                },
            )

            if created:
                # Queue AI analysis
                analyze_comment_task.delay(str(comment.id))

        except Post.DoesNotExist:
            pass  # Post not synced yet

    def _handle_new_post(self, value):
        """Process new post from webhook"""
        # Similar to handle_new_comment but for posts
        pass
