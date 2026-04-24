#!/bin/sh
echo "Content-Type: application/xml"
echo ""

OPDS_URL=""
AUTH=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $QUERY_STRING; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        url)  OPDS_URL=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        auth) AUTH=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$OPDS_URL" ]; then
    echo "<error>No OPDS URL provided</error>"
    exit 0
fi

case "$OPDS_URL" in
    http://*|https://*) ;;
    *) echo "<error>Invalid URL (must be http or https)</error>"; exit 0 ;;
esac

if [ -n "$AUTH" ]; then
    OPDS_USER=$(echo "$AUTH" | cut -d: -f1)
    OPDS_PASS=$(echo "$AUTH" | cut -d: -f2-)
    RESULT=$(wget -q -O - --timeout=15 --user="$OPDS_USER" --password="$OPDS_PASS" "$OPDS_URL" 2>/dev/null)
else
    RESULT=$(wget -q -O - --timeout=15 "$OPDS_URL" 2>/dev/null)
fi

if [ -z "$RESULT" ]; then
    echo "<error>Failed to fetch OPDS feed</error>"
else
    printf '%s' "$RESULT"
fi
