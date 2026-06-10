from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.flags.models import FeatureFlag
from apps.flags.services import flag_enabled
from apps.settings_engine.models import SiteSetting
from apps.settings_engine.services import get_public_settings, get_setting
from .models import Course, Enrollment, Lesson, Quiz, QuizAttempt, QuizQuestion
from .serializers import LESSON_LOCKED_MESSAGE
from .services import get_course_detail, get_published_courses

User = get_user_model()


class HealthTests(TestCase):
    def test_health_reports_ok_and_instance(self):
        res = self.client.get("/api/v1/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["database"], "ok")
        self.assertIn("instance", res.json())

    def test_served_by_header_present(self):
        res = self.client.get("/api/v1/health/")
        self.assertTrue(res.headers["X-Served-By"])


class SettingsEngineTests(TestCase):
    def test_public_settings_and_cache_invalidation(self):
        SiteSetting.objects.create(key="site-name", value="MentorMind", is_public=True)
        SiteSetting.objects.create(key="smtp-secret", value="x", is_public=False)

        public = get_public_settings()
        self.assertEqual(public, {"site-name": "MentorMind"})

        # save() must invalidate the cache so changes apply live
        s = SiteSetting.objects.get(key="site-name")
        s.value = "MentorMind BD"
        s.save()
        self.assertEqual(get_setting("site-name"), "MentorMind BD")
        self.assertEqual(get_public_settings()["site-name"], "MentorMind BD")

    def test_public_endpoint_is_open(self):
        SiteSetting.objects.create(key="site-name", value="MentorMind", is_public=True)
        res = APIClient().get("/api/v1/settings/public/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["site-name"], "MentorMind")


class FlagsTests(TestCase):
    def test_flags_toggle_live(self):
        flag = FeatureFlag.objects.create(key="chat", enabled=True)
        self.assertTrue(flag_enabled("chat"))
        flag.enabled = False
        flag.save()
        self.assertFalse(flag_enabled("chat"))
        self.assertFalse(flag_enabled("unknown-module"))


class AuthTests(TestCase):
    def test_register_and_jwt_login_and_me(self):
        client = APIClient()
        res = client.post(
            "/api/v1/auth/register/",
            {"email": "student@mentormind.dev", "password": "Sup3r-secret!", "display_name": "Student"},
        )
        self.assertEqual(res.status_code, 201)

        res = client.post(
            "/api/v1/auth/token/",
            {"email": "student@mentormind.dev", "password": "Sup3r-secret!"},
        )
        self.assertEqual(res.status_code, 200)
        access = res.json()["access"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        res = client.get("/api/v1/auth/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["email"], "student@mentormind.dev")

    def test_me_requires_auth(self):
        self.assertEqual(APIClient().get("/api/v1/auth/me/").status_code, 401)


class LearningEngineTests(TestCase):
    def setUp(self):
        cache.clear()
        self.instructor_group, _ = Group.objects.get_or_create(name="Instructors")

        self.instructor = User.objects.create_user(
            email="instructor@mentormind.dev",
            password="password123",
            display_name="Dr. Jane",
        )
        self.instructor.groups.add(self.instructor_group)

        self.student = User.objects.create_user(
            email="student@mentormind.dev",
            password="password123",
            display_name="Alex",
        )

        self.course = Course.objects.create(
            title="Introduction to AI",
            slug="intro-to-ai",
            description="Learn artificial intelligence from scratch.",
            instructor=self.instructor,
            is_published=True,
        )

        self.lesson = Lesson.objects.create(
            course=self.course,
            title="What is Machine Learning?",
            content="Machine learning is the study of computer algorithms...",
            video_url="https://example.com/ml-video",
            order=1,
            is_published=True,
        )

        self.quiz = Quiz.objects.create(
            course=self.course,
            lesson=self.lesson,
            title="ML Basics Quiz",
            description="Test your knowledge on ML basics.",
        )

        self.question = QuizQuestion.objects.create(
            quiz=self.quiz,
            text="What does ML stand for?",
            options=["Machine Learning", "Max Likelihood", "My Life", "More Laughter"],
            correct_option_index=0,
            order=1,
        )

        self.client_instructor = APIClient()
        self.client_instructor.force_authenticate(user=self.instructor)

        self.client_student = APIClient()
        self.client_student.force_authenticate(user=self.student)

    def test_course_creation_permissions(self):
        # Student should not be able to create courses
        res = self.client_student.post(
            "/api/v1/courses/",
            {
                "title": "Invalid Course",
                "slug": "invalid-course",
                "description": "Student shouldn't create this.",
            },
        )
        self.assertEqual(res.status_code, 403)

        # Instructor can create course
        res = self.client_instructor.post(
            "/api/v1/courses/",
            {
                "title": "Advanced PyTorch",
                "slug": "advanced-pytorch",
                "description": "Deep dive into PyTorch.",
                "is_published": False,
            },
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["instructor"], self.instructor.id)

    def test_course_list_caching_and_invalidation(self):
        # Fetch initial courses (should cache it)
        courses = get_published_courses()
        self.assertEqual(len(courses), 1)

        # Create new published course
        new_course = Course.objects.create(
            title="Deep Learning",
            slug="deep-learning",
            description="Neural networks explained.",
            instructor=self.instructor,
            is_published=True,
        )

        # Cache should be invalidated automatically
        courses = get_published_courses()
        self.assertEqual(len(courses), 2)

    def test_course_detail_caching_and_invalidation(self):
        # Fetch detail (should cache detail)
        course = get_course_detail("intro-to-ai")
        self.assertEqual(course.title, "Introduction to AI")

        # Modify course title directly in DB bypass save to test cache persistence
        Course.objects.filter(id=self.course.id).update(title="Intro to AI (Updated)")
        course_cached = get_course_detail("intro-to-ai")
        self.assertEqual(course_cached.title, "Introduction to AI")

        # Now save properly to trigger signal and invalidate cache
        self.course.title = "Introduction to AI (New Title)"
        self.course.save()

        # Cache should be invalidated and return new title
        course_updated = get_course_detail("intro-to-ai")
        self.assertEqual(course_updated.title, "Introduction to AI (New Title)")

    def test_lesson_content_censoring_for_non_enrolled(self):
        # Student views course details
        res = self.client_student.get(f"/api/v1/courses/{self.course.slug}/")
        self.assertEqual(res.status_code, 200)

        # Student is not enrolled, content should be censored
        lesson_data = res.json()["lessons"][0]
        self.assertEqual(lesson_data["content"], LESSON_LOCKED_MESSAGE)
        self.assertIsNone(lesson_data["video_url"])

        # Instructor views course details, content should be visible
        res_inst = self.client_instructor.get(f"/api/v1/courses/{self.course.slug}/")
        self.assertEqual(res_inst.status_code, 200)
        lesson_data_inst = res_inst.json()["lessons"][0]
        self.assertIn("computer algorithms", lesson_data_inst["content"])
        self.assertEqual(lesson_data_inst["video_url"], "https://example.com/ml-video")

    def test_quiz_correct_option_masking_for_students(self):
        # Student enrolls first
        self.client_student.post(f"/api/v1/courses/{self.course.slug}/enroll/")

        # Student gets quiz
        res = self.client_student.get(f"/api/v1/quizzes/{self.quiz.id}/")
        self.assertEqual(res.status_code, 200)
        
        # Student should not see correct option index
        self.assertNotIn("correct_option_index", res.json()["questions"][0])

        # Instructor gets quiz
        res_inst = self.client_instructor.get(f"/api/v1/quizzes/{self.quiz.id}/")
        self.assertEqual(res_inst.status_code, 200)
        
        # Instructor should see correct option index
        self.assertEqual(res_inst.json()["questions"][0]["correct_option_index"], 0)

    def test_enrollment_and_progress_flow(self):
        # Student enrolls
        res = self.client_student.post(f"/api/v1/courses/{self.course.slug}/enroll/")
        self.assertEqual(res.status_code, 201)
        enrollment_id = res.json()["id"]

        # View enrollment progress (should be 0%)
        self.assertEqual(res.json()["progress_percentage"], 0.0)

        # Verify lesson content is now unlocked for student
        res_course = self.client_student.get(f"/api/v1/courses/{self.course.slug}/")
        self.assertEqual(res_course.status_code, 200)
        self.assertIn("computer algorithms", res_course.json()["lessons"][0]["content"])

        # Mark lesson completed
        res_complete = self.client_student.post(
            f"/api/v1/enrollments/{enrollment_id}/complete-lesson/",
            {"lesson_id": self.lesson.id},
        )
        self.assertEqual(res_complete.status_code, 200)
        self.assertEqual(res_complete.json()["progress_percentage"], 100.0)

    def test_quiz_submission_and_attempt(self):
        # Student enrolls first
        self.client_student.post(f"/api/v1/courses/{self.course.slug}/enroll/")

        # Submit correct answer (Machine Learning is index 0)
        res = self.client_student.post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {"answers": {self.question.id: 0}},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["score"], 100.0)
        self.assertEqual(res.json()["correct_answers"], 1)

        # Submit wrong answer
        res_wrong = self.client_student.post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {"answers": {self.question.id: 1}},
            format="json",
        )
        self.assertEqual(res_wrong.status_code, 201)
        self.assertEqual(res_wrong.json()["score"], 0.0)
        self.assertEqual(res_wrong.json()["correct_answers"], 0)


class LeaderboardTests(TestCase):
    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="lb-teach@mentormind.dev", password="pass-123456", display_name="Teach"
        )
        self.instructor.groups.add(group)
        self.course = Course.objects.create(
            title="Leaderboard 101",
            slug="leaderboard-101",
            description="d",
            instructor=self.instructor,
            is_published=True,
        )
        self.quiz = Quiz.objects.create(course=self.course, title="LB Quiz")

        for i, score in enumerate([40.0, 90.0, 75.0]):
            student = User.objects.create_user(
                email=f"lb-s{i}@mentormind.dev",
                password="pass-123456",
                display_name=f"Student {i}",
            )
            enrollment = Enrollment.objects.create(student=student, course=self.course)
            QuizAttempt.objects.create(
                enrollment=enrollment,
                quiz=self.quiz,
                score=score,
                total_questions=10,
                correct_answers=int(score / 10),
            )

    def test_leaderboard_orders_by_best_score(self):
        res = APIClient().get(f"/api/v1/courses/{self.course.slug}/leaderboard/")
        self.assertEqual(res.status_code, 200)
        entries = res.json()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["student"], "Student 1")
        self.assertEqual(entries[0]["best_score"], 90.0)
        self.assertEqual([e["rank"] for e in entries], [1, 2, 3])

    def test_best_score_wins_over_retakes(self):
        cache.clear()
        enrollment = Enrollment.objects.get(student__email="lb-s0@mentormind.dev")
        QuizAttempt.objects.create(
            enrollment=enrollment, quiz=self.quiz, score=95.0,
            total_questions=10, correct_answers=9,
        )
        res = APIClient().get(f"/api/v1/courses/{self.course.slug}/leaderboard/")
        self.assertEqual(res.json()[0]["student"], "Student 0")
        self.assertEqual(res.json()[0]["best_score"], 95.0)


