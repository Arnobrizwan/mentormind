from django.core.cache import cache

from .models import SiteSetting

CACHE_KEY_PUBLIC = "settings:public"
CACHE_KEY_ONE = "settings:key:{key}"
CACHE_TTL = 300  # seconds; invalidated eagerly on save via signals


def get_setting(key, default=None):
    cache_key = CACHE_KEY_ONE.format(key=key)
    sentinel = object()
    cached = cache.get(cache_key, sentinel)
    if cached is not sentinel:
        return cached
    try:
        value = SiteSetting.objects.get(key=key).value
    except SiteSetting.DoesNotExist:
        return default
    cache.set(cache_key, value, CACHE_TTL)
    return value


def get_public_settings():
    cached = cache.get(CACHE_KEY_PUBLIC)
    if cached is not None:
        return cached
    data = {s.key: s.value for s in SiteSetting.objects.filter(is_public=True)}
    cache.set(CACHE_KEY_PUBLIC, data, CACHE_TTL)
    return data


def invalidate(key=None):
    if key:
        cache.delete(CACHE_KEY_ONE.format(key=key))
    cache.delete(CACHE_KEY_PUBLIC)
