# apps/crm/models.py
from django.db import models
from core.models import BaseWorkspaceModel
from apps.accounts.models import User


class Contact(BaseWorkspaceModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    avatar_url = models.URLField(null=True)
    source = models.CharField(
        max_length=30,
        choices=[
            ("facebook_comment", "Facebook Comment"),
            ("facebook_message", "Facebook Message"),
            ("instagram_comment", "Instagram Comment"),
            ("instagram_dm", "Instagram DM"),
            ("whatsapp", "WhatsApp"),
            ("lead_form", "Lead Form"),
            ("manual", "Manual"),
        ],
    )
    platform_user_id = models.CharField(max_length=100, null=True)
    last_interaction_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "contacts"


class Lead(BaseWorkspaceModel):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="leads")
    source = models.CharField(
        max_length=20,
        choices=[
            ("comment", "Comment"),
            ("message", "Message"),
            ("campaign", "Campaign"),
            ("manual", "Manual"),
            ("form", "Form"),
        ],
    )
    stage = models.CharField(
        max_length=30,
        choices=[
            ("new_lead", "New Lead"),
            ("interested", "Interested"),
            ("asked_price", "Asked Price"),
            ("follow_up_needed", "Follow-up Needed"),
            ("offer_sent", "Offer Sent"),
            ("won", "Won"),
            ("lost", "Lost"),
        ],
        default="new_lead",
    )
    score = models.IntegerField(default=0)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="assigned_leads"
    )
    value_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    notes = models.TextField(null=True, blank=True)
    last_follow_up_at = models.DateTimeField(null=True)
    next_follow_up_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "leads"
        indexes = [
            models.Index(fields=["workspace", "stage"]),
            models.Index(fields=["workspace", "score"]),
            models.Index(fields=["workspace", "assigned_to"]),
        ]


class Tag(BaseWorkspaceModel):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7)  # Hex color

    class Meta:
        db_table = "tags"
        unique_together = ["workspace", "name"]


class LeadTag(models.Model):
    id = models.UUIDField(primary_key=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = "lead_tags"
        unique_together = ["lead", "tag"]


class LeadNote(BaseWorkspaceModel):
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="notes_history"
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.TextField()

    class Meta:
        db_table = "lead_notes"


class LeadScoreEvent(BaseWorkspaceModel):
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="score_events"
    )
    event_type = models.CharField(max_length=50)
    score_change = models.IntegerField()
    reason = models.TextField()

    class Meta:
        db_table = "lead_score_events"


class LifecycleEvent(BaseWorkspaceModel):
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="lifecycle_events"
    )
    from_stage = models.CharField(max_length=30, null=True)
    to_stage = models.CharField(max_length=30)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "lifecycle_events"