class AvatarUploadTests(TestCase):
    def test_avatar_upload_sets_url(self):
        import io

        from PIL import Image

        user = User.objects.create_user(
            email="ava@mentormind.dev", password="pass-123456"
        )
        client = APIClient()
        client.force_authenticate(user=user)

        buf = io.BytesIO()
        Image.new("RGB", (32, 32), color=(200, 69, 31)).save(buf, format="PNG")
        buf.seek(0)
        buf.name = "avatar.png"

        res = client.put("/api/v1/auth/me/avatar/", {"file": buf}, format="multipart")
        self.assertEqual(res.status_code, 200)
        self.assertIn("avatars/", res.json()["avatar_url"])

        user.refresh_from_db()
        self.assertTrue(user.avatar.name.startswith("avatars/"))
        user.avatar.delete(save=False)

    def test_rejects_non_image(self):
        import io

        user = User.objects.create_user(
            email="ava2@mentormind.dev", password="pass-123456"
        )
        client = APIClient()
        client.force_authenticate(user=user)
        bad = io.BytesIO(b"not an image")
        bad.name = "notes.txt"
        res = client.put("/api/v1/auth/me/avatar/", {"file": bad}, format="multipart")
        self.assertEqual(res.status_code, 400)


class RecommendationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.instructor = User.objects.create_user(
            email="rec-teach@mentormind.dev", password="pass-123456"
        )
        self.courses = [
            Course.objects.create(
                title=f"Course {i}", slug=f"rec-course-{i}", description="d",
                instructor=self.instructor, is_published=True,
            )
            for i in range(4)
        ]
        # peers who took course 0 also took courses 1 and 2 (2x overlap on 1)
        self.me = User.objects.create_user(email="rec-me@mentormind.dev", password="pass-123456")
        Enrollment.objects.create(student=self.me, course=self.courses[0])
        for i, extra in enumerate([[1, 2], [1]]):
            peer = User.objects.create_user(
                email=f"rec-peer{i}@mentormind.dev", password="pass-123456"
            )
            Enrollment.objects.create(student=peer, course=self.courses[0])
            for idx in extra:
                Enrollment.objects.create(student=peer, course=self.courses[idx])

        self.client_me = APIClient()
        self.client_me.force_authenticate(user=self.me)

    def test_co_occurrence_ranking(self):
        res = self.client_me.get("/api/v1/courses/recommended/")
        self.assertEqual(res.status_code, 200)
        slugs = [c["slug"] for c in res.json()]
        # course 1 (two peers) outranks course 2 (one peer); own course excluded
        self.assertNotIn("rec-course-0", slugs)
        self.assertEqual(slugs[0], "rec-course-1")
        self.assertEqual(slugs[1], "rec-course-2")
        # padded out with popular courses (course 3 has no peers but is published)
        self.assertIn("rec-course-3", slugs)

    def test_new_user_gets_popular_fallback(self):
        cache.clear()
        fresh = User.objects.create_user(email="rec-new@mentormind.dev", password="pass-123456")
        client = APIClient()
        client.force_authenticate(user=fresh)
        res = client.get("/api/v1/courses/recommended/")
        self.assertEqual(res.status_code, 200)
        slugs = [c["slug"] for c in res.json()]
        self.assertEqual(slugs[0], "rec-course-0")  # most enrolled

    def test_requires_auth(self):
        self.assertEqual(APIClient().get("/api/v1/courses/recommended/").status_code, 401)


