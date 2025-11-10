# 🔧 Logstash Pipeline - Complete Explanation

## Overview

Logstash is the **parsing and transformation engine** in your ELK pipeline. It:
1. **Consumes** raw log lines from Kafka
2. **Parses** them using Grok patterns
3. **Enriches** with metadata and tags
4. **Detects** anomalies
5. **Sends** to Elasticsearch

---

## 📋 Pipeline Structure

```
┌─────────────┐
│   INPUT     │  ← Read from Kafka
└──────┬──────┘
       │
┌──────▼──────┐
│   FILTER    │  ← Parse & Transform
└──────┬──────┘
       │
┌──────▼──────┐
│   OUTPUT    │  ← Send to Elasticsearch
└─────────────┘
```

---

## 1️⃣ INPUT SECTION

### Code:
```ruby
input {
  kafka {
    bootstrap_servers => "kafka:29092"
    topics => ["firefox-build-logs"]
    group_id => "logstash-consumer-group"
    consumer_threads => 3
    codec => "plain"
    auto_offset_reset => "earliest"
    decorate_events => true
  }
}
```

### Detailed Breakdown:

#### **`bootstrap_servers => "kafka:29092"`**
- **What**: Kafka broker address
- **Why `kafka:29092`**: Docker internal network hostname
- **From host machine**: Would be `localhost:9092`

#### **`topics => ["firefox-build-logs"]`**
- **What**: Kafka topic to consume from
- **Multiple topics**: Can be `["topic1", "topic2"]`
- **Pattern**: Or use regex: `/firefox-.*/`

#### **`group_id => "logstash-consumer-group"`**
- **What**: Kafka consumer group identifier
- **Purpose**: 
  - Tracks which messages have been read
  - Enables parallel processing
  - Allows restart without re-reading

**Example:**
```
Kafka Topic: firefox-build-logs
├── Partition 0 → Consumer 1
├── Partition 1 → Consumer 2
└── Partition 2 → Consumer 3
```

#### **`consumer_threads => 3`**
- **What**: Number of parallel consumers
- **Performance**: More threads = faster processing
- **Recommendation**: Match your CPU cores

#### **`codec => "plain"`**
- **What**: How to decode messages
- **Options**:
  - `plain`: Raw text (our choice)
  - `json`: Parse JSON automatically
  - `line`: Each line is separate event

#### **`auto_offset_reset => "earliest"`**
- **What**: Where to start reading
- **Options**:
  - `earliest`: From beginning (first message ever)
  - `latest`: From now (only new messages)
- **Use case**: `earliest` processes historical data

#### **`decorate_events => true`**
- **What**: Adds Kafka metadata to event
- **Adds**:
  - Topic name
  - Partition number
  - Offset
  - Headers
  - Timestamp

**Example Output:**
```json
{
  "message": "18:34:08 INFO - TEST-PASS...",
  "@metadata": {
    "kafka": {
      "topic": "firefox-build-logs",
      "partition": 1,
      "offset": 45789,
      "headers": {
        "filename": "129557128_2018-06-08-02-22-19.txt",
        "line_number": "1534"
      }
    }
  }
}
```

---

## 2️⃣ FILTER SECTION (The Heart of Logstash)

This is where **ALL the magic happens**!

---

### **Step 1: Extract Metadata from Kafka Headers**

```ruby
if [@metadata][kafka][headers][filename] {
  mutate {
    add_field => {
      "filename" => "%{[@metadata][kafka][headers][filename]}"
      "line_number" => "%{[@metadata][kafka][headers][line_number]}"
    }
  }
}
```

**What it does:**
- Reads headers sent by Python producer
- Promotes them to regular fields

**Before:**
```json
{
  "message": "18:34:08 INFO - ...",
  "@metadata": {
    "kafka": {
      "headers": {
        "filename": "129557128_2018-06-08-02-22-19.txt"
      }
    }
  }
}
```

**After:**
```json
{
  "message": "18:34:08 INFO - ...",
  "filename": "129557128_2018-06-08-02-22-19.txt",
  "line_number": "1534"
}
```

---

### **Step 2: Parse Filename for Build Metadata**

```ruby
if [filename] {
  grok {
    match => {
      "filename" => "%{NUMBER:build_id}_%{YEAR:year}-%{MONTHNUM:month}-%{MONTHDAY:day}-%{HOUR:hour}-%{MINUTE:minute}-%{SECOND:second}"
    }
  }
}
```

