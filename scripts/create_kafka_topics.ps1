# Create Kafka Topics for Firefox Logs Pipeline (PowerShell)

Write-Host "Creating Kafka topics..." -ForegroundColor Green

# Wait for Kafka to be ready
Start-Sleep -Seconds 10

# Create main logs topic
Write-Host "`nCreating topic: firefox-build-logs..." -ForegroundColor Yellow

docker exec -it kafka kafka-topics `
  --bootstrap-server localhost:9092 `
  --create `
  --if-not-exists `
  --topic firefox-build-logs `
  --partitions 3 `
  --replication-factor 1 `
  --config retention.ms=604800000 `
  --config compression.type=gzip

if ($LASTEXITCODE -eq 0) {
  Write-Host "✓ Created topic: firefox-build-logs" -ForegroundColor Green
}
else {
  Write-Host "✗ Failed to create topic" -ForegroundColor Red
  exit 1
}

# List all topics
Write-Host "`nAvailable topics:" -ForegroundColor Cyan
docker exec -it kafka kafka-topics `
  --bootstrap-server localhost:9092 `
  --list

# Describe the topic
Write-Host "`nTopic details:" -ForegroundColor Cyan
docker exec -it kafka kafka-topics `
  --bootstrap-server localhost:9092 `
  --describe `
  --topic firefox-build-logs

Write-Host "`n✓ Topic setup complete!" -ForegroundColor Green
