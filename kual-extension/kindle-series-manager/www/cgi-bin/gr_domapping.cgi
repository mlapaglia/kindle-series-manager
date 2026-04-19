#!/bin/sh
echo "Content-Type: text/plain"
echo ""

GR_DIR="/mnt/us/extensions/kindle-series-manager/goodreads"
MAPPING_SCRIPT="$GR_DIR/gr_build_mapping.sh"

if [ ! -f "$MAPPING_SCRIPT" ]; then
    echo "Error: gr_build_mapping.sh not found"
    exit 0
fi

if [ ! -f "$GR_DIR/gr_creds.json" ]; then
    echo "Error: Save credentials first"
    exit 0
fi

bash "$MAPPING_SCRIPT" 2>&1
