#!/bin/sh
echo "Content-Type: text/plain"
echo ""

SS_DIR="/usr/share/blanket/screensaver"
DISABLED_DIR="/mnt/us/screensaver_disabled"

read -r POST_BODY
NAME=$(echo "$POST_BODY" | sed 's/name=//;s/&.*//')
NAME=$(echo "$NAME" | sed 's/[^a-zA-Z0-9._-]//g')

if [ -z "$NAME" ]; then
    echo "Error: no filename"
    exit 0
fi

if [ ! -f "$SS_DIR/$NAME" ]; then
    echo "Error: file not found"
    exit 0
fi

mkdir -p "$DISABLED_DIR"
mntroot rw
mv "$SS_DIR/$NAME" "$DISABLED_DIR/$NAME"

if [ -f "$DISABLED_DIR/$NAME" ]; then
    echo "Disabled $NAME"
else
    echo "Error: failed to move file"
fi
