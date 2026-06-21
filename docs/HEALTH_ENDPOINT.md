# Health Endpoint Documentation

## Overview
The application provides health check endpoints that can be used for container orchestration, monitoring, and load balancing.

## Endpoints

### `/health` and `/healthz`
Both endpoints provide identical functionality and return the same health status information.

**Method:** `GET`

**Response Format:** JSON

**HTTP Status Codes:**
- `200` - Service is healthy or degraded but operational
- `503` - Service is unhealthy (not currently implemented)

## Response Structure

### Healthy State

When all services are functioning normally:

```json
{
  "status": "healthy",
  "service": "simple-web-server",
  "checks": {
    "llm": {
      "configured": true,
      "url": "https://litellm-prod.apps.maas.redhatworkshops.io/v1",
      "model": "granite-3-2-8b-instruct"
    },
    "database": {
      "connected": true,
      "message": "Connected",
      "visits": 0
    }
  }
}
```

### Degraded State

When some services are unavailable but the application can still run:

```json
{
  "status": "degraded",
  "service": "simple-web-server",
  "checks": {
    "llm": {
      "configured": true,
      "url": "https://litellm-prod.apps.maas.redhatworkshops.io/v1",
      "model": "granite-3-2-8b-instruct"
    },
    "database": {
      "connected": false,
      "message": "connection failed: connection to server at \"127.0.0.1\", port 5432 failed: Connection refused",
      "visits": 0
    }
  }
}
```

## Health Checks Performed

### 1. LLM Service Check
Verifies that the LLM client is configured with:
- API key set
- Base URL configured
- Model name specified

**Fields:**
- `configured` (boolean) - Whether the LLM client is initialized
- `url` (string) - The LLM service base URL
- `model` (string) - The model being used

### 2. Database Check
Verifies PostgreSQL database connectivity:
- Attempts connection with 3-second timeout
- Retrieves total visit count
- Reports connection status

**Fields:**
- `connected` (boolean) - Whether database is reachable
- `message` (string) - Connection status or error message
- `visits` (integer) - Total number of recorded visits

## Status Determination

The overall `status` field can be:

- **`healthy`** - All services are operational
- **`degraded`** - Some services are unavailable but the application can still function
- **`unhealthy`** - Critical services are down (not currently implemented)

### Current Logic:
- If database is not connected → `degraded`
- If LLM is not configured → `degraded`
- If both are operational → `healthy`

## Usage Examples

### Basic Health Check

```bash
curl http://localhost:8000/health
```

### Pretty-printed Output

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

or

```bash
curl -s http://localhost:8000/health | jq
```

### Check HTTP Status Code Only

```bash
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/health
```

### Health Check with Timeout

```bash
curl --max-time 5 http://localhost:8000/health
```

## Container Orchestration Integration

### Docker/Podman Healthcheck

Add to your Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

Or use when running a container:

```bash
podman run -d \
  --name my-app \
  --health-cmd="curl -f http://localhost:8000/health || exit 1" \
  --health-interval=30s \
  --health-timeout=3s \
  --health-retries=3 \
  simple-web-server:latest
```

### Kubernetes Liveness Probe

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: simple-web-server
spec:
  containers:
  - name: app
    image: simple-web-server:latest
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 30
      timeoutSeconds: 3
      failureThreshold: 3
```

### Kubernetes Readiness Probe

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: simple-web-server
spec:
  containers:
  - name: app
    image: simple-web-server:latest
    readinessProbe:
      httpGet:
        path: /healthz
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 10
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
```

## Monitoring and Alerting

### Prometheus Monitoring

Example script to export health status as Prometheus metrics:

```bash
#!/bin/bash
# health-exporter.sh
while true; do
  STATUS=$(curl -s http://localhost:8000/health)
  HEALTH=$(echo $STATUS | jq -r '.status')
  DB_CONNECTED=$(echo $STATUS | jq -r '.checks.database.connected')
  LLM_CONFIGURED=$(echo $STATUS | jq -r '.checks.llm.configured')
  VISITS=$(echo $STATUS | jq -r '.checks.database.visits')

  echo "# HELP app_health Application health status"
  echo "# TYPE app_health gauge"
  echo "app_health{status=\"$HEALTH\"} $([ "$HEALTH" = "healthy" ] && echo 1 || echo 0)"
  
  echo "# HELP db_connected Database connection status"
  echo "# TYPE db_connected gauge"
  echo "db_connected $([ "$DB_CONNECTED" = "true" ] && echo 1 || echo 0)"
  
  echo "# HELP total_visits Total number of visits"
  echo "# TYPE total_visits counter"
  echo "total_visits $VISITS"
  
  sleep 15
done
```

