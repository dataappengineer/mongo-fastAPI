# Production Deployment Guide

**FastAPI MongoDB REST API - Production-Ready Configuration**

This guide provides complete instructions for deploying the FastAPI MongoDB REST API to production environments (Kubernetes/Rancher).

---

## 📋 Table of Contents

- [What's New - Production-Ready Changes](#whats-new---production-ready-changes)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Step-by-Step Deployment](#step-by-step-deployment)
- [Testing & Verification](#testing--verification)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## 🆕 What's New - Production-Ready Changes

This deployment configuration includes significant improvements over the base repository:

### ✅ **1. Production Dockerfile (`docker/Dockerfile.prod`)**
- **Removed `--reload` flag** (development-only feature that causes performance overhead)
- **Added `--workers 4`** for multi-process deployment and better performance
- **Optimized `.dockerignore`** to reduce image size by excluding unnecessary files

**Before (Development):**
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**After (Production):**
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### ✅ **2. Enhanced Health Check (`app/main.py`)**
- **MongoDB connection test** - Health endpoint now verifies actual MongoDB connectivity
- **Kubernetes-ready** - Provides detailed status for liveness/readiness probes
- **Error reporting** - Returns diagnostic information when unhealthy

**Before:**
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}  # ❌ Doesn't test MongoDB!
```

**After:**
```python
@app.get("/health")
async def health_check():
    try:
        db = get_database()
        db.command("ping")  # ✅ Tests MongoDB connection
        return {
            "status": "healthy",
            "mongodb": "connected",
            "database": db.name,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "mongodb": "disconnected",
            "error": str(e)
        }
```

### ✅ **3. Complete Kubernetes Configuration**
- **6 ready-to-use YAML files** for Kubernetes/Rancher deployment
- **ConfigMap pattern** for non-sensitive configuration
- **Secret pattern** for credentials (optional)
- **Production-grade resource limits** and health probes
- **Ingress configuration** with CORS support

### ✅ **4. Comprehensive Documentation**
- **Step-by-step deployment guide** (this file)
- **Kubernetes quick reference** ([kubernetes/README.md](kubernetes/README.md))
- **Troubleshooting section** with common issues and solutions
- **Security best practices**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    Ingress                             │  │
│  │              (fastapi.dss.local)                       │  │
│  └────────────────────┬──────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼──────────────────────────────────┐  │
│  │              Service (ClusterIP)                       │  │
│  │              fastapi-service:80                        │  │
│  └────────────────────┬──────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼──────────────────────────────────┐  │
│  │          Deployment (2 replicas)                       │  │
│  │                                                         │  │
│  │  ┌──────────────┐         ┌──────────────┐           │  │
│  │  │  Pod 1       │         │  Pod 2       │           │  │
│  │  │  FastAPI:8000│         │  FastAPI:8000│           │  │
│  │  └──────┬───────┘         └──────┬───────┘           │  │
│  │         │                        │                    │  │
│  │         │  ┌──────────────────┐  │                    │  │
│  │         └──┤   ConfigMap      ├──┘                    │  │
│  │            │  mongodb-config  │                       │  │
│  │            └──────────────────┘                       │  │
│  │                                                         │  │
│  │         │  ┌──────────────────┐  │                    │  │
│  │         └──┤   Secret         ├──┘                    │  │
│  │            │mongodb-credentials│                      │  │
│  │            └──────────────────┘                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                       │                                      │
│                       │ TCP:27017                            │
│                       ▼                                      │
└───────────────────────┼──────────────────────────────────────┘
                        │
                ┌───────▼────────┐
                │    MongoDB     │
                │  (External)    │
                │ Production DB  │
                └────────────────┘
```

**Key Points:**
- ✅ **MongoDB is EXTERNAL** - Not running in Kubernetes, must be pre-existing
- ✅ **API is a Layer** - FastAPI provides REST API over existing MongoDB
- ✅ **ConfigMap** - Stores MongoDB connection details (non-sensitive)
- ✅ **Secret** - Stores credentials (optional, if MongoDB requires auth)

---

## ✅ Prerequisites

Before deploying, ensure you have:

- [ ] **Kubernetes/Rancher cluster** with `kubectl` access
- [ ] **MongoDB** already running and accessible (hostname/IP)
- [ ] **MongoDB connection details:**
  - Hostname/IP address
  - Port (usually 27017)
  - Database name
  - Credentials (if authentication is enabled)
- [ ] **Docker registry** access for pushing images
- [ ] **Namespace** created (default: `dss`)
- [ ] **Ingress controller** installed (e.g., nginx-ingress)

---

## 🚀 Quick Start

### 1. Build Production Image

```bash
# Build using production Dockerfile
docker build -f deployment/docker/Dockerfile.prod -t your-registry/mongo-fastapi:1.0.0 .

# Tag as latest
docker tag your-registry/mongo-fastapi:1.0.0 your-registry/mongo-fastapi:latest

# Push to registry
docker push your-registry/mongo-fastapi:1.0.0
docker push your-registry/mongo-fastapi:latest
```

### 2. Configure MongoDB Connection

Edit `deployment/kubernetes/01-configmap.yaml`:

```yaml
data:
  host: "mongodb-prod.dss.local"  # ⚠️ YOUR MongoDB hostname
  port: "27017"
  database: "edge_database"        # ⚠️ YOUR database name
```

### 3. Configure Credentials (if needed)

If MongoDB requires authentication, edit `deployment/kubernetes/02-secret.yaml`:

```yaml
stringData:
  username: "api_user"              # ⚠️ YOUR username
  password: "your_secure_password"  # ⚠️ YOUR password
```

**⚠️ SECURITY WARNING:** Do NOT commit real passwords to Git!

### 4. Update Image Reference

Edit `deployment/kubernetes/03-deployment.yaml` line 35:

```yaml
image: your-registry/mongo-fastapi:latest  # ⚠️ YOUR registry and image
```

### 5. Deploy to Kubernetes

```bash
cd deployment/kubernetes

# Apply all configurations
kubectl apply -f 00-namespace.yaml      # Optional if namespace exists
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secret.yaml         # Optional if no auth
kubectl apply -f 03-deployment.yaml
kubectl apply -f 04-service.yaml
kubectl apply -f 05-ingress.yaml
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods -n dss -l app=fastapi-mongodb-api

# Test health endpoint
curl http://fastapi.dss.local/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "database": "edge_database",
  "version": "1.0.0"
}
```

---

## 📖 Step-by-Step Deployment

### Step 1: Prepare MongoDB Information

Gather the following information about your production MongoDB:

| Information | Example | Your Value |
|-------------|---------|------------|
| Hostname/IP | `mongodb-prod.dss.local` | ________________ |
| Port | `27017` | ________________ |
| Database Name | `edge_database` | ________________ |
| Username (if auth) | `api_user` | ________________ |
| Password (if auth) | `********` | ________________ |

### Step 2: Test MongoDB Connectivity

Before deploying, verify that MongoDB is accessible from the Kubernetes cluster:

```bash
# From a test pod in the same namespace
kubectl run -it --rm --restart=Never mongo-test \
  --image=mongo:8.0.0 \
  --namespace=dss \
  -- mongosh mongodb://mongodb-prod.dss.local:27017/edge_database --eval "db.runCommand('ping')"
```

**Expected output:**
```json
{ "ok": 1 }
```

If this fails, check:
- DNS resolution: `nslookup mongodb-prod.dss.local`
- Network policies
- Firewall rules
- MongoDB configuration (bind_ip)

### Step 3: Build and Push Docker Image

#### 3.1 Build Production Image

```bash
# Navigate to repository root
cd /path/to/mongo-fastAPI

# Build using production Dockerfile
docker build -f deployment/docker/Dockerfile.prod -t mongo-fastapi:prod .
```

#### 3.2 Test Image Locally (Optional)

```bash
# Start MongoDB (if not already running)
docker-compose up -d mongodb

# Run production image locally
docker run --rm -d \
  --name fastapi-prod-test \
  --network mongo-fastapi_mongo-fastapi-network \
  -p 8001:8000 \
  -e MONGO_HOST=mongodb \
  -e MONGO_PORT=27017 \
  -e MONGO_DB=testdb \
  mongo-fastapi:prod

# Test endpoints
curl http://localhost:8001/health
curl http://localhost:8001/collections/

# Stop test container
docker stop fastapi-prod-test
```

#### 3.3 Tag and Push to Registry

```bash
# Tag with version and latest
docker tag mongo-fastapi:prod your-registry/mongo-fastapi:1.0.0
docker tag mongo-fastapi:prod your-registry/mongo-fastapi:latest

# Push to registry
docker push your-registry/mongo-fastapi:1.0.0
docker push your-registry/mongo-fastapi:latest
```

Replace `your-registry` with:
- Docker Hub: `your-username/mongo-fastapi`
- Private registry: `registry.company.com/mongo-fastapi`
- Harbor: `harbor.company.com/project/mongo-fastapi`

### Step 4: Configure Kubernetes Manifests

#### 4.1 Update ConfigMap

Edit `deployment/kubernetes/01-configmap.yaml`:

```yaml
data:
  host: "mongodb-prod.dss.local"  # ⚠️ CHANGE THIS
  port: "27017"
  database: "edge_database"        # ⚠️ CHANGE THIS
```

#### 4.2 Update Secret (if needed)

**Option A: Create Secret from file**

Edit `deployment/kubernetes/02-secret.yaml` with real credentials, then:

```bash
kubectl apply -f deployment/kubernetes/02-secret.yaml
```

**Option B: Create Secret from command line (RECOMMENDED)**

```bash
kubectl create secret generic mongodb-credentials \
  --from-literal=username=api_user \
  --from-literal=password=your_secure_password \
  --namespace=dss
```

This keeps credentials out of Git.

#### 4.3 Update Deployment Image

Edit `deployment/kubernetes/03-deployment.yaml` line 35:

```yaml
image: your-registry/mongo-fastapi:latest  # ⚠️ CHANGE THIS
```

#### 4.4 Update Ingress Hostname

Edit `deployment/kubernetes/05-ingress.yaml` line 29:

```yaml
- host: fastapi.dss.local  # ⚠️ CHANGE THIS to your hostname
```

### Step 5: Deploy to Kubernetes

```bash
# Change to kubernetes directory
cd deployment/kubernetes

# Apply configurations in order
kubectl apply -f 00-namespace.yaml      # Creates namespace (optional)
kubectl apply -f 01-configmap.yaml      # MongoDB configuration
kubectl apply -f 02-secret.yaml         # Credentials (optional)
kubectl apply -f 03-deployment.yaml     # API deployment
kubectl apply -f 04-service.yaml        # Internal service
kubectl apply -f 05-ingress.yaml        # External access

# Or apply all at once:
kubectl apply -f .
```

### Step 6: Monitor Deployment

```bash
# Watch pod status
kubectl get pods -n dss -l app=fastapi-mongodb-api -w

# View logs
kubectl logs -n dss -l app=fastapi-mongodb-api --tail=50 -f

# Check deployment status
kubectl rollout status deployment/fastapi-mongodb-api -n dss
```

Wait until pods show `Running` and `2/2` ready:

```
NAME                                   READY   STATUS    RESTARTS   AGE
fastapi-mongodb-api-xxxxxxxxxx-xxxxx   1/1     Running   0          30s
fastapi-mongodb-api-xxxxxxxxxx-xxxxx   1/1     Running   0          30s
```

---

## 🧪 Testing & Verification

### Test 1: Health Check (Critical)

```bash
curl http://fastapi.dss.local/health
```

**Expected (Healthy):**
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "database": "edge_database",
  "version": "1.0.0"
}
```

**If Unhealthy:**
```json
{
  "status": "unhealthy",
  "mongodb": "disconnected",
  "error": "connection timeout",
  "version": "1.0.0"
}
```

👉 **If unhealthy**, see [Troubleshooting](#troubleshooting) section.

### Test 2: Root Endpoint

```bash
curl http://fastapi.dss.local/
```

**Expected:**
```json
{
  "message": "MongoDB REST API",
  "version": "1.0.0",
  "endpoints": {
    "list_collections": "GET /collections/",
    "collection_metadata": "GET /collections/{collection_name}/metadata",
    "collection_data": "GET /collections/{collection_name}/data?max_righe={n}"
  }
}
```

### Test 3: List Collections (Tests MongoDB Access)

```bash
curl http://fastapi.dss.local/collections/
```

**Expected:**
```json
{
  "collections": [
    {"name": "collection1", "type": "collection"},
    {"name": "collection2", "type": "collection"}
  ],
  "count": 2
}
```

👉 **If this fails**, MongoDB connection has issues.

### Test 4: Interactive API Documentation

Open in browser:
```
http://fastapi.dss.local/docs
```

You should see the Swagger UI with all API endpoints.

### Test 5: Get Collection Metadata

```bash
# Replace 'your_collection' with an actual collection name
curl http://fastapi.dss.local/collections/your_collection/metadata
```

### Full Test Checklist

Run this complete test suite:

```bash
#!/bin/bash
# save as test_api.sh

