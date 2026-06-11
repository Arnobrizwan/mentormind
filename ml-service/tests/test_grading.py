"""Short-answer grader tests — hermetic: no model load, no network."""

from fastapi.testclient import TestClient

from app import grading
from app.main import app

client = TestClient(app)

MARK_SCHEME = """- States the definition of acceleration as rate of change of velocity
- Uses a = (v - u) / t with correct values
- Gives 2.5 with SI units m/s^2
"""


class TestHeuristicGrade:
    def test_full_marks_when_all_criteria_covered(self):
        answer = (
            "Acceleration is the rate of change of velocity. "
            "Using a = (v - u) / t = (20 - 0) / 8 with the given values, "
            "the answer is 2.5 m/s^2 in SI units."
        )
        result = grading._heuristic_grade(answer, MARK_SCHEME, 5)
        assert result["engine"] == "heuristic"
        assert result["score"] == 5
        assert result["criteria_missing"] == []

    def test_partial_marks_for_partial_answer(self):
        answer = "Acceleration is the rate of change of velocity."
        result = grading._heuristic_grade(answer, MARK_SCHEME, 6)
        assert 0 < result["score"] < 6
        assert result["criteria_missing"]
        assert "mark scheme also expects" in result["feedback"]

    def test_zero_for_unrelated_answer(self):
        result = grading._heuristic_grade("Mitochondria make energy.", MARK_SCHEME, 5)
        assert result["score"] == 0

    def test_prose_scheme_falls_back_to_sentences(self):
        criteria = grading._criteria_lines(
            "States the definition. Uses the formula correctly; gives units."
        )
        assert len(criteria) == 3


class TestLlmParse:
    def test_parses_json_with_prose_around_it(self):
        raw = (
            'Here is the grade:\n{"score": 4, "criteria_met": ["a"], '
            '"criteria_missing": ["b"], "feedback": "Good."}\nThanks!'
        )
        parsed = grading._parse_llm_grade(raw, 5)
        assert parsed == {
            "score": 4,
            "max_score": 5,
            "criteria_met": ["a"],
            "criteria_missing": ["b"],
            "feedback": "Good.",
            "engine": "llm",
        }

    def test_clamps_out_of_range_score(self):
        raw = '{"score": 99, "criteria_met": [], "criteria_missing": [], "feedback": ""}'
        assert grading._parse_llm_grade(raw, 5)["score"] == 5

    def test_rejects_malformed_replies(self):
        assert grading._parse_llm_grade("no json here", 5) is None
        assert grading._parse_llm_grade('{"score": "lots"}', 5) is None
        assert grading._parse_llm_grade('{"score": 3}', 5) is None  # missing lists


class TestGradeEndpoint:
    def test_grades_via_endpoint_with_heuristic_fallback(self, monkeypatch):
        monkeypatch.delenv("CUSTOM_LLM_URL", raising=False)
        response = client.post(
            "/v1/grade/short-answer",
            json={
                "question": "Define acceleration and calculate it for 0 to 20 m/s in 8 s.",
                "student_answer": "Acceleration is the rate of change of velocity. a = 20/8 = 2.5 m/s^2 (SI units).",
                "mark_scheme": MARK_SCHEME,
                "max_score": 5,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["max_score"] == 5
        assert body["engine"] == "heuristic"
        assert isinstance(body["criteria_met"], list)
        assert isinstance(body["criteria_missing"], list)
        assert body["score"] >= 1

    def test_uses_llm_result_when_model_answers(self, monkeypatch):
        monkeypatch.setattr(
            grading.local_llm,
            "generate",
            lambda *a, **k: '{"score": 3, "criteria_met": ["x"], "criteria_missing": ["y"], "feedback": "Show working."}',
        )
        response = client.post(
            "/v1/grade/short-answer",
            json={
                "question": "Q",
                "student_answer": "A",
                "mark_scheme": "M",
                "max_score": 5,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["engine"] == "llm"
        assert body["score"] == 3
        assert body["feedback"] == "Show working."

    def test_rejects_blank_answer(self):
        response = client.post(
            "/v1/grade/short-answer",
            json={
                "question": "Q",
                "student_answer": "   ",
                "mark_scheme": "M",
                "max_score": 5,
            },
        )
        assert response.status_code in (400, 422)


class TestReviewFixes:
    """Regressions from the adversarial review."""

    def test_second_json_object_after_payload_still_parses(self):
        raw = (
            '{"score": 3, "criteria_met": [], "criteria_missing": [], '
            '"feedback": "ok"} P.S. {"note": "ignore me"}'
        )
        parsed = grading._parse_llm_grade(raw, 5)
        assert parsed is not None and parsed["score"] == 3

    def test_braces_in_prose_before_payload_are_skipped(self):
        raw = '{not json} then the real one: {"score": 2, "criteria_met": [], "criteria_missing": [], "feedback": ""}'
        parsed = grading._parse_llm_grade(raw, 5)
        assert parsed is not None and parsed["score"] == 2

    def test_long_thorough_answer_is_not_penalized(self):
        # Criterion recall must not shrink as the answer grows (the old
        # cosine normalized by answer length and failed thorough answers).
        long_answer = (
            "First, recall that acceleration is defined as the rate of change "
            "of velocity with respect to time. We are told the car starts from "
            "rest, so the initial velocity u is zero, and reaches a final "
            "velocity v of twenty metres per second after a time t of eight "
            "seconds. Using a = (v - u) / t with the correct values gives "
            "(20 - 0) / 8, and so the answer is 2.5 m/s^2 in SI units, which "
            "is a sensible magnitude for a road car accelerating briskly."
        )
        result = grading._heuristic_grade(long_answer, MARK_SCHEME, 5)
        assert result["score"] == 5
        assert result["criteria_missing"] == []
