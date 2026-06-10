from django.core.cache import cache

from .models import FeatureFlag

CACHE_KEY_ALL = "flags:all"
CACHE_TTL = 300


def all_flags():
    cached = cache.get(CACHE_KEY_ALL)
    if cached is not None:
        return cached
    data = dict(FeatureFlag.objects.values_list("key", "enabled"))
    cache.set(CACHE_KEY_ALL, data, CACHE_TTL)
    return data


def flag_enabled(key, default=False):
    return all_flags().get(key, default)


def invalidate():
    cache.delete(CACHE_KEY_ALL)
