#!/bin/sh
echo "Content-Type: text/html"
echo ""

HC_DIR="/mnt/us/extensions/kindle-series-manager/hardcover"
CONFIG="$HC_DIR/hc_config.json"
MAPPING_FILE="$HC_DIR/hc_mapping.json"
LOG_FILE="$HC_DIR/hc_sync.log"
FLAG_FILE="/mnt/us/ENABLE_HC_SYNC"

html_escape() {
    echo "$1" | sed 's/&/\&amp;/g;s/</\&lt;/g;s/>/\&gt;/g;s/"/\&quot;/g;s/'"'"'/\&#39;/g'
}

TOKEN_SET="false"
if [ -f "$CONFIG" ]; then
    TOKEN=$(grep '"token"' "$CONFIG" | sed 's/.*"token".*"\([^"]*\)".*/\1/')
    if [ -n "$TOKEN" ]; then
        TOKEN_SET="true"
    fi
fi

SERVICE_STATUS="unknown"
SERVICE_RAW=$(status hc-sync 2>/dev/null)
case "$SERVICE_RAW" in
    *"start/running"*) SERVICE_STATUS="running" ;;
    *"stop/waiting"*) SERVICE_STATUS="stopped" ;;
esac

FLAG_ENABLED="false"
if [ -f "$FLAG_FILE" ]; then
    FLAG_ENABLED="true"
fi

echo "<div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Hardcover API Token</span></div>"
echo "<p style='font-size:13px;color:var(--fg-muted);margin:0 0 8px 0;'>Get your token from <strong>hardcover.app &rarr; Settings &rarr; API</strong></p>"
echo "<input type='password' id='hcToken' class='input-field input-small' placeholder='Paste your Hardcover API token'>"
echo "<button class='btn' onclick='hcSaveToken()' style='margin-right:8px;'>Save Token</button>"
echo "<button class='btn btn-secondary' onclick='hcTestToken()' style='margin-right:8px;'>Test</button>"
if [ "$TOKEN_SET" = "true" ]; then
    echo "<span id='hcTokenStatus' style='font-size:13px;color:#27ae60;'>Token configured</span>"
else
    echo "<span id='hcTokenStatus' style='font-size:13px;color:var(--fg-muted);'>No token set</span>"
fi
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Book Mapping</span></div>"
echo "<p style='font-size:13px;color:var(--fg-muted);margin:0 0 8px 0;'>Maps your Kindle books to Hardcover books by searching titles.</p>"
echo "<button class='btn' onclick='hcBuildMapping()' style='margin-bottom:8px;'>Build Mapping</button>"
echo "<pre id='hcMappingOutput' style='margin-top:8px;font-size:12px;max-height:200px;overflow-y:auto;background:var(--surface-alt);padding:8px;border-radius:6px;border:1px solid var(--border);display:none;white-space:pre-wrap;word-break:break-all;'></pre>"

echo "<div id='hcMappingTable'>"
if [ -f "$MAPPING_FILE" ]; then
    echo "<table style='width:100%;font-size:13px;border-collapse:collapse;margin-top:8px;'>"
    echo "<tr style='text-align:left;border-bottom:2px solid var(--border);'><th style='padding:6px;'>Kindle Title</th><th style='padding:6px;'>Hardcover Title</th><th style='padding:6px;'>HC ID</th><th style='padding:6px;'>Pages</th><th style='padding:6px;'>Read ID</th></tr>"
    grep '"cdeKey"' "$MAPPING_FILE" | while read -r LINE; do
        K_TITLE=$(echo "$LINE" | grep -o '"kindleTitle":"[^"]*"' | sed 's/"kindleTitle":"//;s/"//')
        H_TITLE=$(echo "$LINE" | grep -o '"hcTitle":"[^"]*"' | sed 's/"hcTitle":"//;s/"//')
        H_ID=$(echo "$LINE" | grep -o '"hcBookId":"[^"]*"' | sed 's/"hcBookId":"//;s/"//')
        H_PAGES=$(echo "$LINE" | grep -o '"hcPages":[0-9]*' | sed 's/"hcPages"://')
        UBR_ID=$(echo "$LINE" | grep -o '"userBookReadId":[0-9]*' | sed 's/"userBookReadId"://')
        K_TITLE=$(html_escape "$K_TITLE")
        H_TITLE=$(html_escape "$H_TITLE")
        H_ID=$(html_escape "$H_ID")
        H_PAGES=$(html_escape "${H_PAGES:-—}")
        UBR_ID=$(html_escape "${UBR_ID:-—}")
        echo "<tr style='border-bottom:1px solid var(--border-row);'><td style='padding:6px;'>$K_TITLE</td><td style='padding:6px;'>$H_TITLE</td><td style='padding:6px;'>$H_ID</td><td style='padding:6px;'>$H_PAGES</td><td style='padding:6px;'>$UBR_ID</td></tr>"
    done
    echo "</table>"
else
    echo "<div style='font-size:13px;color:var(--fg-fainter);margin-top:8px;'>No mapping file found. Click Build Mapping to create one.</div>"
fi
echo "</div>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Sync Service</span></div>"
echo "<div style='font-size:14px;margin-bottom:4px;'>Service: <strong id='hcSvcStatus'>"
if [ "$SERVICE_STATUS" = "running" ]; then
    echo "<span style='color:#27ae60;'>Running</span>"
elif [ "$SERVICE_STATUS" = "stopped" ]; then
    echo "<span style='color:var(--danger);'>Stopped</span>"
else
    echo "<span style='color:var(--fg-muted);'>Unknown</span>"
fi
echo "</strong></div>"
echo "<div style='font-size:14px;margin-bottom:8px;'>Auto-start: <strong>"
if [ "$FLAG_ENABLED" = "true" ]; then
    echo "<span style='color:#27ae60;'>Enabled</span>"
else
    echo "<span style='color:var(--fg-muted);'>Disabled</span>"
fi
echo "</strong></div>"
echo "<button class='btn' onclick='hcRefreshStatus()' style='margin-right:8px;'>Refresh Status</button>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Sync Log</span></div>"
echo "<pre id='hcSyncLog' style='font-size:12px;max-height:300px;overflow-y:auto;background:var(--surface-alt);padding:8px;border-radius:6px;border:1px solid var(--border);white-space:pre-wrap;word-break:break-all;'>"
if [ -f "$LOG_FILE" ]; then
    tail -30 "$LOG_FILE"
else
    echo "(no log file yet)"
fi
echo "</pre>"
echo "</div>"

echo "</div>"
