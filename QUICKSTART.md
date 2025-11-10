# Quick Start Guide for Windows

## Prerequisites Check

1. **Check Docker Desktop is running**
   ```powershell
   docker --version
   docker-compose --version
   ```

2. **Check Python installation**
   ```powershell
   python --version
   ```
   (Should be 3.8 or higher)

## Step-by-Step Setup

### 1. Start Docker Services

Open PowerShell in the project directory:

```powershell
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

Wait 2-3 minutes for services to initialize.

### 2. Verify Services

```powershell
# Test Elasticsearch
Invoke-WebRequest -Uri http://localhost:9200 -UseBasicParsing

# Test Kibana (may take 1-2 minutes)
Invoke-WebRequest -Uri http://localhost:5601 -UseBasicParsing

# Check Kafka
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### 3. Install Python Dependencies

```powershell
cd scripts
pip install -r requirements.txt
```

### 4. Setup Elasticsearch

```powershell
python elasticsearch_setup.py --es-host localhost:9200
```

### 5. Stream Log Data

```powershell
# Test with one day's logs first
python kafka_producer.py --log-dir ..\data\log-2018-06-08\log-2018-06-08

# Or stream all logs
python kafka_producer.py --log-dir ..\data
```

### 6. Access Kibana

Open browser:
```
http://localhost:5601
```

**Setup Index Pattern:**
1. Click hamburger menu (☰) → Management → Stack Management
2. Under Kibana, click "Index Patterns"
3. Click "Create index pattern"
4. Type: `firefox-logs-*`
5. Click "Next step"
6. Select "@timestamp" as time field
7. Click "Create index pattern"

### 7. View Data

1. Click hamburger menu (☰) → Analytics → Discover
2. Select "firefox-logs-*" from dropdown
3. Adjust time range to include June 8, 2018

## Quick Queries

### View Anomalies
```
is_anomaly:true
```

### View Test Failures
```
test_status:failed
```

### View Warnings
```
log_level:WARNING
```

## Stop Services

```powershell
docker-compose down
```

## Restart Services

```powershell
docker-compose restart
```

## View Logs

```powershell
# All services
docker-compose logs

# Specific service
docker-compose logs elasticsearch
docker-compose logs logstash
docker-compose logs kafka
```

## Common Issues

### "Connection refused" errors
- Wait 2-3 minutes after `docker-compose up`
- Check: `docker-compose ps` - all should be "Up (healthy)"

### Elasticsearch "max virtual memory" error
1. In Docker Desktop, go to Settings → Resources
2. Increase Memory to at least 4GB
3. Restart Docker Desktop

### No data in Kibana
1. Check Elasticsearch has data:
   ```powershell
   Invoke-WebRequest -Uri http://localhost:9200/firefox-logs-*/_count -UseBasicParsing
   ```
2. If count is 0, re-run the producer script

### Python module not found
```powershell
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## Next Steps

1. Create visualizations in Kibana
2. Build dashboards
3. Set up alerts for anomalies
4. Export/Import dashboards for reuse

## Useful Commands

```powershell
# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# View resource usage
docker stats

# Clean up old containers
docker system prune
```

## Support

For issues, check:
1. Docker Desktop logs
2. Individual container logs: `docker logs <container_name>`
3. README.md for detailed troubleshooting
