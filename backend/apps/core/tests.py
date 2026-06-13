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
    def setUp(self):
        # Start from a clean slate — migrations seed brand rows (site-name,
        # tagline); these tests assert exact dicts on their own keys.
        cache.clear()
        SiteSetting.objects.all().delete()

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

    def test_login_throttle_scope_configured(self):
        from django.conf import settings as dj_settings
        from django.urls import resolve
        from rest_framework.throttling import ScopedRateThrottle

        from apps.accounts.views import ThrottledTokenObtainPairView

        view_class = resolve("/api/v1/auth/token/").func.view_class
        self.assertIs(view_class, ThrottledTokenObtainPairView)
        self.assertEqual(view_class.throttle_scope, "auth")
        self.assertIn(ScopedRateThrottle, view_class.throttle_classes)
        # The rate key exists (None under the test runner, 10/min live)
        self.assertIn("auth", dj_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])


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

    def test_quiz_submit_rejects_malformed_payload(self):
        self.client_student.post(f"/api/v1/courses/{self.course.slug}/enroll/")

        # A list (or any non-object) payload must 400, never 500
        res = self.client_student.post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {"answers": [0, 1]},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

        # Non-numeric answers count as wrong, not as a server error
        res = self.client_student.post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {"answers": {self.question.id: "abc"}},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["score"], 0.0)

    def test_quiz_attempts_are_capped(self):
        self.client_student.post(f"/api/v1/courses/{self.course.slug}/enroll/")
        for _ in range(3):  # default cap
            res = self.client_student.post(
                f"/api/v1/quizzes/{self.quiz.id}/submit/",
                {"answers": {self.question.id: 0}},
                format="json",
            )
            self.assertEqual(res.status_code, 201)

        res = self.client_student.post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {"answers": {self.question.id: 0}},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Attempt limit", res.json()["error"])

    def test_quiz_visibility_requires_enrollment(self):
        outsider = User.objects.create_user(
            email="quiz-out@mentormind.dev", password="pass-123456"
        )
        client = APIClient()
        client.force_authenticate(user=outsider)

        # Not enrolled — the quiz is invisible in list and detail
        res = client.get("/api/v1/quizzes/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["results"], [])
        self.assertEqual(client.get(f"/api/v1/quizzes/{self.quiz.id}/").status_code, 404)

        # Enrolled student sees it
        self.client_student.post(f"/api/v1/courses/{self.course.slug}/enroll/")
        res = self.client_student.get("/api/v1/quizzes/")
        self.assertIn(self.quiz.id, [q["id"] for q in res.json()["results"]])


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

    def test_leaderboard_never_shows_email_local_part(self):
        cache.clear()
        anon = User.objects.create_user(
            email="lb-anon@mentormind.dev", password="pass-123456"  # no display_name
        )
        enrollment = Enrollment.objects.create(student=anon, course=self.course)
        QuizAttempt.objects.create(
            enrollment=enrollment, quiz=self.quiz, score=99.0,
            total_questions=10, correct_answers=9,
        )
        res = APIClient().get(f"/api/v1/courses/{self.course.slug}/leaderboard/")
        students = [e["student"] for e in res.json()]
        self.assertIn(f"Student #{anon.id}", students)
        self.assertNotIn("lb-anon", students)


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
    def test_system_status_is_staff_only_and_healthy(self):
        # students/anonymous get nothing — infra detail is admin-only
        self.assertIn(self.client.get("/api/v1/system/").status_code, (401, 403))

        admin = User.objects.create_user(
            email="sys-admin@mentormind.dev", password="password123",
            is_staff=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.get("/api/v1/system/")
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
            "key": "hero-banner", "value": "Welcome", "is_public": True,
        }, format="json")
        self.assertEqual(res.status_code, 201)

        from apps.settings_engine.services import get_public_settings
        self.assertEqual(get_public_settings()["hero-banner"], "Welcome")

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


