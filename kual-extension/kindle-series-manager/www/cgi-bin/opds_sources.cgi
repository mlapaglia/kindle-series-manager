#!/bin/sh
echo "Content-Type: application/json"
echo ""

CONF="/mnt/us/extensions/kindle-series-manager/opds_sources.json"

if [ "$REQUEST_METHOD" = "POST" ]; then
    read -r POST_BODY
    echo "$POST_BODY" > "$CONF"
    printf '{"status":"ok"}'
else
    if [ -f "$CONF" ]; then
        cat "$CONF"
    else
        printf '{"sources":[]}'
    fi
fi
