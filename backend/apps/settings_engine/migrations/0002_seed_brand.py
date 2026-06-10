"""Seed public brand settings so all apps bootstrap as 'MentorMinds'.
These are plain rows — editable live from the admin console."""

from django.db import migrations

BRAND = [
    ("site-name", "MentorMinds", True),
    ("tagline", "the AI tutor that never sleeps", True),
]


def seed(apps, schema_editor):
    SiteSetting = apps.get_model("settings_engine", "SiteSetting")
    for key, value, is_public in BRAND:
        SiteSetting.objects.get_or_create(
            key=key, defaults={"value": value, "is_public": is_public}
        )


def unseed(apps, schema_editor):
    SiteSetting = apps.get_model("settings_engine", "SiteSetting")
    SiteSetting.objects.filter(key__in=[b[0] for b in BRAND]).delete()


class Migration(migrations.Migration):
    dependencies = [("settings_engine", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
