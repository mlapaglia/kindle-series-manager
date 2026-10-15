#!/bin/sh
echo "Content-Type: application/json"
echo ""

HC_DIR="/mnt/us/extensions/kindle-series-manager/hardcover"
CONFIG="$HC_DIR/hc_config.json"
FLAG_FILE="/mnt/us/ENABLE_HC_SYNC"
LOG_FILE="$HC_DIR/hc_sync.log"
MAPPING_FILE="$HC_DIR/hc_mapping.json"

TOKEN_SET="false"
if [ -f "$CONFIG" ]; then
    TOKEN=$(grep '"token"' "$CONFIG" | sed 's/.*"token".*"\([^"]*\)".*/\1/')
    if [ -n "$TOKEN" ]; then
        TOKEN_SET="true"
    fi
fi

MAPPING_COUNT=0
if [ -f "$MAPPING_FILE" ]; then
    MAPPING_COUNT=$(grep -c '"cdeKey"' "$MAPPING_FILE" 2>/dev/null || echo "0")
fi

SERVICE_RUNNING="false"
SERVICE_RAW=$(status hc-sync 2>/dev/null)
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

echo "{\"token_set\":$TOKEN_SET,\"mapping_count\":$MAPPING_COUNT,\"service_running\":$SERVICE_RUNNING,\"flag_enabled\":$FLAG_ENABLED,\"last_log\":\"$LAST_LOG\"}"
