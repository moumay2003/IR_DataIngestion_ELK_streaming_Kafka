# Quick ML Model Evaluation

Write-Host "🎯 ML Model Performance Evaluation" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta

# 1. Get total anomalies detected
$total = Invoke-WebRequest -Uri "http://localhost:9200/firefox-ml-anomalies-*/_count" | ConvertFrom-Json
Write-Host "`n📊 DETECTION STATISTICS" -ForegroundColor Cyan
Write-Host "Total Anomalies Detected: $($total.count)" -ForegroundColor Yellow

# 2. Get score statistics
$scoreStats = Invoke-WebRequest -Method POST -Uri "http://localhost:9200/firefox-ml-anomalies-*/_search" -Body '{
  "size": 0,
  "aggs": {
    "score_stats": {
      "stats": {
        "field": "anomaly_score"
      }
    },
    "score_distribution": {
      "histogram": {
        "field": "anomaly_score",
        "interval": 10
      }
    }
  }
}' -ContentType "application/json" | ConvertFrom-Json

Write-Host "`n📈 ANOMALY SCORE STATISTICS" -ForegroundColor Cyan
$stats = $scoreStats.aggregations.score_stats
Write-Host "Average Score:  $([math]::Round($stats.avg, 2))" -ForegroundColor Yellow
Write-Host "Min Score:      $([math]::Round($stats.min, 2))" -ForegroundColor Yellow
Write-Host "Max Score:      $([math]::Round($stats.max, 2))" -ForegroundColor Yellow
Write-Host "Std Deviation:  $([math]::Round($stats.std_deviation, 2))" -ForegroundColor Yellow

# 3. Score distribution
Write-Host "`n📊 SCORE DISTRIBUTION" -ForegroundColor Cyan
$scoreStats.aggregations.score_distribution.buckets | ForEach-Object {
    $range = "$($_.key)-$($_.key + 10)"
    $bar = "█" * [math]::Min($_.doc_count, 50)
    Write-Host "$range : $bar ($($_.doc_count))" -ForegroundColor Green
}

# 4. Check for verified anomalies (precision data)
$verified = Invoke-WebRequest -Method POST -Uri "http://localhost:9200/firefox-ml-anomalies-*/_search" -Body '{
  "size": 0,
  "query": {
    "exists": {
      "field": "is_verified"
    }
  },
  "aggs": {
    "true_positives": {
      "filter": {
        "term": {
          "is_true_positive": true
        }
      }
    },
    "false_positives": {
      "filter": {
        "term": {
          "is_true_positive": false
        }
      }
    }
  }
}' -ContentType "application/json" | ConvertFrom-Json

$totalVerified = $verified.hits.total.value
$tp = $verified.aggregations.true_positives.doc_count
$fp = $verified.aggregations.false_positives.doc_count

if ($totalVerified -gt 0) {
    $precision = $tp / $totalVerified
    
    Write-Host "`n🎯 PRECISION METRICS (Based on Verified Data)" -ForegroundColor Cyan
    Write-Host "Verified Anomalies:     $totalVerified" -ForegroundColor Yellow
    Write-Host "True Positives:         $tp ($([math]::Round($tp/$totalVerified*100, 1))%)" -ForegroundColor Green
    Write-Host "False Positives:        $fp ($([math]::Round($fp/$totalVerified*100, 1))%)" -ForegroundColor Red
    Write-Host "Precision:              $([math]::Round($precision * 100, 2))%" -ForegroundColor $(if($precision -ge 0.85){"Green"}else{"Yellow"})
    
    if ($precision -lt 0.85) {
        Write-Host "`n⚠️  WARNING: Precision below target (85%)" -ForegroundColor Yellow
        Write-Host "   Consider increasing anomaly score threshold" -ForegroundColor Yellow
    } else {
        Write-Host "`n✅ Precision meets target!" -ForegroundColor Green
    }
} else {
    Write-Host "`n⚠️  NO VERIFIED DATA YET" -ForegroundColor Yellow
    Write-Host "Run: python scripts\anomaly_feedback.py" -ForegroundColor Cyan
    Write-Host "to start verifying anomalies and calculate precision" -ForegroundColor Cyan
}

# 5. Anomaly types breakdown
Write-Host "`n🔍 ANOMALY TYPES" -ForegroundColor Cyan
$types = Invoke-WebRequest -Method POST -Uri "http://localhost:9200/firefox-ml-anomalies-*/_search" -Body '{
  "size": 0,
  "aggs": {
    "types": {
      "terms": {
        "field": "anomaly_type.keyword"
      }
    }
  }
}' -ContentType "application/json" | ConvertFrom-Json

$types.aggregations.types.buckets | ForEach-Object {
    $percentage = [math]::Round($_.doc_count / $total.count * 100, 1)
    Write-Host "$($_.key): $($_.doc_count) ($percentage%)" -ForegroundColor White
}

Write-Host "`n" + "=" * 60 -ForegroundColor Magenta
