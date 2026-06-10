FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# DEBUG=1 here keeps collectstatic from tripping the production SECRET_KEY /
# ALLOWED_HOSTS guards at build time; runtime config is supplied via env.
RUN DJANGO_SETTINGS_MODULE=config.settings DEBUG=1 python manage.py collectstatic --noinput

EXPOSE 8000

# ASGI worker so HTTP and the Channels websocket chat share one port.
# Worker count scales with the container's CPU allocation via WEB_CONCURRENCY
# (gunicorn reads it natively); falls back to 4 when unset.
ENV WEB_CONCURRENCY=4
CMD ["sh", "-c", "gunicorn config.asgi:application -k uvicorn_worker.UvicornWorker --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY} --access-logfile -"]
