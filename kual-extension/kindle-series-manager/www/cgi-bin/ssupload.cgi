#!/bin/sh
echo "Content-Type: text/plain"
echo ""

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
SS_DIR="$EXT_DIR/screensavers"

if [ -z "$CONTENT_LENGTH" ] || [ "$CONTENT_LENGTH" = "0" ]; then
    echo "Error: no image data received"
    exit 0
fi

MAX_SIZE=10000000
if [ "$CONTENT_LENGTH" -gt "$MAX_SIZE" ] 2>/dev/null; then
    echo "Error: upload too large (max 10MB)"
    exit 0
fi

TMPFILE="/tmp/ss_upload_$$.png"

head -c "$CONTENT_LENGTH" | base64 -d > "$TMPFILE" 2>/dev/null

if [ ! -s "$TMPFILE" ]; then
    rm -f "$TMPFILE"
    echo "Error: failed to decode image"
    exit 0
fi

NEXT_NUM=0
while [ -f "$SS_DIR/bg_ss$(printf '%02d' $NEXT_NUM).png" ]; do
    NEXT_NUM=$((NEXT_NUM + 1))
done
FNAME="bg_ss$(printf '%02d' $NEXT_NUM).png"

mkdir -p "$SS_DIR"
cp "$TMPFILE" "$SS_DIR/$FNAME"
rm -f "$TMPFILE"

if [ -f "$SS_DIR/$FNAME" ]; then
    echo "Saved as $FNAME"
else
    echo "Error: failed to save image"
fi