API_URL="http://fastapi.dss.local"

echo "🧪 Testing FastAPI MongoDB API"
echo "================================"

echo -e "\n✅ Test 1: Health Check"
curl -s "$API_URL/health" | jq .

echo -e "\n✅ Test 2: Root Endpoint"
curl -s "$API_URL/" | jq .

echo -e "\n✅ Test 3: List Collections"
curl -s "$API_URL/collections/" | jq .

echo -e "\n✅ Test 4: API Docs Available"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$API_URL/docs"

echo -e "\n================================"
echo "🎉 Tests completed!"
```

Run with:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## 🔧 Troubleshooting

### Problem 1: Pods in CrashLoopBackOff

**Symptoms:**
```bash
$ kubectl get pods -n dss
NAME                                   READY   STATUS             RESTARTS   AGE
fastapi-mongodb-api-xxx                0/1     CrashLoopBackOff   5          3m
```

**Diagnosis:**

```bash
# View logs from crashed container
kubectl logs -n dss -l app=fastapi-mongodb-api --previous

# View pod events
kubectl describe pod -n dss -l app=fastapi-mongodb-api
```

**Common Causes:**

1. **MongoDB not reachable**
   - Check MongoDB hostname in ConfigMap
   - Test DNS: `kubectl exec -n dss -it <pod-name> -- nslookup mongodb-prod.dss.local`
   - Check network policies

2. **Wrong credentials**
   - Verify Secret values
   - Test MongoDB auth manually

3. **ConfigMap/Secret not applied**
   ```bash
   kubectl get configmap -n dss mongodb-config
   kubectl get secret -n dss mongodb-credentials
   ```

### Problem 2: Health Check Returns Unhealthy

**Symptoms:**
```json
{
  "status": "unhealthy",
  "mongodb": "disconnected",
  "error": "connection timeout"
}
```

**Solution Steps:**

```bash
# 1. Check MongoDB from inside pod
kubectl exec -n dss -it $(kubectl get pod -n dss -l app=fastapi-mongodb-api -o jsonpath='{.items[0].metadata.name}') -- python3 -c "
from pymongo import MongoClient
import os
print(f'Connecting to: {os.getenv(\"MONGO_HOST\")}:{os.getenv(\"MONGO_PORT\")}')
client = MongoClient(f'mongodb://{os.getenv(\"MONGO_HOST\")}:{os.getenv(\"MONGO_PORT\")}/', serverSelectionTimeoutMS=5000)
try:
    print(client.admin.command('ping'))
    print('✅ MongoDB connection successful!')
