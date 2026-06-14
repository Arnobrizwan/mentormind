"""Computer-vision primitives for the ML service.

Three classic OpenCV workloads, no GPU required:
- proctoring: frontal-face count via Haar cascade
- OMR: bubble-sheet grading on a fixed grid layout
- OCR: text extraction via Tesseract (optional engine)
"""

from __future__ import annotations

import os

import cv2
import numpy as np

_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# Detection knobs — env-tunable for different cameras / sheet styles.
PROCTOR_SCALE_FACTOR = float(os.getenv("PROCTOR_SCALE_FACTOR", "1.1"))
PROCTOR_MIN_NEIGHBORS = int(os.getenv("PROCTOR_MIN_NEIGHBORS", "5"))
PROCTOR_MIN_FACE_PX = int(os.getenv("PROCTOR_MIN_FACE_PX", "40"))
OMR_FILL_THRESHOLD = float(os.getenv("OMR_FILL_THRESHOLD", "0.08"))


def decode_image(raw: bytes) -> np.ndarray | None:
    buf = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return image


# --- Proctoring -------------------------------------------------------------


def proctor_check(image: np.ndarray) -> dict:
    """Count frontal faces in a webcam frame.

    Verdicts: ok (exactly one face), no_face (student absent / camera
    covered), multiple_faces (someone else in frame).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = _FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=PROCTOR_SCALE_FACTOR,
        minNeighbors=PROCTOR_MIN_NEIGHBORS,
        minSize=(PROCTOR_MIN_FACE_PX, PROCTOR_MIN_FACE_PX),
    )
    count = len(faces)
    if count == 1:
        verdict = "ok"
    elif count == 0:
        verdict = "no_face"
    else:
        verdict = "multiple_faces"
    return {
        "faces": int(count),
        "verdict": verdict,
        "boxes": [[int(x), int(y), int(w), int(h)] for (x, y, w, h) in faces],
    }


# --- OMR (bubble-sheet) grading ---------------------------------------------


def omr_grade(
    image: np.ndarray,
    answer_key: list[int],
    num_options: int = 4,
) -> dict:
    """Grade a bubble sheet laid out as a uniform grid:
    one question per row, `num_options` bubbles per row.

    For each cell we measure the dark-pixel ratio; the most-filled bubble in
    a row is that question's answer. A row with no bubble above the fill
    threshold is 'blank'.
    """
    num_questions = len(answer_key)
    if num_questions == 0:
        raise ValueError("answer_key must not be empty")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Otsu picks the pencil/paper split without manual tuning
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    height, width = binary.shape
    row_height = height / num_questions
    col_width = width / num_options

    detected: list[int | None] = []
    fill_grid: list[list[float]] = []
    for q in range(num_questions):
        fills = []
        for opt in range(num_options):
            y0, y1 = int(q * row_height), int((q + 1) * row_height)
            x0, x1 = int(opt * col_width), int((opt + 1) * col_width)
            cell = binary[y0:y1, x0:x1]
            fills.append(float(cell.mean()) / 255.0)
        fill_grid.append([round(f, 3) for f in fills])
        best = int(np.argmax(fills))
        detected.append(best if fills[best] > OMR_FILL_THRESHOLD else None)

    correct = sum(
        1 for got, expected in zip(detected, answer_key) if got == expected
    )
    return {
        "total_questions": num_questions,
        "correct": correct,
        "score": round(correct / num_questions * 100, 2),
        "detected_answers": detected,
        "fill_grid": fill_grid,
    }


# --- OCR ---------------------------------------------------------------------


def ocr_available() -> bool:
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_extract(image: np.ndarray) -> dict:
    import pytesseract

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Light denoise + binarise helps Tesseract on photographed pages
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = pytesseract.image_to_string(binary)
    return {"text": text.strip(), "characters": len(text.strip())}


# --- Vision-language model (moondream2) — actually "sees" the image ----------
#
# Open-source, small (~1.6B), permissive — answers questions about diagrams,
# figures and photos, not just OCR. Opt-in via VISION_VLM=1 (needs torch +
# transformers, same stack as the local tutor LLM). Lazy-loaded; callers fall
# back to OCR if it's disabled or fails.

_VLM: dict = {"model": None, "tokenizer": None, "loaded": False}


def vqa_available() -> bool:
    return os.getenv("VISION_VLM", "0") == "1"


def _load_vlm():
    if _VLM["loaded"]:
        return _VLM["model"], _VLM["tokenizer"]
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = os.getenv("VISION_VLM_MODEL", "vikhyatk/moondream2")
    revision = os.getenv("VISION_VLM_REVISION", "2025-06-21")
    model = AutoModelForCausalLM.from_pretrained(
        model_id, revision=revision, trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    _VLM.update(model=model, tokenizer=tokenizer, loaded=True)
    return model, tokenizer


def vqa_answer(image: np.ndarray, question: str) -> dict:
    """Answer a question about the image with moondream2 (visual understanding).

    Tries the newer .query() API, falls back to encode_image/answer_question
    for older moondream2 revisions.
    """
    from PIL import Image

    pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    model, tokenizer = _load_vlm()
    prompt = (question or "").strip() or (
        "Describe this image in detail for a student, including any diagram, "
        "figure, equation or handwritten work."
    )
    try:
        answer = model.query(pil, prompt)["answer"]
    except (AttributeError, TypeError):
        enc = model.encode_image(pil)
        answer = model.answer_question(enc, prompt, tokenizer)
    return {"answer": str(answer).strip(), "model": "moondream2"}
