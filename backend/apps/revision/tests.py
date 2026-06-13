from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Course, Enrollment, Lesson

from . import sm2
from .models import Flashcard, ReviewCard

User = get_user_model()


class Sm2Tests(TestCase):
    def _card(self):
        instructor = User.objects.create_user(
            email="sm2-i@mentormind.dev", password="password123"
        )
        course = Course.objects.create(
            title="C", slug="sm2-c", description="d", instructor=instructor
        )
        flashcard = Flashcard.objects.create(
            course=course, front="f", back="b", is_published=True
        )
        student = User.objects.create_user(
            email="sm2-s@mentormind.dev", password="password123"
        )
        return ReviewCard.objects.create(
            user=student, flashcard=flashcard, due_at=timezone.now()
        )

    def test_good_grades_grow_the_interval(self):
        card = self._card()
        sm2.review(card, 5)
        self.assertEqual(card.interval_days, 1)
        sm2.review(card, 5)
        self.assertEqual(card.interval_days, 6)
        sm2.review(card, 5)
        self.assertGreater(card.interval_days, 6)
        self.assertGreater(card.ease_factor, 2.5)

    def test_lapse_resets_and_returns_within_minutes(self):
        card = self._card()
        sm2.review(card, 5)
        sm2.review(card, 1)  # lapse
        self.assertEqual(card.repetitions, 0)
        self.assertLess(card.due_at, timezone.now() + timedelta(minutes=11))

    def test_ease_never_drops_below_floor(self):
        card = self._card()
        for _ in range(10):
            sm2.review(card, 0)
        self.assertGreaterEqual(card.ease_factor, sm2.MIN_EASE)


class RevisionApiTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="rev-i@mentormind.dev", password="password123"
        )
        self.instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="rev-s@mentormind.dev", password="password123"
        )
        self.course = Course.objects.create(
            title="Revise", slug="rev-c", description="d",
            instructor=self.instructor, is_published=True,
        )
        Enrollment.objects.create(student=self.student, course=self.course)
        self.published = Flashcard.objects.create(
            course=self.course, front="What is X?", back="X is Y.",
            is_published=True, topic="Basics",
        )
        self.draft = Flashcard.objects.create(
            course=self.course, front="draft", back="draft", is_published=False
        )
        self.as_student = APIClient()
        self.as_student.force_authenticate(user=self.student)
        self.as_instructor = APIClient()
        self.as_instructor.force_authenticate(user=self.instructor)

    def test_queue_adopts_only_published_cards(self):
        res = self.as_student.get("/api/v1/revision/queue/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["due_count"], 1)
        self.assertEqual(body["cards"][0]["front"], "What is X?")
        self.assertEqual(ReviewCard.objects.filter(user=self.student).count(), 1)

    def test_review_reschedules_and_awards_points(self):
        from apps.engagement.models import PointsEvent

        self.as_student.get("/api/v1/revision/queue/")
        card = ReviewCard.objects.get(user=self.student)
        res = self.as_student.post(
            "/api/v1/revision/review/", {"card": card.id, "grade": 5}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        card.refresh_from_db()
        self.assertEqual(card.repetitions, 1)
        self.assertGreater(card.due_at, timezone.now())
        self.assertTrue(
            PointsEvent.objects.filter(
                user=self.student, action="revision_review"
            ).exists()
        )
        # reviewed card no longer due
        res = self.as_student.get("/api/v1/revision/queue/")
        self.assertEqual(res.json()["due_count"], 0)

    def test_cannot_review_someone_elses_card(self):
        other = User.objects.create_user(
            email="rev-o@mentormind.dev", password="password123"
        )
        card = ReviewCard.objects.create(
            user=other, flashcard=self.published, due_at=timezone.now()
        )
        res = self.as_student.post(
            "/api/v1/revision/review/", {"card": card.id, "grade": 4}, format="json"
        )
        self.assertEqual(res.status_code, 404)

    def test_flashcard_crud_is_instructor_only(self):
        self.assertEqual(
            self.as_student.get("/api/v1/revision/flashcards/").status_code, 403
        )
        res = self.as_instructor.post(
            "/api/v1/revision/flashcards/",
            {"course": self.course.id, "front": "New?", "back": "Yes.", "is_published": True},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["source"], "instructor")

    def test_generate_files_unpublished_drafts_and_notifies(self):
        from apps.notifications.models import Notification

        lesson = Lesson.objects.create(
            course=self.course, title="Cells",
            content="Mitochondria: the powerhouse of the cell.",
            order=1, is_published=True,
        )
        generated = {
            "cards": [{"front": "What is a mitochondrion?", "back": "The powerhouse."}],
            "engine": "llm",
        }
        with patch("apps.core.ml_client.post_json", return_value=generated):
            res = self.as_instructor.post(
                "/api/v1/revision/generate/", {"lesson": lesson.id}, format="json"
            )
        self.assertEqual(res.status_code, 202)
        draft = Flashcard.objects.get(lesson=lesson)
        self.assertFalse(draft.is_published)
        self.assertEqual(draft.source, "llm")
        self.assertTrue(
            Notification.objects.filter(
                user=self.instructor, title__icontains="flashcard"
            ).exists()
        )

    def test_export_csv_includes_published_cards_only(self):
        res = self.as_student.get("/api/v1/revision/export.csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        body = res.content.decode()
        # Anki import directives + the published card; never the draft.
        self.assertIn("#separator:Comma", body)
        self.assertIn("What is X?", body)
        self.assertIn("course::rev-c", body)
        self.assertNotIn("draft", body)

    def test_export_csv_neutralizes_formula_injection(self):
        Flashcard.objects.create(
            course=self.course,
            front="=HYPERLINK(\"http://evil\",\"x\")",
            back="+1+2",
            is_published=True,
        )
        body = self.as_student.get("/api/v1/revision/export.csv").content.decode()
        # Formula-leading cells are prefixed with an apostrophe so a spreadsheet
        # treats them as text, never executes them.
        self.assertIn("'=HYPERLINK", body)
        self.assertIn("'+1+2", body)
        # The raw, un-neutralized formula must not appear at a cell boundary.
        self.assertNotIn(",=HYPERLINK", body)


class ReviewFixTests(TestCase):
    """Regression: reviewing a not-yet-due card must not farm points."""

    def test_early_re_review_is_rejected(self):
        instructor = User.objects.create_user(
            email="farm-i@mentormind.dev", password="password123"
        )
        student = User.objects.create_user(
            email="farm-s@mentormind.dev", password="password123"
        )
        course = Course.objects.create(
            title="F", slug="farm-c", description="d",
            instructor=instructor, is_published=True,
        )
        Enrollment.objects.create(student=student, course=course)
        flashcard = Flashcard.objects.create(
            course=course, front="f", back="b", is_published=True
        )
        card = ReviewCard.objects.create(
            user=student, flashcard=flashcard, due_at=timezone.now()
        )
        client = APIClient()
        client.force_authenticate(user=student)
        first = client.post(
            "/api/v1/revision/review/", {"card": card.id, "grade": 5}, format="json"
        )
        self.assertEqual(first.status_code, 200)
        # Card is now scheduled in the future — immediate re-review refused
        again = client.post(
            "/api/v1/revision/review/", {"card": card.id, "grade": 5}, format="json"
        )
        self.assertEqual(again.status_code, 409)

        from apps.engagement.models import PointsEvent

        self.assertEqual(
            PointsEvent.objects.filter(user=student, action="revision_review").count(),
            1,
        )
