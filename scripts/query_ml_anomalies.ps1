<#
.SYNOPSIS
    Easy access to ML anomaly detection results
.DESCRIPTION
    PowerShell script with multiple functions to query and display ML anomalies
#>

$ES_HOST = "http://localhost:9200"
$ML_INDEX = "firefox-ml-anomalies-*"

function Get-LatestAnomalies {
    param(
        [int]$Count = 10
    )
    
    Write-Host "🔍 Fetching latest $Count anomalies..." -ForegroundColor Cyan
    
    $body = @{
        size = $Count
        sort = @(@{"@timestamp" = "desc"})
        query = @{
            match_all = @{}
        }
    } | ConvertTo-Json -Depth 10
    
    $response = Invoke-WebRequest -Method POST -Uri "$ES_HOST/$ML_INDEX/_search" -Body $body -ContentType "application/json" | ConvertFrom-Json
    
    $anomalies = $response.hits.hits | ForEach-Object {
        [PSCustomObject]@{
            Timestamp = $_._source.'@timestamp'
            Type = $_._source.anomaly_type
            Score = [math]::Round($_._source.anomaly_score, 2)
            Severity = $_._source.severity
            Recommendation = $_._source.recommendation
        }
    }
    
    $anomalies | Format-Table -AutoSize
}

function Get-AnomaliesByType {
    Write-Host "📊 Anomaly distribution by type..." -ForegroundColor Cyan
    
    $body = @{
        size = 0
        aggs = @{
            by_type = @{
                terms = @{
                    field = "anomaly_type.keyword"
                    size = 10
                }
            }
        }
    } | ConvertTo-Json -Depth 10
    
    $response = Invoke-WebRequest -Method POST -Uri "$ES_HOST/$ML_INDEX/_search" -Body $body -ContentType "application/json" | ConvertFrom-Json
    
    $response.aggregations.by_type.buckets | ForEach-Object {
        [PSCustomObject]@{
            Type = $_.key
            Count = $_.doc_count
            Percentage = [math]::Round(($_.doc_count / $response.hits.total.value) * 100, 2)
        }
    } | Format-Table -AutoSize
}

function Get-AnomaliesBySeverity {
    Write-Host "⚠️ Anomaly distribution by severity..." -ForegroundColor Cyan
    
    $body = @{
        size = 0
        aggs = @{
            by_severity = @{
                terms = @{
                    field = "severity.keyword"
                    size = 10
                }
            }
        }
    } | ConvertTo-Json -Depth 10
    
    $response = Invoke-WebRequest -Method POST -Uri "$ES_HOST/$ML_INDEX/_search" -Body $body -ContentType "application/json" | ConvertFrom-Json
    
    $response.aggregations.by_severity.buckets | ForEach-Object {
        [PSCustomObject]@{
            Severity = $_.key
            Count = $_.doc_count
            Percentage = [math]::Round(($_.doc_count / $response.hits.total.value) * 100, 2)
        }
    } | Format-Table -AutoSize
}

function Get-CriticalAnomalies {
    Write-Host "🚨 Critical anomalies..." -ForegroundColor Red
    
    $body = @{
        size = 20
        sort = @(@{"anomaly_score" = "desc"})
        query = @{
            term = @{
                "severity.keyword" = "critical"
            }
        }
    } | ConvertTo-Json -Depth 10
    
    $response = Invoke-WebRequest -Method POST -Uri "$ES_HOST/$ML_INDEX/_search" -Body $body -ContentType "application/json" | ConvertFrom-Json
    
    $response.hits.hits | ForEach-Object {
        [PSCustomObject]@{
            Timestamp = $_._source.'@timestamp'
            Type = $_._source.anomaly_type
            Score = [math]::Round($_._source.anomaly_score, 2)
            Recommendation = $_._source.recommendation
        }
    } | Format-Table -AutoSize -Wrap
}

