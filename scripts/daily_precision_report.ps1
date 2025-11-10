# Daily Precision Report Generator

param(
    [int]$Days = 7
)

Write-Host "📊 Generating $Days-day Precision Report..." -ForegroundColor Cyan

$report = @"
═══════════════════════════════════════════════════════
    ML MODEL PRECISION REPORT - $(Get-Date -Format 'yyyy-MM-dd')
═══════════════════════════════════════════════════════

Period: Last $Days days
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

"@

# Fetch precision data for each day
for ($i = 0; $i -lt $Days; $i++) {
    $dayStart = (Get-Date).AddDays(-$i-1).ToString("yyyy-MM-dd")
    $dayEnd = (Get-Date).AddDays(-$i).ToString("yyyy-MM-dd")
    
    $body = @{
        size = 0
        query = @{
            bool = @{
                must = @(
                    @{range = @{"@timestamp" = @{gte = $dayStart; lt = $dayEnd}}},
                    @{exists = @{field = "is_verified"}}
                )
            }
        }
        aggs = @{
            tp = @{filter = @{term = @{is_true_positive = $true}}}
            fp = @{filter = @{term = @{is_true_positive = $false}}}
        }
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-WebRequest -Method POST -Uri "http://localhost:9200/firefox-ml-anomalies-*/_search" -Body $body -ContentType "application/json" | ConvertFrom-Json
    
    $total = $result.hits.total.value
    $tp = $result.aggregations.tp.doc_count
    $fp = $result.aggregations.fp.doc_count
    $precision = if ($total -gt 0) { $tp / $total } else { 0 }
    
    $status = if ($precision -ge 0.85) { "✅" } else { "⚠️" }
    
    $report += @"
$dayStart : Precision $([math]::Round($precision*100, 1))% (TP:$tp FP:$fp) $status
"@
}

$report += @"

═══════════════════════════════════════════════════════

TARGET PRECISION: 85%
STATUS: $(if ($precision -ge 0.85) {"✅ MEETING TARGET"} else {"⚠️ BELOW TARGET"})

"@

Write-Host $report

# Save to file
$report | Out-File "ml_precision_report_$(Get-Date -Format 'yyyyMMdd').txt"
Write-Host "`n✅ Report saved to: ml_precision_report_$(Get-Date -Format 'yyyyMMdd').txt" -ForegroundColor Green
