#!/bin/sh
echo "Content-Type: text/plain"
echo ""

HC_DIR="/mnt/us/extensions/kindle-series-manager/hardcover"
CONFIG="$HC_DIR/hc_config.json"

read -r POST_BODY

TOKEN=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        token) TOKEN=$(echo "$PVAL" | sed 's/+/ /g;s/%20/ /g;s/%3A/:/g;s/%2F/\//g;s/%3D/=/g;s/%2B/+/g') ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$TOKEN" ]; then
    echo "Error: token is required"
    exit 0
fi

mkdir -p "$HC_DIR"

SAFE_TOKEN=$(echo "$TOKEN" | sed 's/\\/\\\\/g;s/"/\\"/g')

API_URL="https://api.hardcover.app/v1/graphql"
if [ -f "$CONFIG" ]; then
    EXISTING_URL=$(grep '"api_url"' "$CONFIG" | sed 's/.*"api_url".*"\([^"]*\)".*/\1/')
    if [ -n "$EXISTING_URL" ]; then
        API_URL="$EXISTING_URL"
    fi
fi

cat > "$CONFIG" << EOF
{
  "token": "$SAFE_TOKEN",
  "api_url": "$API_URL"
}
EOF

echo "Token saved"
