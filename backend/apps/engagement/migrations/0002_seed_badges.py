"""Seed the starter badge set. Badges are plain DB rows — operators can
re-tune names, icons and thresholds in the admin at any time."""

from django.db import migrations

STARTER_BADGES = [
    ("first-steps", "First Steps", "Enroll in your first course", "🎒", "enrollments", 1, 1),
    ("quiz-rookie", "Quiz Rookie", "Complete your first quiz", "✏️", "quizzes_taken", 1, 2),
    ("bookworm", "Bookworm", "Complete 10 lessons", "📚", "lessons_completed", 10, 3),
    ("perfectionist", "Perfectionist", "Score 100% on 5 quizzes", "💯", "perfect_quizzes", 5, 4),
    ("on-fire", "On Fire", "Keep a 7-day study streak", "🔥", "streak_days", 7, 5),
    ("point-collector", "Point Collector", "Earn 500 points", "💰", "points_total", 500, 6),
    ("chatterbox", "Chatterbox", "Send 50 course chat messages", "💬", "chat_messages", 50, 7),
    ("curious-mind", "Curious Mind", "Ask the AI tutor 25 questions", "🧠", "tutor_questions", 25, 8),
]


def seed(apps, schema_editor):
    Badge = apps.get_model("engagement", "Badge")
    for key, name, description, icon, rule, threshold, order in STARTER_BADGES:
        Badge.objects.get_or_create(
            key=key,
            defaults={
                "name": name,
                "description": description,
                "icon": icon,
                "rule": rule,
                "threshold": threshold,
                "order": order,
            },
        )


def unseed(apps, schema_editor):
    Badge = apps.get_model("engagement", "Badge")
    Badge.objects.filter(key__in=[b[0] for b in STARTER_BADGES]).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
