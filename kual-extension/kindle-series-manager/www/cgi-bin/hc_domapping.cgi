#!/bin/sh
echo "Content-Type: text/plain"
echo ""

HC_DIR="/mnt/us/extensions/kindle-series-manager/hardcover"
MAPPING_SCRIPT="$HC_DIR/hc_build_mapping.sh"
CONFIG="$HC_DIR/hc_config.json"

if [ ! -f "$MAPPING_SCRIPT" ]; then
    echo "Error: hc_build_mapping.sh not found"
    exit 0
fi

if [ ! -f "$CONFIG" ]; then
    echo "Error: Save your API token first"
    exit 0
fi

TOKEN=$(grep '"token"' "$CONFIG" | sed 's/.*"token".*"\([^"]*\)".*/\1/')
if [ -z "$TOKEN" ]; then
    echo "Error: API token not configured"
    exit 0
fi

sh "$MAPPING_SCRIPT" 2>&1