### Simple Monitoring Script

```bash
#!/bin/bash
# monitor-health.sh

ENDPOINT="http://localhost:8000/health"
LOG_FILE="/var/log/app-health.log"

while true; do
  RESPONSE=$(curl -s -w "\n%{http_code}" "$ENDPOINT")
  STATUS_CODE=$(echo "$RESPONSE" | tail -n 1)
  BODY=$(echo "$RESPONSE" | head -n -1)
  HEALTH_STATUS=$(echo "$BODY" | jq -r '.status')
  
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  
  if [ "$STATUS_CODE" -eq 200 ] && [ "$HEALTH_STATUS" = "healthy" ]; then
    echo "[$TIMESTAMP] OK - Status: $HEALTH_STATUS" | tee -a "$LOG_FILE"
  else
    echo "[$TIMESTAMP] WARNING - Status: $HEALTH_STATUS (HTTP $STATUS_CODE)" | tee -a "$LOG_FILE"
    echo "$BODY" | jq '.' | tee -a "$LOG_FILE"
  fi
  
  sleep 60
done
```

## Testing Health States

### Test Healthy State

```bash
# Start pod with all services
podman pod create --name test-pod -p 8000:8000
podman run -d --pod test-pod --name postgres -e POSTGRES_PASSWORD=podman postgres:latest
sleep 5
podman run -d --pod test-pod --name app --env-file llm-maas-envs.txt simple-web-server:latest
sleep 3

# Check health
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected: `"status": "healthy"`

### Test Degraded State (Database Down)

```bash
# Stop the database
podman stop postgres
sleep 2

# Check health
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected: `"status": "degraded"` with database connection error

### Test Degraded State (LLM Not Configured)

```bash
# Run without LLM environment variables
podman run -d -p 8000:8000 --name app-no-llm simple-web-server:latest
sleep 3

# Check health
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected: `"status": "degraded"` with LLM not configured

## Load Balancer Integration

### HAProxy Backend Health Check

```
backend app_servers
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    server app1 192.168.1.10:8000 check inter 10s
    server app2 192.168.1.11:8000 check inter 10s
```

### NGINX Upstream Health Check

```nginx
upstream app_backend {
    server 192.168.1.10:8000 max_fails=3 fail_timeout=30s;
    server 192.168.1.11:8000 max_fails=3 fail_timeout=30s;
}

server {
    location /health {
        access_log off;
        proxy_pass http://app_backend;
    }
}
```

## Troubleshooting

### Health Endpoint Returns 404

**Issue:** Endpoint not found

**Solutions:**
- Verify the app is running: `podman ps`
- Check app logs: `podman logs <container-name>`
- Ensure you're using the correct port
- Verify the route is registered in Flask

### Health Endpoint Times Out

**Issue:** Request takes too long or hangs

**Solutions:**
- Database connection timeout is set to 3 seconds
- Check if database is responsive
- Check network connectivity between app and database
- Review app logs for errors

### Health Shows Degraded but Services Work

**Issue:** False negative health check

**Solutions:**
- Database might be slow but functional
- LLM configuration might be missing but app can still serve requests
- This is expected behavior - degraded means "working but not optimal"

### Health Check Frequency

**Recommendations:**
- **Liveness probe:** 30-60 seconds interval
- **Readiness probe:** 10-30 seconds interval
- **Monitoring:** 15-60 seconds interval
- Avoid too frequent checks (< 5 seconds) to prevent overhead

## Best Practices

1. **Use `/healthz` for Kubernetes** - It's the conventional endpoint name
2. **Use `/health` for general monitoring** - More human-readable
3. **Set appropriate timeouts** - Default 3 seconds for database check
4. **Don't use health checks for metrics** - Use dedicated metrics endpoints instead
5. **Log health check failures** - Monitor for patterns
6. **Test failure scenarios** - Ensure health checks accurately reflect service state
7. **Consider startup time** - Use `initialDelaySeconds` in Kubernetes probes

## Future Enhancements

Potential improvements:
- Add `/ready` endpoint for readiness checks separate from liveness
- Add `/live` endpoint for basic liveness (just Flask running)
- Include response time metrics
- Add version information
- Add uptime information
- Include memory and CPU usage
- Add custom health check plugins
- Support for weighted health scores
