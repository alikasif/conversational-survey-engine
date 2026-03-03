# Kubernetes Deployment Guide

Step-by-step guide for deploying the Conversational Survey Engine to a Kubernetes cluster.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Build container images |
| kubectl | 1.28+ | Kubernetes CLI |
| Container Registry | — | Push/pull images (e.g., `ghcr.io`, Docker Hub, GCR, ECR) |
| Kubernetes Cluster | 1.28+ | Target deployment environment |

Ensure you have:
- `kubectl` configured to access your target cluster (`kubectl cluster-info`)
- Docker logged into your container registry (`docker login`)
- Access to the NeonDB PostgreSQL connection string

---

## Quick Deploy with `deploy.ps1`

The `deploy.ps1` PowerShell script automates the full deployment pipeline.

### Usage

```powershell
# Full deployment
.\deploy.ps1 -Registry "ghcr.io/your-org" -Tag "v1.0.0"

# Dry run — prints commands without executing
.\deploy.ps1 -Registry "ghcr.io/your-org" -Tag "v1.0.0" -DryRun
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `-Registry` | Yes | — | Container registry URL (e.g., `ghcr.io/myorg`) |
| `-Tag` | No | `latest` | Image tag |
| `-DryRun` | No | `$false` | Print commands without executing |

### What the Script Does

1. **Builds** Docker images for all three services (`cse-backend`, `cse-llm-service`, `cse-frontend`)
2. **Pushes** images to the specified registry
3. **Creates** the `cse` Kubernetes namespace
4. **Applies** secrets and configmap
5. **Runs** the Alembic migration job (waits for completion)
6. **Deploys** backend, LLM service, and frontend
7. **Verifies** rollout status for all deployments
8. **Prints** service endpoints

> **Important:** You must populate `k8s/secrets.yaml` with real base64-encoded values before running the script. See [Secrets Configuration](#secrets-configuration) below.

---

## Manual Deployment Steps

If you prefer to deploy manually without the script:

### Step 1: Build and Push Images

```bash
# Build images
docker build -t <registry>/cse-backend:latest ./backend
docker build -t <registry>/cse-llm-service:latest ./llm-service
docker build -t <registry>/cse-frontend:latest ./frontend

# Push images
docker push <registry>/cse-backend:latest
docker push <registry>/cse-llm-service:latest
docker push <registry>/cse-frontend:latest
```

### Step 2: Update Image References

The K8s deployment manifests use placeholder image names (e.g., `cse-backend:latest`). Update them to point to your registry:

```bash
# Option A: Use kubectl set image after applying
kubectl set image deployment/backend backend=<registry>/cse-backend:latest -n cse
kubectl set image deployment/llm-service llm-service=<registry>/cse-llm-service:latest -n cse
kubectl set image deployment/frontend frontend=<registry>/cse-frontend:latest -n cse

# Option B: Edit the manifests directly before applying
# Replace "image: cse-backend:latest" with "image: <registry>/cse-backend:latest"
```

### Step 3: Configure Secrets

See [Secrets Configuration](#secrets-configuration).

### Step 4: Apply Manifests

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply configuration
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# Run database migration
kubectl delete job alembic-migrate -n cse --ignore-not-found
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/alembic-migrate -n cse --timeout=120s

# Deploy services
kubectl apply -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml
kubectl apply -f k8s/llm-service-deployment.yaml -f k8s/llm-service-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml
```

### Step 5: Verify Deployment

```bash
# Check rollout status
kubectl rollout status deployment/backend -n cse --timeout=120s
kubectl rollout status deployment/llm-service -n cse --timeout=120s
kubectl rollout status deployment/frontend -n cse --timeout=120s

# Check all pods are running
kubectl get pods -n cse

# Check service endpoints
kubectl get services -n cse -o wide
```

---

## K8s Manifest Overview

