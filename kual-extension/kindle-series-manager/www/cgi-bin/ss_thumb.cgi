#!/bin/sh

SS_DIR="/usr/share/blanket/screensaver"
DISABLED_DIR="/mnt/us/screensaver_disabled"

NAME=$(echo "$QUERY_STRING" | sed 's/.*name=//;s/&.*//')
SRC=$(echo "$QUERY_STRING" | sed 's/.*src=//;s/&.*//')

NAME=$(echo "$NAME" | sed 's/[^a-zA-Z0-9._-]//g')

case "$SRC" in
    active)   FILE="$SS_DIR/$NAME" ;;
    disabled) FILE="$DISABLED_DIR/$NAME" ;;
    *)
        echo "Content-Type: text/plain"
        echo ""
        echo "Invalid source"
        exit 0
        ;;
esac

if [ ! -f "$FILE" ]; then
    echo "Content-Type: text/plain"
    echo ""
    echo "Not found"
    exit 0
fi

FILE_SIZE=$(wc -c < "$FILE" | tr -d ' ')
echo "Content-Type: image/png"
echo "Content-Length: $FILE_SIZE"
echo "Cache-Control: public, max-age=86400"
echo ""
cat "$FILE"
