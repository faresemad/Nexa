# tasks/ai_tasks.py
from celery import shared_task
from services.ai_analyzer import AIAnalyzer
from services.lead_converter import LeadConverter
from apps.social.models import Comment
from apps.ai_services.models import AIRequest


@shared_task(queue="ai")
def analyze_comment_task(comment_id):
    """Analyze comment with AI and auto-convert to lead if high score"""
    try:
        comment = Comment.objects.get(id=comment_id)

        # Analyze with AI
        result = AIAnalyzer.analyze_comment(comment.message)

        # Update comment with AI analysis
        comment.ai_intent = result.get("intent")
        comment.ai_intent_confidence = result.get("intent_confidence")
        comment.ai_sentiment = result.get("sentiment")
        comment.ai_sentiment_confidence = result.get("sentiment_confidence")
        comment.ai_lead_score = result.get("lead_score", 0)
        comment.ai_extracted_phone = result.get("phone")
        comment.ai_extracted_email = result.get("email")
        comment.ai_extracted_location = result.get("location")
        comment.ai_keywords = result.get("keywords", [])
        comment.ai_language = result.get("language", "ar")
        comment.ai_model_version = result.get("model_version")
        comment.ai_processed_at = timezone.now()
        comment.status = "ai_processed"
        comment.save()

        # Log AI request
        AIRequest.objects.create(
            workspace=comment.workspace,
            type="classify_comment",
            input_text=comment.message[:500],
            output_text=str(result),
            tokens_used=result.get("tokens_used", 0),
            status="success",
        )

        # Auto-convert to lead if high score
        if comment.ai_lead_score >= 70 and not comment.is_converted_to_lead:
            LeadConverter.convert_comment_to_lead(comment)

        return {"success": True, "comment_id": str(comment.id)}

    except Comment.DoesNotExist:
        return {"success": False, "error": "Comment not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@shared_task(queue="ai")
def generate_comment_reply_task(comment_id, user_id, tone="professional"):
    """Generate AI reply for a comment"""
    try:
        comment = Comment.objects.get(id=comment_id)

        result = AIAnalyzer.generate_reply(
            comment.message,
            comment.ai_intent or "general",
            comment.ai_sentiment or "neutral",
            tone,
        )

        # Log AI request
        AIRequest.objects.create(
            workspace=comment.workspace,
            user_id=user_id,
            type="comment_reply",
            input_text=comment.message[:500],
            output_text=result["reply"],
            tokens_used=result["tokens_used"],
            status="success",
        )

        return {"success": True, "reply": result["reply"]}

    except Exception as e:
        return {"success": False, "error": str(e)}


@shared_task(queue="comments")
def bulk_reply_comments(comment_ids, message, user_id):
    """Bulk reply to comments"""
    for comment_id in comment_ids:
        try:
            comment = Comment.objects.select_related("post__social_page").get(
                id=comment_id
            )

            # Send reply to Facebook
            token = FacebookService.decrypt_token(
                comment.post.social_page.page_access_token_encrypted
            )

            result = FacebookService.reply_to_comment(
                comment.facebook_comment_id, token, message
            )

            # Update comment
            comment.is_replied = True
            comment.reply_text = message
            comment.reply_facebook_id = result.get("id")
            comment.reply_sent_at = timezone.now()
            comment.reply_by_id = user_id
            comment.status = "replied"
            comment.save()

        except Exception as e:
            continue

    return {"success": True, "processed": len(comment_ids)}
