"""Classical test theory item analysis for a quiz.

Each QuizAttempt stores per-question detail {question_id: {selected,
correct, topic}} — enough to compute, per question:

- difficulty: proportion of responses answered correctly (the p-value;
  HIGH means EASY)
- discrimination: p(upper 27% of attempts) - p(lower 27%), the classic
  upper-lower index — negative means strong students miss the question
  more often than weak ones, which almost always marks a miskeyed or
  ambiguous item
- distractors: how often each option was picked

Attempts (not students) are the analysis unit: retakes are real responses
and the instructor cares how the cohort answered, not who answered.
"""

import math

from .models import QuizAttempt, QuizQuestion

# Below this many attempts the upper/lower split is noise, not signal.
MIN_ATTEMPTS_FOR_DISCRIMINATION = 4

TOO_EASY_P = 0.90
TOO_HARD_P = 0.30


def quiz_item_analysis(quiz):
    """Per-question statistics for one quiz. Returns a dict ready for the
    instructor studio: overall attempt count plus one row per question."""
    questions = list(
        QuizQuestion.objects.using("default").filter(quiz=quiz).order_by("order", "id")
    )
    attempts = list(QuizAttempt.objects.using("default").filter(quiz=quiz))

    # Kelley's classic split: top and bottom 27% of attempts by overall score.
    upper_ids = lower_ids = frozenset()
    if len(attempts) >= MIN_ATTEMPTS_FOR_DISCRIMINATION:
        ranked = sorted(attempts, key=lambda a: a.score, reverse=True)
        k = max(1, math.ceil(len(ranked) * 0.27))
        upper_ids = frozenset(a.pk for a in ranked[:k])
        lower_ids = frozenset(a.pk for a in ranked[-k:])

    rows = []
    for question in questions:
        key = str(question.id)
        options = question.options if isinstance(question.options, list) else []
        picks = [0] * len(options)
        responses = correct = 0
        upper_n = upper_correct = lower_n = lower_correct = 0
        for attempt in attempts:
            detail = (attempt.answers or {}).get(key)
            if not isinstance(detail, dict):
                continue
            responses += 1
            was_correct = bool(detail.get("correct"))
            if was_correct:
                correct += 1
            selected = detail.get("selected")
            if isinstance(selected, int) and 0 <= selected < len(picks):
                picks[selected] += 1
            if attempt.pk in upper_ids:
                upper_n += 1
                upper_correct += was_correct
            if attempt.pk in lower_ids:
                lower_n += 1
                lower_correct += was_correct

        difficulty = round(correct / responses, 2) if responses else None
        discrimination = None
        if upper_n and lower_n:
            discrimination = round(
                upper_correct / upper_n - lower_correct / lower_n, 2
            )

        flags = []
        if difficulty is not None:
            if difficulty >= TOO_EASY_P:
                flags.append("too_easy")
            elif difficulty <= TOO_HARD_P:
                flags.append("too_hard")
        if discrimination is not None and discrimination <= 0:
            flags.append("review")

        rows.append(
            {
                "id": question.id,
                "text": question.text,
                "topic": question.topic,
                "responses": responses,
                "difficulty": difficulty,
                "discrimination": discrimination,
                "distractors": [
                    {
                        "option": option,
                        "picks": picks[index],
                        "is_correct": index == question.correct_option_index,
                    }
                    for index, option in enumerate(options)
                ],
                "flags": flags,
            }
        )

    return {
        "quiz": quiz.id,
        "title": quiz.title,
        "attempts": len(attempts),
        "min_attempts_for_discrimination": MIN_ATTEMPTS_FOR_DISCRIMINATION,
        "questions": rows,
    }
