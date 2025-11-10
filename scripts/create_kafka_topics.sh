#!/usr/bin/env bash
# Create Kafka Topics for Firefox Logs Pipeline

echo "Creating Kafka topics..."

# Wait for Kafka to be ready
sleep 10

# Create main logs topic
docker exec -it kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --if-not-exists \
  --topic firefox-build-logs \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=gzip

echo "✓ Created topic: firefox-build-logs"

# List all topics
echo ""
echo "Available topics:"
docker exec -it kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list

# Describe the topic
echo ""
echo "Topic details:"
docker exec -it kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic firefox-build-logs

echo ""
echo "✓ Topic setup complete!"