| File | Kind | Purpose |
|------|------|---------|
| `namespace.yaml` | Namespace | Creates the `cse` namespace to isolate resources |
| `configmap.yaml` | ConfigMap | Non-sensitive configuration: `CORS_ORIGINS`, `LOG_LEVEL`, `LLM_SERVICE_URL` |
| `secrets.yaml` | Secret | Sensitive values: `DATABASE_URL`, `GEMINI_API_KEY`, GCP credentials |
| `migration-job.yaml` | Job | Runs `alembic upgrade head` before deployments; auto-cleans after 5 min |
| `backend-deployment.yaml` | Deployment | Backend API: 2 replicas, port 8000, health checks, resource limits |
| `backend-service.yaml` | Service | ClusterIP service exposing backend on port 8000 |
| `llm-service-deployment.yaml` | Deployment | LLM Service: 2 replicas, port 8001, GCP credentials volume mount |
| `llm-service-service.yaml` | Service | ClusterIP service exposing LLM service on port 8001 |
| `frontend-deployment.yaml` | Deployment | Frontend: 2 replicas, nginx on port 80 |
| `frontend-service.yaml` | Service | LoadBalancer service exposing frontend on port 80 (external access) |

### Service Discovery

- Backend → LLM Service: `http://llm-service.cse.svc.cluster.local:8001` (set in ConfigMap)
- Frontend (nginx) → Backend: `http://backend:8000` (set in nginx.conf; resolves via K8s DNS)

---

## Secrets Configuration

The `k8s/secrets.yaml` file contains placeholder values that **must** be replaced before deployment.

### How to Base64 Encode Values

```bash
# Linux / macOS
echo -n "your-actual-value" | base64

# Windows PowerShell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-actual-value"))
```

### Required Secrets

| Key | Description | Example (before encoding) |
|-----|-------------|---------------------------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host/db?ssl=require` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Full GCP service account JSON file contents | `{"type":"service_account",...}` |

### Example

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cse-secrets
  namespace: cse
type: Opaque
data:
  DATABASE_URL: cG9zdGdyZXNxbCthc3luY3BnOi8vdXNlcjpwYXNzQGhvc3QvZGI/c3NsPXJlcXVpcmU=
  GEMINI_API_KEY: QUl6YVN5Li4u
  GOOGLE_APPLICATION_CREDENTIALS_JSON: eyJ0eXBlIjoic2VydmljZV9hY2NvdW50In0=
```

> **Security:** Never commit real secrets to version control. Use a secrets manager (e.g., Sealed Secrets, External Secrets Operator, or SOPS) in production.

### GCP Credentials in K8s

The LLM Service deployment mounts the `GOOGLE_APPLICATION_CREDENTIALS_JSON` secret as a file at `/app/credentials/service-account.json`. The `GOOGLE_APPLICATION_CREDENTIALS` env var is set to this path automatically.

---

## Monitoring

### Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| Backend | `GET http://<backend-svc>:8000/health` | `{"status": "ok"}` |
| LLM Service | `GET http://<llm-svc>:8001/health` | `{"status": "healthy", "service": "cse-llm-service", "model": "..."}` |
| Frontend | `GET http://<frontend-svc>:80/` | HTTP 200 (HTML) |

### Checking Health from Inside the Cluster

```bash
# Port-forward to test locally
kubectl port-forward svc/backend 8000:8000 -n cse
curl http://localhost:8000/health

kubectl port-forward svc/llm-service 8001:8001 -n cse
curl http://localhost:8001/health
```

### Viewing Logs

```bash
# Backend logs
kubectl logs -l app.kubernetes.io/name=backend -n cse --tail=100 -f

# LLM Service logs
kubectl logs -l app.kubernetes.io/name=llm-service -n cse --tail=100 -f

# Frontend (nginx) logs
kubectl logs -l app.kubernetes.io/name=frontend -n cse --tail=100 -f

# Migration job logs
kubectl logs job/alembic-migrate -n cse
```

### Kubernetes Probes

All deployments have readiness and liveness probes:

