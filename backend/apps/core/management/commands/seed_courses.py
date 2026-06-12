"""Load the real IGCSE course library into the database. Idempotent.

    python manage.py seed_courses [--instructor email]

Imports every course module in course_content/ (full lessons, topic-tagged
quizzes, mark-scheme short answers, flashcards) and publishes them under
the given instructor (default: the first staff user, created as
instructor@mentormind.dev if none exists).

This seeds CONTENT ONLY — no fake students, activity, or analytics. Use
seed_demo for a fully populated public demo on top of this.
"""

import importlib
import pkgutil

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Course, Lesson, Quiz, QuizQuestion, ShortAnswerQuestion
from apps.revision.models import Flashcard

from . import course_content

User = get_user_model()


def load_course_specs():
    """Every COURSE dict defined by a module in course_content/."""
    specs = []
    for module_info in pkgutil.iter_modules(course_content.__path__):
        module = importlib.import_module(
            f"{course_content.__name__}.{module_info.name}"
        )
        spec = getattr(module, "COURSE", None)
        if isinstance(spec, dict):
            specs.append(spec)
    return sorted(specs, key=lambda item: item["slug"])


class Command(BaseCommand):
    help = "Publish the real course library (content only, no demo users)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--instructor",
            help="Email of the instructor to own the courses "
            "(default: first staff user).",
        )

    def handle(self, *args, **options):
        if options["instructor"]:
            instructor = User.objects.filter(email=options["instructor"]).first()
            if instructor is None:
                raise CommandError(f"No user with email {options['instructor']}")
        else:
            instructor = User.objects.filter(is_staff=True).order_by("id").first()
            if instructor is None:
                instructor = User.objects.create_user(
                    email="instructor@mentormind.dev",
                    password="mentormind123",
                    display_name="Sarah Lim",
                    is_staff=True,
                )
                self.stdout.write("Created instructor@mentormind.dev (password: mentormind123)")

        specs = load_course_specs()
        if not specs:
            raise CommandError("course_content/ has no COURSE modules.")

        for spec in specs:
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

            for quiz_spec in spec.get("quizzes", []):
                lesson_index = quiz_spec.get("lesson_index")
                quiz, _ = Quiz.objects.update_or_create(
                    course=course,
                    title=quiz_spec["title"],
                    defaults={
                        "description": f"Checkpoint quiz for {course.title}.",
                        "lesson": lessons[lesson_index]
                        if lesson_index is not None and lesson_index < len(lessons)
                        else None,
                    },
                )
                for order, (text, options, correct, topic) in enumerate(
                    quiz_spec["questions"], start=1
                ):
                    QuizQuestion.objects.update_or_create(
                        quiz=quiz,
                        order=order,
                        defaults={
                            "text": text,
                            "options": options,
                            "correct_option_index": correct,
                            "topic": topic,
                        },
                    )

            for order, sa in enumerate(spec.get("short_answers", []), start=1):
                ShortAnswerQuestion.objects.update_or_create(
                    course=course,
                    order=order,
                    defaults={
                        "prompt": sa["prompt"],
                        "mark_scheme": sa["mark_scheme"],
                        "topic": sa["topic"],
                        "max_score": sa["max_score"],
                        "is_published": True,
                    },
                )

            for front, back, topic in spec.get("flashcards", []):
                Flashcard.objects.update_or_create(
                    course=course,
                    front=front,
                    defaults={
                        "back": back,
                        "topic": topic,
                        "source": Flashcard.Source.INSTRUCTOR,
                        "is_published": True,
                    },
                )
            self.stdout.write(
                f"  {course.title}: {len(lessons)} lessons, "
                f"{course.quizzes.count()} quizzes, "
                f"{course.short_answer_questions.count()} short answers, "
                f"{course.flashcards.count()} flashcards"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Published {len(specs)} course(s) under {instructor.email}."
        ))
