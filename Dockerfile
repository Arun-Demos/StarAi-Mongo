FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./app.py
COPY gunicorn.conf.py ./gunicorn.conf.py
COPY templates ./templates

# Replace gunicorn with your wrapper (so K8s CLI TLS flags won't crash the app)
RUN mv /usr/local/bin/gunicorn /usr/local/bin/gunicorn.real
COPY docker/gunicorn-wrapper.sh /usr/local/bin/gunicorn
RUN chmod +x /usr/local/bin/gunicorn

# Defaults: serve HTTP on 8080 unless USE_TLS=true *and* certs exist
ENV GUNICORN_BIND=0.0.0.0:8080 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=4 \
    USE_TLS=auto \
    TLS_CERT_PATH=/tls/tls.crt \
    TLS_KEY_PATH=/tls/tls.key

EXPOSE 8080

# Start gunicorn (the wrapper is invoked as "gunicorn")
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
