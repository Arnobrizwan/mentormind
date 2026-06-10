from django.db import models


class SiteSetting(models.Model):
    """A single dynamic configuration value.

    Everything the platform shows or toggles (site name, logo, colors,
    payment switches, contact info...) lives here — never in code.
    """

    key = models.SlugField(max_length=100, unique=True)
    value = models.JSONField()
    is_public = models.BooleanField(
        default=False, help_text="Public settings are exposed to the frontend unauthenticated."
    )
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key