class SearchTests(TestCase):
    def setUp(self):
        cache.clear()
        instructor = User.objects.create_user(
            email="search-teach@mentormind.dev", password="pass-123456"
        )
        course = Course.objects.create(
            title="Quantum Mechanics", slug="quantum-mech", description="waves and particles",
            instructor=instructor, is_published=True,
        )
        Lesson.objects.create(
            course=course, title="Wave functions explained", content="c",
            order=1, is_published=True,
        )
        Course.objects.create(
            title="Hidden Draft", slug="hidden-draft", description="quantum secrets",
            instructor=instructor, is_published=False,
        )

    def test_search_finds_published_only(self):
        res = APIClient().get("/api/v1/search/?q=quantum")
        self.assertEqual(res.status_code, 200)
        slugs = [c["slug"] for c in res.json()["courses"]]
        self.assertIn("quantum-mech", slugs)
        self.assertNotIn("hidden-draft", slugs)

    def test_search_matches_lessons(self):
        res = APIClient().get("/api/v1/search/?q=wave")
        self.assertEqual(res.json()["lessons"][0]["title"], "Wave functions explained")

    def test_short_query_returns_empty(self):
        res = APIClient().get("/api/v1/search/?q=a")
        self.assertEqual(res.json()["courses"], [])


class AdminStatsTests(TestCase):
    def test_stats_staff_only(self):
        admin = User.objects.create_user(
            email="stats-admin@mentormind.dev", password="pass-123456", is_staff=True
        )
        student = User.objects.create_user(
            email="stats-user@mentormind.dev", password="pass-123456"
        )
        as_admin = APIClient()
        as_admin.force_authenticate(user=admin)
        as_student = APIClient()
        as_student.force_authenticate(user=student)

        res = as_admin.get("/api/v1/admin/stats/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["users_total"], 2)
        self.assertIn("premium_users", res.json())

        self.assertEqual(as_student.get("/api/v1/admin/stats/").status_code, 403)


class ShortAnswerGradingTests(TestCase):
    """LLM rubric grading — questions, permissions, and the ml-service call."""

    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="sa-instructor@mentormind.dev", password="password123"
        )
        self.instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="sa-student@mentormind.dev", password="password123"
        )
        self.outsider = User.objects.create_user(
            email="sa-outsider@mentormind.dev", password="password123"
        )
        self.course = Course.objects.create(
            title="Physics",
            slug="sa-physics",
            description="Forces and motion.",
            instructor=self.instructor,
            is_published=True,
        )
        Enrollment.objects.create(student=self.student, course=self.course)
        from .models import ShortAnswerQuestion

        self.question = ShortAnswerQuestion.objects.create(
            course=self.course,
            prompt="Define acceleration and calculate it for 0 to 20 m/s in 8 s.",
            mark_scheme="- rate of change of velocity\n- a = (v-u)/t\n- 2.5 m/s^2",
            max_score=5,
        )
        self.as_student = APIClient()
        self.as_student.force_authenticate(user=self.student)
        self.as_instructor = APIClient()
        self.as_instructor.force_authenticate(user=self.instructor)

    def test_mark_scheme_hidden_from_students(self):
        res = self.as_student.get(f"/api/v1/short-answers/{self.question.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("mark_scheme", res.json())
        res = self.as_instructor.get(f"/api/v1/short-answers/{self.question.id}/")
        self.assertIn("mark_scheme", res.json())

    def test_submit_grades_and_stores_breakdown(self):
        from unittest.mock import patch

        graded = {
            "score": 4,
            "max_score": 5,
            "criteria_met": ["rate of change of velocity", "a = (v-u)/t"],
            "criteria_missing": ["2.5 m/s^2"],
            "feedback": "Show the final value with units.",
            "engine": "llm",
        }
        with patch("apps.core.ml_client.post_json", return_value=graded) as mocked:
            res = self.as_student.post(
                f"/api/v1/short-answers/{self.question.id}/submit/",
                {"answer": "Acceleration is the rate of change of velocity, a=(v-u)/t."},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["score"], 4)
        self.assertEqual(body["engine"], "llm")
        self.assertEqual(len(body["criteria_missing"]), 1)
        mocked.assert_called_once()
        sent = mocked.call_args.args[1]
        self.assertEqual(sent["max_score"], 5)
        self.assertIn("mark_scheme", sent)

    def test_submit_requires_enrollment(self):
        as_outsider = APIClient()
        as_outsider.force_authenticate(user=self.outsider)
        res = as_outsider.post(
            f"/api/v1/short-answers/{self.question.id}/submit/",
            {"answer": "An answer."},
            format="json",
        )
        # Outsiders can't even see the question (404) or submit (400)
        self.assertIn(res.status_code, (400, 404))

    def test_attempt_cap_enforced(self):
        from .models import ShortAnswerSubmission

        enrollment = Enrollment.objects.get(student=self.student, course=self.course)
        for _ in range(3):
            ShortAnswerSubmission.objects.create(
                question=self.question,
                enrollment=enrollment,
                answer_text="x",
                score=1,
                max_score=5,
            )
        res = self.as_student.post(
            f"/api/v1/short-answers/{self.question.id}/submit/",
            {"answer": "Another go."},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Attempt limit", res.json()["error"])

    def test_grader_outage_returns_502_and_stores_nothing(self):
        from unittest.mock import patch

        from apps.core import ml_client
        from .models import ShortAnswerSubmission

        with patch(
            "apps.core.ml_client.post_json",
            side_effect=ml_client.MLServiceError("down"),
        ):
            res = self.as_student.post(
                f"/api/v1/short-answers/{self.question.id}/submit/",
                {"answer": "An answer."},
                format="json",
            )
        self.assertEqual(res.status_code, 502)
        self.assertEqual(ShortAnswerSubmission.objects.count(), 0)

    def test_students_see_only_their_own_submissions(self):
        from .models import ShortAnswerSubmission

        enrollment = Enrollment.objects.get(student=self.student, course=self.course)
        other = User.objects.create_user(
            email="sa-other@mentormind.dev", password="password123"
        )
        other_enrollment = Enrollment.objects.create(student=other, course=self.course)
        ShortAnswerSubmission.objects.create(
            question=self.question, enrollment=enrollment,
            answer_text="mine", score=2, max_score=5,
        )
        ShortAnswerSubmission.objects.create(
            question=self.question, enrollment=other_enrollment,
            answer_text="theirs", score=3, max_score=5,
        )
        res = self.as_student.get(
            f"/api/v1/short-answers/{self.question.id}/submissions/"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["answer_text"], "mine")
        res = self.as_instructor.get(
            f"/api/v1/short-answers/{self.question.id}/submissions/"
        )
        self.assertEqual(len(res.json()), 2)

    def test_only_course_instructor_creates_questions(self):
        res = self.as_student.post(
            "/api/v1/short-answers/",
            {"course": self.course.id, "prompt": "Q?", "mark_scheme": "M", "max_score": 3},
            format="json",
        )
        self.assertEqual(res.status_code, 403)
        res = self.as_instructor.post(
            "/api/v1/short-answers/",
            {"course": self.course.id, "prompt": "Q?", "mark_scheme": "M", "max_score": 3},
            format="json",
        )
        self.assertEqual(res.status_code, 201)


class ProctoringTests(TestCase):
    """Webcam-frame logging, the consecutive-violation alert, and the
    instructor timeline."""

    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="proc-instructor@mentormind.dev", password="password123"
        )
        self.instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="proc-student@mentormind.dev", password="password123",
            display_name="Proctored Pat",
        )
        self.course = Course.objects.create(
            title="Maths", slug="proc-maths", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        self.quiz = Quiz.objects.create(course=self.course, title="Final")
        QuizQuestion.objects.create(
            quiz=self.quiz, text="1+1?", options=["1", "2"], correct_option_index=1
        )
        self.as_student = APIClient()
        self.as_student.force_authenticate(user=self.student)
        self.as_instructor = APIClient()
        self.as_instructor.force_authenticate(user=self.instructor)

    def _frame(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile("frame.jpg", b"jpegbytes", content_type="image/jpeg")

    def _post_frame(self, verdict="ok", faces=1):
        from unittest.mock import patch

        with patch(
            "apps.core.ml_client.post_image",
            return_value={"faces": faces, "verdict": verdict, "boxes": []},
        ):
            return self.as_student.post(
                f"/api/v1/quizzes/{self.quiz.id}/proctor-frame/",
                {"image": self._frame()},
                format="multipart",
            )

    def test_frame_is_logged_without_storing_the_image(self):
        from .models import ProctoringLog

        res = self._post_frame()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["verdict"], "ok")
        log = ProctoringLog.objects.get()
        self.assertEqual(log.enrollment, self.enrollment)
        self.assertEqual(log.quiz, self.quiz)
        self.assertFalse(log.is_violation)

    def test_three_consecutive_violations_alert_instructor_once(self):
        from apps.notifications.models import Notification

        for _ in range(2):
            self._post_frame(verdict="no_face", faces=0)
        self.assertEqual(
            Notification.objects.filter(kind=Notification.Kind.PROCTORING).count(), 0
        )
        self._post_frame(verdict="no_face", faces=0)
        alerts = Notification.objects.filter(kind=Notification.Kind.PROCTORING)
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.get().user, self.instructor)
        self.assertIn("Proctored Pat", alerts.get().title)
        # A continuing streak doesn't re-alert
        self._post_frame(verdict="multiple_faces", faces=2)
        self.assertEqual(alerts.count(), 1)

    def test_timeline_is_instructor_only_and_grouped(self):
        self._post_frame()
        self._post_frame(verdict="no_face", faces=0)
        res = self.as_student.get(f"/api/v1/quizzes/{self.quiz.id}/proctoring/")
        self.assertEqual(res.status_code, 403)
        res = self.as_instructor.get(f"/api/v1/quizzes/{self.quiz.id}/proctoring/")
        self.assertEqual(res.status_code, 200)
        sessions = res.json()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["student_email"], self.student.email)
        self.assertEqual(sessions[0]["violations"], 1)
        self.assertEqual(len(sessions[0]["logs"]), 2)

    def test_rejects_missing_or_oversized_image(self):
        res = self.as_student.post(
            f"/api/v1/quizzes/{self.quiz.id}/proctor-frame/", {}, format="multipart"
        )
        self.assertEqual(res.status_code, 400)


