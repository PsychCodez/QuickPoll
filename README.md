# QuickPoll — Argo CD Learning Project (Dummy)

A simple poll app created as a learning exercise for Argo CD and Kubernetes. Minimal production features added so it feels "complete": create polls, vote, realtime updates via Socket.IO, 24-hour poll expiry, and optional MySQL persistence.

## Features
- Create a poll with multiple choices
- Vote on existing polls
- 24-hour timer per poll (expires automatically)
- Realtime updates (Socket.IO) and voter list visibility
- Optional MySQL persistence (default: SQLite file inside container)
- Basic Kubernetes manifests for Argo CD

## Repo layout
- app/api — FastAPI backend (Socket.IO integrated)
- app/web — React + Vite frontend (served by nginx in Docker image)
- app/k8s/base — Kubernetes manifests (Deployments, Services, Ingress)

## Quick local run (dev)
1. Ensure hosts file contains:
   ```
   127.0.0.1 quickpoll.local
   ```
2. Run API locally:
   ```
   cd app/api
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Run web locally:
   ```
   cd app/web
   npm install
   npm run dev
   ```
4. Open: `http://quickpoll.local` (or `http://localhost:5173` for dev server)

## Build & deploy images (quick)
- Build API:
  ```
  cd app/api
  docker build -t quickpoll-api:dev .
  ```
- Build Web:
  ```
  cd app/web
  docker build -t quickpoll-web:dev .
  ```
- Apply manifests (local cluster / Docker Desktop):
  ```
  kubectl apply -k app/k8s/base
  kubectl rollout restart -n quickpoll deployment/api
  kubectl rollout restart -n quickpoll deployment/web
  ```

Note: If using same image tag, either set imagePullPolicy: Always or restart pods to pick up rebuilt images.

## Use a MySQL DB (optional)
1. Create DB and user in MySQL Workbench.
2. Create Kubernetes secret with DATABASE_URL:
   ```
   kubectl create secret generic quickpoll-db \
     --from-literal=DATABASE_URL='mysql+pymysql://user:pass@host:3306/quickpoll' -n quickpoll
   ```
3. Patch `app/k8s/base/api.yaml` to mount env from that secret and restart API.

## GitOps / Argo CD notes
- Argo CD syncs from Git. After building and pushing images, update image tags in Git manifests (or use Argo CD Image Updater) so Argo syncs the new version.
- CI recommendation: build image with commit SHA, update manifest in Git, push — Argo CD will deploy.

## Testing multiple users
- Open different browsers / incognito windows and use distinct "Your name" values.
- Or use cURL / small Node scripts to simulate multiple voters.

## Troubleshooting
- 503 / HTML returned: backend not reachable or ingress misconfigured — check ingress, hosts file, and pod logs.
- 404 on UI create: ensure frontend uses `/api/polls` path that your ingress routes to backend.
- DB: default is SQLite (ephemeral). Use MySQL for persistence.

This project is a learning/dummy app — keep configs simple and avoid production assumptions (no TLS, basic auth, or backups included).