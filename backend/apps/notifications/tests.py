from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Course, Enrollment, Quiz, QuizAttempt, QuizQuestion

from .models import Notification

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="teach@mentormind.dev", password="pass-123456", display_name="Teach"
        )
        self.instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="learn@mentormind.dev", password="pass-123456", display_name="Learner"
        )
        self.course = Course.objects.create(
            title="Notify 101",
            slug="notify-101",
            description="d",
            instructor=self.instructor,
            is_published=True,
        )
        self.client_student = APIClient()
        self.client_student.force_authenticate(user=self.student)

    def test_enrollment_notifies_student_and_instructor(self):
        Enrollment.objects.create(student=self.student, course=self.course)

        self.assertTrue(
            Notification.objects.filter(
                user=self.student, kind=Notification.Kind.ENROLLMENT
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.instructor, kind=Notification.Kind.ENROLLMENT
            ).exists()
        )

    def test_quiz_attempt_notifies_student(self):
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        quiz = Quiz.objects.create(course=self.course, title="Q")
        QuizQuestion.objects.create(
            quiz=quiz, text="?", options=["a", "b"], correct_option_index=0, order=1
        )
        QuizAttempt.objects.create(
            enrollment=enrollment, quiz=quiz, score=50.0, total_questions=2, correct_answers=1
        )

        note = Notification.objects.filter(
            user=self.student, kind=Notification.Kind.QUIZ_RESULT
        ).first()
        self.assertIsNotNone(note)
        self.assertIn("50.0%", note.title)

    def test_api_lists_own_and_marks_read(self):
        Enrollment.objects.create(student=self.student, course=self.course)

        res = self.client_student.get("/api/v1/notifications/")
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertEqual(len(results), 1)  # instructor's copy must not leak
        note_id = results[0]["id"]

        res = self.client_student.get("/api/v1/notifications/unread-count/")
        self.assertEqual(res.json()["unread"], 1)

        res = self.client_student.post(f"/api/v1/notifications/{note_id}/read/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_read"])

        res = self.client_student.get("/api/v1/notifications/unread-count/")
        self.assertEqual(res.json()["unread"], 0)

    def test_read_all(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        quiz = Quiz.objects.create(course=self.course, title="Q2")
        QuizAttempt.objects.create(
            enrollment=Enrollment.objects.get(student=self.student),
            quiz=quiz,
            score=10,
            total_questions=1,
            correct_answers=0,
        )
        res = self.client_student.post("/api/v1/notifications/read-all/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["marked_read"], 2)


class PushUnsubscribeTests(TestCase):
    """The DELETE endpoint must remove only the named device, never fan out to
    every subscription a user owns."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="push@mentormind.dev", password="pass-123456"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        from .models import PushSubscription

        self.phone = PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example/phone", p256dh="k", auth="a"
        )
        self.laptop = PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example/laptop", p256dh="k", auth="a"
        )

    def test_delete_without_endpoint_is_rejected_and_keeps_subscriptions(self):
        from .models import PushSubscription

        res = self.client.delete("/api/v1/notifications/push/subscribe/", {}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 2)

    def test_delete_removes_only_the_named_device(self):
        from .models import PushSubscription

        res = self.client.delete(
            "/api/v1/notifications/push/subscribe/",
            {"endpoint": "https://push.example/phone"},
            format="json",
        )
        self.assertEqual(res.status_code, 204)
        remaining = list(
            PushSubscription.objects.filter(user=self.user).values_list(
                "endpoint", flat=True
            )
        )
        self.assertEqual(remaining, ["https://push.example/laptop"])

    def test_delete_all_opt_in_clears_everything(self):
        from .models import PushSubscription

        res = self.client.delete(
            "/api/v1/notifications/push/subscribe/", {"all": "true"}, format="json"
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 0)
