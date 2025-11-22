# 🔧 Troubleshooting Guide

## System Health Checks

### Quick Health Check
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "agent_registry": {"status": "healthy", "agent_count": 15},
    "knowledge_graph": {"status": "healthy", "metrics": {"queries": 42}}
  }
}
```

### System Metrics
```bash
curl http://localhost:8000/api/metrics
```

## Common Issues & Solutions

### 1. Agent Registration Failures

**Symptoms:**
- Agents not appearing in registry
- `agent_count` is 0 in health check

**Solutions:**
```bash
# Check agent initialization logs
tail -f logs/agent_initialization.log

# Verify agent classes are importable
python -c "from agents.domain.midjourney_agent import MidjourneyAgent; print('OK')"

# Restart agent registry
curl -X POST http://localhost:8000/api/agents/restart-registry
```

### 2. Knowledge Graph Connection Issues

**Symptoms:**
- Knowledge graph status shows "unhealthy"
- SPARQL queries fail

**Solutions:**
```bash
# Check KG service status
curl http://localhost:8000/api/kg/status

# Verify connection string
python -c "from kg.models.graph_manager import KnowledgeGraphManager; kg = KnowledgeGraphManager(); print('KG OK')"

# Restart KG service
docker restart kg-service  # If using Docker
```

### 3. Midjourney Integration Problems

**Symptoms:**
- Image generation fails
- API token errors

**Solutions:**
```bash
# Verify environment variables
echo $MIDJOURNEY_API_TOKEN | head -c 10  # Should show token start

# Test API connectivity
curl -H "Authorization: Bearer $MIDJOURNEY_API_TOKEN" \
     https://api.midjourney.com/status

# Check rate limits
curl http://localhost:8000/api/midjourney/rate-limits
```

### 4. Qdrant Vector Database Issues

**Symptoms:**
- Embedding storage fails
- Similarity search not working

**Solutions:**
```bash
# Check Qdrant health
curl http://localhost:6333/health

# Verify collections exist
curl http://localhost:6333/collections

# Restart Qdrant
docker restart qdrant
```

### 5. Memory/Resource Issues

**Symptoms:**
- System slowdowns
- Out of memory errors

**Solutions:**
```bash
# Check system resources
top -p $(pgrep -f "python.*main.py")

# Clear agent caches
curl -X POST http://localhost:8000/api/agents/clear-cache

# Monitor memory usage
curl http://localhost:8000/api/metrics | jq '.memory_usage'
```

## Error Codes & Meanings

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | No action needed |
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Verify API keys |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Check logs, restart service |
| 503 | Service Unavailable | Check dependencies |

### Agent Error Codes

| Error | Description | Solution |
|-------|-------------|----------|
| AGENT_NOT_FOUND | Agent not registered | Check agent initialization |
| CAPABILITY_MISSING | Required capability unavailable | Add capability or use fallback |
| TIMEOUT_ERROR | Operation timed out | Increase timeout or check network |
| VALIDATION_ERROR | Input validation failed | Check input format |

## Performance Optimization

### Monitoring Queries

```bash
# Slow query detection
curl "http://localhost:8000/api/metrics?filter=slow_queries"

# Cache hit ratio
curl "http://localhost:8000/api/metrics" | jq '.cache_hit_ratio'
```

### Agent Performance Tuning

```python
# Optimize agent configuration
agent_config = {
    "max_concurrent_tasks": 5,
    "timeout_seconds": 30,
    "retry_attempts": 3
}
```

### Database Optimization

```sparql
# Use optimized SPARQL queries
SELECT ?s ?p ?o
WHERE {
    ?s ?p ?o .
    FILTER(?p = ex:hasCapability)
}
LIMIT 100
```

## Logging & Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export LOG_LEVEL=DEBUG
```

### Common Log Locations

```
/var/log/semant/
├── agent_registry.log
├── knowledge_graph.log
├── midjourney_integration.log
├── api_requests.log
└── error.log
```

### Debug Commands

```bash
# Enable trace logging for specific component
curl -X POST http://localhost:8000/api/debug/enable \
  -d '{"component": "agent_registry", "level": "TRACE"}'

# Get component status
curl http://localhost:8000/api/debug/status

# Reset debug settings
curl -X POST http://localhost:8000/api/debug/reset
```

## Recovery Procedures

### Full System Restart

```bash
# Stop all services
docker-compose down

# Clear caches
rm -rf /tmp/semant_cache/*
rm -rf /var/log/semant/*.log

# Restart services
docker-compose up -d

# Verify health
curl http://localhost:8000/api/health
```

### Agent Recovery

```bash
# List failed agents
curl http://localhost:8000/api/agents/failed

# Recover specific agent
curl -X POST http://localhost:8000/api/agents/recover \
  -d '{"agent_id": "failed_agent_123"}'

# Bulk recovery
curl -X POST http://localhost:8000/api/agents/recover-all
```

### Data Recovery

```bash
# Backup current state
curl http://localhost:8000/api/backup/create

# Restore from backup
curl -X POST http://localhost:8000/api/backup/restore \
  -d '{"backup_id": "2025-01-11-backup"}'
```

## Support & Escalation

### Community Resources

- **Documentation**: `/static/documentation.html`
- **API Docs**: `/docs`
- **Monitoring**: `/static/monitoring.html`

### Getting Help

1. **Check this guide first**
2. **Review logs**: `tail -f /var/log/semant/error.log`
3. **Run diagnostics**: `curl http://localhost:8000/api/diagnostics/full`
4. **Collect system info**:
   ```bash
   curl http://localhost:8000/api/health > health_snapshot.json
   curl http://localhost:8000/api/metrics > metrics_snapshot.json
   ```

### Escalation Contacts

- **Critical Issues**: Contact system administrator immediately
- **Performance Issues**: Open GitHub issue with metrics data
- **Feature Requests**: Use GitHub discussions

## Prevention Best Practices

### Regular Maintenance

```bash
# Daily health checks
0 2 * * * curl -f http://localhost:8000/api/health || echo "Health check failed"

# Weekly cache cleanup
0 3 * * 1 curl -X POST http://localhost:8000/api/maintenance/cleanup

# Monthly full backup
0 4 1 * * curl http://localhost:8000/api/backup/create
```

### Monitoring Alerts

Set up alerts for:
- Agent registration failures
- Knowledge graph connection issues
- High memory usage (>80%)
- API response times >5 seconds
- Error rates >5%

### Capacity Planning

Monitor these metrics for scaling decisions:
- Concurrent agent connections
- Knowledge graph query volume
- API request rates
- Storage utilization

---

## Quick Reference Commands

```bash
# System status
curl http://localhost:8000/api/health
curl http://localhost:8000/api/metrics

# Agent management
curl http://localhost:8000/api/agents/list
curl http://localhost:8000/api/agents/status

# Knowledge graph
curl http://localhost:8000/api/kg/stats
curl http://localhost:8000/api/kg/validate

# Midjourney
curl http://localhost:8000/api/midjourney/status
curl http://localhost:8000/api/midjourney/queue

# Logs
tail -f /var/log/semant/system.log
tail -f /var/log/semant/error.log
```

---

*This guide is automatically updated with system changes. Last updated: January 11, 2025*