except Exception as e:
    print(f'❌ Error: {e}')
"

# 2. Check environment variables are set correctly
kubectl exec -n dss -it $(kubectl get pod -n dss -l app=fastapi-mongodb-api -o jsonpath='{.items[0].metadata.name}') -- env | grep MONGO

# 3. Test network connectivity
kubectl exec -n dss -it $(kubectl get pod -n dss -l app=fastapi-mongodb-api -o jsonpath='{.items[0].metadata.name}') -- nc -zv mongodb-prod.dss.local 27017
```

### Problem 3: Ingress Not Accessible

**Symptoms:**
```bash
$ curl http://fastapi.dss.local/
curl: (6) Could not resolve host: fastapi.dss.local
```

**Solution:**

1. **Check Ingress status:**
   ```bash
   kubectl get ingress -n dss fastapi-ingress
   kubectl describe ingress -n dss fastapi-ingress
   ```

2. **Verify DNS/hosts:**
   ```bash
   # Add to /etc/hosts if needed
   <ingress-ip> fastapi.dss.local
   ```

3. **Check Ingress Controller:**
   ```bash
   kubectl get pods -n ingress-nginx
   kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
   ```

### Problem 4: "collections/" Returns Empty

**Symptoms:**
```json
{
  "collections": [],
  "count": 0
}
```

**Possible Causes:**

1. **Wrong database name** - Check ConfigMap
2. **No collections in database** - Verify MongoDB has data
3. **Permission issues** - User doesn't have list permissions

**Verify:**
```bash
# Connect to MongoDB directly
mongosh mongodb://mongodb-prod.dss.local:27017/edge_database -u api_user -p

