#!/bin/sh
echo "Content-Type: text/html"
echo ""

GR_DIR="/mnt/us/extensions/kindle-series-manager/goodreads"
CREDS_FILE="$GR_DIR/gr_creds.json"
COOKIE_JAR="$GR_DIR/gr_cookies.txt"
MAPPING_FILE="$GR_DIR/gr_mapping.json"
LOG_FILE="$GR_DIR/gr_sync.log"
FLAG_FILE="/mnt/us/ENABLE_GR_SYNC"

html_escape() {
    echo "$1" | sed 's/&/\&amp;/g;s/</\&lt;/g;s/>/\&gt;/g;s/"/\&quot;/g;s/'"'"'/\&#39;/g'
}

EMAIL=""
USER_ID=""
if [ -f "$CREDS_FILE" ]; then
    EMAIL=$(grep '"email"' "$CREDS_FILE" | sed 's/.*"email".*"\([^"]*\)".*/\1/')
    USER_ID=$(grep '"goodreads_user_id"' "$CREDS_FILE" | sed 's/.*"goodreads_user_id".*"\([^"]*\)".*/\1/')
fi
SAFE_EMAIL=$(html_escape "$EMAIL")
SAFE_USER_ID=$(html_escape "$USER_ID")

LOGGED_IN="false"
if [ -f "$COOKIE_JAR" ] && [ -f "$GR_DIR/gr_session.txt" ]; then
    LOGGED_IN="true"
fi

SERVICE_STATUS="unknown"
SERVICE_RAW=$(status gr-sync 2>/dev/null)
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
echo "<div class='card-header'><span class='card-title'>Goodreads Credentials</span></div>"
echo "<input type='text' id='grEmail' class='input-field input-small' placeholder='Email' value='$SAFE_EMAIL'>"
echo "<input type='password' id='grPassword' class='input-field input-small' placeholder='Password'>"
echo "<input type='text' id='grUserId' class='input-field input-small' placeholder='Goodreads User ID (e.g. 183958037)' value='$SAFE_USER_ID'>"
echo "<button class='btn' onclick='grSaveCreds()' style='margin-right:8px;'>Save Credentials</button>"
echo "<span id='credsStatus' style='font-size:13px;color:var(--fg-muted);'></span>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Authentication</span></div>"
if [ "$LOGGED_IN" = "true" ]; then
    echo "<div style='margin-bottom:8px;font-size:14px;color:var(--fg-muted);'>Status: <strong style='color:#27ae60;'>Logged in</strong></div>"
    echo "<button class='btn btn-danger' onclick='grLogout()'>Log out of Goodreads</button>"
else
    echo "<div style='margin-bottom:8px;font-size:14px;color:var(--fg-muted);'>Status: <strong style='color:var(--danger);'>Not logged in</strong></div>"
    echo "<button class='btn' onclick='grLogin()'>Sign In to Goodreads</button>"
fi
echo "<pre id='loginOutput' style='margin-top:8px;font-size:12px;max-height:200px;overflow-y:auto;background:var(--surface-alt);padding:8px;border-radius:6px;border:1px solid var(--border);display:none;white-space:pre-wrap;word-break:break-all;'></pre>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Book Mapping</span></div>"
echo "<p style='font-size:13px;color:var(--fg-muted);margin:0 0 8px 0;'>Maps your Kindle books to Goodreads books using your currently-reading shelf.</p>"
echo "<button class='btn' onclick='grBuildMapping()' style='margin-bottom:8px;'>Build Mapping</button>"
echo "<pre id='mappingOutput' style='margin-top:8px;font-size:12px;max-height:200px;overflow-y:auto;background:var(--surface-alt);padding:8px;border-radius:6px;border:1px solid var(--border);display:none;white-space:pre-wrap;word-break:break-all;'></pre>"

echo "<div id='mappingTable'>"
if [ -f "$MAPPING_FILE" ]; then
    echo "<table style='width:100%;font-size:13px;border-collapse:collapse;margin-top:8px;'>"
    echo "<tr style='text-align:left;border-bottom:2px solid var(--border);'><th style='padding:6px;'>Kindle Title</th><th style='padding:6px;'>Goodreads Title</th><th style='padding:6px;'>Book ID</th></tr>"
    grep '"cdeKey"' "$MAPPING_FILE" | while read -r LINE; do
        K_TITLE=$(echo "$LINE" | grep -o '"kindleTitle":"[^"]*"' | sed 's/"kindleTitle":"//;s/"//')
        G_TITLE=$(echo "$LINE" | grep -o '"grTitle":"[^"]*"' | sed 's/"grTitle":"//;s/"//')
        G_ID=$(echo "$LINE" | grep -o '"grBookId":"[^"]*"' | sed 's/"grBookId":"//;s/"//')
        K_TITLE=$(html_escape "$K_TITLE")
        G_TITLE=$(html_escape "$G_TITLE")
        G_ID=$(html_escape "$G_ID")
        echo "<tr style='border-bottom:1px solid var(--border-row);'><td style='padding:6px;'>$K_TITLE</td><td style='padding:6px;'>$G_TITLE</td><td style='padding:6px;'>$G_ID</td></tr>"
    done
    echo "</table>"
else
    echo "<div style='font-size:13px;color:var(--fg-fainter);margin-top:8px;'>No mapping file found. Click Build Mapping to create one.</div>"
fi
echo "</div>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Sync Service</span></div>"
echo "<div style='font-size:14px;margin-bottom:4px;'>Service: <strong id='svcStatus'>"
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
echo "<button class='btn' onclick='grRefreshStatus()' style='margin-right:8px;'>Refresh Status</button>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Sync Log</span></div>"
echo "<pre id='syncLog' style='font-size:12px;max-height:300px;overflow-y:auto;background:var(--surface-alt);padding:8px;border-radius:6px;border:1px solid var(--border);white-space:pre-wrap;word-break:break-all;'>"
if [ -f "$LOG_FILE" ]; then
    tail -30 "$LOG_FILE"
else
    echo "(no log file yet)"
fi
echo "</pre>"
echo "</div>"

echo "</div>"
