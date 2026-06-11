"""Flashcard generator tests — hermetic: no model load, no network."""

from fastapi.testclient import TestClient

from app import flashcards
from app.main import app

client = TestClient(app)

LESSON = """# Kinematics

Acceleration: the rate of change of velocity with respect to time.
Displacement — the straight-line distance from start to finish in a given direction.

A body moving with uniform acceleration obeys the equation v = u + at, where u is the
initial velocity and t is the elapsed time. The area under a velocity-time graph gives
the displacement of the body during that interval.
"""


class TestHeuristicCards:
    def test_mines_definition_lines(self):
        cards = flashcards._heuristic_cards(LESSON, "Kinematics", 10)
        fronts = [c["front"] for c in cards]
        self.assert_has_definition(fronts, "Acceleration")
        self.assert_has_definition(fronts, "Displacement")

    def assert_has_definition(self, fronts, term):
        assert any(term in f for f in fronts), f"no card for {term}: {fronts}"

    def test_caps_at_requested_count(self):
        cards = flashcards._heuristic_cards(LESSON, "Kinematics", 2)
        assert len(cards) == 2

    def test_every_card_has_both_sides(self):
        for card in flashcards._heuristic_cards(LESSON, "", 10):
            assert card["front"] and card["back"]


class TestLlmParse:
    def test_parses_array_with_prose_around_it(self):
        raw = 'Sure!\n[{"front": "Q1", "back": "A1"}, {"front": "Q2", "back": "A2"}]\nDone.'
        cards = flashcards._parse_llm_cards(raw, 10)
        assert cards == [
            {"front": "Q1", "back": "A1"},
            {"front": "Q2", "back": "A2"},
        ]

    def test_drops_malformed_entries_and_respects_count(self):
        raw = '[{"front": "Q1", "back": "A1"}, {"front": ""}, "junk", {"front": "Q2", "back": "A2"}]'
        cards = flashcards._parse_llm_cards(raw, 1)
        assert cards == [{"front": "Q1", "back": "A1"}]

    def test_rejects_non_json(self):
        assert flashcards._parse_llm_cards("no array here", 5) is None
        assert flashcards._parse_llm_cards('{"front": "x"}', 5) is None


class TestGenerateEndpoint:
    def test_generates_with_heuristic_fallback(self, monkeypatch):
        monkeypatch.delenv("CUSTOM_LLM_URL", raising=False)
        response = client.post(
            "/v1/generate/flashcards",
            json={"content": LESSON, "topic": "Kinematics", "count": 5},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["engine"] == "heuristic"
        assert 1 <= len(body["cards"]) <= 5
        assert all(c["front"] and c["back"] for c in body["cards"])

    def test_uses_llm_when_model_answers(self, monkeypatch):
        monkeypatch.setattr(
            flashcards.local_llm,
            "generate",
            lambda *a, **k: '[{"front": "Define acceleration", "back": "Rate of change of velocity"}]',
        )
        response = client.post(
            "/v1/generate/flashcards",
            json={"content": LESSON, "topic": "Kinematics", "count": 5},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["engine"] == "llm"
        assert body["cards"][0]["front"] == "Define acceleration"

    def test_rejects_blank_content(self):
        response = client.post(
            "/v1/generate/flashcards", json={"content": "   ", "count": 5}
        )
        assert response.status_code in (400, 422)
