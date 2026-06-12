# Course content library

Real, syllabus-aligned IGCSE course content consumed by `seed_demo`.
One module per subject, each exporting a single `COURSE` dict:

```python
COURSE = {
    "slug": "igcse-physics-0625",
    "title": "IGCSE Physics (0625)",
    "description": "...",                      # 1-2 sentences
    "lessons": [
        ("Lesson title", "Markdown content"),  # real teaching material
        ...
    ],
    "quizzes": [
        {
            "title": "…",
            "lesson_index": 1,                 # 0-based into lessons, or None
            "questions": [
                ("Question text", ["opt A", "opt B", "opt C", "opt D"], 2, "Topic"),
                # (text, options, correct_option_index, syllabus topic)
            ],
        },
    ],
    "short_answers": [
        {
            "prompt": "…",
            "mark_scheme": "- one criterion per line\n- …",
            "topic": "…",
            "max_score": 3,
        },
    ],
    "flashcards": [
        ("Front (question/cue)", "Back (precise answer)", "Topic"),
    ],
}
```

Content rules: original wording (no copyrighted past-paper text), correct at
IGCSE level, lessons in Markdown with headings/worked examples/common
pitfalls, quiz distractors plausible (typical student errors), mark schemes
one criterion per line (the grader scores per line).