**Grok Pattern Explained:**

| Pattern | Matches | Example |
|---------|---------|---------|
| `%{NUMBER:build_id}` | Any digits | `129557128` |
| `%{YEAR:year}` | 4-digit year | `2018` |
| `%{MONTHNUM:month}` | Month (01-12) | `06` |
| `%{MONTHDAY:day}` | Day (01-31) | `08` |
| `%{HOUR:hour}` | Hour (00-23) | `02` |
| `%{MINUTE:minute}` | Minute (00-59) | `22` |
| `%{SECOND:second}` | Second (00-59) | `19` |

**Example:**
- Input: `129557128_2018-06-08-02-22-19.txt`
- Output fields:
  ```json
  {
    "build_id": "129557128",
    "year": "2018",
    "month": "06",
    "day": "08",
    "hour": "02",
    "minute": "22",
    "second": "19"
  }
  ```

**Then Build ISO Timestamp:**
```ruby
if [year] {
  mutate {
    add_field => { "file_timestamp" => "%{year}-%{month}-%{day}T%{hour}:%{minute}:%{second}Z" }
  }
  mutate {
    remove_field => ["year", "month", "day", "hour", "minute", "second"]
  }
}
```

Result: `file_timestamp: "2018-06-08T02:22:19Z"`

---

### **Step 3: Parse the Log Line**

```ruby
grok {
  match => {
    "message" => [
      "%{TIME:log_time}%{SPACE}+%{LOGLEVEL:log_level}%{SPACE}+-%{SPACE}+%{GREEDYDATA:log_message}",
      "%{TIME:log_time}%{SPACE}+%{WORD:log_level}%{SPACE}+-%{SPACE}+\[%{NUMBER:process_id}\]%{SPACE}+%{WORD:message_type}:%{SPACE}+%{GREEDYDATA:log_message}",
      "^=========%{SPACE}+%{GREEDYDATA:section_marker}%{SPACE}+=========",
      "^%{GREEDYDATA:log_message}$"
    ]
  }
}
```

**Multiple Patterns (Try in Order):**

#### **Pattern 1: Standard Log Line**
```
18:34:08     INFO - TEST-PASS | dom/plugins/test/...
```

Grok: `%{TIME:log_time}%{SPACE}+%{LOGLEVEL:log_level}%{SPACE}+-%{SPACE}+%{GREEDYDATA:log_message}`

Extracts:
- `log_time`: `18:34:08`
- `log_level`: `INFO`
- `log_message`: `TEST-PASS | dom/plugins/test/...`

#### **Pattern 2: Log with Process ID**
```
18:34:09 INFO - [4028] WARNING: Failed to load...
```

Grok: `%{TIME:log_time}...`

Extracts:
- `log_time`: `18:34:09`
- `log_level`: `INFO`
- `process_id`: `4028`
- `message_type`: `WARNING`
- `log_message`: `Failed to load...`

#### **Pattern 3: Section Markers**
```
========= Started set props: master =========
```

Extracts:
- `section_marker`: `Started set props: master`

#### **Pattern 4: Fallback**
```
^%{GREEDYDATA:log_message}$
```
Catches everything else → puts in `log_message`

---

### **Step 4: Extract Build Configuration**

These patterns look for specific keywords in the log:

```ruby
if "builder:" in [message] {
  grok {
    match => { "message" => "builder:%{SPACE}+%{GREEDYDATA:builder}" }
  }
}
```

**Example:**
```
Input:  "builder: mozilla-esr52_xp_ix-debug_test-mochitest-chrome-2"
Output: builder = "mozilla-esr52_xp_ix-debug_test-mochitest-chrome-2"
```

**Similarly for:**
- `slave:` → `slave` field
- `buildid:` → `buildid` field
- `revision:` → `git_revision` field
- `results:` → `result` field

---

### **Step 5: Parse TEST Events** (Critical!)

