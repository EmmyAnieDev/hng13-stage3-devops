```markdown
# Blue/Green Deployment Runbook

## Quick Reference

### Alert Types
- 🔴 **Blue → Green**: Primary failed, switched to backup
- 🟢 **Green → Blue**: System recovered, back to primary  
- 🚨 **High Error Rate**: Too many 5xx errors detected

---

## 🔴 Blue → Green Failover

**What happened:** Blue pool failed, traffic moved to Green

**What to do:**

1. **Check Blue container**
   ```bash
   docker logs app_blue --tail 50
   ```

2. **Common fixes**
   ```bash
   # Stop chaos if active
   curl -X POST http://localhost:8081/chaos/stop
   
   # Or restart container
   docker restart app_blue
   ```

3. **Verify recovery**
   ```bash
   sleep 6
   curl http://localhost:8080/version
   # Should see: X-App-Pool: blue (back to primary)
   ```

---

## 🟢 Green → Blue Failover

**What happened:** System recovered successfully

**What to do:**

1. **Confirm it's healthy**
   ```bash
   curl http://localhost:8080/version
   # Should see: X-App-Pool: blue
   ```

2. **Monitor for 5 minutes** - if no new alerts, you're good ✅

---

## 🚨 High Error Rate Alert

**What happened:** More than 2% of requests are failing

**What to do:**

1. **Check which pool is active**
   ```bash
   curl http://localhost:8080/version
   ```

2. **Check for chaos mode**
   ```bash
   # Stop chaos on both pools
   curl -X POST http://localhost:8081/chaos/stop
   curl -X POST http://localhost:8082/chaos/stop
   ```

3. **Check container health**
   ```bash
   docker logs app_blue --tail 20
   docker logs app_green --tail 20
   ```

4. **Restart if needed**
   ```bash
   docker restart app_blue
   # or
   docker restart app_green
   ```

---

## 🛠️ Useful Commands

```bash
# Check current pool
curl http://localhost:8080/version

# View recent logs (now in nginx container)
docker logs nginx_lb --tail 10

# Follow logs in real-time
docker logs -f nginx_lb

# Check all containers
docker-compose ps

# Test failover manually
curl -X POST "http://localhost:8081/chaos/start?mode=error"
for i in {1..10}; do curl http://localhost:8080/version; done
curl -X POST "http://localhost:8081/chaos/stop"

# Restart everything
docker-compose restart
```

---

## 📞 Escalation

If problems persist after following this runbook:
1. Check application logs for errors
2. Verify environment variables in `.env`
3. Restart entire stack: `docker-compose down && docker-compose up -d`
```