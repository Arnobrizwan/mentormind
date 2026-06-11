"""Quiz generator tests — hermetic: no model load, no network."""

from fastapi.testclient import TestClient

from app import quizgen
from app.main import app

client = TestClient(app)

LESSON = """# Kinematics

Acceleration: the rate of change of velocity with respect to time.
Displacement — the straight-line distance from start to finish in a given direction.
Velocity: the rate of change of displacement with respect to time.
Speed — the distance travelled per unit time, with no direction.
"""


class TestHeuristicQuestions:
    def test_builds_mcqs_from_definitions(self):
        questions = quizgen._heuristic_questions(LESSON, "Kinematics", 10)
        assert len(questions) == 4
        for q in questions:
            assert 2 <= len(q["options"]) <= 4
            assert 0 <= q["correct_option_index"] < len(q["options"])

    def test_correct_option_is_the_real_definition(self):
        questions = quizgen._heuristic_questions(LESSON, "", 10)
        acceleration_q = next(q for q in questions if "Acceleration" in q["text"])
        correct = acceleration_q["options"][acceleration_q["correct_option_index"]]
        assert "rate of change of velocity" in correct

    def test_too_little_material_yields_nothing(self):
        assert quizgen._heuristic_questions("Just prose, no definitions.", "", 5) == []


class TestLlmParse:
    def test_parses_and_validates(self):
        raw = (
            'Here you go:\n[{"text": "Q1", "options": ["a", "b", "c", "d"], '
            '"correct_option_index": 2}, {"text": "bad", "options": ["only one"], '
            '"correct_option_index": 0}]'
        )
        questions = quizgen._parse_llm_questions(raw, 10)
        assert len(questions) == 1
        assert questions[0]["correct_option_index"] == 2

    def test_rejects_out_of_range_index(self):
        raw = '[{"text": "Q", "options": ["a", "b"], "correct_option_index": 5}]'
        assert quizgen._parse_llm_questions(raw, 10) is None


class TestGenerateQuizEndpoint:
    def test_generates_with_heuristic_fallback(self, monkeypatch):
        monkeypatch.delenv("CUSTOM_LLM_URL", raising=False)
        response = client.post(
            "/v1/generate/quiz",
            json={"content": LESSON, "topic": "Kinematics", "count": 3},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["engine"] == "heuristic"
        assert 1 <= len(body["questions"]) <= 3

    def test_uses_llm_when_model_answers(self, monkeypatch):
        monkeypatch.setattr(
            quizgen.local_llm,
            "generate",
            lambda *a, **k: '[{"text": "Define velocity", "options": ["a", "b", "c", "d"], "correct_option_index": 1}]',
        )
        response = client.post(
            "/v1/generate/quiz",
            json={"content": LESSON, "count": 5},
        )
        body = response.json()
        assert body["engine"] == "llm"
        assert body["questions"][0]["text"] == "Define velocity"
