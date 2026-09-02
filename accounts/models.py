from django.db import models
from django.contrib.auth.models import User


class UserSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    email_notifications = models.BooleanField(default=True)
    pipeline_alerts = models.BooleanField(default=True)
    quality_alerts = models.BooleanField(default=True)
    dashboard_auto_refresh = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Settings"