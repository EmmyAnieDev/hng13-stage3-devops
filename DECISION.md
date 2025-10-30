# Implementation Decisions

## Approach

I implemented Blue/Green deployment using Nginx's native `backup` upstream directive for automatic failover rather than external health checking or manual switching mechanisms.

## Key Design Choices

### 1. Nginx Upstream Configuration
- **Primary/Backup Model**: Blue is primary, Green is backup
- **Rationale**: Nginx's built-in backup directive provides instant failover without external dependencies
- **Benefit**: Zero client-visible failures during primary service downtime

### 2. Tight Timeout Configuration
```nginx
proxy_connect_timeout 2s;
proxy_read_timeout 2s;
max_fails=2 fail_timeout=5s;
```
- **Rationale**: Fast failure detection ensures quick failover (<5 seconds)
- **Trade-off**: Aggressive timeouts may cause false positives under high load, but meet task requirements for quick response

### 3. Template-Based Configuration
- Used `.template` files instead of hardcoded values
- **Rationale**: Allows CI/grader to parameterize deployment via `.env`
- **Benefit**: Same config works across environments without modification

### 4. Retry Strategy
```nginx
proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
proxy_next_upstream_tries 3;
```
- **Rationale**: Failed requests automatically retry on backup within same client request
- **Result**: Client always receives 200 OK, never sees upstream failures

## What Could Be Improved

- **Active Health Checks**: Current solution relies on passive failure detection. Active health checks (nginx-plus or external tool) would detect issues before client impact
- **Gradual Failback**: Currently fails back immediately when Blue recovers. Gradual traffic shifting would be safer
- **Monitoring**: No metrics/alerting included. Production would need observability

## Why This Works

The task required automatic failover with zero failed requests. Nginx's backup directive + aggressive timeouts + retry logic achieves this without complex orchestration or health checking systems.