function Get-AnomalyTimeline {
    param(
        [int]$Hours = 24
    )
    
    Write-Host "📈 Anomaly timeline (last $Hours hours)..." -ForegroundColor Cyan
    
    $body = @{
        size = 0
        query = @{
            range = @{
                "@timestamp" = @{
                    gte = "now-${Hours}h"
                    lte = "now"
                }
            }
        }
        aggs = @{
            over_time = @{
                date_histogram = @{
                    field = "@timestamp"
                    fixed_interval = "1h"
                }
                aggs = @{
                    avg_score = @{
                        avg = @{
                            field = "anomaly_score"
                        }
                    }
                }
            }
        }
    } | ConvertTo-Json -Depth 10
    
    $response = Invoke-WebRequest -Method POST -Uri "$ES_HOST/$ML_INDEX/_search" -Body $body -ContentType "application/json" | ConvertFrom-Json
    
    $response.aggregations.over_time.buckets | ForEach-Object {
        [PSCustomObject]@{
            Time = $_.key_as_string
            Count = $_.doc_count
            AvgScore = if ($_.avg_score.value) { [math]::Round($_.avg_score.value, 2) } else { 0 }
        }
    } | Format-Table -AutoSize
}

function Get-AnomalyStats {
    Write-Host "📊 ML Anomaly Detection Statistics" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    
    $count_response = Invoke-WebRequest -Uri "$ES_HOST/$ML_INDEX/_count" | ConvertFrom-Json
    Write-Host "Total Anomalies Detected: $($count_response.count)" -ForegroundColor Yellow
    
    $body = @{
        size = 0
        aggs = @{
            avg_score = @{ avg = @{ field = "anomaly_score" } }
            max_score = @{ max = @{ field = "anomaly_score" } }
            min_score = @{ min = @{ field = "anomaly_score" } }
        }
    } | ConvertTo-Json -Depth 10
    
    $stats = Invoke-WebRequest -Method POST -Uri "$ES_HOST/$ML_INDEX/_search" -Body $body -ContentType "application/json" | ConvertFrom-Json
    
    Write-Host "Average Anomaly Score: $([math]::Round($stats.aggregations.avg_score.value, 2))" -ForegroundColor Yellow
    Write-Host "Max Anomaly Score: $([math]::Round($stats.aggregations.max_score.value, 2))" -ForegroundColor Yellow
    Write-Host "Min Anomaly Score: $([math]::Round($stats.aggregations.min_score.value, 2))" -ForegroundColor Yellow
}

function Show-Menu {
    Write-Host "`n🤖 ML Anomaly Detection - Quick Access Menu" -ForegroundColor Magenta
    Write-Host "=============================================" -ForegroundColor Magenta
    Write-Host "1. Latest Anomalies (Last 10)"
    Write-Host "2. Anomalies by Type"
    Write-Host "3. Anomalies by Severity"
    Write-Host "4. Critical Anomalies Only"
    Write-Host "5. Anomaly Timeline (24h)"
    Write-Host "6. Overall Statistics"
    Write-Host "7. Open Kibana Dashboard"
    Write-Host "Q. Quit"
    Write-Host ""
}

# Main menu loop
do {
    Show-Menu
    $choice = Read-Host "Select option"
    
    switch ($choice) {
        '1' { Get-LatestAnomalies }
        '2' { Get-AnomaliesByType }
        '3' { Get-AnomaliesBySeverity }
        '4' { Get-CriticalAnomalies }
        '5' { Get-AnomalyTimeline }
        '6' { Get-AnomalyStats }
        '7' { Start-Process "http://localhost:5601/app/dashboards" }
        'Q' { Write-Host "Goodbye!" -ForegroundColor Green }
        default { Write-Host "Invalid option" -ForegroundColor Red }
    }
    
    if ($choice -ne 'Q') {
        Read-Host "`nPress Enter to continue"
    }
} while ($choice -ne 'Q')
