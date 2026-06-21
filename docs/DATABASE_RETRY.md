# Database Initialization with Retry Logic

## Overview

The application now includes automatic retry logic for database initialization. This ensures that the `connections` table is created even if PostgreSQL is not immediately available when the application starts.

## Problem Solved

In container orchestration environments (Kubernetes, Podman pods), services may start in unpredictable order. Previously:
- If the app started before PostgreSQL → Database initialization failed
- The `connections` table was never created
- Database features remained broken until manual intervention

## Solution

The application now:
1. **Retries database initialization** in a background thread
2. **Uses exponential backoff** to avoid overwhelming the database
3. **Continues retrying** until successful or max attempts reached
4. **Allows the app to start immediately** without blocking on database availability

## How It Works

### Retry Configuration

```python
max_retries = 10              # Maximum number of attempts
retry_delay = 1               # Initial delay: 1 second
max_delay = 60                # Maximum delay: 60 seconds
```

### Exponential Backoff Schedule

| Attempt | Delay (seconds) | Cumulative Time |
|---------|----------------|-----------------|
| 1       | 0              | 0s              |
| 2       | 1              | 1s              |
| 3       | 2              | 3s              |
| 4       | 4              | 7s              |
| 5       | 8              | 15s             |
| 6       | 16             | 31s             |
| 7       | 32             | 63s             |
| 8       | 60             | 123s            |
| 9       | 60             | 183s            |
| 10      | 60             | 243s (~4 min)   |

Total time: Up to ~4 minutes of retries

### Log Messages

**Successful initialization:**
```
🔄 Attempting database initialization (attempt 1/10)...
✅ Database tables initialized successfully
```

**Failed attempt with retry:**
```
🔄 Attempting database initialization (attempt 2/10)...
❌ Failed to initialize database tables: connection failed...
⏳ Retrying in 2 seconds...
```

**All attempts exhausted:**
```
❌ Failed to initialize database after 10 attempts
⚠️  Database features will not be available until database is ready
```

## Database Status Messages

The `/api/db-status` endpoint now shows initialization state:

### While initializing:
```json
{
  "connected": true,
  "message": "Connected (initializing...)",
  "visits": 0
}
```

### After successful initialization:
```json
{
  "connected": true,
  "message": "Connected",
  "visits": 5
}
```

### When database is down:
```json
{
  "connected": false,
  "message": "connection failed: Connection refused",
  "visits": 0
}
```

## Implementation Details

### Background Thread

Database initialization runs in a **daemon background thread**:
- Doesn't block Flask app startup
- Automatically terminates when main app exits
- Runs concurrently with request handling

### Global State Tracking

```python
db_initialized = False  # Tracks successful initialization
```

This flag:
- Set to `True` once table is created
- Prevents duplicate initialization attempts
- Can be checked by other functions if needed

### Connection Timeout

Each retry attempt uses a **5-second connection timeout**:
```python
connect_timeout=5
```

This ensures failed attempts don't hang indefinitely.

## Testing the Retry Logic

### Test 1: App Starts Before Database

```bash
# Create pod
podman pod create --name test-pod -p 8000:8000

# Start app first (database not available)
podman run -d --pod test-pod --name app \
  --env-file llm-maas-envs.txt \
  simple-web-server:latest

# Wait 5 seconds, then check logs
sleep 5
podman logs app | grep "Attempting database"

# Expected: See retry attempts

# Now start database
podman run -d --pod test-pod --name postgres \
  -e POSTGRES_PASSWORD=podman \
  postgres:latest

# Wait for PostgreSQL to initialize (5-10 seconds)
sleep 10

# Verify table was created
podman exec postgres psql -U postgres -c "\dt"

# Expected: connections table exists

# Test the API
curl http://localhost:8000/api/db-status

# Expected: {"connected": true, "message": "Connected", "visits": 0}
```

### Test 2: Database Starts First (Normal Case)

