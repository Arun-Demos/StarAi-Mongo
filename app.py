# app.py
import os, base64, time, logging
import requests
from decimal import Decimal
from bson.decimal128 import Decimal128
from pymongo import MongoClient
from flask import Flask, render_template, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import quote

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)  # respect ALB headers
logging.basicConfig(level=logging.INFO)

# --- Config (override via env / ConfigMap) ---
# Accept either CONJUR_API_BASE or CONJUR_APPLIANCE_URL from ConfigMap; ensure '/api' is present
_raw_conjur_base = (
    os.getenv("CONJUR_API_BASE") or
    os.getenv("CONJUR_APPLIANCE_URL") or
    "https://aruntenant.secretsmgr.cyberark.cloud"
)
CONJUR_API_BASE = _raw_conjur_base.rstrip("/")
if not CONJUR_API_BASE.endswith("/api"):
    CONJUR_API_BASE = f"{CONJUR_API_BASE}/api"

CONJUR_ACCOUNT    = os.getenv("CONJUR_ACCOUNT", "conjur")
CONJUR_TOKEN_PATH = os.getenv("CONJUR_TOKEN_PATH", "/run/conjur/access-token")

MONGO_DB      = os.getenv("MONGO_DB", "stardb")
MONGO_AUTH_DB = os.getenv("MONGO_AUTH_DB", "admin")  # where the user lives (likely 'admin')

MONGO_SECRETS = {
    "uri":  os.getenv("MONGO_URI_VAR",  "data/vault/DevOps/MongoEB-EC2/address"),
    "user": os.getenv("MONGO_USER_VAR", "data/vault/DevOps/MongoEB-EC2/username"),
    "pass": os.getenv("MONGO_PASS_VAR", "data/vault/DevOps/MongoEB-EC2/password"),
}

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))

# --- Conjur helpers ---
def _auth_header() -> dict:
    # Wait briefly if token not written yet (sidecar race)
    deadline = time.time() + 30
    while not os.path.exists(CONJUR_TOKEN_PATH) and time.time() < deadline:
        time.sleep(0.5)
    with open(CONJUR_TOKEN_PATH, "rb") as f:
        token_bytes = f.read()  # raw short-lived token
    b64 = base64.b64encode(token_bytes).decode("ascii")
    return {"Authorization": f'Token token="{b64}"'}

def get_secret(secret_id: str) -> str:
    var_id = quote(secret_id, safe='')  # <— encode
    url = f"{CONJUR_API_BASE}/secrets/{CONJUR_ACCOUNT}/variable/{var_id}"
    for attempt in (1, 2):
        r = requests.get(url, headers=_auth_header(), timeout=HTTP_TIMEOUT)
        if r.status_code == 401 and attempt == 1:
            time.sleep(0.3); continue
        r.raise_for_status()
        return r.text.strip()
    raise RuntimeError(f"Failed to fetch secret {secret_id}")

def get_mongo_uri() -> str:
    return get_secret(MONGO_SECRETS["uri"])

def get_mongo_user() -> str:
    return get_secret(MONGO_SECRETS["user"])

def get_mongo_password() -> str:
    return get_secret(MONGO_SECRETS["pass"])

# --- Data access ---
def _dec128_to_float(x):
    if isinstance(x, Decimal128):
        return float(x.to_decimal())
    if isinstance(x, Decimal):
        return float(x)
    return x

def query_services(uri: str, user: str, password: str):
    client = MongoClient(
        uri,
        username=user,
        password=password,
        authSource=MONGO_AUTH_DB,
        directConnection=True,              # set False if using a replica set/connection string
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
    )
    try:
        coll = client[MONGO_DB]["services"]
        cursor = coll.find({}, {"_id": 0, "name": 1, "subscribers": 1, "revenue": 1})
        rows = []
        for d in cursor:
            rows.append({
                "name": d.get("name"),
                "subscribers": int(d.get("subscribers", 0)),
                "revenue": _dec128_to_float(d.get("revenue")),
            })
        return rows
    finally:
        client.close()

# --- Routes ---
@app.route("/")
def index():
    try:
        uri = get_mongo_uri()
        user = get_mongo_user()
        password = get_mongo_password()
        app.logger.info(f"Connecting to Mongo DB '{MONGO_DB}' at {uri} as {user}")
        services = query_services(uri, user, password)
        # If you don't have a template yet, fall back to JSON
        try:
            return render_template("index.html", services=services)
        except Exception:
            return jsonify(services)
    except Exception as e:
        app.logger.exception("Failed handling /")
        return f"Error: {e}", 500

@app.route("/api/services")
def api_services():
    uri = get_mongo_uri()
    user = get_mongo_user()
    password = get_mongo_password()
    return jsonify(query_services(uri, user, password))

@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    # Dev server only; in Kubernetes you run via gunicorn
    app.run(host="0.0.0.0", port=80)
