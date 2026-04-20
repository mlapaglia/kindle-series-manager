#!/bin/sh
echo "Content-Type: text/plain"
echo ""

GR_DIR="/mnt/us/extensions/kindle-series-manager/goodreads"
LOGIN_SCRIPT="$GR_DIR/gr_login.sh"

if [ ! -f "$LOGIN_SCRIPT" ]; then
    echo "Error: gr_login.sh not found"
    exit 0
fi

if [ ! -f "$GR_DIR/gr_creds.json" ]; then
    echo "Error: Save credentials first"
    exit 0
fi

bash "$LOGIN_SCRIPT" 2>&1
