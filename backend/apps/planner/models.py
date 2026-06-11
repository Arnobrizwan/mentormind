"""Weekly study plans — the agentic layer that turns analytics into a
concrete to-do list, built by Celery beat every Monday (or on demand the
first time a student opens the planner that week)."""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class StudyPlan(models.Model):
    """One student's plan for one ISO week. Items are a JSON list of
    {id, kind, title, detail, link, done} — kinds: revision, practice,
    lesson, quiz."""

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="study_plans"
    )
    week_start = models.DateField(help_text="Monday of the plan's week.")
    items = models.JSONField(default=list)
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "week_start")
        ordering = ["-week_start"]

    @property
    def completion_pct(self):
        if not self.items:
            return 0.0
        done = sum(1 for item in self.items if item.get("done"))
        return round(100.0 * done / len(self.items), 1)

    def __str__(self):
        return f"{self.student.email} · week of {self.week_start}"
