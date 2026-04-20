#!/bin/sh

CONF="/mnt/us/extensions/kindle-series-manager/calibre.conf"

CALIBRE_URL=""
THUMB_PATH=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $QUERY_STRING; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        url)  CALIBRE_URL=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        path) THUMB_PATH=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$CALIBRE_URL" ] && [ -f "$CONF" ]; then
    CALIBRE_URL=$(tr -d '\r\n' < "$CONF")
fi

if [ -z "$CALIBRE_URL" ] || [ -z "$THUMB_PATH" ]; then
    echo "Content-Type: text/plain"
    echo "Status: 404"
    echo ""
    echo "Not found"
    exit 0
fi

CALIBRE_URL=$(echo "$CALIBRE_URL" | sed 's|/$||')
FULL_URL="${CALIBRE_URL}${THUMB_PATH}"

TMPFILE=$(mktemp /tmp/calibre_thumb_XXXXXX) || exit 0
trap 'rm -f "$TMPFILE"' EXIT

wget -q -O "$TMPFILE" --timeout=5 "$FULL_URL" 2>/dev/null

if [ ! -s "$TMPFILE" ]; then
    echo "Content-Type: text/plain"
    echo "Status: 404"
    echo ""
    echo "Not found"
    exit 0
fi

FILE_SIZE=$(wc -c < "$TMPFILE" | tr -d ' ')
echo "Content-Type: image/jpeg"
echo "Content-Length: $FILE_SIZE"
echo "Cache-Control: public, max-age=86400"
echo ""
cat "$TMPFILE"
