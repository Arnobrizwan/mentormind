from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Course, Enrollment, Quiz, QuizAttempt

from . import services
from .models import AwardedBadge, DailyActivity, PointsEvent

User = get_user_model()


class EngagementTests(TestCase):
    def setUp(self):
        cache.clear()
        self.instructor = User.objects.create_user(
            email="eng-teach@mentormind.dev", password="pass-123456"
        )
        self.student = User.objects.create_user(
            email="eng-learn@mentormind.dev", password="pass-123456", display_name="Engager"
        )
        self.course = Course.objects.create(
            title="Engage 101", slug="engage-101", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.client_student = APIClient()
        self.client_student.force_authenticate(user=self.student)

    def test_enrollment_awards_points_and_badge(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.assertEqual(services.total_points(self.student), services.point_value("enrollment"))
        self.assertTrue(
            AwardedBadge.objects.filter(user=self.student, badge__key="first-steps").exists()
        )

    def test_perfect_quiz_awards_bonus(self):
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        quiz = Quiz.objects.create(course=self.course, title="Q")
        QuizAttempt.objects.create(
            enrollment=enrollment, quiz=quiz, score=100.0,
            total_questions=2, correct_answers=2,
        )
        actions = set(
            PointsEvent.objects.filter(user=self.student).values_list("action", flat=True)
        )
        self.assertIn("quiz_attempt", actions)
        self.assertIn("quiz_perfect", actions)

    def test_quiz_retake_awards_no_points(self):
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        quiz = Quiz.objects.create(course=self.course, title="Q")
        QuizAttempt.objects.create(
            enrollment=enrollment, quiz=quiz, score=50.0,
            total_questions=2, correct_answers=1,
        )
        total_after_first = services.total_points(self.student)

        # A perfect retake must not add quiz_attempt or quiz_perfect points
        QuizAttempt.objects.create(
            enrollment=enrollment, quiz=quiz, score=100.0,
            total_questions=2, correct_answers=2,
        )
        self.assertEqual(services.total_points(self.student), total_after_first)
        self.assertFalse(
            PointsEvent.objects.filter(user=self.student, action="quiz_perfect").exists()
        )
        self.assertEqual(
            PointsEvent.objects.filter(user=self.student, action="quiz_attempt").count(), 1
        )

    def test_weekly_leaderboard_never_shows_email_local_part(self):
        anon = User.objects.create_user(
            email="eng-anon@mentormind.dev", password="pass-123456"  # no display_name
        )
        services.award_points(anon, "daily_challenge")
        students = [e["student"] for e in services.weekly_leaderboard()]
        self.assertIn(f"Student #{anon.id}", students)
        self.assertNotIn("eng-anon", students)

    def test_daily_login_is_idempotent(self):
        res = self.client_student.post("/api/v1/engagement/daily-login/")
        self.assertTrue(res.json()["claimed"])
        self.assertEqual(res.json()["points"], 5)

        res = self.client_student.post("/api/v1/engagement/daily-login/")
        self.assertFalse(res.json()["claimed"])
        self.assertEqual(
            PointsEvent.objects.filter(user=self.student, action="daily_login").count(), 1
        )

    def test_streak_counts_consecutive_days(self):
        today = timezone.localdate()
        for offset in (0, 1, 2, 4):  # gap at day 3 breaks the run
            DailyActivity.objects.create(user=self.student, date=today - timedelta(days=offset))
        self.assertEqual(services.current_streak(self.student), 3)

    def test_points_value_overridable_via_settings_engine(self):
        from apps.settings_engine.models import SiteSetting

        SiteSetting.objects.create(key="points-daily_login", value=50)
        cache.clear()
        self.assertEqual(services.point_value("daily_login"), 50)

    def test_engagement_me_payload(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        res = self.client_student.get("/api/v1/engagement/me/")
        body = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertGreater(body["points_total"], 0)
        self.assertEqual(body["streak"], 1)
        badges = {b["key"]: b for b in body["badges"]}
        self.assertTrue(badges["first-steps"]["earned"])
        self.assertFalse(badges["on-fire"]["earned"])
        self.assertIn("more to go", badges["on-fire"]["hint"])

    def test_weekly_leaderboard(self):
        other = User.objects.create_user(email="eng-other@mentormind.dev", password="pass-123456")
        services.award_points(self.student, "daily_challenge")  # 20
        services.award_points(other, "chat_message")  # 1
        board = services.weekly_leaderboard()
        self.assertEqual(board[0]["student"], "Engager")
        self.assertEqual(board[0]["rank"], 1)
