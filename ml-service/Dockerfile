# 3.13 (not 3.14) — ceiling for full PyTorch/OpenCV wheel coverage, which
# this service grows into in Phase 4.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# tesseract powers the OCR endpoint; libglib is needed by opencv-headless
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Ship the exported artifacts (dropout_risk.json; tutor-lora if trained).
# .dockerignore keeps raw papers/datasets and the local DB out of the image.
COPY models ./models

# Drop root: the service only reads baked-in artifacts.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/healthz', timeout=4)"]

# Scale uvicorn workers with the container's CPU allocation (UVICORN_WORKERS);
# defaults to 2. CPU-bound OpenCV/inference work benefits from >1 process.
ENV UVICORN_WORKERS=2
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers ${UVICORN_WORKERS}"]