```ruby
if [log_message] =~ /^TEST-/ {
  grok {
    match => {
      "log_message" => [
        "TEST-START | %{GREEDYDATA:test_name}",
        "TEST-PASS | %{GREEDYDATA:test_name} | took %{NUMBER:test_duration:int}ms",
        "TEST-SKIP | %{GREEDYDATA:test_name} | took %{NUMBER:test_duration:int}ms",
        "TEST-UNEXPECTED-FAIL | %{GREEDYDATA:test_name} |%{GREEDYDATA:fail_reason}",
        "TEST-OK | %{GREEDYDATA:test_name} | took %{NUMBER:test_duration:int}ms"
      ]
    }
    add_tag => ["test_event"]
  }
}
```

**Example Transformations:**

#### **Test Pass:**
```
Input:  "TEST-PASS | dom/plugins/test/mochitest/test_convertpoint.xul | took 230ms"

Output:
{
  "test_name": "dom/plugins/test/mochitest/test_convertpoint.xul",
  "test_duration": 230,
  "test_status": "passed",
  "tags": ["test_event"]
}
```

#### **Test Failure:**
```
Input:  "TEST-UNEXPECTED-FAIL | browser/test_cookies.js | Expected true, got false"

Output:
{
  "test_name": "browser/test_cookies.js",
  "fail_reason": " Expected true, got false",
  "test_status": "failed",
  "tags": ["test_event", "anomaly", "test_failure"]
}
```

**Status Classification:**
```ruby
if [log_message] =~ /TEST-START/ {
  mutate { add_field => { "test_status" => "started" } }
} else if [log_message] =~ /TEST-PASS/ {
  mutate { add_field => { "test_status" => "passed" } }
} else if [log_message] =~ /TEST-SKIP/ {
  mutate { add_field => { "test_status" => "skipped" } }
} else if [log_message] =~ /TEST-UNEXPECTED-FAIL/ {
  mutate { add_field => { "test_status" => "failed" } }
  mutate { add_tag => ["anomaly", "test_failure"] }  # ← Marks as anomaly!
}
```

---

### **Step 6: Parse WARNING Events**

```ruby
if [log_message] =~ /WARNING:/ {
  grok {
    match => {
      "log_message" => [
        "WARNING:%{SPACE}+%{GREEDYDATA:warning_message}:%{SPACE}+file%{SPACE}+%{PATH:file_path},%{SPACE}+line%{SPACE}+%{NUMBER:line_number_in_code:int}",
        "WARNING:%{SPACE}+%{GREEDYDATA:warning_message}"
      ]
    }
    add_tag => ["warning"]
  }
}
```

**Example:**
```
Input: "WARNING: NS_ENSURE_SUCCESS(rv, rv) failed with result 0x80520012: file c:/builds/.../nsIOService.cpp, line 793"

Output:
{
  "warning_message": "NS_ENSURE_SUCCESS(rv, rv) failed with result 0x80520012",
  "file_path": "c:/builds/.../nsIOService.cpp",
  "line_number_in_code": 793,
  "tags": ["warning"]
}
```

**Severity Classification:**
```ruby
if [warning_message] =~ /NS_ENSURE_SUCCESS/ or [warning_message] =~ /failed with result/ {
  mutate { add_field => { "warning_severity" => "high" } }
  mutate { add_tag => ["anomaly", "critical_warning"] }
} else if [warning_message] =~ /Failed to load|composition not available/ {
  mutate { add_field => { "warning_severity" => "medium" } }
} else {
  mutate { add_field => { "warning_severity" => "low" } }
}
```

**Extract Error Codes:**
```ruby
if [warning_message] =~ /0x[0-9a-fA-F]+/ {
  grok {
    match => { "warning_message" => "0x%{BASE16NUM:error_code}" }
  }
  mutate { add_tag => ["error_code"] }
}
```

Example: `0x80520012` → `error_code: "80520012"`

---

### **Step 7: Detect Anomalies**

#### **ERROR Patterns:**
```ruby
if [log_message] =~ /ERROR|Exception|AssertionError/ {
  mutate { 
    add_tag => ["error", "anomaly", "exception"]
    add_field => { "severity" => "critical" }
  }
}
```

#### **Performance Issues:**
```ruby
if [log_message] =~ /took \d+ms|elapsed|elapsedTime/ {
  grok {
    match => {
      "log_message" => [
        "elapsedTime=%{NUMBER:elapsed_time:float}",
        "took %{NUMBER:duration_ms:int}ms"
      ]
    }
    add_tag => ["performance"]
  }
  
  if [elapsed_time] {
    if [elapsed_time] > 60 {
      mutate { add_tag => ["slow_operation", "anomaly"] }
    }
  }
  if [duration_ms] {
    if [duration_ms] > 60000 {
      mutate { add_tag => ["slow_test", "anomaly"] }
    }
  }
}
```