| Probe | Backend | LLM Service | Frontend |
|-------|---------|-------------|----------|
| Readiness | `GET /health` :8000 (5s initial, 10s interval) | `GET /health` :8001 (5s initial, 10s interval) | `GET /` :80 (5s initial, 10s interval) |
| Liveness | `GET /health` :8000 (15s initial, 20s interval) | `GET /health` :8001 (15s initial, 20s interval) | `GET /` :80 (10s initial, 20s interval) |

---

## Scaling

### Adjusting Replica Counts

Edit the `spec.replicas` field in the deployment manifests, or use `kubectl scale`:

```bash
# Scale backend to 4 replicas
kubectl scale deployment/backend --replicas=4 -n cse

# Scale LLM service to 3 replicas (for heavier LLM load)
kubectl scale deployment/llm-service --replicas=3 -n cse

# Scale frontend to 1 replica (low traffic)
kubectl scale deployment/frontend --replicas=1 -n cse
```

### Resource Limits

Default resource allocations:

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| Backend | 250m | 500m | 256Mi | 512Mi |
| LLM Service | 250m | 1000m | 256Mi | 1Gi |
| Frontend | 100m | 200m | 64Mi | 128Mi |

The LLM Service has higher limits because it processes LLM requests that can be CPU/memory intensive. Adjust these in the respective deployment YAML files based on observed usage.

### Future Enhancements

For production workloads, consider adding:
- **HorizontalPodAutoscaler (HPA):** Auto-scale based on CPU/memory utilization
- **PodDisruptionBudget (PDB):** Ensure minimum availability during node maintenance

---

## Troubleshooting

### Migration Job Failures

**Symptom:** `kubectl wait` times out or the migration job shows `Error` or `BackoffLimitExceeded`.

```bash
# Check job status
kubectl describe job alembic-migrate -n cse

# Check migration pod logs
kubectl logs job/alembic-migrate -n cse
```

**Common causes:**
- `DATABASE_URL` secret is not properly base64-encoded or is missing
- Database is unreachable (network policy, firewall, wrong hostname)
- NeonDB requires `ssl=require` in the connection string — ensure it's included
- Previous migration job still exists — delete it first: `kubectl delete job alembic-migrate -n cse --ignore-not-found`

### Service Connectivity Issues

**Symptom:** Backend returns 500 errors when generating questions; logs show "LLM service unreachable".

```bash
# Verify LLM service is running
kubectl get pods -l app.kubernetes.io/name=llm-service -n cse

# Test connectivity from backend pod
kubectl exec -it deployment/backend -n cse -- curl http://llm-service.cse.svc.cluster.local:8001/health
```

**Common causes:**
- LLM service pods not ready (check readiness probe failures)
- ConfigMap `LLM_SERVICE_URL` value is wrong
- LLM service crashing on startup (check logs for missing `GEMINI_API_KEY` or invalid credentials)

### Frontend Cannot Reach Backend

**Symptom:** Browser shows network errors; API calls fail.

```bash
# Check frontend nginx config is proxying correctly
kubectl exec -it deployment/frontend -n cse -- cat /etc/nginx/conf.d/default.conf

# Check backend service exists and has endpoints
kubectl get endpoints backend -n cse
```

**Common causes:**
- Backend service has no endpoints (pods not ready)
- nginx `proxy_pass` hostname doesn't match the K8s service name (`backend`)

### Pods Stuck in CrashLoopBackOff

```bash
# Check pod events
kubectl describe pod <pod-name> -n cse

# Check container logs
kubectl logs <pod-name> -n cse --previous
```

**Common causes:**
- Missing or invalid environment variables (secrets not applied)
- Import errors in Python code
- Port already in use (unlikely in K8s but possible with hostPort)

### Image Pull Errors

**Symptom:** Pods show `ImagePullBackOff` or `ErrImagePull`.

**Common causes:**
- Image not pushed to registry
- K8s manifest still uses local image name (`cse-backend:latest`) instead of registry-prefixed name
- Missing `imagePullSecrets` for private registries

```bash
# Check pod events for the specific error
kubectl describe pod <pod-name> -n cse | grep -A 5 "Events"
```
