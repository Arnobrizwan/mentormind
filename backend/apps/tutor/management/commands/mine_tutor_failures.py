"""Weakness mining for the tutor harness (Self-Harness style,
arXiv:2606.09498): cluster the failure signals students already give us —
thumbs-down replies — by subject/level, with the question that triggered
each. The output tells you *where* the tutor fails; feed those topics to
ml-service/scripts/eval_tutor.py before and after any prompt/threshold
change to validate the fix.

    DEBUG=1 python manage.py mine_tutor_failures --days 30
"""

from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tutor.models import TutorMessage


class Command(BaseCommand):
    help = "Cluster thumbs-down tutor replies by subject/level."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--examples", type=int, default=3,
                            help="failing questions shown per cluster")

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=options["days"])
        downvoted = (
            TutorMessage.objects.using("default")
            .filter(
                role=TutorMessage.Role.ASSISTANT,
                feedback=-1,
                created_at__gte=since,
            )
            .select_related("session")
            .order_by("created_at")
        )
        total_assistant = TutorMessage.objects.using("default").filter(
            role=TutorMessage.Role.ASSISTANT, created_at__gte=since
        ).count()

        clusters: dict[tuple, list] = defaultdict(list)
        for message in downvoted:
            session = message.session
            question = (
                TutorMessage.objects.using("default")
                .filter(
                    session=session,
                    role=TutorMessage.Role.USER,
                    created_at__lt=message.created_at,
                )
                .order_by("-created_at")
                .first()
            )
            key = (session.subject or "(no subject)", session.level or "(no level)")
            clusters[key].append(question.content[:120] if question else "(unknown)")

        flagged = sum(len(v) for v in clusters.values())
        rate = 100.0 * flagged / total_assistant if total_assistant else 0.0
        self.stdout.write(
            f"last {options['days']}d: {total_assistant} replies, "
            f"{flagged} thumbs-down ({rate:.1f}%)\n"
        )
        if not clusters:
            self.stdout.write("No flagged replies — nothing to mine.")
            return

        for (subject, level), questions in sorted(
            clusters.items(), key=lambda item: -len(item[1])
        ):
            self.stdout.write(
                self.style.WARNING(f"\n{subject} · {level} — {len(questions)} flagged")
            )
            for question in questions[: options["examples"]]:
                self.stdout.write(f"  · {question}")
        self.stdout.write(
            "\nNext: reproduce these against eval_tutor.py, adjust the "
            "harness, and re-run the gate before shipping."
        )
