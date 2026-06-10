import os

from django.core.cache import cache
from django.db.models import Count, Max

from .models import Course, Enrollment, QuizAttempt

CACHE_KEY_PUBLISHED_LIST = "courses:published:list"
CACHE_KEY_COURSE_DETAIL = "courses:detail:{slug}"
CACHE_KEY_COURSE_DETAIL_BY_ID = "courses:detail:id:{id}"
# Invalidated eagerly on changes; TTLs are operational backstops.
CACHE_TTL = int(os.getenv("COURSE_CACHE_TTL", "300"))

LEADERBOARD_ZSET_KEY = "leaderboard:course:{id}"
LEADERBOARD_CACHE_KEY = "leaderboard:course:{id}:top"
LEADERBOARD_TTL = int(os.getenv("LEADERBOARD_CACHE_TTL", "60"))


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


# --- Leaderboard: Redis sorted set showcase, DB aggregate fallback ---------


def record_leaderboard_score(course_id, user_id, score):
    """Keep each student's best score in a Redis sorted set. When the cache
    backend isn't Redis (bare-metal dev, tests) this quietly no-ops and the
    DB fallback in get_leaderboard serves instead."""
    try:
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        # GT: only update if the new score is greater (best-score semantics)
        conn.zadd(LEADERBOARD_ZSET_KEY.format(id=course_id), {str(user_id): score}, gt=True)
    except Exception:
        pass
    cache.delete(LEADERBOARD_CACHE_KEY.format(id=course_id))


def _leaderboard_from_redis(course_id, limit):
    try:
        from django.contrib.auth import get_user_model
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        pairs = conn.zrevrange(
            LEADERBOARD_ZSET_KEY.format(id=course_id), 0, limit - 1, withscores=True
        )
        if not pairs:
            return None
        user_ids = [int(member) for member, _ in pairs]
        users = get_user_model().objects.in_bulk(user_ids)
        entries = []
        for rank, (member, score) in enumerate(pairs, start=1):
            user = users.get(int(member))
            if not user:
                continue
            entries.append(
                {
                    "rank": rank,
                    "student": user.display_name or user.email.split("@")[0],
                    "best_score": round(score, 2),
                }
            )
        return entries or None
    except Exception:
        return None


def _leaderboard_from_db(course_id, limit):
    rows = (
        QuizAttempt.objects.filter(quiz__course_id=course_id)
        .values(
            "enrollment__student_id",
            "enrollment__student__display_name",
            "enrollment__student__email",
        )
        .annotate(best_score=Max("score"), attempts=Count("id"))
        .order_by("-best_score")[:limit]
    )
    return [
        {
            "rank": rank,
            "student": row["enrollment__student__display_name"]
            or row["enrollment__student__email"].split("@")[0],
            "best_score": round(row["best_score"], 2),
        }
        for rank, row in enumerate(rows, start=1)
    ]


def get_leaderboard(course_id, limit=10):
    """Top quiz scorers for a course, cached for 60s."""
    cache_key = LEADERBOARD_CACHE_KEY.format(id=course_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    entries = _leaderboard_from_redis(course_id, limit)
    if entries is None:
        entries = _leaderboard_from_db(course_id, limit)

    cache.set(cache_key, entries, LEADERBOARD_TTL)
    return entries


# --- Recommendations: enrollment co-occurrence ------------------------------

RECOMMENDATIONS_CACHE_KEY = "recs:user:{id}"
RECOMMENDATIONS_TTL = 300


def get_recommendations(user, limit=5):
    """'Students who took your courses also took…' — classic item-based
    co-occurrence over enrollments, topped up with the most popular courses
    when the user's neighbourhood is too small."""
    cache_key = RECOMMENDATIONS_CACHE_KEY.format(id=user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    my_course_ids = list(
        Enrollment.objects.filter(student=user).values_list("course_id", flat=True)
    )

    recommended = []
    if my_course_ids:
        peer_ids = (
            Enrollment.objects.filter(course_id__in=my_course_ids)
            .exclude(student=user)
            .values_list("student_id", flat=True)
        )
        recommended = list(
            Course.objects.filter(is_published=True, enrollments__student_id__in=peer_ids)
            .exclude(id__in=my_course_ids)
            .annotate(overlap=Count("enrollments"))
            .order_by("-overlap", "-created_at")
            .select_related("instructor")[:limit]
        )

    if len(recommended) < limit:
        seen = set(my_course_ids) | {c.id for c in recommended}
        popular = (
            Course.objects.filter(is_published=True)
            .exclude(id__in=seen)
            .annotate(popularity=Count("enrollments"))
            .order_by("-popularity", "-created_at")
            .select_related("instructor")[: limit - len(recommended)]
        )
        recommended.extend(popular)

    cache.set(cache_key, recommended, RECOMMENDATIONS_TTL)
    return recommended
