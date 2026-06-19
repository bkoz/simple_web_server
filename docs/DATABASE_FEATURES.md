# Database Features

## Overview
The application now includes database connection monitoring and IP address logging functionality.

## Features

### 1. Database Connection Status Indicator

A real-time status indicator is displayed on the web page showing the database connection status.

**Visual Indicator:**
- 🟢 **Green LED** - Database connected successfully
- 🔴 **Red LED** - Database disconnected or error
- ⚪ **Gray LED** - Checking status (initial state)

**Location:** Top of the page, below the "LLM Chatter" heading

**Display Information:**
- Connection status (Connected/Disconnected)
- Total visit count (e.g., "(8 visits)")

**Behavior:**
- Checks database status on page load
- Auto-refreshes every 30 seconds
- Displays "Connected" or "Disconnected" status message
- Shows total number of visits when connected
- Visit count updates automatically every 30 seconds

**API Endpoint:** `GET /api/db-status`

Response format:
```json
{
  "connected": true,
  "message": "Connected",
  "visits": 8
}
```

### 2. IP Address Connection Logging

Every time a user accesses the application home page, their IP address is logged to the database.

**Database Table:** `connections`

Schema:
```sql
CREATE TABLE connections (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Logged Information:**
- IP address (supports both IPv4 and IPv6)
- Timestamp (automatic)
- Unique ID (auto-incrementing)

**IP Detection:**
- Checks `X-Forwarded-For` header first (for proxy/load balancer scenarios)
- Falls back to `request.remote_addr`
- Handles comma-separated IP lists (takes first IP)

## Implementation Details

### Database Initialization

On application startup:
1. Tests database connection
2. Creates `connections` table if it doesn't exist
3. Prints initialization status to console

### Connection Logging

When a user visits the home page (`/`):
1. Extracts client IP address
2. Inserts IP and timestamp into database
3. Logs the action to console (in non-production environments)

Console output example:
```
📝 Logged connection from IP: 192.168.127.1
```

### Status Checking

The `/api/db-status` endpoint:
1. Attempts to connect to PostgreSQL with 3-second timeout
2. Returns connection status as JSON
3. Handles errors gracefully

## Testing the Features

### Test Database Status Indicator

1. Start the application in a pod with PostgreSQL:
```bash
podman pod create --name test-pod -p 8000:8000
podman run -d --pod test-pod --name postgres -e POSTGRES_PASSWORD=podman postgres:latest
sleep 5
podman run -d --pod test-pod --name app --env-file llm-maas-envs.txt simple-web-server:latest
```

2. Open browser to `http://localhost:8000`
3. Verify the green LED indicator shows "Connected"

4. Stop PostgreSQL to test disconnected state:
```bash
podman stop postgres
```

5. Wait 30 seconds or refresh the page
6. Verify the LED turns red and shows "Disconnected"

### Test IP Logging

1. Visit the application home page multiple times:
```bash
curl http://localhost:8000/
curl http://localhost:8000/
curl http://localhost:8000/
```

2. Query the database to see logged connections:
```bash
podman exec postgres psql -U postgres -c "SELECT * FROM connections;"
```

Expected output:
```
 id |  ip_address   |         timestamp          
----+---------------+----------------------------
  1 | 192.168.127.1 | 2026-06-18 21:44:35.811568
  2 | 192.168.127.1 | 2026-06-18 21:44:35.863721
  3 | 192.168.127.1 | 2026-06-18 21:44:35.887627
(3 rows)
```

3. Get connection statistics:
```bash
podman exec postgres psql -U postgres -c "
  SELECT 
    COUNT(*) as total_connections, 
    COUNT(DISTINCT ip_address) as unique_ips 
  FROM connections;
"
```

## Database Queries

### View all connections
```sql
SELECT * FROM connections ORDER BY timestamp DESC;
```

### Count total connections
```sql
SELECT COUNT(*) FROM connections;
```

### Count unique IP addresses
```sql
SELECT COUNT(DISTINCT ip_address) FROM connections;
```

### Top IP addresses by connection count
```sql
SELECT 
    ip_address, 
    COUNT(*) as connection_count,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen
FROM connections 
GROUP BY ip_address 
ORDER BY connection_count DESC;
```

