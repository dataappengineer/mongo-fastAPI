# Kubernetes Deployment - Quick Reference

## Prerequisites

- Kubernetes cluster (or Rancher) with `kubectl` access
- Namespace `dss` created (or use existing namespace)
- MongoDB already running and accessible from the cluster
- Docker image built and pushed to your registry

## Quick Start

### 1. Configure MongoDB Connection

Edit [`01-configmap.yaml`](01-configmap.yaml) with your MongoDB details:

```yaml
data:
  host: "your-mongodb-hostname"  # Your MongoDB hostname/IP
  port: "27017"                   # Your MongoDB port
  database: "your_database_name"  # Your database name
```

### 2. Configure Credentials (Optional)

If your MongoDB requires authentication, edit [`02-secret.yaml`](02-secret.yaml):

```yaml
stringData:
  username: "your_username"
  password: "your_secure_password"
```

**⚠️ IMPORTANT:** Never commit real passwords to Git!

### 3. Update Docker Image

Edit [`03-deployment.yaml`](03-deployment.yaml) line 35:

```yaml
image: your-registry/mongo-fastapi:latest  # Your registry and image
```

### 4. Update Hostname

Edit [`05-ingress.yaml`](05-ingress.yaml) line 29:

```yaml
- host: fastapi.dss.local  # Your actual hostname
```

### 5. Apply Kubernetes Manifests

```bash
# Apply in order (files are numbered for correct sequence)
kubectl apply -f 00-namespace.yaml      # Optional: skip if namespace exists
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secret.yaml         # Optional: skip if no auth
kubectl apply -f 03-deployment.yaml
kubectl apply -f 04-service.yaml
kubectl apply -f 05-ingress.yaml

# Or apply all at once:
kubectl apply -f .
```

### 6. Verify Deployment

```bash
# Check pods are running
kubectl get pods -n dss -l app=fastapi-mongodb-api

# Check logs
kubectl logs -n dss -l app=fastapi-mongodb-api --tail=50

# Check service
kubectl get svc -n dss fastapi-service

# Check ingress
kubectl get ingress -n dss fastapi-ingress
```

## Testing

### Test Endpoints

```bash
# Health check (should show MongoDB connection status)
curl http://fastapi.dss.local/health

# Root endpoint
curl http://fastapi.dss.local/

# List collections (tests MongoDB connectivity)
curl http://fastapi.dss.local/collections/

# API documentation
# Open in browser: http://fastapi.dss.local/docs
```

### Expected Responses

**Healthy:**
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "database": "your_database_name",
  "version": "1.0.0"
}
```

**Unhealthy (MongoDB connection issue):**
```json
{
  "status": "unhealthy",
  "mongodb": "disconnected",
  "error": "connection timeout...",
  "version": "1.0.0"
}
```

## Troubleshooting

### Pod in CrashLoopBackOff

```bash
# View logs from previous crashed container
kubectl logs -n dss -l app=fastapi-mongodb-api --previous

# Describe pod to see events
kubectl describe pod -n dss -l app=fastapi-mongodb-api
```

**Common causes:**
- MongoDB hostname not resolvable
- MongoDB not accessible from pod's network
- Wrong credentials in Secret
- ConfigMap or Secret not applied

### Health Check Fails

```bash
# Execute command inside pod
kubectl exec -n dss -it $(kubectl get pod -n dss -l app=fastapi-mongodb-api -o jsonpath='{.items[0].metadata.name}') -- curl localhost:8000/health

# Test MongoDB connection from inside pod
kubectl exec -n dss -it $(kubectl get pod -n dss -l app=fastapi-mongodb-api -o jsonpath='{.items[0].metadata.name}') -- python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(f'mongodb://{os.getenv(\"MONGO_HOST\")}:{os.getenv(\"MONGO_PORT\")}/')
print(client.admin.command('ping'))
"
```

### Ingress Not Reachable

```bash
# Check DNS resolution
ping fastapi.dss.local

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller

# Verify ingress configuration
kubectl describe ingress -n dss fastapi-ingress
```

## Scaling

```bash
# Scale to 4 replicas
kubectl scale deployment/fastapi-mongodb-api --replicas=4 -n dss

# Configure Horizontal Pod Autoscaler (HPA)
kubectl autoscale deployment/fastapi-mongodb-api \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n dss
```

## Updates

```bash
# Update image
kubectl set image deployment/fastapi-mongodb-api \
  fastapi=your-registry/mongo-fastapi:v1.0.1 \
  -n dss

# Rollback to previous version
kubectl rollout undo deployment/fastapi-mongodb-api -n dss

# View rollout history
kubectl rollout history deployment/fastapi-mongodb-api -n dss
```

## Cleanup

```bash
# Delete all resources
kubectl delete -f .

# Or delete individual resources
kubectl delete deployment fastapi-mongodb-api -n dss
kubectl delete service fastapi-service -n dss
kubectl delete ingress fastapi-ingress -n dss
kubectl delete configmap mongodb-config -n dss
kubectl delete secret mongodb-credentials -n dss
```

## Security Best Practices

1. **Never commit Secret files with real passwords to Git**
2. Use `kubectl create secret` from command line instead
3. Enable RBAC and limit service account permissions
4. Use Network Policies to restrict pod-to-pod communication
5. Enable TLS/HTTPS for Ingress in production
6. Regularly update Docker images with security patches
7. Set resource limits to prevent resource exhaustion

## Need Help?

See the main deployment guide: [`../README.md`](../README.md)
