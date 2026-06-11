"""Idempotent demo seed — safe to run repeatedly.

    python manage.py seed_demo

Creates demo accounts (password: mentormind123), published courses with
lessons and quizzes, enrollments with progress, gamification activity,
chat history, notifications, a tutor session, and feature flags.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Subscription
from apps.chat.models import ChatMessage
from apps.core.models import (
    Course,
    Enrollment,
    Lesson,
    Quiz,
    QuizAttempt,
    QuizQuestion,
)
from apps.engagement.models import DailyActivity, PointsEvent
from apps.flags.models import FeatureFlag
from apps.notifications.models import Notification
from apps.tutor.models import TutorMessage, TutorSession

User = get_user_model()

PASSWORD = "mentormind123"

COURSES = [
    {
        "slug": "igcse-mathematics-0580",
        "title": "IGCSE Mathematics (0580)",
        "description": "Full syllabus coverage with past-paper practice: number, algebra, geometry, probability and statistics.",
        "lessons": [
            ("Number and the four operations", "Place value, directed numbers, fractions, decimals and percentages with worked past-paper examples."),
            ("Algebraic manipulation", "Expanding, factorising, rearranging formulae and solving linear and quadratic equations."),
            ("Geometry and mensuration", "Angles, similarity, circle theorems, perimeter, area and volume."),
            ("Probability and statistics", "Tree diagrams, relative frequency, averages, cumulative frequency and scatter diagrams."),
        ],
        "quiz": {
            "title": "Algebra checkpoint",
            "questions": [
                ("Solve 3x + 5 = 20.", ["x = 3", "x = 5", "x = 15", "x = 25/3"], 1),
                ("Factorise x² − 9.", ["(x − 3)(x − 3)", "(x + 9)(x − 1)", "(x + 3)(x − 3)", "x(x − 9)"], 2),
                ("Expand (x + 2)(x − 5).", ["x² − 3x − 10", "x² + 3x − 10", "x² − 7x + 10", "x² − 10"], 0),
            ],
        },
    },
    {
        "slug": "igcse-physics-0625",
        "title": "IGCSE Physics (0625)",
        "description": "Forces, energy, waves, electricity and magnetism, taught through mark-scheme-aligned explanations.",
        "lessons": [
            ("Motion, forces and momentum", "Speed-time graphs, resultant forces, Newton's laws and momentum conservation."),
            ("Energy, work and power", "Energy stores and transfers, efficiency, work done and power calculations."),
            ("Waves and optics", "Wave properties, reflection, refraction, lenses and the electromagnetic spectrum."),
            ("Electricity and magnetism", "Circuits, Ohm's law, electromagnetic induction and transformers."),
        ],
        "quiz": {
            "title": "Forces and motion checkpoint",
            "questions": [
                ("A 2 kg mass accelerates at 3 m/s². What resultant force acts on it?", ["1.5 N", "5 N", "6 N", "12 N"], 2),
                ("Which quantity is a vector?", ["Speed", "Distance", "Velocity", "Energy"], 2),
                ("The gradient of a distance-time graph gives…", ["acceleration", "speed", "force", "momentum"], 1),
            ],
        },
    },
    {
        "slug": "igcse-computer-science-0478",
        "title": "IGCSE Computer Science (0478)",
        "description": "Computational thinking, algorithms, programming, data representation and computer systems.",
        "lessons": [
            ("Data representation", "Binary, hexadecimal, two's complement, text, images and sound."),
            ("Algorithms and pseudocode", "Flowcharts, trace tables, searching and sorting algorithms."),
            ("Programming concepts", "Variables, selection, iteration, procedures, functions and arrays."),
            ("Computer systems and networks", "CPU architecture, storage, operating systems and network protocols."),
        ],
        "quiz": {
            "title": "Data representation checkpoint",
            "questions": [
                ("What is binary 1011 in denary?", ["9", "11", "13", "15"], 1),
                ("How many bits are in one byte?", ["4", "8", "16", "32"], 1),
                ("Hexadecimal 1F equals which denary value?", ["15", "21", "31", "47"], 2),
            ],
        },
    },
]

STUDENTS = [
    ("student@mentormind.dev", "Aisha Rahman"),
    ("liam@mentormind.dev", "Liam Chen"),
    ("fatima@mentormind.dev", "Fatima Noor"),
    ("daniel@mentormind.dev", "Daniel Okafor"),
]

FLAGS = [
    ("chat", True, "Live course chat rooms"),
    ("recommendations", True, "ML course recommendations"),
    ("proctoring", False, "Quiz proctoring module"),
    ("payments", True, "Premium subscription flow"),
]


class Command(BaseCommand):
    help = "Seed the database with demo users, courses, progress and activity."

    def handle(self, *args, **options):
        now = timezone.now()

        admin = self._user("admin@mentormind.dev", "Admin", is_staff=True, is_superuser=True)
        instructor = self._user("instructor@mentormind.dev", "Sarah Lim", is_staff=True)
        students = [self._user(email, name) for email, name in STUDENTS]

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

        courses = []
        for spec in COURSES:
            course, _ = Course.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "description": spec["description"],
                    "instructor": instructor,
                    "is_published": True,
                },
            )
            lessons = []
            for order, (title, content) in enumerate(spec["lessons"], start=1):
                lesson, _ = Lesson.objects.update_or_create(
                    course=course,
                    order=order,
                    defaults={"title": title, "content": content, "is_published": True},
                )
                lessons.append(lesson)

            quiz, _ = Quiz.objects.update_or_create(
                course=course,
                title=spec["quiz"]["title"],
                defaults={"description": f"Checkpoint quiz for {course.title}.", "lesson": lessons[1]},
            )
            for order, (text, options, correct) in enumerate(spec["quiz"]["questions"], start=1):
                QuizQuestion.objects.update_or_create(
                    quiz=quiz,
                    order=order,
                    defaults={"text": text, "options": options, "correct_option_index": correct},
                )
            courses.append((course, lessons, quiz))

        # Every student takes the first course; spread the rest around so
        # dashboards, leaderboards and recommendations have variety.
        for i, student in enumerate(students):
            enrolled = [courses[0], courses[1 + i % 2]]
            for course, lessons, quiz in enrolled:
                enrollment, _ = Enrollment.objects.get_or_create(student=student, course=course)
                done = lessons[: 1 + i]  # 1-4 lessons completed per student
                enrollment.completed_lessons.set(done)

                if not QuizAttempt.objects.filter(enrollment=enrollment, quiz=quiz).exists():
                    total = quiz.questions.count()
                    correct = max(1, total - i % 3)
                    QuizAttempt.objects.create(
                        enrollment=enrollment,
                        quiz=quiz,
                        score=round(100.0 * correct / total, 1),
                        total_questions=total,
                        correct_answers=correct,
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
                title=f"Welcome to {courses[0][0].title}!",
                defaults={
                    "body": "Your enrollment is confirmed — jump into lesson 1 whenever you're ready.",
                    "link": f"/courses/{courses[0][0].slug}",
                },
            )

        maths = courses[0][0]
        chat_lines = [
            (students[0], "Anyone else stuck on question 7 from the 2019 paper?"),
            (students[1], "Yes! The circle theorem one — you need the alternate segment theorem."),
            (instructor, "Good discussion — I've pinned a worked solution in lesson 3."),
            (students[0], "That makes sense now, thank you!"),
        ]
        if not ChatMessage.objects.filter(course=maths).exists():
            for sender, body in chat_lines:
                ChatMessage.objects.create(course=maths, sender=sender, body=body)

        session, created = TutorSession.objects.get_or_create(
            user=students[0],
            subject="Mathematics",
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

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {User.objects.count()} users, {Course.objects.count()} courses, "
            f"{Lesson.objects.count()} lessons, {Quiz.objects.count()} quizzes, "
            f"{Enrollment.objects.count()} enrollments, {ChatMessage.objects.count()} chat messages. "
            f"Logins: admin@mentormind.dev / instructor@mentormind.dev / student@mentormind.dev "
            f"(password: {PASSWORD})"
        ))

    def _user(self, email, display_name, **flags):
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(email=email, password=PASSWORD, display_name=display_name, **flags)
        return user
