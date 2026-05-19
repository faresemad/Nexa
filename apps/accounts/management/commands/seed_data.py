# apps/accounts/management/commands/seed_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.workspaces.models import (
    Workspace,
    WorkspaceUser,
    Role,
    Permission,
    RolePermission,
    Plan,
    Subscription,
    FeatureFlag,
)
from apps.social.models import SocialPage, Post, Comment
from apps.crm.models import Contact, Lead, Tag
from apps.campaigns.models import Campaign
import uuid
from datetime import timedelta


class Command(BaseCommand):
    help = "Seed database with demo data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...")

        # Create permissions
        permissions_data = [
            ("view_social_pages", "View Social Pages", "social"),
            ("manage_social_pages", "Manage Social Pages", "social"),
            ("sync_posts", "Sync Posts", "social"),
            ("view_comments", "View Comments", "comments"),
            ("reply_comments", "Reply to Comments", "comments"),
            ("bulk_reply_comments", "Bulk Reply Comments", "comments"),
            ("assign_comments", "Assign Comments", "comments"),
            ("convert_comment_to_lead", "Convert Comments to Leads", "crm"),
            ("use_ai_comment_reply", "Use AI Reply", "ai"),
            ("view_leads", "View Leads", "crm"),
            ("create_leads", "Create Leads", "crm"),
            ("edit_leads", "Edit Leads", "crm"),
            ("assign_leads", "Assign Leads", "crm"),
            ("change_lead_stage", "Change Lead Stage", "crm"),
            ("create_campaigns", "Create Campaigns", "campaigns"),
            ("launch_campaigns", "Launch Campaigns", "campaigns"),
            ("view_reports", "View Reports", "reports"),
            ("use_ai", "Use AI Features", "ai"),
            ("manage_workspace_users", "Manage Users", "workspace"),
            ("manage_roles", "Manage Roles", "workspace"),
        ]

        permissions = {}
        for key, name, category in permissions_data:
            perm, _ = Permission.objects.get_or_create(
                key=key, defaults={"name": name, "category": category}
            )
            permissions[key] = perm

        # Create super admin
        admin_user, created = User.objects.get_or_create(
            email="admin@nexa.com",
            defaults={
                "name": "Super Admin",
                "global_role": "super_admin",
                "status": "active",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("123456")
            admin_user.save()

        # Create demo client
        client_user, created = User.objects.get_or_create(
            email="client@nexa.com",
            defaults={"name": "Demo Client", "global_role": "user", "status": "active"},
        )
        if created:
            client_user.set_password("123456")
            client_user.save()

        # Create plans
        plans_data = [
            {
                "name": "Starter",
                "key": "starter",
                "price_monthly": 999,
                "price_yearly": 9990,
                "max_pages": 1,
                "max_users": 2,
                "max_campaigns_per_month": 5,
                "max_ai_replies_per_month": 50,
                "max_comments_sync_per_month": 1000,
                "max_leads": 100,
                "features": ["comment_manager", "ai_replies", "crm_leads"],
            },
            {
                "name": "Growth",
                "key": "growth",
                "price_monthly": 2499,
                "price_yearly": 24990,
                "max_pages": 3,
                "max_users": 5,
                "max_campaigns_per_month": 15,
                "max_ai_replies_per_month": 200,
                "max_comments_sync_per_month": 5000,
                "max_leads": 500,
                "features": [
                    "comment_manager",
                    "ai_replies",
                    "campaign_center",
                    "crm_leads",
                    "reports",
                ],
            },
            {
                "name": "Pro",
                "key": "pro",
                "price_monthly": 4999,
                "price_yearly": 49990,
                "max_pages": 10,
                "max_users": 15,
                "max_campaigns_per_month": 50,
                "max_ai_replies_per_month": 1000,
                "max_comments_sync_per_month": 15000,
                "max_leads": 2000,
                "features": [
                    "comment_manager",
                    "ai_replies",
                    "campaign_center",
                    "crm_leads",
                    "reports",
                    "bulk_actions",
                ],
            },
            {
                "name": "Agency",
                "key": "agency",
                "price_monthly": 9999,
                "price_yearly": 99990,
                "max_pages": -1,  # unlimited
                "max_users": -1,
                "max_campaigns_per_month": -1,
                "max_ai_replies_per_month": 5000,
                "max_comments_sync_per_month": 50000,
                "max_leads": -1,
                "features": [
                    "comment_manager",
                    "ai_replies",
                    "campaign_center",
                    "crm_leads",
                    "reports",
                    "bulk_actions",
                    "invite_engagers",
                ],
            },
        ]

        for plan_data in plans_data:
            Plan.objects.get_or_create(key=plan_data["key"], defaults=plan_data)

        # Create demo workspace
        demo_workspace, created = Workspace.objects.get_or_create(
            name="Nexa Demo",
            defaults={
                "owner": client_user,
                "plan": Plan.objects.get(key="growth"),
                "status": "active",
                "business_type": "retail",
            },
        )

        # Create roles
        roles_data = [
            ("Client Owner", "owner", True, list(permissions.keys())),
            (
                "Admin",
                "admin",
                True,
                [k for k in permissions.keys() if k not in ["manage_roles"]],
            ),
            (
                "Marketer",
                "marketer",
                True,
                [
                    "view_social_pages",
                    "view_comments",
                    "reply_comments",
                    "bulk_reply_comments",
                    "create_campaigns",
                    "launch_campaigns",
                    "use_ai_comment_reply",
                    "use_ai",
                ],
            ),
            (
                "Sales Agent",
                "sales_agent",
                True,
                [
                    "view_comments",
                    "reply_comments",
                    "view_leads",
                    "create_leads",
                    "edit_leads",
                    "assign_leads",
                    "change_lead_stage",
                    "convert_comment_to_lead",
                ],
            ),
            (
                "Content Creator",
                "content_creator",
                True,
                [
                    "view_social_pages",
                    "view_comments",
                    "reply_comments",
                    "use_ai_comment_reply",
                ],
            ),
            (
                "Analyst",
                "analyst",
                True,
                ["view_reports", "view_comments", "view_leads"],
            ),
            (
                "Viewer",
                "viewer",
                True,
                ["view_social_pages", "view_comments", "view_leads", "view_reports"],
            ),
        ]

        roles = {}
        for name, key, is_system, perm_keys in roles_data:
            role, created = Role.objects.get_or_create(
                workspace=demo_workspace,
                key=key,
                defaults={
                    "name": name,
                    "is_system_role": is_system,
                    "description": f"{name} role",
                },
            )
            if created:
                for perm_key in perm_keys:
                    RolePermission.objects.create(
                        role=role, permission=permissions[perm_key]
                    )
            roles[key] = role

        # Add client as workspace owner
        WorkspaceUser.objects.get_or_create(
            workspace=demo_workspace,
            user=client_user,
            defaults={"role": roles["owner"], "status": "active"},
        )

        # Create subscription
        Subscription.objects.get_or_create(
            workspace=demo_workspace,
            status="active",
            defaults={
                "plan": Plan.objects.get(key="growth"),
                "billing_cycle": "monthly",
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=365),
            },
        )

        # Enable feature flags
        feature_keys = [
            "comment_manager",
            "ai_replies",
            "campaign_center",
            "crm_leads",
            "reports",
            "bulk_actions",
        ]
        for key in feature_keys:
            FeatureFlag.objects.get_or_create(
                workspace=demo_workspace, feature_key=key, defaults={"is_enabled": True}
            )

        # Create demo social page
        demo_page, created = SocialPage.objects.get_or_create(
            workspace=demo_workspace,
            facebook_page_id="demo_page_123",
            defaults={
                "platform": "facebook",
                "facebook_page_name": "Demo Business Page",
                "facebook_page_username": "demobusiness",
                "followers_count": 1500,
                "likes_count": 1200,
                "category": "Retail",
                "page_access_token_encrypted": "demo_encrypted_token",
                "status": "connected",
            },
        )

        # Create demo posts
        demo_posts_data = [
            {
                "content": "🔥 عرض خاص! خصم 30% على جميع المنتجات لفترة محدودة. سارع بالحجز الآن!",
                "media_type": "photo",
                "likes": 45,
                "comments": 12,
                "shares": 8,
            },
            {
                "content": "منتجاتنا الجديدة وصلت! تعرف على أحدث تشكيلة صيف 2024 ☀️",
                "media_type": "carousel",
                "likes": 32,
                "comments": 8,
                "shares": 5,
            },
            {
                "content": "شكراً لكل عملائنا الكرام على ثقتكم فينا ❤️ تقييماتكم تهمنا",
                "media_type": "text",
                "likes": 67,
                "comments": 15,
                "shares": 3,
            },
            {
                "content": "خدمة التوصيل مجاناً للطلبات فوق 500 جنيه 🚚 اطلب الآن!",
                "media_type": "photo",
                "likes": 28,
                "comments": 10,
                "shares": 12,
            },
            {
                "content": "فيديو جديد: شاهد طريقة استخدام منتجنا الأكثر مبيعاً 📹",
                "media_type": "video",
                "likes": 89,
                "comments": 20,
                "shares": 25,
            },
        ]

        posts = []
        for i, post_data in enumerate(demo_posts_data):
            post = Post.objects.create(
                workspace=demo_workspace,
                social_page=demo_page,
                facebook_post_id=f"demo_post_{i}",
                content=post_data["content"],
                media_type=post_data["media_type"],
                facebook_likes_count=post_data["likes"],
                facebook_comments_count=post_data["comments"],
                facebook_shares_count=post_data["shares"],
                published_at=timezone.now() - timedelta(days=i),
            )
            posts.append(post)

        # Create demo comments with various intents
        comments_data = [
            ("كم سعر المنتج ده؟", "price", 85, "very_positive"),
            ("ممكن اعرف التفاصيل كاملة؟", "details", 70, "positive"),
            ("عايز احجز موعد بكرة الصبح", "booking", 90, "very_positive"),
            ("فين مكانكم بالضبط؟", "location", 60, "neutral"),
            ("الخدمة سيئة جداً ومش راضي عن المنتج", "complaint", 20, "very_negative"),
            ("ممكن رقم تليفون للتواصل؟ 01234567890", "phone", 80, "positive"),
            ("المنتج تحفة بجد شكراً ليكم ❤️", "positive_feedback", 30, "very_positive"),
            ("هل يوجد توصيل لمحافظة الاسكندرية؟", "question", 50, "neutral"),
            ("عايز اعرف سعر الاشتراك الشهري لو سمحت", "price", 88, "positive"),
            ("بكام الحجز للفرد الواحد في الصيف؟", "price", 82, "neutral"),
            ("مشكلة في الطلب اللي استلمته النهاردة", "complaint", 15, "negative"),
            ("هل تقبلوا الدفع عند الاستلام؟", "question", 65, "positive"),
            ("01234567890 كلموني ضروري", "phone", 78, "neutral"),
            (
                "اجمل منتج شفته في حياتي ما شاء الله",
                "positive_feedback",
                25,
                "very_positive",
            ),
            ("عايز الغي الحجز اللي عملته امبارح", "complaint", 10, "negative"),
            ("لوسمحت عايز عنوان الفرع الرئيسي", "location", 55, "neutral"),
            ("ممتاز جداً وسرعة في التوصيل", "positive_feedback", 20, "very_positive"),
            ("هل فيه خصم للكميات الكبيرة؟", "price", 75, "positive"),
            ("ممكن اعرف مواعيد العمل في رمضان؟", "question", 45, "neutral"),
            ("سيء جداً جداً مفيش مصداقية خالص", "complaint", 5, "very_negative"),
            (
                "التعامل راقي والمنتج زي ما هو في الصور",
                "positive_feedback",
                35,
                "very_positive",
            ),
            ("عايز احجز ٣ افراد يوم الجمعة الجاي", "booking", 92, "very_positive"),
            ("هل ممكن اشوف المنتج قبل ما اشتري؟", "question", 60, "positive"),
            ("السعر اللي على الصفحة شامل الضريبة؟", "price", 72, "neutral"),
            ("في فرع ليكم في مدينة نصر؟", "location", 58, "neutral"),
            (
                "شكراً على الخدمة الممتازة ❤️❤️",
                "positive_feedback",
                25,
                "very_positive",
            ),
            ("محتاج اسال عن حاجة ضروري 01012345678", "phone", 85, "positive"),
            ("المنتج جيد ولكن السعر مبالغ فيه", "price", 65, "neutral"),
            ("عندي مشكلة في تشغيل المنتج ممكن مساعدة؟", "complaint", 30, "negative"),
            ("تمام هجرب واسيب تقييم بعد الاستخدام", "general", 40, "neutral"),
        ]

        for i, (message, intent, score, sentiment) in enumerate(comments_data):
            comment = Comment.objects.create(
                workspace=demo_workspace,
                post=posts[i % 5],
                facebook_comment_id=f"demo_comment_{i}",
                facebook_user_id=f"user_{i}",
                facebook_user_name=f"User {i}",
                message=message,
                created_time=timezone.now() - timedelta(hours=i * 2),
                ai_intent=intent,
                ai_intent_confidence=0.9,
                ai_sentiment=sentiment,
                ai_sentiment_confidence=0.85,
                ai_lead_score=score,
                ai_processed_at=timezone.now(),
                status="new" if score < 70 else "lead",
            )

            # Create contacts and leads for high-score comments
            if score >= 70:
                contact = Contact.objects.create(
                    workspace=demo_workspace,
                    name=f"User {i}",
                    source="facebook_comment",
                    platform_user_id=f"user_{i}",
                )

                lead = Lead.objects.create(
                    workspace=demo_workspace,
                    contact=contact,
                    source="comment",
                    stage="new_lead",
                    score=score,
                )

                comment.is_converted_to_lead = True
                comment.lead = lead
                comment.status = "lead"
                comment.save()

        # Create demo campaigns
        campaign_statuses = ["draft", "running", "completed", "paused"]
        campaign_goals = [
            "follow_up",
            "recover_old_customers",
            "price_question",
            "offer",
        ]

        for i in range(4):
            Campaign.objects.create(
                workspace=demo_workspace,
                name=f"Campaign {i+1}",
                goal=campaign_goals[i],
                channel="comment_reply",
                status=campaign_statuses[i],
                audience_type="asked_price",
                message_text="عرض خاص لفترة محدودة! تواصل معنا للمزيد من التفاصيل",
                created_by=client_user,
            )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