### Connections in the last hour
```sql
SELECT * FROM connections 
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

## Error Handling

### Database Not Configured
If `POSTGRES_PASSWORD` is not set:
- Status indicator shows gray LED
- Status message: "Database not configured"
- IP logging is skipped (no errors)
- Application continues to function normally

### Database Connection Fails
If PostgreSQL is unreachable:
- Status indicator shows red LED
- Status message shows error details
- IP logging attempts are logged but don't crash the app
- Console shows error: `❌ Failed to log connection: [error details]`

### Database Initialization Fails
If table creation fails:
- Error is logged to console
- Application continues to run
- IP logging will fail but won't crash the app

## Security Considerations

### IP Address Privacy
- IP addresses are stored in plain text
- Consider implementing IP anonymization for production
- Comply with privacy regulations (GDPR, CCPA, etc.)

### Database Access
- Use strong passwords for PostgreSQL
- Limit database user permissions to only required tables
- Use connection timeouts to prevent hanging connections

### SQL Injection Protection
- All queries use parameterized statements (via psycopg)
- No user input is directly interpolated into SQL

## Podman Commands to Query Database

### List All Connections

Find your PostgreSQL container name:
```bash
podman ps --filter name=postgres
```

Query all connections (most recent first):
```bash
podman exec <postgres-container-name> psql -U postgres -c "SELECT * FROM connections ORDER BY timestamp DESC;"
```

Example output:
```
 id |  ip_address   |         timestamp          
----+---------------+----------------------------
  5 | 192.168.127.1 | 2026-06-18 21:53:34.73307
  4 | 192.168.127.1 | 2026-06-18 21:53:34.7076
  3 | 192.168.127.1 | 2026-06-18 21:53:34.681822
  2 | 192.168.127.1 | 2026-06-18 21:53:34.655499
  1 | 192.168.127.1 | 2026-06-18 21:53:34.589189
(5 rows)
```

### View Connection Statistics

Total connections and unique IPs:
```bash
podman exec <postgres-container-name> psql -U postgres -c "SELECT COUNT(*) as total_connections, COUNT(DISTINCT ip_address) as unique_ips FROM connections;"
```

Example output:
```
 total_connections | unique_ips 
-------------------+------------
                 5 |          1
(1 row)
```

### View Per-IP Statistics

Group connections by IP address:
```bash
podman exec <postgres-container-name> psql -U postgres -c "SELECT ip_address, COUNT(*) as visits, MIN(timestamp) as first_visit, MAX(timestamp) as last_visit FROM connections GROUP BY ip_address ORDER BY visits DESC;"
```

Example output:
```
  ip_address   | visits |        first_visit         |        last_visit         
---------------+--------+----------------------------+---------------------------
 192.168.127.1 |      5 | 2026-06-18 21:53:34.589189 | 2026-06-18 21:53:34.73307
(1 row)
```

### View Recent Connections (Last 10)

```bash
podman exec <postgres-container-name> psql -U postgres -c "SELECT * FROM connections ORDER BY timestamp DESC LIMIT 10;"
```

### View Connections from Last Hour

```bash
podman exec <postgres-container-name> psql -U postgres -c "SELECT * FROM connections WHERE timestamp > NOW() - INTERVAL '1 hour' ORDER BY timestamp DESC;"
```

### Interactive PostgreSQL Shell

For more complex queries, enter the PostgreSQL shell:
```bash
podman exec -it <postgres-container-name> psql -U postgres
```

Then you can run queries directly:
```sql
postgres=# SELECT * FROM connections;
postgres=# \d connections  -- Show table structure
postgres=# \q  -- Exit
```

### Complete Testing Example

```bash
# 1. Create a test pod
podman pod create --name db-test-pod -p 8004:8000

# 2. Start PostgreSQL
podman run -d --pod db-test-pod --name db-test-postgres -e POSTGRES_PASSWORD=podman postgres:latest

# 3. Wait for PostgreSQL to initialize
sleep 5

# 4. Start the app
podman run -d --pod db-test-pod --name db-test-app --env-file llm-maas-envs.txt simple-web-server:latest

# 5. Wait for app to initialize
sleep 3

# 6. Generate some connections
curl -s http://localhost:8004/ > /dev/null
curl -s http://localhost:8004/ > /dev/null
curl -s http://localhost:8004/ > /dev/null
curl -s http://localhost:8004/ > /dev/null
curl -s http://localhost:8004/ > /dev/null

# 7. View connections in database
podman exec db-test-postgres psql -U postgres -c "SELECT * FROM connections ORDER BY timestamp DESC;"

# 8. View statistics
podman exec db-test-postgres psql -U postgres -c "SELECT COUNT(*) as total_connections, COUNT(DISTINCT ip_address) as unique_ips FROM connections;"

# 9. Clean up when done
podman pod stop db-test-pod
podman pod rm db-test-pod
```

## Future Enhancements

Potential improvements:
- Add connection analytics dashboard
- Implement IP geolocation
- Add user session tracking
- Create data retention/cleanup policies
- Add metrics export (Prometheus format)
- Implement connection rate limiting
- Add IP anonymization option
