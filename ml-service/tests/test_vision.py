"""ML service tests — synthetic images keep these hermetic and fast."""

import io
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import vision
from app.main import app

client = TestClient(app)


def encode_png(image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image)
    assert ok
    return buf.tobytes()


def make_bubble_sheet(answers, num_options=4, cell=60):
    """Render a synthetic bubble sheet matching the grid layout the grader
    expects: one row per question, filled disc on the chosen option."""
    rows = len(answers)
    sheet = np.full((rows * cell, num_options * cell), 255, dtype=np.uint8)
    for q, answer in enumerate(answers):
        for opt in range(num_options):
            cy, cx = q * cell + cell // 2, opt * cell + cell // 2
            if opt == answer:
                cv2.circle(sheet, (cx, cy), cell // 3, 0, -1)  # filled
            else:
                cv2.circle(sheet, (cx, cy), cell // 3, 0, 2)  # outline
    return cv2.cvtColor(sheet, cv2.COLOR_GRAY2BGR)


class TestHealth:
    def test_healthz(self):
        res = client.get("/healthz")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_models_reports_engines(self):
        res = client.get("/v1/models")
        assert res.json()["proctoring"]["status"] == "loaded"
        assert res.json()["omr_grader"]["status"] == "loaded"


class TestProctoring:
    def test_blank_frame_has_no_face(self):
        blank = np.full((240, 320, 3), 128, dtype=np.uint8)
        res = client.post(
            "/v1/proctor/check",
            files={"image": ("frame.png", encode_png(blank), "image/png")},
        )
        assert res.status_code == 200
        assert res.json()["verdict"] == "no_face"
        assert res.json()["faces"] == 0

    def test_rejects_garbage_bytes(self):
        res = client.post(
            "/v1/proctor/check",
            files={"image": ("frame.png", b"not an image", "image/png")},
        )
        assert res.status_code == 400


class TestOmr:
    def test_perfect_sheet_scores_100(self):
        answers = [0, 2, 1, 3, 2]
        sheet = make_bubble_sheet(answers)
        res = client.post(
            "/v1/omr/grade",
            files={"image": ("sheet.png", encode_png(sheet), "image/png")},
            data={"answer_key": json.dumps(answers), "num_options": "4"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["score"] == 100.0
        assert body["detected_answers"] == answers

    def test_wrong_answers_are_caught(self):
        marked = [0, 1, 1]
        key = [0, 2, 1]  # question 2 answered wrong
        sheet = make_bubble_sheet(marked)
        res = client.post(
            "/v1/omr/grade",
            files={"image": ("sheet.png", encode_png(sheet), "image/png")},
            data={"answer_key": json.dumps(key), "num_options": "4"},
        )
        body = res.json()
        assert body["correct"] == 2
        assert body["score"] == round(2 / 3 * 100, 2)

    def test_invalid_answer_key_rejected(self):
        sheet = make_bubble_sheet([0])
        res = client.post(
            "/v1/omr/grade",
            files={"image": ("sheet.png", encode_png(sheet), "image/png")},
            data={"answer_key": "not json", "num_options": "4"},
        )
        assert res.status_code == 400


class TestOcr:
    @pytest.mark.skipif(not vision.ocr_available(), reason="tesseract not installed")
    def test_reads_rendered_text(self):
        page = np.full((120, 640, 3), 255, dtype=np.uint8)
        cv2.putText(
            page, "MENTORMIND", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 4
        )
        res = client.post(
            "/v1/ocr/extract",
            files={"image": ("page.png", encode_png(page), "image/png")},
        )
        assert res.status_code == 200
        assert "MENTORMIND" in res.json()["text"].upper()
