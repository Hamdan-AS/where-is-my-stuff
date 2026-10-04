import uuid
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.conf import settings

class User(AbstractUser):
    # Email is also the login username; both columns must accept the same length.
    username = models.CharField(max_length=254, unique=True, validators=[UnicodeUsernameValidator()],
        help_text="Required. 254 characters or fewer. Letters, digits and @/./+/-/_ only.",
        error_messages={"unique": "A user with that username already exists."})
    email = models.EmailField(unique=True)

    @property
    def visible_report_count(self):
        return self.report_set.exclude(status="Removed").count()

class Report(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=5, choices=[("Lost", "Lost"), ("Found", "Found")])
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=40)
    description = models.TextField()
    location = models.CharField(max_length=100)
    lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    lng = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    location_detail = models.CharField(max_length=255)
    event_date = models.DateField()
    contact = models.CharField(max_length=120)
    answers = models.JSONField(default=dict)
    photo = models.ImageField(upload_to="report_photos/", blank=True)
    status = models.CharField(max_length=10, default="Open")
    reserved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.kind} #{self.pk}: {self.title}"

    @property
    def display_id(self):
        prefix = "LFD" if self.kind == "Lost" else "FND"
        return f"{prefix}-{self.pk:03d}"

class Draft(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, null=True, blank=True, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)
    photo = models.ImageField(upload_to="draft_photos/", blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class QRLabel(models.Model):
    """An owner-managed, time-limited contact label for a personal item."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="qr_labels")
    item_name = models.CharField(max_length=80)
    contact_phone = models.CharField(max_length=11)
    token_hash = models.CharField(max_length=64, unique=True)
    qr_image = models.FileField(upload_to="private_qr_labels/")
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        from django.utils import timezone
        return not self.revoked and self.expires_at > timezone.now()

class Match(models.Model):
    lost = models.ForeignKey(Report, related_name="lost_matches", on_delete=models.PROTECT)
    found = models.ForeignKey(Report, related_name="found_matches", on_delete=models.PROTECT)
    score = models.PositiveSmallIntegerField()
    breakdown = models.JSONField(default=dict)
    state = models.CharField(max_length=24, default="Possible Match")
    proposer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="dismissed_matches", on_delete=models.PROTECT)
    meeting_place = models.CharField(max_length=255, blank=True)
    meeting_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["lost", "found"], name="unique_pair"),
            models.CheckConstraint(condition=models.Q(score__lte=100), name="score_maximum"),
        ]

    def __str__(self):
        return f"{self.lost.display_id} ↔ {self.found.display_id} ({self.state})"


class Event(models.Model):
    report = models.ForeignKey(Report, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text} — {self.report.display_id}"
