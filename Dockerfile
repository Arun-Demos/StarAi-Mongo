FROM python:3.11-slim

# System deps (certs + build basics if wheels aren’t available)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./app.py
COPY gunicorn.conf.py ./gunicorn.conf.py

# Defaults: HTTP on 8080 (TLS off)
ENV GUNICORN_BIND=0.0.0.0:8080 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=4 \
    USE_TLS=0 \
    TLS_CERT_PATH=/tls/tls.crt \
    TLS_KEY_PATH=/tls/tls.key

EXPOSE 8080

# Start Gunicorn using the config file (no TLS flags in CLI)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
