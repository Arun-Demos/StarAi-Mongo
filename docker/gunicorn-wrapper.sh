#!/bin/sh
set -e
REAL="/usr/local/bin/gunicorn.real"
CERT="${TLS_CERT_PATH:-/tls/tls.crt}"
KEY="${TLS_KEY_PATH:-/tls/tls.key}"
USE_TLS="${USE_TLS:-auto}"   # auto|true|false

want_tls=0
case "$USE_TLS" in
  [Tt][Rr][Uu][Ee]|1|yes) want_tls=1 ;;
  [Ff][Aa][Ll][Ss][Ee]|0|no) want_tls=0 ;;
  *) [ -s "$CERT" ] && [ -s "$KEY" ] && want_tls=1 || want_tls=0 ;;
esac

if [ "$want_tls" -eq 1 ]; then
  exec "$REAL" "$@"
else
  exec "$REAL" --workers "${GUNICORN_WORKERS:-2}" --threads "${GUNICORN_THREADS:-4}" \
       --bind "${GUNICORN_BIND:-0.0.0.0:8080}" app:app
fi
