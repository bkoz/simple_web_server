# OpenShift Deployment with Kustomize

This directory contains Kubernetes manifests for deploying a web application with PostgreSQL database to OpenShift using Kustomize.

## Architecture

Both the web server and PostgreSQL database run as **separate containers in the same pod**, enabling:
- Localhost communication between containers (no network overhead)
- Shared lifecycle and networking
- Simplified deployment model

## Components

- **simplewebserver**: Web application container (`quay.io/bkozdemb/simplewebserver`)
- **postgresql**: PostgreSQL database container (`quay.io/hummingbird/postgresql`)

## Resources

- `kustomization.yaml` - Kustomize configuration file
- `webserver-deployment.yaml` - Combined deployment with both containers in one pod
- `postgresql-service.yaml` - PostgreSQL service (port 5432)
- `webserver-service.yaml` - Web server service (port 8080)
- `webserver-route.yaml` - OpenShift route for external access
- `secret.env.example` - Template for required environment variables
- `HEALTHCHECKS.md` - Detailed health check configuration documentation

## Deployment

### 1. Login to OpenShift
```bash
oc login --token=<your-token> --server=<api-url>
```

### 2. Create or switch to your project
```bash
oc new-project my-app
# or
oc project my-app
```

### 3. Create database secret from environment file

Create a `secret.env` file with your database and LLM credentials:
```bash
cat > secret.env <<EOF
POSTGRES_USER=appuser
POSTGRES_PASSWORD=changeme123
POSTGRES_DB=appdb
DATABASE_URL=postgresql://appuser:changeme123@localhost:5432/appdb
LLM_URL=https://your-llm-service.example.com/v1
LLM_MODEL=granite-3-2-8b-instruct
LLM_API_KEY=your-api-key-here
EOF
```

Create the secret in OpenShift:
```bash
oc create secret generic database-secret --from-env-file=secret.env
```

**Alternative methods:**
```bash
# From individual literals
oc create secret generic database-secret \
  --from-literal=POSTGRES_USER=appuser \
  --from-literal=POSTGRES_PASSWORD=changeme123 \
  --from-literal=POSTGRES_DB=appdb \
  --from-literal=DATABASE_URL=postgresql://appuser:changeme123@postgresql:5432/appdb

# From individual files (filename becomes the key)
oc create secret generic database-secret \
  --from-file=POSTGRES_USER=./user.txt \
  --from-file=POSTGRES_PASSWORD=./password.txt
```

### 4. Deploy using Kustomize
```bash
oc apply -k kustomize/
```

### 5. Verify deployment
```bash
# Check all resources
oc get all

# Check pods
oc get pods

# Check routes
oc get routes

# View logs
oc logs -f deployment/simplewebserver
oc logs -f deployment/postgresql
```

### 6. Access the application
```bash
# Get the route URL
oc get route simplewebserver -o jsonpath='{.spec.host}'
```

Visit `https://<route-host>` in your browser.

## Configuration

### Environment Variables

All sensitive environment variables are stored in the `database-secret` Secret:

**Database Configuration:**
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_DB` - Database name
- `DATABASE_URL` - Full database connection string (uses localhost since containers share a pod)

**LLM Configuration:**
- `LLM_URL` - LLM API endpoint (e.g., https://maas-rhdp.apps.maas.redhatworkshops.io/v1)
- `LLM_MODEL` - Model name (e.g., granite-3-2-8b-instruct)
- `LLM_API_KEY` - API key for LLM service

To update secrets after deployment:
```bash
oc edit secret database-secret
# Then restart the deployment to pick up changes
oc rollout restart deployment/simplewebserver
```

### Scaling

Scale the web server:
```bash
oc scale deployment/simplewebserver --replicas=3
```

**Note**: PostgreSQL is configured with 1 replica and uses `emptyDir` for storage. For production, consider using a PersistentVolumeClaim.

### Health Checks

The deployment includes comprehensive health checks for both containers:

**PostgreSQL:**
- Startup probe: `pg_isready` (up to 30s)
- Liveness probe: `pg_isready` (simple connection check)
- Readiness probe: `pg_isready` + `SELECT 1` query (verifies query execution)

**Web Server:**
- Startup probe: HTTP GET `/health` (up to 60s for app initialization)
- Liveness probe: HTTP GET `/health` (every 10s)
- Readiness probe: HTTP GET `/health` (every 5s)

The `/health` endpoint checks database connectivity, LLM availability, and application status.

See [HEALTHCHECKS.md](HEALTHCHECKS.md) for detailed configuration and troubleshooting.

## Cleanup

Remove all resources:
```bash
oc delete -k kustomize/
```

## Customization

### Change namespace
Edit `kustomization.yaml` and update the `namespace` field.

### Add persistent storage for PostgreSQL
Create a `postgresql-pvc.yaml`:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgresql-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

Update `postgresql-deployment.yaml` to use the PVC instead of `emptyDir`.

### Customize resource limits
Edit the `resources` sections in the deployment files.
