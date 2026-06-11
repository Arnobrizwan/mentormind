"""SM-2 spaced-repetition scheduling (SuperMemo-2, Anki's ancestor).

Grades are 0–5; below 3 the card lapses and comes back in minutes,
3+ grows the interval by the ease factor. Pure function of the card's
state so it's trivially testable.
"""

from datetime import timedelta

from django.utils import timezone

MIN_EASE = 1.3
# A lapsed card returns within the same study session.
LAPSE_RETRY = timedelta(minutes=10)


def review(card, grade):
    """Apply one review with `grade` (0-5) to a ReviewCard, in place.
    Caller saves. Returns the card for chaining."""
    grade = max(0, min(5, int(grade)))

    if grade < 3:
        card.repetitions = 0
        card.interval_days = 0
        due = timezone.now() + LAPSE_RETRY
    else:
        if card.repetitions == 0:
            card.interval_days = 1
        elif card.repetitions == 1:
            card.interval_days = 6
        else:
            card.interval_days = round(card.interval_days * card.ease_factor, 1)
        card.repetitions += 1
        due = timezone.now() + timedelta(days=card.interval_days)

    card.ease_factor = max(
        MIN_EASE,
        card.ease_factor + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02),
    )
    card.due_at = due
    card.last_grade = grade
    card.reviews_count += 1
    return card