# List collections
show collections
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `connection timeout` | MongoDB not reachable | Check hostname, network policies |
| `authentication failed` | Wrong credentials | Verify Secret values |
| `database does not exist` | Wrong DB name | Check ConfigMap database field |
| `ImagePullBackOff` | Can't pull image | Check image name, registry credentials |
| `503 Service Unavailable` | Service not ready | Check pod status, health probes |

---

## ❓ FAQ

### Q: Do I need to deploy MongoDB in Kubernetes?

**A: No!** This API connects to your **existing MongoDB**. The MongoDB in `docker-compose.yml` is only for local testing.

### Q: What if my MongoDB doesn't require authentication?

**A:** You can skip creating the Secret (02-secret.yaml). The Deployment has `optional: true` for credentials, so it will work without them.

### Q: Can I use the development Dockerfile in production?

**A:** No, use `deployment/docker/Dockerfile.prod`. The main `Dockerfile` has `--reload` which causes performance issues in production.

### Q: How many workers should I use?

**A:** Rule of thumb: `(2 × CPU cores) + 1`. Default is 4, which works for most deployments. Adjust in `Dockerfile.prod` if needed.

### Q: How do I enable HTTPS?

**A:** Configure TLS in the Ingress manifest. You'll need a TLS certificate stored as a Kubernetes Secret. See [05-ingress.yaml](kubernetes/05-ingress.yaml) comments.

