# apps/social/models.py
from django.db import models
from core.models import BaseWorkspaceModel
from apps.accounts.models import User


class SocialPage(BaseWorkspaceModel):
    platform = models.CharField(
        max_length=20,
        choices=[
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("whatsapp", "WhatsApp"),
        ],
        default="facebook",
    )
    facebook_page_id = models.CharField(max_length=100, unique=True)
    facebook_page_name = models.CharField(max_length=255)
    facebook_page_username = models.CharField(max_length=255, null=True, blank=True)
    page_picture_url = models.URLField(null=True)
    page_access_token_encrypted = models.TextField()
    token_expires_at = models.DateTimeField(null=True)
    token_status = models.CharField(
        max_length=20,
        choices=[
            ("valid", "Valid"),
            ("expired", "Expired"),
            ("refresh_failed", "Refresh Failed"),
        ],
        default="valid",
    )
    followers_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    category = models.CharField(max_length=100, null=True)
    last_synced_posts_at = models.DateTimeField(null=True)
    last_synced_comments_at = models.DateTimeField(null=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[("idle", "Idle"), ("syncing", "Syncing"), ("error", "Error")],
        default="idle",
    )
    sync_error_message = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("connected", "Connected"),
            ("disconnected", "Disconnected"),
            ("expired", "Expired"),
            ("error", "Error"),
        ],
        default="connected",
    )

    class Meta:
        db_table = "social_pages"


class Post(BaseWorkspaceModel):
    social_page = models.ForeignKey(
        SocialPage, on_delete=models.CASCADE, related_name="posts"
    )
    facebook_post_id = models.CharField(max_length=100, unique=True)
    content = models.TextField(null=True, blank=True)
    facebook_permalink = models.URLField(null=True)
    media_type = models.CharField(
        max_length=20,
        choices=[
            ("text", "Text"),
            ("photo", "Photo"),
            ("video", "Video"),
            ("link", "Link"),
            ("carousel", "Carousel"),
        ],
    )
    media_urls = models.JSONField(default=list)
    facebook_likes_count = models.IntegerField(default=0)
    facebook_comments_count = models.IntegerField(default=0)
    facebook_shares_count = models.IntegerField(default=0)
    facebook_reactions = models.JSONField(default=dict)
    unreplied_comments_count = models.IntegerField(default=0)
    leads_generated_count = models.IntegerField(default=0)
    engagers_count = models.IntegerField(default=0)
    ai_sentiment = models.CharField(max_length=20, null=True)
    ai_summary = models.TextField(null=True)
    published_at = models.DateTimeField()
    status = models.CharField(max_length=20, default="active")
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "posts"


class Comment(BaseWorkspaceModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    parent_comment = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    facebook_comment_id = models.CharField(max_length=100, unique=True)
    facebook_user_id = models.CharField(max_length=100)
    facebook_user_name = models.CharField(max_length=255)
    facebook_user_picture = models.URLField(null=True)
    message = models.TextField()
    created_time = models.DateTimeField()

    # AI Analysis Fields
    ai_intent = models.CharField(max_length=30, null=True)
    ai_intent_confidence = models.FloatField(null=True)
    ai_sentiment = models.CharField(max_length=20, null=True)
    ai_sentiment_confidence = models.FloatField(null=True)
    ai_lead_score = models.IntegerField(default=0)
    ai_extracted_phone = models.CharField(max_length=20, null=True)
    ai_extracted_email = models.EmailField(null=True)
    ai_extracted_location = models.CharField(max_length=255, null=True)
    ai_keywords = models.JSONField(default=list)
    ai_language = models.CharField(max_length=10, default="ar")
    ai_processed_at = models.DateTimeField(null=True)
    ai_model_version = models.CharField(max_length=50, null=True)

    # Reply Fields
    is_replied = models.BooleanField(default=False)
    reply_text = models.TextField(null=True)
    reply_facebook_id = models.CharField(max_length=100, null=True)
    reply_sent_at = models.DateTimeField(null=True)
    reply_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="comment_replies"
    )
    reply_is_ai_generated = models.BooleanField(default=False)

    # Lead Conversion
    is_converted_to_lead = models.BooleanField(default=False)
    lead = models.ForeignKey(
        "crm.Lead", on_delete=models.SET_NULL, null=True, related_name="source_comments"
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="assigned_comments"
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("new", "New"),
            ("replied", "Replied"),
            ("ignored", "Ignored"),
            ("lead", "Lead"),
            ("escalated", "Escalated"),
            ("spam", "Spam"),
            ("ai_processed", "AI Processed"),
            ("pending_reply", "Pending Reply"),
        ],
        default="new",
    )

    class Meta:
        db_table = "comments"
        indexes = [
            models.Index(fields=["workspace", "status", "ai_intent"]),
            models.Index(fields=["workspace", "ai_lead_score"]),
            models.Index(fields=["workspace", "is_replied"]),
            models.Index(fields=["post", "created_time"]),
        ]
