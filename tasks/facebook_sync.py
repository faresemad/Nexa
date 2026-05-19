# tasks/facebook_sync.py
from celery import shared_task
from django.utils import timezone
from services.facebook import FacebookService
from apps.social.models import SocialPage, Post, Comment
from tasks.ai_tasks import analyze_comment_task


@shared_task(queue="facebook")
def sync_all_page_data(page_id):
    """Sync all data for a page"""
    try:
        page = SocialPage.objects.get(id=page_id)
        page.sync_status = "syncing"
        page.save()

        # Sync posts
        sync_page_posts_task.delay(str(page.id))

        page.last_synced_posts_at = timezone.now()
        page.sync_status = "idle"
        page.save()

    except SocialPage.DoesNotExist:
        pass
    except Exception as e:
        page.sync_status = "error"
        page.sync_error_message = str(e)
        page.save()


@shared_task(queue="facebook")
def sync_page_posts_task(page_id):
    """Sync posts for a specific page"""
    try:
        page = SocialPage.objects.get(id=page_id)
        token = FacebookService.decrypt_token(page.page_access_token_encrypted)

        posts_data = FacebookService.sync_page_posts(page.facebook_page_id, token)

        for post_data in posts_data.get("data", []):
            post, created = Post.objects.update_or_create(
                workspace=page.workspace,
                facebook_post_id=post_data["id"],
                defaults={
                    "social_page": page,
                    "content": post_data.get("message", ""),
                    "facebook_permalink": post_data.get("permalink_url"),
                    "published_at": post_data["created_time"],
                    "facebook_likes_count": post_data.get("likes", {})
                    .get("summary", {})
                    .get("total_count", 0),
                    "facebook_comments_count": post_data.get("comments", {})
                    .get("summary", {})
                    .get("total_count", 0),
                    "last_synced_at": timezone.now(),
                },
            )

            # Queue comment sync for this post
            if post.facebook_comments_count > 0:
                sync_post_comments_task.delay(str(post.id))

        return {"success": True, "posts_synced": len(posts_data.get("data", []))}

    except Exception as e:
        return {"success": False, "error": str(e)}


@shared_task(queue="comments")
def sync_post_comments_task(post_id):
    """Sync comments for a specific post"""
    try:
        post = Post.objects.select_related("social_page").get(id=post_id)
        token = FacebookService.decrypt_token(
            post.social_page.page_access_token_encrypted
        )

        comments_data = FacebookService.sync_post_comments(post.facebook_post_id, token)

        for comment_data in comments_data.get("data", []):
            from_user = comment_data.get("from", {})

            comment, created = Comment.objects.update_or_create(
                workspace=post.workspace,
                facebook_comment_id=comment_data["id"],
                defaults={
                    "post": post,
                    "facebook_user_id": from_user.get("id", ""),
                    "facebook_user_name": from_user.get("name", ""),
                    "facebook_user_picture": from_user.get("picture", {})
                    .get("data", {})
                    .get("url"),
                    "message": comment_data.get("message", ""),
                    "created_time": comment_data["created_time"],
                },
            )

            # Queue AI analysis for new comments
            if created:
                analyze_comment_task.delay(str(comment.id))

            # Process nested replies
            if "comments" in comment_data:
                for reply_data in comment_data["comments"].get("data", []):
                    # Handle nested replies similarly
                    pass

        # Update post sync time
        post.last_synced_at = timezone.now()
        post.save()

        return {"success": True, "comments_synced": len(comments_data.get("data", []))}

    except Exception as e:
        return {"success": False, "error": str(e)}


@shared_task(queue="facebook")
def periodic_sync_scheduler():
    """Celery Beat task to sync all connected pages periodically"""
    pages = SocialPage.objects.filter(
        status="connected",
        last_synced_posts_at__lt=timezone.now() - timezone.timedelta(minutes=30),
    )

    for page in pages:
        sync_all_page_data.delay(str(page.id))

    return {"pages_queued": pages.count()}


@shared_task(queue="facebook")
def refresh_page_tokens():
    """Refresh Facebook page tokens that are about to expire"""
    pages = SocialPage.objects.filter(
        status="connected",
        token_expires_at__lt=timezone.now() + timezone.timedelta(days=7),
    )

    for page in pages:
        try:
            # Refresh token logic
            token = FacebookService.decrypt_token(page.page_access_token_encrypted)
            new_token, expires_in = FacebookService.get_long_lived_token(token)

            page.page_access_token_encrypted = FacebookService.encrypt_token(new_token)
            page.token_expires_at = timezone.now() + timezone.timedelta(
                seconds=expires_in
            )
            page.save()

        except Exception as e:
            page.token_status = "refresh_failed"
            page.save()

    return {"tokens_refreshed": pages.count()}
