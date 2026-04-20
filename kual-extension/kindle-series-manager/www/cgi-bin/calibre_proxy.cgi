#!/bin/sh
echo "Content-Type: application/json"
echo ""

CONF="/mnt/us/extensions/kindle-series-manager/calibre.conf"

CALIBRE_URL=""
API_PATH=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $QUERY_STRING; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        url)  CALIBRE_URL=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        path) API_PATH=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$CALIBRE_URL" ] && [ -f "$CONF" ]; then
    CALIBRE_URL=$(tr -d '\r\n' < "$CONF")
fi

if [ -z "$CALIBRE_URL" ]; then
    printf '{"error":"No Calibre URL configured"}'
    exit 0
fi

if [ -z "$API_PATH" ]; then
    printf '{"error":"No API path specified"}'
    exit 0
fi

CALIBRE_URL=$(echo "$CALIBRE_URL" | sed 's|/$||')
FULL_URL="${CALIBRE_URL}${API_PATH}"

RESULT=$(wget -q -O - --timeout=10 "$FULL_URL" 2>/dev/null)
if [ -z "$RESULT" ]; then
    printf '{"error":"Failed to reach Calibre"}'
    exit 0
fi

printf '%s' "$RESULT"
