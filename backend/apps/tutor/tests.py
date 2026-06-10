from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Subscription

from .models import TutorMessage, TutorSession

User = get_user_model()


class TutorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(
            email="tutor-learn@mentormind.dev", password="pass-123456"
        )
        self.client_student = APIClient()
        self.client_student.force_authenticate(user=self.student)

    def _make_session(self):
        res = self.client_student.post(
            "/api/v1/tutor/sessions/",
            {"subject": "Physics", "level": "A-Level"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        return res.json()["id"]

    def test_chat_round_trip_with_stub_provider(self):
        session_id = self._make_session()
        res = self.client_student.post(
            f"/api/v1/tutor/sessions/{session_id}/messages/",
            {"content": "Explain Newton's second law"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["user_message"]["role"], "user")
        self.assertEqual(body["assistant_message"]["role"], "assistant")
        self.assertIn("step", body["assistant_message"]["content"].lower())
        self.assertEqual(body["remaining"], 9)

        # session got titled from the first question and is resumable
        res = self.client_student.get(f"/api/v1/tutor/sessions/{session_id}/")
        self.assertIn("Newton", res.json()["title"])
        self.assertEqual(len(res.json()["messages"]), 2)

    def test_free_daily_limit_enforced(self):
        session = TutorSession.objects.create(user=self.student)
        for _ in range(10):
            TutorMessage.objects.create(
                session=session, role=TutorMessage.Role.USER, content="q"
            )
        res = self.client_student.post(
            f"/api/v1/tutor/sessions/{session.id}/messages/",
            {"content": "one more?"},
            format="json",
        )
        self.assertEqual(res.status_code, 429)
        self.assertIn("upgrade", res.json())

    def test_premium_is_unlimited(self):
        Subscription.objects.create(
            user=self.student,
            plan=Subscription.Plan.MONTHLY,
            expires_at=timezone.now() + timedelta(days=30),
        )
        session = TutorSession.objects.create(user=self.student)
        for _ in range(12):
            TutorMessage.objects.create(
                session=session, role=TutorMessage.Role.USER, content="q"
            )
        res = self.client_student.post(
            f"/api/v1/tutor/sessions/{session.id}/messages/",
            {"content": "still going"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.json()["remaining"])

    def test_limit_configurable_via_settings_engine(self):
        from apps.settings_engine.models import SiteSetting

        SiteSetting.objects.create(key="tutor-daily-limit", value=1)
        cache.clear()
        session_id = self._make_session()
        first = self.client_student.post(
            f"/api/v1/tutor/sessions/{session_id}/messages/",
            {"content": "q1"},
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        second = self.client_student.post(
            f"/api/v1/tutor/sessions/{session_id}/messages/",
            {"content": "q2"},
            format="json",
        )
        self.assertEqual(second.status_code, 429)

    def test_feedback_on_assistant_message(self):
        session_id = self._make_session()
        res = self.client_student.post(
            f"/api/v1/tutor/sessions/{session_id}/messages/",
            {"content": "hello"},
            format="json",
        )
        message_id = res.json()["assistant_message"]["id"]
        res = self.client_student.post(
            f"/api/v1/tutor/sessions/{session_id}/messages/{message_id}/feedback/",
            {"value": 1},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["feedback"], 1)

    def test_sessions_are_private(self):
        outsider = User.objects.create_user(
            email="tutor-out@mentormind.dev", password="pass-123456"
        )
        session = TutorSession.objects.create(user=outsider)
        res = self.client_student.get(f"/api/v1/tutor/sessions/{session.id}/")
        self.assertEqual(res.status_code, 404)

    def test_subscribe_flow_sets_premium(self):
        res = self.client_student.post(
            "/api/v1/auth/subscribe/", {"plan": "monthly"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_premium"])
        self.assertEqual(res.json()["subscription"]["plan"], "monthly")

        quota = self.client_student.get("/api/v1/tutor/sessions/quota/")
        self.assertIsNone(quota.json()["limit"])