```bash
# Create pod
podman pod create --name test-pod -p 8000:8000

# Start database first
podman run -d --pod test-pod --name postgres \
  -e POSTGRES_PASSWORD=podman \
  postgres:latest

# Wait for PostgreSQL to initialize
sleep 5

# Start app
podman run -d --pod test-pod --name app \
  --env-file llm-maas-envs.txt \
  simple-web-server:latest

# Wait for app to start
sleep 3

# Check logs
podman logs app | grep "Database tables initialized"

# Expected: "✅ Database tables initialized successfully" on first attempt
```

### Test 3: Database Never Comes Up

```bash
# Create pod
podman pod create --name test-pod -p 8000:8000

# Start app without database
podman run -d --pod test-pod --name app \
  --env-file llm-maas-envs.txt \
  simple-web-server:latest

# Wait for all retries to complete (~4 minutes)
sleep 250

# Check final status
podman logs app | tail -20

# Expected: "❌ Failed to initialize database after 10 attempts"

# App should still be running and serving requests
curl http://localhost:8000/health

# Expected: {"status": "degraded", ...}
```

## Kubernetes Deployment Considerations

### Init Container (Alternative Approach)

If you prefer to wait for database before starting the app, use an init container:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: simple-web-server
spec:
  template:
    spec:
      initContainers:
      - name: wait-for-postgres
        image: postgres:latest
        command:
        - sh
        - -c
        - |
          until pg_isready -h postgres-service -U postgres; do
            echo "Waiting for postgres..."
            sleep 2
          done
      containers:
      - name: app
        image: simple-web-server:latest
```

### Readiness Probe

Use a readiness probe that checks database initialization:

```yaml
readinessProbe:
  httpGet:
    path: /api/db-status
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  successThreshold: 1
  failureThreshold: 3
```

The pod won't receive traffic until the database is initialized.

### Liveness Probe

Use a separate liveness probe that doesn't fail on database issues:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
  failureThreshold: 3
```

The `/health` endpoint returns `200` even when database is degraded.

## Configuration Options

### Adjust Retry Parameters

Edit `app.py` to customize retry behavior:

```python
def init_database_with_retry():
    max_retries = 20      # More attempts
    retry_delay = 2       # Start with longer delay
    max_delay = 120       # Allow up to 2 minutes between retries
    
    # ... rest of function
```

### Disable Retry Logic

If you want the old behavior (fail immediately):

```python
# Change this:
init_database_background()

# To this:
init_database_once()
```

## Troubleshooting

### Retries Keep Failing

**Check:**
1. Database is actually running: `podman ps | grep postgres`
2. Network connectivity: Ensure pods are in the same pod/network
3. Credentials are correct: Check `POSTGRES_PASSWORD` environment variable
4. Database accepts connections: `podman exec postgres pg_isready`

### Table Still Doesn't Exist After Retries

**Check:**
1. All retry attempts exhausted: Look for "Failed after 10 attempts" in logs
2. Permission issues: User might not have CREATE TABLE permission
3. Database name is wrong: Verify `POSTGRES_DB` matches actual database

**Manual fix:**
```bash
podman exec postgres psql -U postgres -c "
CREATE TABLE IF NOT EXISTS connections (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"
```

### Background Thread Not Logging

**Note:** Background thread output may not appear in container logs depending on how stdout is buffered. The functionality still works - verify by checking:

1. API endpoint: `curl http://localhost:8000/api/db-status`
2. Database directly: `podman exec postgres psql -U postgres -c "\dt"`

## Best Practices

1. **Use readiness probes** - Don't send traffic until database is ready
2. **Set appropriate timeouts** - 5 seconds is good for local/pod networking
3. **Monitor retry attempts** - Alert if initialization fails repeatedly
4. **Use init containers** - For critical dependencies that MUST be ready first
5. **Don't rely on timing** - The retry logic handles unpredictable startup order

## Future Enhancements

Potential improvements:
- Make retry parameters configurable via environment variables
- Add retry metrics/counters for monitoring
- Support for multiple table creation (migrations)
- Exponential backoff with jitter to prevent thundering herd
- Health check that fails if database never initializes
- Option to exit app if initialization fails after all retries