class AdaptivePracticeTests(TestCase):
    """Topic stats and the weak-topic recommendation feed."""

    def setUp(self):
        cache.clear()
        Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="ap-instructor@mentormind.dev", password="password123"
        )
        self.student = User.objects.create_user(
            email="ap-student@mentormind.dev", password="password123"
        )
        self.course = Course.objects.create(
            title="Mechanics", slug="ap-mechanics", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        self.quiz = Quiz.objects.create(course=self.course, title="Motion check")
        self.kinematics = QuizQuestion.objects.create(
            quiz=self.quiz, text="v=u+at?", options=["yes", "no"],
            correct_option_index=0, topic="Kinematics",
        )
        self.dynamics = QuizQuestion.objects.create(
            quiz=self.quiz, text="F=ma?", options=["yes", "no"],
            correct_option_index=0, topic="Dynamics", order=1,
        )
        self.as_student = APIClient()
        self.as_student.force_authenticate(user=self.student)

    def _attempt(self, kinematics_correct):
        res = self.as_student.post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {
                "answers": {
                    str(self.kinematics.id): 0 if kinematics_correct else 1,
                    str(self.dynamics.id): 0,
                }
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)

    def test_submit_records_per_question_topic_detail(self):
        self._attempt(kinematics_correct=False)
        attempt = QuizAttempt.objects.get()
        detail = attempt.answers[str(self.kinematics.id)]
        self.assertEqual(detail["topic"], "Kinematics")
        self.assertFalse(detail["correct"])
        self.assertTrue(attempt.answers[str(self.dynamics.id)]["correct"])

    def test_recommendations_surface_weak_topics_first(self):
        # Two attempts: Kinematics 0/2, Dynamics 2/2
        self._attempt(kinematics_correct=False)
        self._attempt(kinematics_correct=False)
        res = self.as_student.get("/api/v1/practice/recommendations/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        topics = [t["topic"] for t in body["topics"]]
        self.assertIn("Kinematics", topics)
        self.assertNotIn("Dynamics", topics)  # 100% accurate — not weak
        self.assertTrue(body["recommended"])
        self.assertEqual(body["recommended"][0]["topic"], "Kinematics")

    def test_no_data_means_empty_feed(self):
        res = self.as_student.get("/api/v1/practice/recommendations/")
        self.assertEqual(res.json(), {"topics": [], "recommended": []})


class ReadinessTests(TestCase):
    """The exam-readiness blend and its two API surfaces."""

    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="rd-instructor@mentormind.dev", password="password123"
        )
        self.instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="rd-student@mentormind.dev", password="password123"
        )
        self.course = Course.objects.create(
            title="Waves", slug="rd-waves", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title="Superposition", content="c",
            order=1, is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )

    def test_fresh_enrollment_scores_zero(self):
        from .readiness import enrollment_readiness

        result = enrollment_readiness(self.enrollment)
        self.assertEqual(result["readiness"], 0.0)

    def test_progress_and_quizzes_raise_the_score(self):
        from .readiness import enrollment_readiness

        self.enrollment.completed_lessons.add(self.lesson)
        quiz = Quiz.objects.create(course=self.course, title="W1")
        QuizAttempt.objects.create(
            enrollment=self.enrollment, quiz=quiz, score=90.0,
            total_questions=2, correct_answers=2,
            answers={"1": {"selected": 0, "correct": True, "topic": ""},
                     "2": {"selected": 1, "correct": True, "topic": ""}},
        )
        result = enrollment_readiness(self.enrollment)
        self.assertGreater(result["readiness"], 60)
        self.assertEqual(result["components"]["progress_pct"], 100.0)
        self.assertEqual(result["components"]["quiz_avg"], 90.0)

    def test_student_and_instructor_endpoints(self):
        as_student = APIClient()
        as_student.force_authenticate(user=self.student)
        res = as_student.get("/api/v1/practice/readiness/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]["course_slug"], "rd-waves")

        # students can't see the roster view
        self.assertEqual(
            as_student.get(f"/api/v1/courses/{self.course.slug}/readiness/").status_code,
            403,
        )
        as_instructor = APIClient()
        as_instructor.force_authenticate(user=self.instructor)
        res = as_instructor.get(f"/api/v1/courses/{self.course.slug}/readiness/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]["student_email"], self.student.email)


class QuizDraftGenerationTests(TestCase):
    """AI quiz drafting — instructor-only, suggestions never auto-saved."""

    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="qg-instructor@mentormind.dev", password="password123"
        )
        self.instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="qg-student@mentormind.dev", password="password123"
        )
        self.course = Course.objects.create(
            title="Optics", slug="qg-optics", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title="Refraction",
            content="Refraction: bending of light between media.",
            order=1, is_published=True,
        )
        self.as_instructor = APIClient()
        self.as_instructor.force_authenticate(user=self.instructor)

    def test_draft_returns_suggestions_without_saving(self):
        from unittest.mock import patch

        generated = {
            "questions": [
                {"text": "Q?", "options": ["a", "b", "c", "d"], "correct_option_index": 1}
            ],
            "engine": "llm",
        }
        with patch("apps.core.ml_client.post_json", return_value=generated):
            res = self.as_instructor.post(
                "/api/v1/quizzes/generate-draft/",
                {"lesson": self.lesson.id},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(len(body["questions"]), 1)
        self.assertEqual(body["engine"], "llm")
        self.assertIn("Refraction", body["suggested_title"])
        self.assertEqual(Quiz.objects.count(), 0)  # nothing persisted

    def test_students_cannot_generate(self):
        as_student = APIClient()
        as_student.force_authenticate(user=self.student)
        res = as_student.post(
            "/api/v1/quizzes/generate-draft/", {"lesson": self.lesson.id}, format="json"
        )
        self.assertEqual(res.status_code, 403)


class PredictedGradeTests(TestCase):
    """Readiness → Cambridge grade band mapping, exposed on both surfaces."""

    def test_band_boundaries(self):
        from .readiness import predicted_grade

        self.assertEqual(predicted_grade(95), "A*")
        self.assertEqual(predicted_grade(87), "A*")
        self.assertEqual(predicted_grade(86.9), "A")
        self.assertEqual(predicted_grade(67), "B")
        self.assertEqual(predicted_grade(57), "C")
        self.assertEqual(predicted_grade(47), "D")
        self.assertEqual(predicted_grade(37), "E")
        self.assertEqual(predicted_grade(36.9), "U")
        self.assertEqual(predicted_grade(0), "U")

    def test_grade_included_in_readiness_payloads(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        instructor = User.objects.create_user(
            email="pg-instructor@mentormind.dev", password="password123"
        )
        instructor.groups.add(group)
        student = User.objects.create_user(
            email="pg-student@mentormind.dev", password="password123"
        )
        course = Course.objects.create(
            title="Forces", slug="pg-forces", description="d",
            instructor=instructor, is_published=True,
        )
        Enrollment.objects.create(student=student, course=course)

        as_student = APIClient()
        as_student.force_authenticate(user=student)
        body = as_student.get("/api/v1/practice/readiness/").json()
        self.assertEqual(body[0]["predicted_grade"], "U")

        as_instructor = APIClient()
        as_instructor.force_authenticate(user=instructor)
        body = as_instructor.get(f"/api/v1/courses/{course.slug}/readiness/").json()
        self.assertIn("predicted_grade", body[0])


class ItemAnalysisTests(TestCase):
    """Per-question difficulty/discrimination for the instructor studio."""

    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="ia-instructor@mentormind.dev", password="password123"
        )
        self.instructor.groups.add(group)
        self.course = Course.objects.create(
            title="Energy", slug="ia-energy", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.quiz = Quiz.objects.create(course=self.course, title="E1")
        self.q1 = QuizQuestion.objects.create(
            quiz=self.quiz, text="Unit of energy?", options=["J", "N", "W"],
            correct_option_index=0, order=1,
        )
        self.q2 = QuizQuestion.objects.create(
            quiz=self.quiz, text="KE formula?", options=["mv", "½mv²", "mgh"],
            correct_option_index=1, order=2,
        )
        self.as_instructor = APIClient()
        self.as_instructor.force_authenticate(user=self.instructor)

        # Four students: strong pair aces both; weak pair misses q2 — q1 is
        # easy for everyone, q2 should discriminate positively.
        for index, (q1_ok, q2_ok) in enumerate(
            [(True, True), (True, True), (True, False), (False, False)]
        ):
            student = User.objects.create_user(
                email=f"ia-student{index}@mentormind.dev", password="password123"
            )
            enrollment = Enrollment.objects.create(student=student, course=self.course)
            correct = int(q1_ok) + int(q2_ok)
            QuizAttempt.objects.create(
                enrollment=enrollment, quiz=self.quiz,
                score=50.0 * correct, total_questions=2, correct_answers=correct,
                answers={
                    str(self.q1.id): {"selected": 0 if q1_ok else 1, "correct": q1_ok, "topic": ""},
                    str(self.q2.id): {"selected": 1 if q2_ok else 0, "correct": q2_ok, "topic": ""},
                },
            )

    def test_difficulty_discrimination_and_distractors(self):
        res = self.as_instructor.get(f"/api/v1/quizzes/{self.quiz.id}/item-analysis/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["attempts"], 4)
        rows = {row["id"]: row for row in body["questions"]}

        easy = rows[self.q1.id]
        self.assertEqual(easy["difficulty"], 0.75)
        hard = rows[self.q2.id]
        self.assertEqual(hard["difficulty"], 0.5)
        # Upper pair (100%) both right, lower pair (one 50%, one 0%) both wrong.
        self.assertEqual(hard["discrimination"], 1.0)
        self.assertEqual(hard["distractors"][1]["picks"], 2)
        self.assertTrue(hard["distractors"][1]["is_correct"])

    def test_flags_mark_problem_questions(self):
        from .item_analysis import quiz_item_analysis

        # Flip q2 so the strong pair misses it and the weak pair gets it:
        # negative discrimination → "review" flag.
        for attempt in QuizAttempt.objects.filter(quiz=self.quiz):
            detail = attempt.answers[str(self.q2.id)]
            detail["correct"] = not detail["correct"]
            attempt.save()
        rows = {row["id"]: row for row in quiz_item_analysis(self.quiz)["questions"]}
        self.assertIn("review", rows[self.q2.id]["flags"])

    def test_instructor_only(self):
        student = User.objects.create_user(
            email="ia-outsider@mentormind.dev", password="password123"
        )
        as_student = APIClient()
        as_student.force_authenticate(user=student)
        res = as_student.get(f"/api/v1/quizzes/{self.quiz.id}/item-analysis/")
        self.assertEqual(res.status_code, 403)


class GradebookExportTests(TestCase):
    """Whole-class CSV export from the instructor studio."""

    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name="Instructors")
        self.instructor = User.objects.create_user(
            email="gb-instructor@mentormind.dev", password="password123"
        )
        self.instructor.groups.add(group)
        self.student = User.objects.create_user(
            email="gb-student@mentormind.dev", password="password123"
        )
        self.course = Course.objects.create(
            title="Atoms", slug="gb-atoms", description="d",
            instructor=self.instructor, is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        self.quiz = Quiz.objects.create(course=self.course, title="A1")
        # Two attempts — the gradebook keeps the best.
        for score in (40.0, 80.0):
            QuizAttempt.objects.create(
                enrollment=self.enrollment, quiz=self.quiz, score=score,
                total_questions=1, correct_answers=int(score > 50),
            )
        self.as_instructor = APIClient()
        self.as_instructor.force_authenticate(user=self.instructor)

    def test_csv_has_best_scores_and_predicted_grade(self):
        res = self.as_instructor.get(f"/api/v1/courses/{self.course.slug}/gradebook/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn("gradebook-gb-atoms.csv", res["Content-Disposition"])
        lines = res.content.decode().strip().splitlines()
        self.assertIn("Quiz: A1 (best %)", lines[0])
        self.assertIn("Predicted grade", lines[0])
        self.assertIn("gb-student@mentormind.dev", lines[1])
        self.assertIn("80.0", lines[1])

    def test_students_and_other_instructors_blocked(self):
        as_student = APIClient()
        as_student.force_authenticate(user=self.student)
        res = as_student.get(f"/api/v1/courses/{self.course.slug}/gradebook/")
        self.assertEqual(res.status_code, 403)

        group = Group.objects.get(name="Instructors")
        rival = User.objects.create_user(
            email="gb-rival@mentormind.dev", password="password123"
        )
        rival.groups.add(group)
        as_rival = APIClient()
        as_rival.force_authenticate(user=rival)
        res = as_rival.get(f"/api/v1/courses/{self.course.slug}/gradebook/")
        self.assertEqual(res.status_code, 403)
