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

EXPOSE 9000

# Scale uvicorn workers with the container's CPU allocation (UVICORN_WORKERS);
# defaults to 2. CPU-bound OpenCV/inference work benefits from >1 process.
ENV UVICORN_WORKERS=2
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers ${UVICORN_WORKERS}"]
