import os
import json
import time
import logging
import requests
from collections import deque
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class LogWatcher:
    """
    Watches Nginx access logs for failovers and high error rates,
    sending alerts to Slack when thresholds are exceeded.
    """
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
        self.error_threshold = float(os.getenv('ERROR_RATE_THRESHOLD', '2'))
        self.window_size = int(os.getenv('WINDOW_SIZE', '200'))
        self.cooldown_sec = int(os.getenv('ALERT_COOLDOWN_SEC', '300'))
        self.maintenance_mode = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
        self.log_file = '/var/log/nginx/access.log'
        
        self.last_pool = None
        self.request_window = deque(maxlen=self.window_size)
        self.last_failover_alert = 0
        self.last_error_rate_alert = 0
        
        # Stats for monitoring
        self.total_requests = 0
        self.total_errors = 0
        
        logger.info("=" * 70)
        logger.info("[WATCHER] Blue/Green Deployment Monitor - INITIALIZED")
        logger.info("=" * 70)
        logger.info(f"[CONFIG] Error Rate Threshold: {self.error_threshold}%")
        logger.info(f"[CONFIG] Sliding Window Size: {self.window_size} requests")
        logger.info(f"[CONFIG] Alert Cooldown: {self.cooldown_sec} seconds")
        logger.info(f"[CONFIG] Maintenance Mode: {self.maintenance_mode}")
        logger.info(f"[CONFIG] Slack Webhook: {'✓ Configured' if self.slack_webhook else '✗ Not configured'}")
        logger.info(f"[CONFIG] Log File: {self.log_file}")
        logger.info("=" * 70)

        # Send startup notification to Slack
        self.send_startup_notification()
        

    def send_startup_notification(self):
        """
        Sends a beautiful startup notification to Slack when the watcher starts.
        """
        if not self.slack_webhook:
            logger.info("[STARTUP] Skipping Slack notification (webhook not configured)")
            return
        
        startup_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        slack_payload = {
            "attachments": [{
                "color": "#36A2EB",  # Beautiful blue
                "title": "🚀 Blue/Green Monitor - Online",
                "text": "Log watcher has successfully started and is now monitoring your deployment.",
                "fields": [
                    {"title": "Status", "value": "✅ Active", "short": True},
                    {"title": "Started At", "value": startup_time, "short": True},
                    {"title": "Error Threshold", "value": f"{self.error_threshold}%", "short": True},
                    {"title": "Window Size", "value": f"{self.window_size} requests", "short": True},
                    {"title": "Alert Cooldown", "value": f"{self.cooldown_sec}s", "short": True},
                    {"title": "Maintenance Mode", "value": "🔧 Enabled" if self.maintenance_mode else "✓ Disabled", "short": True}
                ],
                "footer": "Blue/Green Monitor",
                "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                "ts": int(time.time())
            }]
        }
        
        try:
            logger.info("[STARTUP] Sending startup notification to Slack...")
            response = requests.post(self.slack_webhook, json=slack_payload, timeout=5)
            if response.status_code == 200:
                logger.info("[STARTUP] ✓ Startup notification sent successfully")
            else:
                logger.error(f"[STARTUP] ✗ Failed to send notification: {response.status_code}")
        except Exception as e:
            logger.error(f"[STARTUP] ✗ Error sending notification: {e}")


    def send_slack_alert(self, alert_type, message, details=None, from_pool=None, to_pool=None):
        """
        Sends a formatted alert to Slack.
        alert_type: 'failover' or 'error_rate'
        message: Main alert message
        details: Additional details as a dict
        from_pool: Previous pool in case of failover
        to_pool: Current pool in case of failover
        """
        now = time.time()
        
        if self.maintenance_mode:
            logger.info(f"[MAINTENANCE] Alert suppressed: {alert_type}")
            return
        
        if alert_type == 'failover':
            if now - self.last_failover_alert < self.cooldown_sec:
                logger.info(f"[COOLDOWN] Failover alert suppressed (last alert {int(now - self.last_failover_alert)}s ago)")
                return
            self.last_failover_alert = now
        elif alert_type == 'error_rate':
            if now - self.last_error_rate_alert < self.cooldown_sec:
                logger.info(f"[COOLDOWN] Error rate alert suppressed (last alert {int(now - self.last_error_rate_alert)}s ago)")
                return
            self.last_error_rate_alert = now
        
        # Beautiful color scheme
        if alert_type == 'error_rate':
            color = '#DC143C'  # Crimson red for errors
            emoji = '🚨'
        elif alert_type == 'failover':
            # Different colors based on failover direction
            if from_pool == 'blue' and to_pool == 'green':
                color = '#FF6B6B'  # Coral red - failure detected
                emoji = '⚠️'
            elif from_pool == 'green' and to_pool == 'blue':
                color = '#4CAF50'  # Green - recovery/healthy
                emoji = '✅'
            else:
                color = '#FFA500'  # Orange - default
                emoji = '🔄'
        else:
            color = '#36A2EB'  # Blue - info
            emoji = 'ℹ️'
        
        slack_payload = {
            "attachments": [{
                "color": color,
                "title": f"{emoji} {alert_type.upper().replace('_', ' ')} Alert",
                "text": message,
                "fields": [
                    {"title": "Timestamp", "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "short": True},
                    {"title": "Alert Type", "value": alert_type, "short": True}
                ],
                "footer": "Blue/Green Monitor",
                "ts": int(now)
            }]
        }
        
        if details:
            for key, value in details.items():
                slack_payload["attachments"][0]["fields"].append({
                    "title": key,
                    "value": str(value),
                    "short": True
                })
        
        if self.slack_webhook:
            try:
                logger.info(f"[SLACK] Sending {alert_type} alert to Slack...")
                response = requests.post(self.slack_webhook, json=slack_payload, timeout=5)
                if response.status_code == 200:
                    logger.info(f"[SLACK] ✓ Alert sent successfully: {alert_type}")
                else:
                    logger.error(f"[SLACK] ✗ Error response: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"[SLACK] ✗ Failed to send alert: {e}")
        else:
            logger.warning("[SLACK] ✗ Webhook not configured - alert would be sent:")
            logger.info(f"[ALERT] Type: {alert_type}")
            logger.info(f"[ALERT] Message: {message}")
            if details:
                for key, value in details.items():
                    logger.info(f"[ALERT] {key}: {value}")


    def check_failover(self, pool):
        """
        Checks for failover events and sends alerts.
        pool: Current pool from log entry
        """
        if self.last_pool is None:
            self.last_pool = pool
            logger.info(f"[POOL] Initial pool detected: {pool.upper()}")
            return
        
        if pool and pool != self.last_pool:
            message = f"Failover detected: {self.last_pool} → {pool}"
            details = {
                "Previous Pool": self.last_pool,
                "Current Pool": pool,
                "Action Required": "Check primary container health"
            }
            logger.warning("!" * 70)
            logger.warning(f"[FAILOVER] {message}")
            logger.warning(f"[FAILOVER] Previous: {self.last_pool.upper()} | Current: {pool.upper()}")
            logger.warning("!" * 70)
            self.send_slack_alert('failover', message, details, from_pool=self.last_pool, to_pool=pool)
            self.last_pool = pool


    def check_error_rate(self):
        """
        Checks the error rate in the current window and sends alerts if threshold exceeded.
        500-level upstream responses are considered errors.
        """
        if len(self.request_window) < 20:
            return
        
        error_count = sum(1 for had_error in self.request_window if had_error)
        total_count = len(self.request_window)
        error_rate = (error_count / total_count) * 100
        
        # Log stats periodically (every 100 requests)
        if self.total_requests % 100 == 0:
            logger.info(f"[STATS] Total Requests: {self.total_requests} | "
                       f"Total Errors: {self.total_errors} | "
                       f"Current Window Error Rate: {error_rate:.2f}%")
        
        if error_rate > self.error_threshold:
            message = f"High error rate: {error_rate:.2f}% (threshold: {self.error_threshold}%)"
            details = {
                "Error Rate": f"{error_rate:.2f}%",
                "Threshold": f"{self.error_threshold}%",
                "Requests with Errors": error_count,
                "Total Requests": total_count,
                "Action Required": "Inspect logs, consider pool toggle"
            }
            logger.warning("!" * 70)
            logger.warning(f"[ERROR_RATE] {message}")
            logger.warning(f"[ERROR_RATE] Errors: {error_count}/{total_count} requests")
            logger.warning("!" * 70)
            self.send_slack_alert('error_rate', message, details)


    def tail_log(self):
        """
        Tails the Nginx access log and processes new entries.
        """
        logger.info(f"[WATCHER] Starting to tail {self.log_file}")
        
        while not os.path.exists(self.log_file):
            logger.info(f"[WATCHER] Waiting for log file to be created...")
            time.sleep(2)
        
        logger.info(f"[WATCHER] Log file found. Beginning monitoring...")
        
        try:
            with open(self.log_file, 'r') as f:
                # Move to end of file
                f.seek(0, 2)
                logger.info("[WATCHER] ✓ Ready. Monitoring for failovers and errors...")
                logger.info("=" * 70)
                
                while True:
                    line = f.readline()
                    if line:
                        try:
                            log_entry = json.loads(line.strip())
                            pool = log_entry.get('pool', '')
                            upstream_status = log_entry.get('upstream_status', '')
                            request = log_entry.get('request', '')
                            status = log_entry.get('status', 0)
                            
                            self.total_requests += 1
                            
                            # Check if upstream had any errors (500s)
                            # upstream_status can be like "500, 500, 200" when retries happen
                            had_error = False
                            if upstream_status:
                                statuses = str(upstream_status).split(', ')
                                # Check if any upstream attempt was 5xx
                                had_error = any(s.startswith('5') for s in statuses if s.strip())
                            
                            if had_error:
                                self.total_errors += 1
                                logger.debug(f"[ERROR] {request} | Status: {status} | "
                                           f"Upstream: {upstream_status} | Pool: {pool}")
                            
                            self.request_window.append(had_error)
                            
                            if pool:
                                self.check_failover(pool)
                            
                            self.check_error_rate()
                        except json.JSONDecodeError:
                            # Skip non-JSON lines
                            pass
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 70)
            logger.info("[WATCHER] Shutting down gracefully...")
            logger.info(f"[STATS] Final Statistics:")
            logger.info(f"[STATS]   Total Requests Processed: {self.total_requests}")
            logger.info(f"[STATS]   Total Errors Detected: {self.total_errors}")
            if self.total_requests > 0:
                logger.info(f"[STATS]   Overall Error Rate: {(self.total_errors/self.total_requests)*100:.2f}%")
            logger.info("=" * 70)
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error: {e}")
            raise

if __name__ == '__main__':
    watcher = LogWatcher()
    watcher.tail_log()