#!/bin/sh
echo "Content-Type: text/plain"
echo ""

SS_DIR="/usr/share/blanket/screensaver"
DISABLED_DIR="/mnt/us/screensaver_disabled"

read -r POST_BODY
NAME=$(echo "$POST_BODY" | sed 's/.*name=//;s/&.*//')
SRC=$(echo "$POST_BODY" | sed 's/.*src=//;s/&.*//')
NAME=$(echo "$NAME" | sed 's/[^a-zA-Z0-9._-]//g')

if [ -z "$NAME" ]; then
    echo "Error: no filename"
    exit 0
fi

case "$SRC" in
    active)   FILE="$SS_DIR/$NAME" ;;
    disabled) FILE="$DISABLED_DIR/$NAME" ;;
    *)
        echo "Error: invalid source"
        exit 0
        ;;
esac

if [ ! -f "$FILE" ]; then
    echo "Error: file not found"
    exit 0
fi

mntroot rw
rm -f "$FILE"

if [ ! -f "$FILE" ]; then
    echo "Deleted $NAME"
else
    echo "Error: failed to delete"
fi
