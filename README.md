diff --git a/README.md b/README.md
index b88d9f90c9164313ae3ca053fee0064cf1fd79a1..61a86e56a8a3de0df91d2ba9fef5819efde0e83c 100644
--- a/README.md
+++ b/README.md
@@ -1 +1,66 @@
-# StarAi
+# StarAi
+
+## Project Overview
+StarAi is a small Flask application that renders service information from a PostgreSQL database. Database credentials are retrieved at runtime from [CyberArk Conjur](https://www.conjur.org/) to avoid embedding secrets in the codebase. The application can be containerized for local development or deployed to Kubernetes via the provided manifests and Jenkins pipeline.
+
+## Local Setup
+You can run the application locally either using Docker or directly with Flask.
+
+### Using Docker
+```
+docker build -t starai:latest .
+docker run -p 5000:80 starai:latest
+```
+
+### Using Flask Directly
+```
+pip install -r requirements.txt
+export FLASK_APP=app.py
+flask run --host=0.0.0.0 --port=80
+```
+
+## Configuring Conjur Secrets and Environment Variables
+The app expects the following variables to be available in Conjur and accessible to the running identity:
+
+| Variable name | Purpose |
+|---------------|---------|
+| `data/vault/StarAi-Dev/Arun-Staridb/address`  | Database host (optionally with port) |
+| `data/vault/StarAi-Dev/Arun-Staridb/username` | Database user |
+| `data/vault/StarAi-Dev/Arun-Staridb/password` | Database password |
+
+At runtime, configure these environment variables to point the app to your Conjur instance and database:
+
+```
+CONJUR_API_BASE=https://<tenant>.secretsmgr.cyberark.cloud/api
+CONJUR_ACCOUNT=conjur
+CONJUR_TOKEN_PATH=/run/conjur/access-token
+DB_NAME=postgres
+```
+
+`CONJUR_TOKEN_PATH` should point to a file containing a valid Conjur access token. In Kubernetes this is mounted by the Conjur authenticator sidecar; for local development you can obtain a token using the `conjur` CLI and write it to a file.
+
+## Kubernetes Deployment
+The `manifests/` directory contains example resources for deploying the app to Kubernetes.
+
+1. Build and push the container image to a registry accessible by the cluster.
+2. Create the ConfigMap for application settings:
+   ```
+   kubectl apply -f manifests/starai-configmap.yaml
+   ```
+3. Deploy the application, service, TLS certificate and ingress:
+   ```
+   kubectl apply -f manifests/deployment.yaml
+   kubectl apply -f manifests/Service.yaml
+   kubectl apply -f manifests/TLScert.yaml
+   kubectl apply -f manifests/Ingress.yaml
+   ```
+
+## Jenkins Pipeline
+The `Jenkinsfile` defines a declarative pipeline that runs in a Kubernetes agent:
+
+1. **Clone GitHub Repo** – retrieves the repository using Conjur-managed GitHub credentials.
+2. **Kaniko Build & Push Image** – builds the Docker image with [Kaniko](https://github.com/GoogleContainerTools/kaniko) and pushes it to Docker Hub.
+3. **Deploy App to Kubernetes** – uses `kubectl` along with temporary AWS credentials from Conjur to apply the manifests listed above.
+
+The pipeline assumes that Conjur is configured with appropriate secrets (`github-username`, `github-token`, and AWS dynamic credentials) and that the `regcred` Docker registry secret exists in the Jenkins namespace.
+
