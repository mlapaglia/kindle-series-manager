#!/bin/sh
echo "Content-Type: application/json"
echo ""

HC_DIR="/mnt/us/extensions/kindle-series-manager/hardcover"
CONFIG="$HC_DIR/hc_config.json"

if [ ! -f "$CONFIG" ]; then
    echo '{"ok":false,"error":"No config found. Save your token first."}'
    exit 0
fi

TOKEN=$(grep '"token"' "$CONFIG" | sed 's/.*"token".*"\([^"]*\)".*/\1/')
API_URL=$(grep '"api_url"' "$CONFIG" | sed 's/.*"api_url".*"\([^"]*\)".*/\1/')

if [ -z "$TOKEN" ]; then
    echo '{"ok":false,"error":"No API token configured."}'
    exit 0
fi

API_URL="${API_URL:-https://api.hardcover.app/v1/graphql}"

RESPONSE=$(curl -s -m 10 -X POST "$API_URL" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query":"query { me { id username } }"}' 2>&1)

if [ $? -ne 0 ]; then
    echo '{"ok":false,"error":"Connection failed: could not reach Hardcover API."}'
    exit 0
fi

USERNAME=$(echo "$RESPONSE" | grep -o '"username":"[^"]*"' | head -1 | sed 's/"username":"//;s/"//')

if [ -n "$USERNAME" ]; then
    echo "{\"ok\":true,\"username\":\"$USERNAME\"}"
else
    ERROR=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | head -1 | sed 's/"message":"//;s/"//')
    if [ -z "$ERROR" ]; then
        ERROR="Invalid token or unexpected response"
    fi
    echo "{\"ok\":false,\"error\":\"$ERROR\"}"
fi
