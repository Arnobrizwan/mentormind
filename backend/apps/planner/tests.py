from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Course, Enrollment, Lesson, Quiz, QuizQuestion

from .builder import build_weekly_plans, week_start
from .models import StudyPlan

User = get_user_model()


class PlannerTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="plan-i@mentormind.dev", password="password123"
        )
        self.student = User.objects.create_user(
            email="plan-s@mentormind.dev", password="password123"
        )
        self.course = Course.objects.create(
            title="Plan 101", slug="plan-101", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title="First steps", content="c",
            order=1, is_published=True,
        )
        self.quiz = Quiz.objects.create(course=self.course, title="Checkpoint")
        QuizQuestion.objects.create(
            quiz=self.quiz, text="?", options=["a", "b"], correct_option_index=0
        )
        Enrollment.objects.create(student=self.student, course=self.course)
        self.as_student = APIClient()
        self.as_student.force_authenticate(user=self.student)

    def test_week_endpoint_builds_a_plan_on_demand(self):
        res = self.as_student.get("/api/v1/planner/week/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        kinds = {item["kind"] for item in body["items"]}
        self.assertIn("lesson", kinds)  # next lesson suggested
        self.assertIn("quiz", kinds)  # unattempted quiz suggested
        self.assertEqual(body["completion_pct"], 0.0)
        self.assertEqual(StudyPlan.objects.count(), 1)

    def test_toggle_marks_items_done(self):
        plan_items = self.as_student.get("/api/v1/planner/week/").json()["items"]
        first = plan_items[0]["id"]
        res = self.as_student.post(f"/api/v1/planner/items/{first}/toggle/")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(res.json()["completion_pct"], 0)
        self.assertEqual(
            self.as_student.post("/api/v1/planner/items/999/toggle/").status_code, 404
        )

    def test_weekly_sweep_builds_and_nudges(self):
        from apps.notifications.models import Notification

        built, escalated = build_weekly_plans()
        self.assertEqual(built, 1)
        self.assertEqual(escalated, 0)
        self.assertTrue(
            Notification.objects.filter(
                user=self.student, title__icontains="study plan"
            ).exists()
        )
        # idempotent within the same week
        built_again, _ = build_weekly_plans()
        self.assertEqual(built_again, 0)

    def test_two_slipping_weeks_escalate_to_a_ticket(self):
        from apps.engagement.models import RemediationTicket

        monday = week_start()
        for weeks_ago in (1, 2):
            StudyPlan.objects.create(
                student=self.student,
                week_start=monday - timedelta(weeks=weeks_ago),
                items=[{"id": 1, "kind": "lesson", "title": "x", "done": False}],
            )
        built, escalated = build_weekly_plans()
        self.assertEqual(escalated, 1)
        ticket = RemediationTicket.objects.get(student=self.student)
        self.assertEqual(ticket.risk, "medium")
        self.assertEqual(ticket.features["source"], "study_plan")
        # second sweep doesn't duplicate while the ticket is unresolved
        build_weekly_plans()
        self.assertEqual(RemediationTicket.objects.count(), 1)