### Q: Can I run this on Rancher?

**A:** Yes! Rancher uses Kubernetes underneath. Use the provided YAML files as-is, or import them via Rancher UI.

### Q: How do I update the application?

**A:**
```bash
# Build new version
docker build -f deployment/docker/Dockerfile.prod -t your-registry/mongo-fastapi:1.0.1 .
docker push your-registry/mongo-fastapi:1.0.1

# Update deployment
kubectl set image deployment/fastapi-mongodb-api fastapi=your-registry/mongo-fastapi:1.0.1 -n dss
```

### Q: What are the resource requirements?

**A:** Each pod requests:
- CPU: 250m (0.25 cores)
- Memory: 256Mi

Limits:
- CPU: 500m (0.5 cores)
- Memory: 512Mi

Adjust in `03-deployment.yaml` if needed.

---

## 📞 Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review [Kubernetes README](kubernetes/README.md)
3. Check pod logs: `kubectl logs -n dss -l app=fastapi-mongodb-api`
4. Inspect resources: `kubectl describe pod -n dss <pod-name>`

---

## 📝 Quick Reference Commands

```bash
# View all resources
kubectl get all -n dss -l app=fastapi-mongodb-api

# Restart deployment (rolling restart)
kubectl rollout restart deployment/fastapi-mongodb-api -n dss

# Scale replicas
kubectl scale deployment/fastapi-mongodb-api --replicas=3 -n dss

# View logs from all pods
kubectl logs -n dss -l app=fastapi-mongodb-api --all-containers=true --tail=100

# Port forward for local testing
kubectl port-forward -n dss svc/fastapi-service 8000:80

# Delete all resources
kubectl delete -f deployment/kubernetes/
```

---

**🎉 You're ready to deploy to production!**
