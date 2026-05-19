# services/lead_converter.py
from django.utils import timezone
from apps.crm.models import Contact, Lead, LeadScoreEvent, LifecycleEvent, Tag, LeadTag
from apps.activity_logs.models import ActivityLog


class LeadConverter:
    @staticmethod
    def convert_comment_to_lead(comment, user=None):
        """Convert a high-intent comment to a CRM lead"""
        from apps.social.models import Comment

        if comment.is_converted_to_lead:
            return None

        workspace = comment.workspace

        # Find or create contact
        contact, created = Contact.objects.get_or_create(
            workspace=workspace,
            platform_user_id=comment.facebook_user_id,
            defaults={
                "name": comment.facebook_user_name,
                "avatar_url": comment.facebook_user_picture,
                "source": "facebook_comment",
                "last_interaction_at": timezone.now(),
            },
        )

        if not created:
            contact.last_interaction_at = timezone.now()
            contact.save()

        # Create lead
        lead = Lead.objects.create(
            workspace=workspace,
            contact=contact,
            source="comment",
            stage="new_lead",
            score=comment.ai_lead_score or 0,
            assigned_to=comment.assigned_to,
        )

        # Link comment to lead
        comment.is_converted_to_lead = True
        comment.lead = lead
        comment.status = "lead"
        comment.save()

        # Add auto-tags based on intent
        intent_tags = {
            "price": "Price Inquiry",
            "booking": "Booking Request",
            "complaint": "Complaint",
            "phone": "Phone Lead",
        }

        tag_name = intent_tags.get(comment.ai_intent, "Hot Lead")
        tag, _ = Tag.objects.get_or_create(
            workspace=workspace, name=tag_name, defaults={"color": "#FF5733"}
        )
        LeadTag.objects.get_or_create(lead=lead, tag=tag)

        # Create score event
        LeadScoreEvent.objects.create(
            workspace=workspace,
            lead=lead,
            event_type="ai_auto_conversion",
            score_change=lead.score,
            reason=f"AI detected high intent: {comment.ai_intent}",
        )

        # Create lifecycle event
        LifecycleEvent.objects.create(
            workspace=workspace, lead=lead, to_stage="new_lead", changed_by=user
        )

        # Update post counter
        comment.post.leads_generated_count += 1
        comment.post.save()

        # Log activity
        ActivityLog.objects.create(
            workspace=workspace,
            user=user,
            action="convert_comment_to_lead",
            entity_type="lead",
            entity_id=lead.id,
            description=f"Converted comment {comment.facebook_comment_id} to lead",
        )

        return lead
