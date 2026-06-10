from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import services
from .models import FeatureFlag


@receiver(post_save, sender=FeatureFlag)
@receiver(post_delete, sender=FeatureFlag)
def invalidate_flags_cache(sender, instance, **kwargs):
    services.invalidate()
