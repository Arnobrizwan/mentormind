from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import services
from .models import SiteSetting


@receiver(post_save, sender=SiteSetting)
@receiver(post_delete, sender=SiteSetting)
def invalidate_settings_cache(sender, instance, **kwargs):
    services.invalidate(instance.key)
