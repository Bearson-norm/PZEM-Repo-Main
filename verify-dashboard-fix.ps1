# Script to verify dashboard.html fix
Write-Host "🔍 Verifying dashboard.html fix..." -ForegroundColor Cyan
Write-Host ""

$filePath = "pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html"

# Check if file exists
if (-not (Test-Path $filePath)) {
    Write-Host "❌ Error: dashboard.html not found!" -ForegroundColor Red
    exit 1
}

# Check for duplicate code
$content = Get-Content $filePath -Raw
$duplicateCount = ([regex]::Matches($content, "powerChart\.data\.labels = commonLabels")).Count

if ($duplicateCount -gt 1) {
    Write-Host "❌ Error: Found $duplicateCount instances of 'powerChart.data.labels = commonLabels'" -ForegroundColor Red
    Write-Host "   Expected: 1 instance (inside updateComparisonCharts function)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Problematic lines:" -ForegroundColor Yellow
    $lines = Get-Content $filePath
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "powerChart\.data\.labels = commonLabels") {
            Write-Host "   Line $($i + 1): $($lines[$i])" -ForegroundColor Red
        }
    }
    exit 1
}

# Check line 1605
$allLines = Get-Content $filePath
$line1605 = $allLines[1604]  # 0-indexed

Write-Host "📄 Line 1605: $line1605" -ForegroundColor Cyan

if ($line1605 -match "try \{") {
    Write-Host "✅ Line 1605 is correct (starts try block)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Warning: Line 1605 doesn't match expected pattern" -ForegroundColor Yellow
}

# Check for orphaned code after line 1597
Write-Host ""
Write-Host "✅ Checking for orphaned code after updateComparisonCharts function..." -ForegroundColor Cyan
$linesAfter1597 = $allLines[1597..1609] -join "`n"

if ($linesAfter1597 -match "powerChart\.data\.labels|^\s*\}\s*catch|^\s*\}\s*$") {
    Write-Host "❌ Error: Found orphaned code after line 1597!" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Lines 1598-1610:" -ForegroundColor Yellow
    for ($i = 1597; $i -lt [Math]::Min(1610, $allLines.Count); $i++) {
        Write-Host "   Line $($i + 1): $($allLines[$i])" -ForegroundColor Red
    }
    exit 1
}

# Check JavaScript syntax by counting braces
$openBraces = ([regex]::Matches($content, '\{')).Count
$closeBraces = ([regex]::Matches($content, '\}')).Count

Write-Host ""
Write-Host "📊 Brace count:" -ForegroundColor Cyan
Write-Host "   Opening braces: $openBraces" -ForegroundColor White
Write-Host "   Closing braces: $closeBraces" -ForegroundColor White

if ($openBraces -eq $closeBraces) {
    Write-Host "✅ Braces are balanced" -ForegroundColor Green
} else {
    $diff = $openBraces - $closeBraces
    Write-Host "❌ Error: Braces are NOT balanced! (Difference: $diff)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ All checks passed! File is ready for deployment." -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Commit and push changes to GitHub" -ForegroundColor White
Write-Host "   2. Deploy to VPS (via GitHub Actions or manual)" -ForegroundColor White
Write-Host "   3. Clear browser cache (Ctrl+Shift+R)" -ForegroundColor White
Write-Host "   4. Verify fix on VPS" -ForegroundColor White
