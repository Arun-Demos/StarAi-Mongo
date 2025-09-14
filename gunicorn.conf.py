import os, os.path

bind    = os.getenv("GUNICORN_BIND", "0.0.0.0:8080")  # HTTP by default
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))

# Optional TLS
use_tls = os.getenv("USE_TLS", "").lower() in ("1","true","yes")
cert    = os.getenv("TLS_CERT_PATH", "/tls/tls.crt")
key     = os.getenv("TLS_KEY_PATH",  "/tls/tls.key")

if use_tls and os.path.exists(cert) and os.path.exists(key):
    certfile = cert
    keyfile  = key
