# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the Flask chatbot application.

## Files

- `secret.yaml` - Stores LLM configuration as a Kubernetes Secret
- `deployment.yaml` - Deployment configuration for the Flask app
- `service.yaml` - LoadBalancer service to expose the app

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t simple-web-server:latest .
```

### 2. Create the Secret

**Option A: From your .env file (recommended)**
```bash
kubectl create secret generic llm-config --from-env-file=.env
```

**Option B: From literal values**
```bash
kubectl create secret generic llm-config \
  --from-literal=LLM_URL=https://api.openai.com/v1 \
  --from-literal=LLM_API_KEY=your-actual-api-key \
  --from-literal=LLM_MODEL=gpt-3.5-turbo
```

**Option C: From the YAML file (update values first)**
```bash
# Edit k8s/secret.yaml with your actual values
kubectl apply -f k8s/secret.yaml
```

### 3. Deploy the Application

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Or apply all at once:
```bash
kubectl apply -f k8s/
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -l app=simple-web-server

# Check service
kubectl get svc simple-web-server

# View logs
kubectl logs -l app=simple-web-server --tail=50
```

### 5. Access the Application

```bash
# Get the external IP
kubectl get svc simple-web-server

# Access at http://<EXTERNAL-IP>
```

## Managing Secrets

### View Secret (base64 encoded)
```bash
kubectl get secret llm-config -o yaml
```

### Decode Secret Values
```bash
kubectl get secret llm-config -o jsonpath='{.data.LLM_API_KEY}' | base64 -d
```

### Update Secret
```bash
# Delete and recreate
kubectl delete secret llm-config
kubectl create secret generic llm-config --from-env-file=.env

# Or edit directly
kubectl edit secret llm-config
```

### After updating the secret, restart pods
```bash
kubectl rollout restart deployment/simple-web-server
```

## Security Best Practices

1. **Never commit secrets to git** - The `secret.yaml` contains placeholder values only
2. **Use separate secrets per environment** - dev, staging, production
3. **Enable encryption at rest** - Configure etcd encryption
4. **Use RBAC** - Limit who can read secrets
5. **Consider external secret management** - Use tools like:
   - AWS Secrets Manager + External Secrets Operator
   - HashiCorp Vault
   - Google Secret Manager
   - Azure Key Vault

## Cleanup

```bash
kubectl delete -f k8s/
kubectl delete secret llm-config
```

## Notes

- The deployment uses `envFrom` to load all secret keys as environment variables
- The Dockerfile already exists in the project root
- Service type is `LoadBalancer` - change to `ClusterIP` or `NodePort` if needed
- Default replicas: 2 (adjust in deployment.yaml)
