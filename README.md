# 🔥 Firefox Build/Test Logs - Anomaly Detection Pipeline

[![ELK Stack](https://img.shields.io/badge/ELK-8.10.2-005571?style=flat&logo=elastic)](https://www.elastic.co/)
[![Kafka](https://img.shields.io/badge/Kafka-7.4.0-231F20?style=flat&logo=apache-kafka)](https://kafka.apache.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python)](https://www.python.org/)

**Real-time anomaly detection system for Mozilla Firefox's CI/CD build and test logs using ELK Stack + Kafka.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Anomaly Detection Features](#anomaly-detection-features)
- [Kibana Dashboards](#kibana-dashboards)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## 🎯 Overview

This project implements a comprehensive anomaly detection pipeline for Mozilla Firefox's automated testing logs from their Buildbot CI system. It processes build/test logs to identify:

- ✅ **Test failures and unexpected behaviors**
- ⚠️ **Warning patterns and severity spikes**
- 🐢 **Performance degradation (slow tests)**
- 💥 **Error code frequencies**
- 🔍 **Memory leaks and resource issues**
- 🌐 **Network and security problems**

### Data Source

- **Origin**: Mozilla Firefox Buildbot CI system
- **Platform**: Windows XP 32-bit test environment
- **Test Type**: Mochitest (chrome tests)
- **Format**: Structured build/test logs (`.txt` files)
- **Example**: `129557128_2018-06-08-02-22-19.txt`

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Firefox Logs   │
│   (data/*.txt)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│ Kafka Producer  │─────▶│    Kafka     │
│  (Python Script)│      │   Topic      │
└─────────────────┘      └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  Logstash    │
                         │  (Parsing &  │
                         │   Filtering) │
                         └──────┬───────┘
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
         ┌────────────────┐         ┌──────────────────┐
         │ Elasticsearch  │         │ Elasticsearch    │
         │ (firefox-logs) │         │ (anomalies idx)  │
         └────────┬───────┘         └──────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │     Kibana     │
         │  (Dashboard &  │
         │ Visualization) │
         └────────────────┘
```

### Components

1. **Kafka** - Streaming ingestion layer for log data
2. **Zookeeper** - Kafka cluster coordination
3. **Logstash** - Log parsing with Grok patterns & anomaly tagging
4. **Elasticsearch** - Indexing, search, and anomaly storage
5. **Kibana** - Real-time dashboards and visualizations
6. **Python Producer** - Reads log files and streams to Kafka

---

## 📦 Prerequisites

### Required Software

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** v2.0+
- **Python** 3.8+
- **Git**

### System Requirements

- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 10GB free space
- **CPU**: 4+ cores recommended

---

## 🚀 Quick Start

### 1. Clone the Repository

```powershell
git clone https://github.com/moumay2003/IR_DataIngestion_ELK_streaming_Kafka.git
cd IR_DataIngestion_ELK_streaming_Kafka
```

### 2. Start the ELK + Kafka Stack

```powershell
docker-compose up -d
```

This will start:
- Zookeeper (port 2181)
- Kafka (port 9092)
- Elasticsearch (port 9200)
- Logstash (port 5044)
- Kibana (port 5601)

**Wait 2-3 minutes for all services to be ready.**

### 3. Verify Services

```powershell
# Check if all containers are running
docker-compose ps

# Check Elasticsearch health
curl http://localhost:9200/_cluster/health

# Check Kafka topics
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### 4. Setup Elasticsearch Indices

```powershell
cd scripts
pip install -r requirements.txt
python elasticsearch_setup.py
```

### 5. Stream Logs to Kafka

```powershell
# Process all log files in data directory
python kafka_producer.py --log-dir ../data --kafka-broker localhost:9092

# Or process specific date
python kafka_producer.py --log-dir ../data/log-2018-06-08
```

### 6. Access Kibana

Open your browser and navigate to:

```
http://localhost:5601
```

**Create Index Pattern:**
1. Go to **Management** → **Stack Management** → **Index Patterns**
2. Click **Create index pattern**
3. Enter pattern: `firefox-logs-*`
4. Select time field: `@timestamp`
5. Click **Create**

---

## ⚙️ Configuration

### Kafka Producer Options

```powershell
python kafka_producer.py --help

Options:
  --log-dir         Directory containing log files (default: ./data)
  --kafka-broker    Kafka broker address (default: localhost:9092)
  --topic           Kafka topic name (default: firefox-build-logs)
  --pattern         File pattern to match (default: *.txt)
  --no-recursive    Do not search subdirectories
```

### Logstash Pipeline

Edit `logstash/pipeline/firefox-logs.conf` to customize:

- Grok patterns for log parsing
- Anomaly detection rules
- Output indices
- Filters and transformations

### Elasticsearch Settings

Modify `docker-compose.yml` to adjust:

```yaml
environment:
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"  # Heap size
  - discovery.type=single-node     # Cluster mode
```

---

## 📊 Usage

### View Logs in Kibana

1. Go to **Discover** in Kibana
2. Select index pattern: `firefox-logs-*`
3. Set time range to include your log dates

### Filter by Anomalies

```
is_anomaly:true
```

### Filter by Test Failures

```
test_status:failed OR tags:test_failure
```

### Filter by Warning Severity

```
warning_severity:high
```

### View Slow Tests

```
test_duration:>60000
```

---

## 🔍 Anomaly Detection Features

### Automated Detection Rules

| Rule | Description | Tag |
|------|-------------|-----|
| **Test Failures** | `TEST-UNEXPECTED-FAIL` patterns | `test_failure`, `anomaly` |
| **Critical Warnings** | `NS_ENSURE_SUCCESS` failures | `critical_warning`, `anomaly` |
| **Slow Operations** | elapsed_time > 60s | `slow_operation`, `anomaly` |
| **Slow Tests** | test_duration > 60000ms | `slow_test`, `anomaly` |
| **Memory Issues** | Memory/leak keywords | `memory_issue`, `anomaly` |
| **Network Problems** | Connection/timeout errors | `network_issue` |
| **Security Issues** | Certificate/CORS/SSL problems | `security_issue` |
| **Error Codes** | Hex error codes (0x...) | `error_code` |

### Extracted Fields

```json
{
  "test_name": "dom/plugins/test/mochitest/test_convertpoint.xul",
  "test_status": "skipped",
  "test_duration": 0,
  "warning_message": "NS_ENSURE_SUCCESS(rv, rv) failed",
  "warning_severity": "high",
  "error_code": "80520012",
  "is_anomaly": true,
  "tags": ["warning", "anomaly", "critical_warning"]
}
```

---

## 📈 Kibana Dashboards

### Recommended Visualizations

#### 1. **Build Overview Dashboard**

- **Total Tests Run** (Metric)
- **Test Status Distribution** (Pie Chart)
- **Tests Over Time** (Line Chart)
- **Build Success Rate** (Gauge)

#### 2. **Anomaly Detection Dashboard**

- **Anomaly Timeline** (Area Chart)
  ```
  Query: is_anomaly:true
  Aggregation: Date Histogram on @timestamp
  ```

- **Warning Severity Heatmap** (Heat Map)
  ```
  Y-axis: warning_severity
  X-axis: @timestamp
  ```

- **Top Error Codes** (Bar Chart)
  ```
  Query: error_code:*
  Terms aggregation: error_code
  ```

- **Failed Tests Table** (Data Table)
  ```
  Query: test_status:failed
  Columns: test_name, fail_reason, @timestamp
  ```

#### 3. **Performance Dashboard**

- **Average Test Duration** (Metric)
- **Slowest Tests** (Top 10 Bar Chart)
- **Test Duration Distribution** (Histogram)

### Creating Dashboards

1. Go to **Dashboard** → **Create dashboard**
2. Click **Add** → **Create visualization**
3. Select visualization type
4. Configure query and aggregations
5. Save and add to dashboard

---

## 🐛 Troubleshooting

### Elasticsearch Not Starting

```powershell
# Check logs
docker logs elasticsearch

# Common issue: Memory lock
# Solution: Increase Docker memory to 4GB+
```

### Kafka Connection Refused

```powershell
# Wait for Kafka to be fully ready (30-60 seconds)
docker logs kafka

# Test connection
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

### Logstash Not Processing

```powershell
# Check Logstash logs
docker logs logstash

# Verify Kafka topic has messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic firefox-build-logs \
  --from-beginning \
  --max-messages 10
```

### No Data in Kibana

1. Verify index exists:
   ```
   curl http://localhost:9200/_cat/indices?v
   ```

2. Check document count:
   ```
   curl http://localhost:9200/firefox-logs-*/_count
   ```

3. Refresh index pattern in Kibana:
   **Management** → **Index Patterns** → **Refresh**

### Python Script Errors

```powershell
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Kafka connectivity
python -c "from kafka import KafkaProducer; print('Kafka library OK')"
```

---

## 📁 Project Structure

```
ELK_KAFKA/
├── data/                          # Log files directory
│   ├── log-2018-06-08/
│   ├── log-2018-06-09/
│   └── log-2018-06-10/
│
├── logstash/
│   ├── config/
│   │   └── logstash.yml          # Logstash configuration
│   └── pipeline/
│       └── firefox-logs.conf     # Log parsing pipeline
│
├── scripts/
│   ├── kafka_producer.py         # Stream logs to Kafka
│   ├── elasticsearch_setup.py    # Setup ES indices
│   └── requirements.txt          # Python dependencies
│
├── docker-compose.yml            # Docker services definition
└── README.md                     # This file
```

---

## 🎓 Usage Examples

### Example 1: Process Today's Logs

```powershell
python scripts/kafka_producer.py \
  --log-dir ./data/log-2018-06-08 \
  --kafka-broker localhost:9092
```

### Example 2: Stream All Logs

```powershell
python scripts/kafka_producer.py \
  --log-dir ./data \
  --pattern "*.txt"
```

### Example 3: Query Anomalies via API

```powershell
curl -X GET "localhost:9200/firefox-anomalies-*/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": { "is_anomaly": true }
    },
    "size": 100
  }'
```

---

## 🔧 Advanced Configuration

### Enable ML Anomaly Detection (X-Pack)

**Note**: Requires Elasticsearch license (trial or paid)

```powershell
# Enable trial license
curl -X POST "localhost:9200/_license/start_trial?acknowledge=true"

# Create ML job
curl -X PUT "localhost:9200/_ml/anomaly_detectors/firefox_anomaly_job" \
  -H 'Content-Type: application/json' \
  -d @anomaly_detection_config.json
```

### Scale Kafka for Production

Edit `docker-compose.yml`:

```yaml
kafka:
  environment:
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
    KAFKA_NUM_PARTITIONS: 6
```

### Add Data Retention Policy

```powershell
# Delete indices older than 30 days
curl -X DELETE "localhost:9200/firefox-logs-*" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "range": {
        "@timestamp": {
          "lt": "now-30d"
        }
      }
    }
  }'
```

---

## 📚 Resources

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Logstash Grok Patterns](https://www.elastic.co/guide/en/logstash/current/plugins-filters-grok.html)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Kibana User Guide](https://www.elastic.co/guide/en/kibana/current/index.html)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👤 Author

**Mouad**
- GitHub: [@moumay2003](https://github.com/moumay2003)
- Repository: [IR_DataIngestion_ELK_streaming_Kafka](https://github.com/moumay2003/IR_DataIngestion_ELK_streaming_Kafka)

---

## 🙏 Acknowledgments

- Mozilla Firefox Team for the build/test logs dataset
- Elastic for the ELK Stack
- Apache Kafka community

---

**Ready to detect anomalies? Start the pipeline now! 🚀**

```powershell
docker-compose up -d && python scripts/kafka_producer.py
```
