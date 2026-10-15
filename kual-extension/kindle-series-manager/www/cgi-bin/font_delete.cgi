#!/bin/sh
echo "Content-Type: text/plain"
echo ""

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
FONTS_DIR="$EXT_DIR/fonts"
DISABLED_DIR="$EXT_DIR/fonts-disabled"
SYSTEM_FONTS_DIR="/mnt/us/fonts"

read -r POST_BODY
NAME=$(echo "$POST_BODY" | sed 's/.*name=//;s/&.*//')
SRC=$(echo "$POST_BODY" | sed 's/.*src=//;s/&.*//')
NAME=$(echo "$NAME" | sed 's/+/ /g' | sed 's/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\\x\1/g' | xargs -0 printf "%b" 2>/dev/null || echo "$NAME" | sed 's/+/ /g')

# Validate filename: no path traversal
case "$NAME" in
    */* | *\\* | *..* | "")
        echo "Error: invalid filename"
        exit 0
        ;;
esac

case "$SRC" in
    active)   FILE="$FONTS_DIR/$NAME" ;;
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

# Remove symlink from system fonts if exists
rm -f "$SYSTEM_FONTS_DIR/$NAME"

# Delete the font file
rm -f "$FILE"

if [ ! -f "$FILE" ]; then
    echo "Deleted $NAME"
else
    echo "Error: failed to delete"
fi
