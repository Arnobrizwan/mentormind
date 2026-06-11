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


class CustomModelProviderTests(TestCase):
    """The TUTOR_MODEL_URL path — replies come from your own model server."""

    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(
            email="custom-model@mentormind.dev", password="pass-123456"
        )
        self.client_student = APIClient()
        self.client_student.force_authenticate(user=self.student)

    def test_custom_server_answer_with_source_attribution(self):
        import os
        from unittest import mock

        from apps.tutor import services

        fake_response = {
            "answer": "**Step 1:** $2x = 8$ (M1)\n**Step 2:** $x = 4$ (A1)",
            "matched": True,
            "source": {
                "subject_code": "9709", "year": 2023, "session": "s",
                "variant": "12", "question_number": 1,
            },
        }
        session_id = self.client_student.post(
            "/api/v1/tutor/sessions/", {"subject": "Math", "level": "A-Level"},
            format="json",
        ).json()["id"]

        with mock.patch.dict(os.environ, {"TUTOR_MODEL_URL": "http://ml/v1/tutor/answer"}):
            with mock.patch.object(services, "_post_json", return_value=fake_response) as post:
                res = self.client_student.post(
                    f"/api/v1/tutor/sessions/{session_id}/messages/",
                    {"content": "Solve 2x + 3 = 11"},
                    format="json",
                )
        self.assertEqual(res.status_code, 201)
        content = res.json()["assistant_message"]["content"]
        self.assertIn("$x = 4$", content)
        self.assertIn("Source: Cambridge 9709", content)
        payload = post.call_args.args[1]
        self.assertEqual(payload["question"], "Solve 2x + 3 = 11")
        self.assertEqual(payload["subject"], "Math")

    def test_unreachable_server_does_not_burn_quota(self):
        import os
        from unittest import mock

        from apps.tutor import services

        session_id = self.client_student.post(
            "/api/v1/tutor/sessions/", {}, format="json"
        ).json()["id"]

        with mock.patch.dict(os.environ, {"TUTOR_MODEL_URL": "http://down/answer"}):
            with mock.patch.object(
                services, "_post_json", side_effect=OSError("connection refused")
            ):
                res = self.client_student.post(
                    f"/api/v1/tutor/sessions/{session_id}/messages/",
                    {"content": "hello"},
                    format="json",
                )
        self.assertEqual(res.status_code, 502)
        self.assertEqual(TutorMessage.objects.filter(session_id=session_id).count(), 0)


class TutorImageTests(TestCase):
    """Multimodal tutoring — a photographed question is OCR'd via the
    ml-service and answered like typed text."""

    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(
            email="tutor-photo@mentormind.dev", password="pass-123456"
        )
        self.client_student = APIClient()
        self.client_student.force_authenticate(user=self.student)
        res = self.client_student.post(
            "/api/v1/tutor/sessions/", {"subject": "Maths"}, format="json"
        )
        self.session_id = res.json()["id"]

    def _photo(self, content_type="image/jpeg"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile("question.jpg", b"img", content_type=content_type)

    def test_photo_question_is_ocrd_and_answered(self):
        from unittest.mock import patch

        with patch(
            "apps.core.ml_client.post_image",
            return_value={"text": "Solve 2x + 3 = 11", "characters": 17},
        ) as mocked:
            res = self.client_student.post(
                f"/api/v1/tutor/sessions/{self.session_id}/messages/",
                {"image": self._photo()},
                format="multipart",
            )
        self.assertEqual(res.status_code, 201)
        content = res.json()["user_message"]["content"]
        self.assertIn("[From my photo]", content)
        self.assertIn("Solve 2x + 3 = 11", content)
        self.assertEqual(res.json()["assistant_message"]["role"], "assistant")
        mocked.assert_called_once()

    def test_typed_text_and_photo_are_combined(self):
        from unittest.mock import patch

        with patch(
            "apps.core.ml_client.post_image",
            return_value={"text": "x^2 + 2x", "characters": 8},
        ):
            res = self.client_student.post(
                f"/api/v1/tutor/sessions/{self.session_id}/messages/",
                {"content": "Differentiate this:", "image": self._photo()},
                format="multipart",
            )
        content = res.json()["user_message"]["content"]
        self.assertTrue(content.startswith("Differentiate this:"))
        self.assertIn("x^2 + 2x", content)

    def test_unreadable_photo_without_text_is_rejected(self):
        from unittest.mock import patch

        with patch(
            "apps.core.ml_client.post_image",
            return_value={"text": "", "characters": 0},
        ):
            res = self.client_student.post(
                f"/api/v1/tutor/sessions/{self.session_id}/messages/",
                {"image": self._photo()},
                format="multipart",
            )
        self.assertEqual(res.status_code, 400)
        self.assertIn("photo", res.json()["error"])
        self.assertEqual(
            TutorMessage.objects.filter(session_id=self.session_id).count(), 0
        )

    def test_non_image_upload_is_rejected(self):
        res = self.client_student.post(
            f"/api/v1/tutor/sessions/{self.session_id}/messages/",
            {"image": self._photo(content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)
