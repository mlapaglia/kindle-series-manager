#!/bin/sh
echo "Content-Type: text/plain"
echo ""

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
FONTS_DIR="$EXT_DIR/fonts"
DISABLED_DIR="$EXT_DIR/fonts-disabled"
SYSTEM_FONTS_DIR="/mnt/us/fonts"

read -r POST_BODY
NAME=$(echo "$POST_BODY" | sed 's/name=//;s/&.*//')
NAME=$(echo "$NAME" | sed 's/+/ /g' | sed 's/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\\x\1/g' | xargs -0 printf "%b" 2>/dev/null || echo "$NAME" | sed 's/+/ /g')

# Validate filename: no path traversal
case "$NAME" in
    */* | *\\* | *..* | "")
        echo "Error: invalid filename"
        exit 0
        ;;
esac

if [ ! -f "$FONTS_DIR/$NAME" ]; then
    echo "Error: font not found"
    exit 0
fi

# Remove symlink from system fonts
rm -f "$SYSTEM_FONTS_DIR/$NAME"

# Move to disabled directory
mkdir -p "$DISABLED_DIR"
mv "$FONTS_DIR/$NAME" "$DISABLED_DIR/$NAME"

if [ -f "$DISABLED_DIR/$NAME" ]; then
    echo "Disabled $NAME"
else
    echo "Error: failed to disable font"
fi
