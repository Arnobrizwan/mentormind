from celery import shared_task


@shared_task
def build_weekly_plans():
    """Monday-morning sweep (Celery beat): build every active student's
    weekly study plan, nudge them, and escalate slipping streaks to
    remediation tickets."""
    from .builder import build_weekly_plans as run

    built, escalated = run()
    return f"built {built} plan(s), escalated {escalated} slipping student(s)"
