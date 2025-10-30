# Blue/Green Deployment - Observability & Alerting (Stage 3)

This project extends the [Stage 2 Blue/Green Deployment](https://github.com/EmmyAnieDev/hng13-stage2-devops.git) with comprehensive observability and real-time Slack alerting for failover detection and error rate monitoring.

## What's New in Stage 3

- 📊 **Structured JSON Logging**: Nginx logs in JSON format with pool, release, and upstream status tracking
- 🔔 **Slack Alerting**: Real-time notifications for failovers and high error rates
- 🔍 **Automated Monitoring**: Python watcher service that analyzes logs continuously
- 📈 **Error Rate Tracking**: Sliding window monitoring (default: last 200 requests)
- 🎨 **Smart Color Coding**: Red alerts for failures, green for recoveries

## Prerequisites

- Docker & Docker Compose
- Slack Workspace with webhook URL ([Create one here](https://api.slack.com/messaging/webhooks))

## Quick Start

1. **Clone the repository**
```bash
git https://github.com/EmmyAnieDev/hng13-stage3-devops.git
cd hng13-stage3-devops
```

2. **Configure environment variables**

Copy `.env.example` to `.env` and add your Slack webhook:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Application Images
BLUE_IMAGE=your-blue-image:latest
GREEN_IMAGE=your-green-image:latest

# Active pool
ACTIVE_POOL=blue

# Release IDs
RELEASE_ID_BLUE=blue-v1.0.0
RELEASE_ID_GREEN=green-v1.0.0

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Alert Settings
ERROR_RATE_THRESHOLD=2
WINDOW_SIZE=200
ALERT_COOLDOWN_SEC=30
MAINTENANCE_MODE=false
```

3. **Start all services**
```bash
docker-compose up -d
```

4. **Verify deployment**
```bash
curl http://localhost:8080/version
```

## Service Endpoints

- **Nginx (Public)**: `http://localhost:8080`
- **Blue (Direct)**: `http://localhost:8081`
- **Green (Direct)**: `http://localhost:8082`

## Alert Types

### 1. 🔴 Failover Alert (Blue → Green)
Triggered when primary pool fails and traffic switches to backup.

**Example:**
```
⚠️ FAILOVER Alert
Failover detected: blue → green
Previous Pool: blue
Current Pool: green
```

### 2. 🟢 Failover Alert (Green → Blue)
Triggered when system recovers and traffic returns to primary.

**Example:**
```
✅ FAILOVER Alert
Failover detected: green → blue
Previous Pool: green
Current Pool: blue
```

### 3. 🚨 Error Rate Alert
Triggered when error rate exceeds threshold (default: 2%).

**Example:**
```
🚨 ERROR RATE Alert
High error rate: 8.50% (threshold: 2.0%)
Requests with Errors: 17
Total Requests: 200
```

## Testing the System

### Test Failover Detection

1. **Trigger chaos on Blue**
```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
```

2. **Generate traffic to trigger failover**
```bash
for i in {1..20}; do curl http://localhost:8080/version; sleep 0.5; done
```

3. **Check Slack** - You should receive a red failover alert (Blue → Green)

4. **Stop chaos and trigger failback**
```bash
curl -X POST "http://localhost:8081/chaos/stop"
sleep 6
for i in {1..20}; do curl http://localhost:8080/version; sleep 0.5; done
```

5. **Check Slack** - You should receive a green failover alert (Green → Blue)

### Test Error Rate Detection

1. **Start chaos mode**
```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
```

2. **Generate high-error traffic**
```bash
for i in {1..250}; do curl -s http://localhost:8080/version > /dev/null; done
```

3. **Check Slack** - You should receive a high error rate alert

4. **Clean up**
```bash
curl -X POST "http://localhost:8081/chaos/stop"
```

## Architecture

### Components

- **Blue/Green Services**: Application instances with health checks and chaos endpoints
- **Nginx**: Load balancer with JSON logging and automatic failover
- **Alert Watcher**: Python service monitoring logs and sending Slack alerts

### Monitoring Flow
```
Nginx → JSON Logs → Alert Watcher → Slack
  ↓
Detects failover/errors → Analyzes patterns → Sends alerts
```

## Configuration

### Alert Thresholds

Customize in `.env`:
```env
ERROR_RATE_THRESHOLD=2        # Percentage (default: 2%)
WINDOW_SIZE=200               # Number of requests to track
ALERT_COOLDOWN_SEC=30         # Seconds between same alert type
MAINTENANCE_MODE=false        # Set true to suppress alerts
```

### Log Format

Nginx logs are structured JSON with:
- `timestamp`: ISO 8601 format
- `status`: Final HTTP status
- `upstream_status`: Status from each upstream attempt
- `pool`: Active pool (blue/green)
- `release`: Release ID
- `request_time`: Total request duration
- `upstream_response_time`: Backend response time

**Example log entry:**
```json
{
  "timestamp": "2025-10-30T18:11:00+00:00",
  "status": 200,
  "upstream_status": "500, 500, 200",
  "pool": "green",
  "release": "green-v1.0.0",
  "request_time": 0.002
}
```

## Viewing Logs
```bash
# View recent nginx logs (JSON format)
cat nginx/logs/access.log | tail -10

# Pretty print JSON
cat nginx/logs/access.log | tail -5 | jq .

# View watcher logs
docker logs alert_watcher -f

# View container logs
docker logs app_blue --tail 50
docker logs app_green --tail 50
```

## Maintenance Mode

Suppress alerts during planned maintenance:
```bash
# Enable maintenance mode
# Edit .env: MAINTENANCE_MODE=true
docker-compose restart alert_watcher

# Disable after maintenance
# Edit .env: MAINTENANCE_MODE=false
docker-compose restart alert_watcher
```

## Project Structure
```
.
├── docker-compose.yml              # Service orchestration
├── nginx/
│   ├── conf.d/
│   │   └── default.conf.template   # Nginx config with JSON logging
│   └── logs/                       # Nginx logs (gitignored)
│       ├── access.log
│       └── error.log
├── watcher.py                      # Alert monitoring service
├── .env                            # Environment configuration
├── .env.example                    # Example configuration
├── runbook.md                      # Operational procedures
└── README.md                       # This file
```

## Troubleshooting

### No Slack Alerts

1. Verify Slack webhook URL in `.env`
2. Test webhook manually:
```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test alert"}'
```
3. Check watcher logs: `docker logs alert_watcher`

### Alerts Not Triggered

1. Ensure traffic is flowing: `for i in {1..10}; do curl http://localhost:8080/version; done`
2. Check cooldown period hasn't suppressed alerts
3. Verify watcher is running: `docker ps | grep alert_watcher`

### False Positives

1. Increase error rate threshold: `ERROR_RATE_THRESHOLD=5`
2. Increase window size: `WINDOW_SIZE=500`
3. Increase cooldown: `ALERT_COOLDOWN_SEC=300`

## Stopping Services
```bash
docker-compose down
```

## Related Resources

- [Stage 2 - Blue/Green Deployment](https://github.com/EmmyAnieDev/hng13-stage2-devops.git)
- [Runbook](./runbook.md) - Operational procedures
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)

## Key Features

✅ Zero-downtime failover detection  
✅ Real-time Slack notifications  
✅ Structured JSON logging  
✅ Sliding window error rate tracking  
✅ Automatic failback detection  
✅ Color-coded alerts (red=failure, green=recovery)  
✅ Configurable thresholds  
✅ Maintenance mode support  

---

Built as part of HNG Stage 3 DevOps Challenge