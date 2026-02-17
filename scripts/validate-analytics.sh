#!/bin/bash
# Analytics Dashboard 自己診断スクリプト
# 構造チェック + Playwright スクリーンショット → Claude が Read で確認

set -euo pipefail

DASHBOARD=".claude/analytics/dashboard/dashboard.html"
SCREENSHOT="/tmp/analytics-check.png"

echo "=== [1/2] Structural Check ==="
python3 - <<'PYEOF'
import re, json, sys

DASHBOARD = ".claude/analytics/dashboard/dashboard.html"
try:
    html = open(DASHBOARD).read()
except FileNotFoundError:
    sys.exit(f"❌ {DASHBOARD} not found — run: make analytics")

# データ埋め込み確認
m = re.search(r'window\.__ANALYTICS_DATA__ = (\{.+?\});', html, re.DOTALL)
if not m:
    sys.exit("❌ No analytics data injected — run: make analytics")

data = json.loads(m.group(1))
s = data["summary"]
print(f"✅ Data: {s['session_count']} sessions, ${s['total_cost']:.2f}, {s['total_tokens']:,} tokens")

# HTML 要素確認
checks = [
    ("Overview panel",  'id="panel-overview"'),
    ("Timeline panel",  'id="panel-timeline"'),
    ("Drilldown panel", 'id="panel-tree"'),
    ("Chart.js CDN",    'chart.js'),
    ("Settings modal",  'id="settings-modal"'),
]
all_ok = True
for name, pat in checks:
    if pat in html:
        print(f"✅ Found: {name}")
    else:
        print(f"⚠️  Missing: {name}")
        all_ok = False

sys.exit(0 if all_ok else 1)
PYEOF

echo ""
echo "=== [2/2] Visual Check (Playwright) ==="
ABS_PATH="$(pwd)/${DASHBOARD}"

if ! command -v npx &>/dev/null; then
    echo "⚠️  npx not found, skipping"
    exit 0
fi

npx playwright screenshot \
    "file://${ABS_PATH}" \
    "${SCREENSHOT}" \
    --wait-for-timeout 3000 \
    2>/dev/null \
    && echo "✅ Screenshot: ${SCREENSHOT}" \
    || echo "⚠️  Screenshot failed (run: npx playwright install chromium)"
