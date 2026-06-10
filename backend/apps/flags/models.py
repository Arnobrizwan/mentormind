from django.db import models


class FeatureFlag(models.Model):
    """Modules (chat, proctoring, payments...) are switched on/off here —
    from the admin panel, live, without redeploying."""

    key = models.SlugField(max_length=100, unique=True)
    enabled = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} ({'on' if self.enabled else 'off'})"