**Logic:**
- Extract duration values
- If `elapsed_time` > 60 seconds → Tag as `slow_operation` and `anomaly`
- If `test_duration` > 60,000 ms (1 minute) → Tag as `slow_test` and `anomaly`

#### **Memory Issues:**
```ruby
if [log_message] =~ /memory|leak|allocation|out of memory/i {
  mutate { 
    add_tag => ["memory_issue", "anomaly"]
    add_field => { "anomaly_type" => "memory" }
  }
}
```

#### **Network Issues:**
```ruby
if [log_message] =~ /connection|socket|timeout|refused|unreachable/i {
  mutate { 
    add_tag => ["network_issue"]
    add_field => { "anomaly_type" => "network" }
  }
}
```

#### **Security Issues:**
```ruby
if [log_message] =~ /certificate|SSL|TLS|security|CORS/i {
  mutate { 
    add_tag => ["security_issue"]
  }
}
```

---

### **Step 8: Parse Timestamps**

```ruby
if [log_time] {
  date {
    match => [ "log_time", "HH:mm:ss" ]
    target => "@timestamp"
    timezone => "UTC"
  }
}
```

**What it does:**
- Takes `log_time` (e.g., `18:34:08`)
- Converts to full timestamp
- Stores in `@timestamp` (Elasticsearch's time field)

**Result:**
```json
{
  "log_time": "18:34:08",
  "@timestamp": "2018-06-08T18:34:08.000Z"
}
```

---

### **Step 9: Mark Anomalies**

```ruby
if "anomaly" in [tags] {
  mutate { add_field => { "is_anomaly" => true } }
} else {
  mutate { add_field => { "is_anomaly" => false } }
}
```

**Purpose:** Creates boolean field for easy querying in Kibana

---

## 3️⃣ OUTPUT SECTION

```ruby
output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "firefox-logs-%{+YYYY.MM.dd}"
  }

  if "anomaly" in [tags] {
    elasticsearch {
      hosts => ["http://elasticsearch:9200"]
      index => "firefox-anomalies-%{+YYYY.MM.dd}"
    }
  }

  stdout {
    codec => rubydebug { metadata => true }
  }
}
```

### **Output 1: All Logs to Main Index**
```ruby
elasticsearch {
  hosts => ["http://elasticsearch:9200"]
  index => "firefox-logs-%{+YYYY.MM.dd}"
}
```

Creates indices like:
- `firefox-logs-2018-06-08`
- `firefox-logs-2018-06-09`
- `firefox-logs-2018-06-10`

### **Output 2: Anomalies to Separate Index**
```ruby
if "anomaly" in [tags] {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "firefox-anomalies-%{+YYYY.MM.dd}"
  }
}
```

**Why Separate Index?**
- ✅ Faster queries (smaller dataset)
- ✅ Easy monitoring (count anomaly docs)
- ✅ Different retention policies
- ✅ Dedicated dashboards

### **Output 3: Debug to Console**
```ruby
stdout {
  codec => rubydebug { metadata => true }
}
```

Prints to Logstash logs for debugging

---

## 🎯 Complete Example: Log Line → Elasticsearch Document

### **Input (from Kafka):**
```
18:34:08     INFO - TEST-UNEXPECTED-FAIL | dom/tests/browser/test_bug1234.js | Expected true, got false
```

### **Logstash Processing:**

1. **Extract from headers:**
   - `filename`: `129557128_2018-06-08-02-22-19.txt`
   - `line_number`: `1534`

2. **Parse filename:**
   - `build_id`: `129557128`
   - `file_timestamp`: `2018-06-08T02:22:19Z`

3. **Parse log line:**
   - `log_time`: `18:34:08`
   - `log_level`: `INFO`
   - `log_message`: `TEST-UNEXPECTED-FAIL | dom/tests/browser/test_bug1234.js | Expected true, got false`

4. **Parse TEST event:**
   - `test_name`: `dom/tests/browser/test_bug1234.js`
   - `fail_reason`: ` Expected true, got false`
   - `test_status`: `failed`
   - `tags`: `["test_event", "anomaly", "test_failure"]`

5. **Mark anomaly:**
   - `is_anomaly`: `true`

6. **Parse timestamp:**
   - `@timestamp`: `2018-06-08T18:34:08.000Z`

### **Output (to Elasticsearch):**
```json
{
  "@timestamp": "2018-06-08T18:34:08.000Z",
  "filename": "129557128_2018-06-08-02-22-19.txt",
  "line_number": "1534",
  "build_id": "129557128",
  "file_timestamp": "2018-06-08T02:22:19Z",
  "log_time": "18:34:08",
  "log_level": "INFO",
  "log_message": "TEST-UNEXPECTED-FAIL | dom/tests/browser/test_bug1234.js | Expected true, got false",
  "test_name": "dom/tests/browser/test_bug1234.js",
  "fail_reason": " Expected true, got false",
  "test_status": "failed",
  "is_anomaly": true,
  "tags": ["test_event", "anomaly", "test_failure"],
  "parsed": "true"
}
```

**Sent to BOTH:**
- `firefox-logs-2018-06-08`
- `firefox-anomalies-2018-06-08`

---

## 🚀 How to Run the Pipeline

### **Step 1: Start Services**
```powershell
cd "c:\Users\mouad\OneDrive - um5.ac.ma\Desktop\ELK_KAFKA"
docker-compose up -d
```

### **Step 2: Wait for Services (2-3 minutes)**
```powershell
docker-compose ps
```

All should show "Up (healthy)"

### **Step 3: Setup Elasticsearch**
```powershell
cd scripts
pip install -r requirements.txt
python elasticsearch_setup.py
```

### **Step 4: Stream Logs to Kafka**
```powershell
python kafka_producer_minimal.py --log-dir ..\data
```

### **Step 5: Watch Logstash Process Logs**
```powershell
docker logs -f logstash
```

You'll see:
```
{
  "@timestamp" => 2018-06-08T18:34:08.000Z,
  "test_name" => "dom/tests/browser/test_bug1234.js",
  "test_status" => "failed",
  "is_anomaly" => true
}
```

### **Step 6: Check Elasticsearch**
```powershell
# Count documents
Invoke-WebRequest -Uri http://localhost:9200/firefox-logs-*/_count -UseBasicParsing

# Count anomalies
Invoke-WebRequest -Uri http://localhost:9200/firefox-anomalies-*/_count -UseBasicParsing
```

### **Step 7: Open Kibana**
```
http://localhost:5601
```

Create index pattern: `firefox-logs-*`

---

## 📊 Key Logstash Concepts

### **Grok Patterns**
Pre-defined regex patterns for common data types:

| Pattern | Matches | Example |
|---------|---------|---------|
| `%{NUMBER}` | Integer or float | `123`, `45.67` |
| `%{WORD}` | Alphanumeric | `test`, `INFO` |
| `%{TIME}` | HH:MM:SS | `18:34:08` |
| `%{LOGLEVEL}` | Log levels | `INFO`, `WARNING`, `ERROR` |
| `%{GREEDYDATA}` | Everything | Any remaining text |
| `%{PATH}` | File path | `/usr/bin/file` |

### **Field References**
- `[field]` - Access field value
- `[@metadata][field]` - Metadata (not sent to output)
- `%{field}` - Variable interpolation

### **Conditionals**
```ruby
if [field] == "value" { ... }
if [field] =~ /pattern/ { ... }  # Regex match
if "tag" in [tags] { ... }
```

### **Mutate Operations**
```ruby
add_field => { "new_field" => "value" }
remove_field => ["field1", "field2"]
add_tag => ["tag1", "tag2"]
rename => { "old_name" => "new_name" }
```

---

## 🎓 Summary

**Logstash Flow:**
```
1. Read raw log from Kafka
2. Extract metadata from headers
3. Parse filename for build info
4. Parse log line for timestamp, level
5. Extract build configuration
6. Parse TEST/WARNING/ERROR patterns
7. Detect anomalies (failures, slow tests, errors)
8. Convert timestamps
9. Tag anomalies
10. Send to Elasticsearch (2 indices)
```

**Your pipeline is now ready to run!** 🚀

Logstash will automatically:
- ✅ Parse all log patterns
- ✅ Detect anomalies
- ✅ Structure data
- ✅ Index in Elasticsearch

You just need to start it and watch the data flow! 🔥
