#!/bin/bash
# Script to verify dashboard.html fix on VPS

echo "🔍 Verifying dashboard.html fix..."
echo ""

# Check if file exists
if [ ! -f "pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html" ]; then
    echo "❌ Error: dashboard.html not found!"
    exit 1
fi

# Check for duplicate code (the problematic pattern)
DUPLICATE_COUNT=$(grep -c "powerChart.data.labels = commonLabels" pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html)

if [ "$DUPLICATE_COUNT" -gt 1 ]; then
    echo "❌ Error: Found $DUPLICATE_COUNT instances of 'powerChart.data.labels = commonLabels'"
    echo "   Expected: 1 instance (inside updateComparisonCharts function)"
    echo ""
    echo "   Problematic lines:"
    grep -n "powerChart.data.labels = commonLabels" pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html
    exit 1
fi

# Check for orphaned closing braces after line 1597
echo "✅ Checking for orphaned code after updateComparisonCharts function..."
LINES_AFTER_1597=$(sed -n '1598,1610p' pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html)

if echo "$LINES_AFTER_1597" | grep -q "powerChart.data.labels\|} catch\|^[[:space:]]*}[[:space:]]*$"; then
    echo "❌ Error: Found orphaned code after line 1597!"
    echo ""
    echo "   Lines 1598-1610:"
    echo "$LINES_AFTER_1597"
    exit 1
fi

# Check line 1605 specifically
LINE_1605=$(sed -n '1605p' pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html)
echo "📄 Line 1605: $LINE_1605"

if echo "$LINE_1605" | grep -q "try {"; then
    echo "✅ Line 1605 is correct (starts try block)"
else
    echo "⚠️  Warning: Line 1605 doesn't match expected pattern"
fi

# Check JavaScript syntax by counting braces
OPEN_BRACES=$(grep -o '{' pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html | wc -l)
CLOSE_BRACES=$(grep -o '}' pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html | wc -l)

echo ""
echo "📊 Brace count:"
echo "   Opening braces: $OPEN_BRACES"
echo "   Closing braces: $CLOSE_BRACES"

if [ "$OPEN_BRACES" -eq "$CLOSE_BRACES" ]; then
    echo "✅ Braces are balanced"
else
    echo "❌ Error: Braces are NOT balanced! (Difference: $((OPEN_BRACES - CLOSE_BRACES)))"
    exit 1
fi

echo ""
echo "✅ All checks passed! File is ready for deployment."
echo ""
echo "📋 Next steps:"
echo "   1. Commit and push changes to GitHub"
echo "   2. Deploy to VPS (via GitHub Actions or manual)"
echo "   3. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)"
echo "   4. Verify fix on VPS"
