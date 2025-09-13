
 import os, base64, time, logging
 import requests
 from pymongo import MongoClient
 from flask import Flask, render_template
 
 app = Flask(__name__)
 logging.basicConfig(level=logging.INFO)
 
 # Config (override via env / ConfigMap)
 CONJUR_API_BASE = os.getenv("CONJUR_API_BASE", "https://aruntenant.secretsmgr.cyberark.cloud/api")
 CONJUR_ACCOUNT  = os.getenv("CONJUR_ACCOUNT", "conjur")
 CONJUR_TOKEN_PATH = os.getenv("CONJUR_TOKEN_PATH", "/run/conjur/access-token")
 MONGO_DB = os.getenv("MONGO_DB", "starai")
 
 MONGO_SECRETS = {
     "uri": "data/vault/StarAi-Mongo/Arun-Starimongo/uri",
     "user": "data/vault/StarAi-Mongo/Arun-Starimongo/username",
     "pass": "data/vault/StarAi-Mongo/Arun-Starimongo/password",
 }
 
 def _auth_header() -> dict:
     # Wait briefly if token not written yet
     deadline = time.time() + 30
     while not os.path.exists(CONJUR_TOKEN_PATH) and time.time() < deadline:
         time.sleep(0.5)
     with open(CONJUR_TOKEN_PATH, "rb") as f:
         token_json = f.read()  # JSON string bytes
     b64 = base64.b64encode(token_json).decode("ascii")
     return {"Authorization": f'Token token="{b64}"'}
 
 def get_secret(secret_id: str) -> str:
     url = f"{CONJUR_API_BASE}/secrets/{CONJUR_ACCOUNT}/variable/{secret_id}"
     # try once, then refresh header on 401 (token rotates fast)
     for attempt in (1, 2):
         r = requests.get(url, headers=_auth_header(), timeout=10)
         if r.status_code == 401 and attempt == 1:
             continue
         r.raise_for_status()
         return r.text.strip()
 
 def get_mongo_uri() -> str:
     return get_secret(MONGO_SECRETS["uri"])
 
 
 def get_mongo_user() -> str:
     return get_secret(MONGO_SECRETS["user"])
 
 
 def get_mongo_password() -> str:
     return get_secret(MONGO_SECRETS["pass"])
 
 
 def query_services(uri: str, user: str, password: str):
     client = MongoClient(uri, username=user, password=password)
     try:
         coll = client[MONGO_DB]["services"]
         docs = coll.find({}, {"_id": 0, "service": 1, "subscribers": 1, "revenue": 1})
         return [{"name": d["service"], "subscribers": d["subscribers"], "revenue": d["revenue"]} for d in docs]
     finally:
         client.close()
 
 @app.route("/")
 def index():
     try:
         uri = get_mongo_uri()
         user = get_mongo_user()
         password = get_mongo_password()
         app.logger.info(f"Connecting to Mongo DB '{MONGO_DB}' at {uri} as {user}")
 
         services = query_services(uri, user, password)
         return render_template("index.html", services=services)
     except Exception as e:
         app.logger.exception("Failed handling /")
         return f"Error: {e}", 500
 
 @app.route("/healthz")
 def healthz():
     return "ok", 200
 
 if __name__ == "__main__":
     app.run(host="0.0.0.0", port=80)
