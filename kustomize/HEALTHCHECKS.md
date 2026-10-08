# Health Check Configuration

This document describes the health check configuration for the combined pod deployment.

## Overview

The pod contains two containers (PostgreSQL and Web Server), each with three types of health probes:
- **Startup Probe**: Determines when the container has started successfully
- **Liveness Probe**: Detects if the container is alive (restarts if failed)
- **Readiness Probe**: Determines if the container is ready to serve traffic

## PostgreSQL Container Health Checks

### Startup Probe
```yaml
startupProbe:
  exec:
    command: ["/bin/sh", "-c", "pg_isready -U $POSTGRES_USER"]
  initialDelaySeconds: 5
  periodSeconds: 3
  failureThreshold: 10
  timeoutSeconds: 3
```
- **Purpose**: Waits up to 30 seconds (3s × 10 failures) for PostgreSQL to start
- **Check**: Uses `pg_isready` to verify PostgreSQL is accepting connections

### Liveness Probe
```yaml
livenessProbe:
  exec:
    command: ["/bin/sh", "-c", "pg_isready -U $POSTGRES_USER"]
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 5
```
- **Purpose**: Ensures PostgreSQL process is running
- **Check**: Simple `pg_isready` check
- **Restart**: After 3 consecutive failures (30 seconds)

### Readiness Probe
```yaml
readinessProbe:
  exec:
    command: 
      - /bin/sh
      - -c
      - pg_isready -U $POSTGRES_USER && psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'SELECT 1' > /dev/null
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3
  timeoutSeconds: 3
```
- **Purpose**: Verifies PostgreSQL can accept queries
- **Check**: 
  1. `pg_isready` - Server is accepting connections
  2. `psql ... SELECT 1` - Can execute queries successfully
- **Traffic**: Removed from service after 3 failures (15 seconds)

## Web Server Container Health Checks

### Startup Probe
```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 12
  timeoutSeconds: 3
```
- **Purpose**: Allows up to 60 seconds (5s × 12 failures) for application startup
- **Check**: HTTP GET to `/health` endpoint
- **Why**: Gives time for database initialization and LLM connection tests

### Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 5
```
- **Purpose**: Ensures web server is alive and responding
- **Check**: HTTP GET to `/health` endpoint
- **Restart**: After 3 consecutive failures (30 seconds)

### Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 5
  failureThreshold: 2
  timeoutSeconds: 3
```
- **Purpose**: Determines if web server can handle requests
- **Check**: HTTP GET to `/health` endpoint
- **Traffic**: Removed from service after 2 failures (10 seconds)

## Health Endpoint Details

The web server's `/health` endpoint performs comprehensive checks:
- Database connectivity (PostgreSQL)
- LLM service availability
- Application initialization status

Example response:
```json
{
  "status": "healthy",
  "database": "connected",
  "llm": "available"
}
```

## Monitoring Health Checks

### Check probe status
```bash
# View detailed pod description
oc describe pod -l app=simplewebserver

# Check container status
oc get pods -l app=simplewebserver -o json | \
  jq '.items[0].status.containerStatuses[] | {name, ready, started}'
```

### View health check failures
```bash
# Watch pod events for probe failures
oc get events --field-selector involvedObject.name=<pod-name> --watch

# Filter for Liveness/Readiness events
oc get events | grep -E "(Liveness|Readiness|Startup)"
```

### Test health endpoint directly
```bash
# Port-forward to test locally
oc port-forward deployment/simplewebserver 8000:8000

# In another terminal
curl http://localhost:8000/health
```

## Troubleshooting

### Pod stuck in startup
- Check startup probe failure count: `oc describe pod <pod-name>`
- View container logs: `oc logs <pod-name> -c webserver`
- Common causes: Database not ready, LLM service unreachable

### Container restart loops
- Check liveness probe failures in events
- Review application logs for crashes
- Verify resource limits aren't too restrictive

### Pod not receiving traffic
- Check readiness probe status
- Ensure `/health` endpoint returns 200 status
- Verify database and LLM connectivity

## Best Practices

1. **Startup probes** should be generous - allow time for initialization
2. **Liveness probes** should be simple - just verify the process is alive
3. **Readiness probes** can be comprehensive - verify all dependencies
4. **Timing**: startup → liveness/readiness (startup disables others until successful)
5. **Failure thresholds**: Balance between quick detection and false positives
