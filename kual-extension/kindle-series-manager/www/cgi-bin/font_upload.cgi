#!/bin/sh
echo "Content-Type: text/plain"
echo ""

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
FONTS_DIR="$EXT_DIR/fonts"
SYSTEM_FONTS_DIR="/mnt/us/fonts"

if [ -z "$CONTENT_LENGTH" ] || [ "$CONTENT_LENGTH" = "0" ]; then
    echo "Error: no font data received"
    exit 0
fi

MAX_SIZE=104857600
if [ "$CONTENT_LENGTH" -gt "$MAX_SIZE" ] 2>/dev/null; then
    echo "Error: upload too large (max 100MB)"
    exit 0
fi

# Extract filename from query string
NAME=""
if [ -n "$QUERY_STRING" ]; then
    NAME=$(echo "$QUERY_STRING" | sed 's/.*name=//;s/&.*//')
    # URL decode: + to space, %XX to chars
    NAME=$(echo "$NAME" | sed 's/+/ /g' | sed 's/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\\x\1/g' | xargs -0 printf "%b" 2>/dev/null || echo "$NAME" | sed 's/+/ /g')
fi

# Validate filename: no path traversal
case "$NAME" in
    */* | *\\* | *..* | "")
        echo "Error: invalid filename"
        exit 0
        ;;
esac

# Validate extension
EXT=$(echo "$NAME" | sed 's/.*\.//' | tr 'A-Z' 'a-z')
case "$EXT" in
    ttf|otf|ttc) ;;
    *)
        echo "Error: unsupported format (use .ttf, .otf, or .ttc)"
        exit 0
        ;;
esac

TMPFILE="/tmp/font_upload_$$.tmp"

head -c "$CONTENT_LENGTH" | base64 -d > "$TMPFILE" 2>/dev/null

if [ ! -s "$TMPFILE" ]; then
    rm -f "$TMPFILE"
    echo "Error: failed to decode font data"
    exit 0
fi

# Validate magic bytes
MAGIC=$(xxd -l 4 -p "$TMPFILE" 2>/dev/null || od -A n -t x1 -N 4 "$TMPFILE" | tr -d ' \n')
case "$MAGIC" in
    00010000|74727565) FORMAT="ttf" ;;
    4f54544f) FORMAT="otf" ;;
    74746366) FORMAT="ttc" ;;
    *)
        echo "Error: not a valid font file"
        rm -f "$TMPFILE"
        exit 0
        ;;
esac

mkdir -p "$FONTS_DIR" "$SYSTEM_FONTS_DIR"
cp "$TMPFILE" "$FONTS_DIR/$NAME"
rm -f "$TMPFILE"

if [ ! -f "$FONTS_DIR/$NAME" ]; then
    echo "Error: failed to save font"
    exit 0
fi

# Create symlink in system fonts directory
ln -sf "$FONTS_DIR/$NAME" "$SYSTEM_FONTS_DIR/$NAME"

echo "Uploaded $NAME"
