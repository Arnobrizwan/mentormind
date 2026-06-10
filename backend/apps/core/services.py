from django.core.cache import cache
from .models import Course

CACHE_KEY_PUBLISHED_LIST = "courses:published:list"
CACHE_KEY_COURSE_DETAIL = "courses:detail:{slug}"
CACHE_KEY_COURSE_DETAIL_BY_ID = "courses:detail:id:{id}"
CACHE_TTL = 300  # 5 minutes; invalidated on changes


def get_published_courses():
    """Retrieve all published courses from cache, or database if missing."""
    cached = cache.get(CACHE_KEY_PUBLISHED_LIST)
    if cached is not None:
        return cached

    # Pre-select instructor to avoid N+1 queries when showing lists
    courses = list(Course.objects.filter(is_published=True).select_related("instructor"))
    cache.set(CACHE_KEY_PUBLISHED_LIST, courses, CACHE_TTL)
    return courses


def get_course_detail(slug_or_id):
    """Retrieve a single course with prefetch/select fields from cache, or database."""
    is_id = isinstance(slug_or_id, int) or (isinstance(slug_or_id, str) and slug_or_id.isdigit())
    if is_id:
        cache_key = CACHE_KEY_COURSE_DETAIL_BY_ID.format(id=slug_or_id)
    else:
        cache_key = CACHE_KEY_COURSE_DETAIL.format(slug=slug_or_id)

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        if is_id:
            course = Course.objects.select_related("instructor").prefetch_related("lessons").get(id=int(slug_or_id))
        else:
            course = Course.objects.select_related("instructor").prefetch_related("lessons").get(slug=slug_or_id)
    except Course.DoesNotExist:
        return None

    # Cache the course object
    cache.set(cache_key, course, CACHE_TTL)
    
    # Cache under both ID and slug keys to keep cache consistent
    if is_id:
        cache.set(CACHE_KEY_COURSE_DETAIL.format(slug=course.slug), course, CACHE_TTL)
    else:
        cache.set(CACHE_KEY_COURSE_DETAIL_BY_ID.format(id=course.id), course, CACHE_TTL)

    return course


def invalidate_course_cache(course_id, course_slug=None):
    """Delete keys associated with this course list and detail views."""
    cache.delete(CACHE_KEY_PUBLISHED_LIST)
    cache.delete(CACHE_KEY_COURSE_DETAIL_BY_ID.format(id=course_id))
    if course_slug:
        cache.delete(CACHE_KEY_COURSE_DETAIL.format(slug=course_slug))
