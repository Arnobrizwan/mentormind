from django.apps import AppConfig


class SettingsEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.settings_engine"

    def ready(self):
        from . import signals  # noqa: F401