class SystemStatusTests(TestCase):
    def test_system_status_is_public_and_healthy(self):
        res = self.client.get("/api/v1/system/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["healthy"])
        self.assertEqual(body["components"]["database_primary"]["status"], "ok")
        self.assertEqual(body["components"]["cache"]["status"], "ok")
        self.assertEqual(body["components"]["database_replica"]["status"], "not_configured")
        self.assertEqual(body["components"]["ml_service"]["status"], "not_configured")
        self.assertIn("latency_ms", body["components"]["database_primary"])


class ManagementApiTests(TestCase):
    """Endpoints powering instructor-studio and admin-console."""

    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="mgmt-teach@mentormind.dev", password="pass-123456", display_name="Teach"
        )
        self.instructor.groups.add(group)
        self.other_instructor = User.objects.create_user(
            email="mgmt-other@mentormind.dev", password="pass-123456"
        )
        self.other_instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="mgmt-learn@mentormind.dev", password="pass-123456", display_name="Learner"
        )
        self.admin = User.objects.create_user(
            email="mgmt-admin@mentormind.dev", password="pass-123456", is_staff=True
        )
        self.course = Course.objects.create(
            title="Mgmt 101", slug="mgmt-101", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.quiz = Quiz.objects.create(course=self.course, title="Mgmt Quiz")
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)

        self.as_instructor = APIClient()
        self.as_instructor.force_authenticate(user=self.instructor)
        self.as_other = APIClient()
        self.as_other.force_authenticate(user=self.other_instructor)
        self.as_student = APIClient()
        self.as_student.force_authenticate(user=self.student)
        self.as_admin = APIClient()
        self.as_admin.force_authenticate(user=self.admin)

    def test_instructor_creates_question(self):
        res = self.as_instructor.post("/api/v1/questions/", {
            "quiz": self.quiz.id, "text": "2+2?", "options": ["3", "4"],
            "correct_option_index": 1, "order": 1,
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["correct_option_index"], 1)

    def test_question_validation_rejects_bad_index(self):
        res = self.as_instructor.post("/api/v1/questions/", {
            "quiz": self.quiz.id, "text": "?", "options": ["a", "b"],
            "correct_option_index": 5, "order": 1,
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_other_instructor_cannot_touch_foreign_quiz(self):
        res = self.as_other.post("/api/v1/questions/", {
            "quiz": self.quiz.id, "text": "?", "options": ["a", "b"],
            "correct_option_index": 0, "order": 1,
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_student_cannot_author_questions(self):
        res = self.as_student.post("/api/v1/questions/", {
            "quiz": self.quiz.id, "text": "?", "options": ["a", "b"],
            "correct_option_index": 0, "order": 1,
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_students_roster_for_own_course_only(self):
        res = self.as_instructor.get(f"/api/v1/courses/{self.course.slug}/students/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]["student_email"], "mgmt-learn@mentormind.dev")

        res = self.as_other.get(f"/api/v1/courses/{self.course.slug}/students/")
        self.assertEqual(res.status_code, 403)

    def test_flag_management_is_staff_only(self):
        res = self.as_admin.post("/api/v1/flags/manage/", {
            "key": "proctoring", "enabled": True, "description": "ML proctoring",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        flag_id = res.json()["id"]

        # toggling invalidates the public flags dict
        from apps.flags.services import flag_enabled
        self.assertTrue(flag_enabled("proctoring"))
        self.as_admin.patch(f"/api/v1/flags/manage/{flag_id}/", {"enabled": False}, format="json")
        self.assertFalse(flag_enabled("proctoring"))

        self.assertEqual(
            self.as_instructor.get("/api/v1/flags/manage/").status_code, 403
        )

    def test_setting_management_is_staff_only(self):
        res = self.as_admin.post("/api/v1/settings/manage/", {
            "key": "site-name", "value": "MentorMind", "is_public": True,
        }, format="json")
        self.assertEqual(res.status_code, 201)

        from apps.settings_engine.services import get_public_settings
        self.assertEqual(get_public_settings()["site-name"], "MentorMind")

        self.assertEqual(self.as_student.get("/api/v1/settings/manage/").status_code, 403)


class RecommendationFlagTests(TestCase):
    def test_flag_off_disables_recommendations(self):
        from apps.flags.models import FeatureFlag

        cache.clear()
        user = User.objects.create_user(email="flag-rec@mentormind.dev", password="pass-123456")
        client = APIClient()
        client.force_authenticate(user=user)

        # absent flag -> enabled (fail open)
        self.assertEqual(client.get("/api/v1/courses/recommended/").status_code, 200)

        FeatureFlag.objects.create(key="recommendations", enabled=False)
        cache.clear()
        self.assertEqual(client.get("/api/v1/courses/recommended/").status_code, 403)
