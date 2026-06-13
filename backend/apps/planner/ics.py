"""Minimal RFC 5545 iCalendar emitter — stdlib only, no dependency.

Turns a week's StudyPlan items into all-day VEVENTs so a student can import
(or subscribe to) their plan in Google / Apple / Outlook calendar. Each item
becomes an all-day event spread across the plan week (Mon-Sun, cycling), with
a stable UID so re-imports update rather than duplicate.
"""

from datetime import timedelta

# iCalendar requires CRLF line endings.
_CRLF = "\r\n"


def _escape(text):
    """Escape a TEXT value per RFC 5545 §3.3.11."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line):
    """Fold lines longer than 75 octets (RFC 5545 §3.1)."""
    if len(line) <= 75:
        return line
    chunks = [line[:75]]
    rest = line[75:]
    while rest:
        chunks.append(" " + rest[:74])  # leading space = continuation
        rest = rest[74:]
    return _CRLF.join(chunks)


def build_calendar(plan, *, dtstamp, student_label=""):
    """Render a StudyPlan as an iCalendar document string.

    `dtstamp` is a timezone-aware datetime (DTSTAMP for every event); passed
    in so the caller controls the clock and the output is testable.
    """
    stamp = dtstamp.strftime("%Y%m%dT%H%M%SZ")
    name = f"MentorMind plan — week of {plan.week_start:%d %b %Y}"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MentorMind//Study Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
    ]

    items = plan.items or []
    for index, item in enumerate(items):
        # Spread items across the seven days of the plan week.
        day = plan.week_start + timedelta(days=index % 7)
        nxt = day + timedelta(days=1)
        title = item.get("title", "Study task")
        kind = item.get("kind", "task")
        detail = item.get("detail", "")
        status = "COMPLETED" if item.get("done") else "NEEDS-ACTION"
        uid = f"plan-{plan.id}-item-{item.get('id', index)}@mentormind"

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            # VALUE=DATE => all-day event.
            f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{nxt:%Y%m%d}",
            _fold(f"SUMMARY:{_escape(f'[{kind}] {title}')}"),
            _fold(f"DESCRIPTION:{_escape(detail)}"),
            f"CATEGORIES:{_escape(kind.upper())}",
            f"X-MENTORMIND-STATUS:{status}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return _CRLF.join(_fold(line) for line in lines) + _CRLF
