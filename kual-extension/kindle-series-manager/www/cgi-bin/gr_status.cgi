#!/bin/sh
echo "Content-Type: application/json"
echo ""

GR_DIR="/mnt/us/extensions/kindle-series-manager/goodreads"
FLAG_FILE="/mnt/us/ENABLE_GR_SYNC"
LOG_FILE="$GR_DIR/gr_sync.log"

LOGGED_IN="false"
if [ -f "$GR_DIR/gr_cookies.txt" ] && [ -f "$GR_DIR/gr_session.txt" ]; then
    LOGGED_IN="true"
fi

MAPPING_COUNT=0
if [ -f "$GR_DIR/gr_mapping.json" ]; then
    MAPPING_COUNT=$(grep -c '"cdeKey"' "$GR_DIR/gr_mapping.json" 2>/dev/null || echo "0")
fi

SERVICE_RUNNING="false"
SERVICE_RAW=$(status gr-sync 2>/dev/null)
case "$SERVICE_RAW" in
    *"start/running"*) SERVICE_RUNNING="true" ;;
esac

FLAG_ENABLED="false"
if [ -f "$FLAG_FILE" ]; then
    FLAG_ENABLED="true"
fi

LAST_LOG=""
if [ -f "$LOG_FILE" ]; then
    LAST_LOG=$(tail -30 "$LOG_FILE" | sed 's/\\/\\\\/g;s/"/\\"/g;s/	/\\t/g' | awk '{printf "%s\\n", $0}')
fi

echo "{\"logged_in\":$LOGGED_IN,\"mapping_count\":$MAPPING_COUNT,\"service_running\":$SERVICE_RUNNING,\"flag_enabled\":$FLAG_ENABLED,\"last_log\":\"$LAST_LOG\"}"
