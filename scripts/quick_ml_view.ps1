# Quick ML Metrics Viewer

Write-Host "🤖 ML Model Metrics - Quick View" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta

# Fetch summary
$stats = Invoke-WebRequest -Uri "http://localhost:9200/firefox-ml-anomalies-*/_search?size=0" -Method POST -Body '{
  "aggs": {
    "total": {"value_count": {"field": "_id"}},
    "avg_score": {"avg": {"field": "anomaly_score"}},
    "max_score": {"max": {"field": "anomaly_score"}},
    "by_type": {"terms": {"field": "anomaly_type.keyword"}},
    "by_severity": {"terms": {"field": "severity.keyword"}}
  }
}' -ContentType "application/json" | ConvertFrom-Json

Write-Host "`n📊 STATISTICS" -ForegroundColor Cyan
Write-Host "Total Anomalies: $($stats.aggregations.total.value)" -ForegroundColor Yellow
Write-Host "Average Score: $([math]::Round($stats.aggregations.avg_score.value, 2))" -ForegroundColor Yellow
Write-Host "Max Score: $([math]::Round($stats.aggregations.max_score.value, 2))" -ForegroundColor Yellow

Write-Host "`n🎯 BY TYPE" -ForegroundColor Cyan
$stats.aggregations.by_type.buckets | ForEach-Object {
    Write-Host "  $($_.key): $($_.doc_count)" -ForegroundColor White
}

Write-Host "`n⚠️  BY SEVERITY" -ForegroundColor Cyan
$stats.aggregations.by_severity.buckets | ForEach-Object {
    $color = switch ($_.key) {
        "critical" { "Red" }
        "high" { "Yellow" }
        "medium" { "Cyan" }
        "low" { "Green" }
    }
    Write-Host "  $($_.key): $($_.doc_count)" -ForegroundColor $color
}

Write-Host "`n" -NoNewline
Read-Host "Press Enter to open Kibana dashboard"
Start-Process "http://localhost:5601/app/dashboards"
