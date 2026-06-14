"""Public-demo seed — safe to run repeatedly.

    python manage.py seed_demo

Two layers:
1. `seed_courses` — the REAL course library (course_content/: full lessons,
   topic-tagged quizzes, mark-scheme short answers, flashcards). Nothing
   demo about it; production installs run it alone.
2. Demo accounts + explorable activity (password: mentormind123) so the
   hosted demo's dashboards, analytics and AI features have something to
   show. All activity is derived from the real content — no hardcoded
   course/question data lives in this file.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Subscription
from apps.chat.models import ChatMessage
from apps.core.models import (
    Course,
    Enrollment,
    ProctoringLog,
    QuizAttempt,
    ShortAnswerQuestion,
    ShortAnswerSubmission,
)
from apps.engagement.models import DailyActivity, PointsEvent, RemediationTicket
from apps.flags.models import FeatureFlag
from apps.notifications.models import Notification
from apps.revision.models import Flashcard, ReviewCard
from apps.tutor.models import TutorMessage, TutorSession

User = get_user_model()

PASSWORD = "mentormind123"

STUDENTS = [
    ("student@mentormind.dev", "Aisha Rahman"),
    ("liam@mentormind.dev", "Liam Chen"),
    ("fatima@mentormind.dev", "Fatima Noor"),
    ("daniel@mentormind.dev", "Daniel Okafor"),
]

FLAGS = [
    ("chat", True, "Live course chat rooms"),
    ("recommendations", True, "ML course recommendations"),
    ("proctoring", True, "Quiz proctoring module"),
    ("payments", True, "Premium subscription flow"),
    ("ai_tutor", True, "AI tutor"),
    ("short_answer_grading", True, "LLM rubric grading"),
    ("flashcard_generation", True, "AI flashcard drafting"),
    ("quiz_generation", True, "AI quiz drafting"),
    ("omr_grading", True, "Bubble-sheet OMR grading"),
]


class Command(BaseCommand):
    help = "Seed the real course library plus demo accounts and activity."

    def handle(self, *args, **options):
        now = timezone.now()

        self._user("admin@mentormind.dev", "Admin", is_staff=True, is_superuser=True)
        instructor = self._user("instructor@mentormind.dev", "Sarah Lim", is_staff=True)
        students = [self._user(email, name) for email, name in STUDENTS]

        # Layer 1: the real content library.
        call_command("seed_courses", instructor=instructor.email)
        courses = list(Course.objects.filter(is_published=True).order_by("id"))

        Subscription.objects.update_or_create(
            user=students[0],
            defaults={
                "plan": Subscription.Plan.YEARLY,
                "is_active": True,
                "expires_at": now + timedelta(days=365),
            },
        )
        for key, enabled, description in FLAGS:
            FeatureFlag.objects.update_or_create(
                key=key, defaults={"enabled": enabled, "description": description}
            )

        # Layer 2: explorable activity derived from the real content.
        spread = max(1, len(courses) - 1)
        for i, student in enumerate(students):
            enrolled = [courses[0], courses[1 + i % spread]] if len(courses) > 1 else courses[:1]
            for course in enrolled:
                enrollment, _ = Enrollment.objects.get_or_create(
                    student=student, course=course
                )
                lessons = list(course.lessons.order_by("order"))
                done = lessons[: 1 + i]
                enrollment.completed_lessons.set(done)

                quiz = course.quizzes.order_by("id").first()
                if quiz and not QuizAttempt.objects.filter(
                    enrollment=enrollment, quiz=quiz
                ).exists():
                    questions = list(quiz.questions.all())
                    total = len(questions)
                    if total:
                        correct = max(1, total - 1 - i % 3)
                        detail = {}
                        for position, question in enumerate(questions):
                            got_it = position < correct
                            detail[str(question.id)] = {
                                "selected": question.correct_option_index
                                if got_it
                                else (question.correct_option_index + 1)
                                % len(question.options),
                                "correct": got_it,
                                "topic": question.topic,
                            }
                        QuizAttempt.objects.create(
                            enrollment=enrollment,
                            quiz=quiz,
                            score=round(100.0 * correct / total, 1),
                            total_questions=total,
                            correct_answers=correct,
                            answers=detail,
                        )

                for lesson in done:
                    if not PointsEvent.objects.filter(
                        user=student, action=f"lesson:{lesson.id}"
                    ).exists():
                        PointsEvent.objects.create(
                            user=student, action=f"lesson:{lesson.id}", points=10
                        )

            for day in range(4 - i % 3):  # varied streaks
                DailyActivity.objects.get_or_create(
                    user=student, date=(now - timedelta(days=day)).date()
                )

            Notification.objects.get_or_create(
                user=student,
                kind=Notification.Kind.ENROLLMENT,
                title=f"Welcome to {courses[0].title}!",
                defaults={
                    "body": "Your enrollment is confirmed — jump into lesson 1 "
                    "whenever you're ready.",
                    "link": f"/courses/{courses[0].slug}",
                },
            )

        # Richer showcase: the demo account (students[0]) is enrolled in every
        # course with ~2/3 of lessons complete and a quiz attempt per quiz, so
        # the dashboard reads as an active learner instead of a near-empty page.
        demo = students[0]
        for course in courses:
            enr, _ = Enrollment.objects.get_or_create(student=demo, course=course)
            lessons = list(course.lessons.order_by("order"))
            done = lessons[: max(1, (len(lessons) * 2) // 3)]
            enr.completed_lessons.set(done)
            for lesson in done:
                PointsEvent.objects.get_or_create(
                    user=demo, action=f"lesson:{lesson.id}", defaults={"points": 10}
                )
            for quiz in course.quizzes.order_by("id"):
                if QuizAttempt.objects.filter(enrollment=enr, quiz=quiz).exists():
                    continue
                questions = list(quiz.questions.all())
                total = len(questions)
                if not total:
                    continue
                correct = max(1, total - 1)
                detail = {
                    str(q.id): {
                        "selected": q.correct_option_index
                        if pos < correct
                        else (q.correct_option_index + 1) % len(q.options),
                        "correct": pos < correct,
                        "topic": q.topic,
                    }
                    for pos, q in enumerate(questions)
                }
                QuizAttempt.objects.create(
                    enrollment=enr,
                    quiz=quiz,
                    score=round(100.0 * correct / total, 1),
                    total_questions=total,
                    correct_answers=correct,
                    answers=detail,
                )

        first_course = courses[0]
        if not ChatMessage.objects.filter(course=first_course).exists():
            chat_lines = [
                (students[0], "Anyone else finding lesson 2 tricky? The worked example helped a lot."),
                (students[1], "Same here — re-do the second example yourself before the quiz."),
                (instructor, "Good advice. I've added an extra practice question to the short answers."),
                (students[0], "Thank you, attempting it now!"),
            ]
            for sender, body in chat_lines:
                ChatMessage.objects.create(course=first_course, sender=sender, body=body)

        session, created = TutorSession.objects.get_or_create(
            user=students[0],
            subject="Math",
            level="IGCSE",
            defaults={"title": "Solving simultaneous equations"},
        )
        if created:
            TutorMessage.objects.create(
                session=session,
                role=TutorMessage.Role.USER,
                content="How do I solve 2x + y = 7 and x − y = 2?",
            )
            TutorMessage.objects.create(
                session=session,
                role=TutorMessage.Role.ASSISTANT,
                content=(
                    "Add the two equations to eliminate y: (2x + y) + (x − y) = 7 + 2, "
                    "so 3x = 9 and x = 3. Substitute back: 3 − y = 2, so y = 1. "
                    "Always check in both equations: 2(3) + 1 = 7 ✓ and 3 − 1 = 2 ✓."
                ),
            )
            PointsEvent.objects.create(user=students[0], action="tutor_question", points=5)

        # ---- AI assessment & intervention showcases, from real content ----
        showcase = (
            Enrollment.objects.filter(student=students[0])
            .select_related("course")
            .order_by("id")
            .last()
        )
        if showcase:
            course = showcase.course
            question = (
                ShortAnswerQuestion.objects.filter(course=course, is_published=True)
                .order_by("order")
                .first()
            )
            if question and not question.submissions.exists():
                criteria = [
                    line.lstrip("- ").strip()
                    for line in question.mark_scheme.splitlines()
                    if line.strip()
                ]
                ShortAnswerSubmission.objects.create(
                    question=question,
                    enrollment=showcase,
                    answer_text="(Demo account's graded attempt — try submitting "
                    "your own answer to see live AI grading.)",
                    score=max(1, question.max_score - 1),
                    max_score=question.max_score,
                    criteria_met=criteria[:-1] if len(criteria) > 1 else criteria,
                    criteria_missing=criteria[-1:] if len(criteria) > 1 else [],
                    feedback="Strong attempt — review the final criterion and "
                    "resubmit for full marks.",
                    engine=ShortAnswerSubmission.Engine.LLM,
                )

            for flashcard in Flashcard.objects.filter(course=course, is_published=True):
                ReviewCard.objects.get_or_create(
                    user=students[0],
                    flashcard=flashcard,
                    defaults={"due_at": now - timedelta(hours=2)},
                )

            quiz = course.quizzes.order_by("id").first()
            if quiz and not ProctoringLog.objects.filter(
                quiz=quiz, enrollment=showcase
            ).exists():
                verdicts = ["ok", "ok", "no_face", "no_face", "ok", "multiple_faces", "ok"]
                for verdict in verdicts:
                    ProctoringLog.objects.create(
                        enrollment=showcase,
                        quiz=quiz,
                        faces=0
                        if verdict == "no_face"
                        else (2 if verdict == "multiple_faces" else 1),
                        verdict=verdict,
                    )

        if not RemediationTicket.objects.filter(student=students[3]).exists():
            RemediationTicket.objects.create(
                student=students[3],
                risk=RemediationTicket.Risk.HIGH,
                probability=0.82,
                features={
                    "progress_pct": 12.5,
                    "days_since_last_login": 16.0,
                    "quiz_avg": 41.0,
                    "lessons_per_week": 0.4,
                    "chat_messages": 1.0,
                },
            )

        from apps.core.models import Lesson, Quiz

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {User.objects.count()} users, {Course.objects.count()} courses, "
            f"{Lesson.objects.count()} lessons, {Quiz.objects.count()} quizzes, "
            f"{ShortAnswerQuestion.objects.count()} short answers, "
            f"{Flashcard.objects.count()} flashcards, "
            f"{Enrollment.objects.count()} enrollments. "
            f"Logins: admin@mentormind.dev / instructor@mentormind.dev / "
            f"student@mentormind.dev (password: {PASSWORD})"
        ))

    def _user(self, email, display_name, **flags):
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email, password=PASSWORD, display_name=display_name, **flags
            )
        return user
