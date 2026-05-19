# apps/workspaces/models.py
import uuid
from django.db import models
from core.models import SoftDeleteModel, BaseWorkspaceModel


class Workspace(SoftDeleteModel):
    name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=100, null=True, blank=True)
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="owned_workspaces"
    )
    plan = models.ForeignKey("Plan", on_delete=models.PROTECT, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("trial", "Trial"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
        ],
        default="trial",
    )
    timezone = models.CharField(max_length=50, default="Africa/Cairo")
    language = models.CharField(max_length=10, default="ar")

    class Meta:
        db_table = "workspaces"


class WorkspaceUser(SoftDeleteModel):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="workspace_users"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="workspace_users"
    )
    role = models.ForeignKey("Role", on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("invited", "Invited"),
            ("suspended", "Suspended"),
        ],
        default="active",
    )
    invited_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="invited_users",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspace_users"
        unique_together = ["workspace", "user"]


class Role(SoftDeleteModel):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name="roles"
    )
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    is_system_role = models.BooleanField(default=False)
    permissions = models.ManyToManyField("Permission", through="RolePermission")

    class Meta:
        db_table = "roles"


class Permission(SoftDeleteModel):
    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "permissions"


class RolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = "role_permissions"
        unique_together = ["role", "permission"]


class Plan(SoftDeleteModel):
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=50, unique=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EGP")
    max_pages = models.IntegerField()
    max_users = models.IntegerField()
    max_campaigns_per_month = models.IntegerField()
    max_ai_replies_per_month = models.IntegerField()
    max_comments_sync_per_month = models.IntegerField()
    max_leads = models.IntegerField()
    features = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default="active")

    class Meta:
        db_table = "plans"


class Subscription(SoftDeleteModel):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=[
            ("trial", "Trial"),
            ("active", "Active"),
            ("past_due", "Past Due"),
            ("cancelled", "Cancelled"),
            ("expired", "Expired"),
        ],
    )
    billing_cycle = models.CharField(
        max_length=10, choices=[("monthly", "Monthly"), ("yearly", "Yearly")]
    )
    payment_method = models.CharField(max_length=50, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    trial_ends_at = models.DateTimeField(null=True)
    cancelled_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "subscriptions"


class FeatureFlag(SoftDeleteModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    feature_key = models.CharField(max_length=100)
    is_enabled = models.BooleanField(default=False)
    limit_value = models.IntegerField(null=True)

    class Meta:
        db_table = "feature_flags"
        unique_together = ["workspace", "feature_key"]


class UsageLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    feature_key = models.CharField(max_length=100)
    usage_type = models.CharField(max_length=50)
    usage_count = models.IntegerField(default=1)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usage_logs"
