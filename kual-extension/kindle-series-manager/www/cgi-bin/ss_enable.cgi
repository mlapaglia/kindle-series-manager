#!/bin/sh
echo "Content-Type: text/plain"
echo ""

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
SS_DIR="$EXT_DIR/screensavers"
DISABLED_DIR="$EXT_DIR/screensavers/disabled"

read -r POST_BODY
NAME=$(echo "$POST_BODY" | sed 's/name=//;s/&.*//')
NAME=$(echo "$NAME" | sed 's/[^a-zA-Z0-9._-]//g')

if [ -z "$NAME" ]; then
    echo "Error: no filename"
    exit 0
fi

if [ ! -f "$DISABLED_DIR/$NAME" ]; then
    echo "Error: file not found"
    exit 0
fi

NEXT_NUM=0
while [ -f "$SS_DIR/bg_ss$(printf '%02d' $NEXT_NUM).png" ]; do
    NEXT_NUM=$((NEXT_NUM + 1))
done
NEW_NAME="bg_ss$(printf '%02d' $NEXT_NUM).png"

mkdir -p "$SS_DIR"
mv "$DISABLED_DIR/$NAME" "$SS_DIR/$NEW_NAME"

if [ -f "$SS_DIR/$NEW_NAME" ]; then
    echo "Enabled as $NEW_NAME"
else
    echo "Error: failed to move file"
fi
