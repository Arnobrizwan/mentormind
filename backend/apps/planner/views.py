from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import builder
from .ics import build_calendar
from .models import StudyPlan


def _serialize(plan):
    return {
        "id": plan.id,
        "week_start": plan.week_start,
        "items": plan.items,
        "completion_pct": plan.completion_pct,
        "generated_at": plan.generated_at,
    }


class WeekPlanView(APIView):
    """This week's plan — built on first access, refreshable on demand."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize(builder.ensure_plan(request.user)))

    def post(self, request):
        """Rebuild this week's plan (keeps done-ticks for surviving titles)."""
        plan = builder.ensure_plan(request.user)
        done_titles = {item["title"] for item in plan.items if item.get("done")}
        plan.items = [
            {**item, "done": item["title"] in done_titles}
            for item in builder.build_items(request.user)
        ]
        plan.save(update_fields=["items", "updated_at"])
        return Response(_serialize(plan))


class ToggleItemView(APIView):
    """Tick/untick one plan item."""

    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        plan = builder.ensure_plan(request.user)
        # Row lock for the read-modify-write on the items JSON — two quick
        # ticks otherwise read the same list and the second save reverts
        # the first. (select_for_update is a no-op on SQLite dev DBs.)
        with transaction.atomic(using="default"):
            plan = (
                StudyPlan.objects.using("default")
                .select_for_update()
                .get(id=plan.id)
            )
            items = list(plan.items)
            for item in items:
                if item.get("id") == item_id:
                    item["done"] = not item.get("done")
                    plan.items = items
                    plan.save(update_fields=["items", "updated_at"])
                    return Response(_serialize(plan))
        return Response(
            {"error": "No such item in this week's plan."},
            status=status.HTTP_404_NOT_FOUND,
        )


class WeekPlanIcsView(APIView):
    """This week's plan as an iCalendar (.ics) download.

    Students import it into Google / Apple / Outlook calendar. Authenticated
    (the SPA fetches it with the JWT and saves the blob) — no public token,
    so a student's plan is never exposed by URL alone.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan = builder.ensure_plan(request.user)
        body = build_calendar(
            plan,
            dtstamp=timezone.now(),
            student_label=getattr(request.user, "display_name", ""),
        )
        filename = f"mentormind-plan-{slugify(str(plan.week_start)) or 'week'}.ics"
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class StudyInsightView(APIView):
    """One-paragraph 'AI insight' for the planner: what to focus on this week,
    from the student's weak topics + due cards (model-written, with a
    deterministic fallback)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .insight import study_insight

        return Response(study_insight(request.user))


class GlobalPlannerRebuildView(APIView):
    """Trigger the Monday-morning sweep for all active students' plans."""
    from apps.core.permissions import IsCronOrInstructor
    permission_classes = [IsCronOrInstructor]

    def post(self, request):
        from .builder import build_weekly_plans as run
        built, escalated = run()
        return Response({
            "detail": f"built {built} plan(s), escalated {escalated} slipping student(s)"
        }, status=status.HTTP_200_OK)
