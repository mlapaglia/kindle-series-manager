#!/bin/sh
echo "Content-Type: application/json"
echo ""

DOC_DIR="/mnt/us/documents"
MAX_SIZE=67000000

json_escape() {
    echo "$1" | sed 's/\\/\\\\/g;s/"/\\"/g'
}

json_ok() {
    EPATH=$(json_escape "$1")
    ENAME=$(json_escape "$2")
    printf '{"status":"ok","path":"%s","filename":"%s","size":%s}' "$EPATH" "$ENAME" "$3"
    exit 0
}

json_error() {
    printf '{"status":"error","message":"%s"}' "$(json_escape "$1")"
    exit 0
}

urldecode() {
    printf '%b' "$(echo "$1" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')"
}

if [ -z "$CONTENT_LENGTH" ] || [ "$CONTENT_LENGTH" = "0" ]; then
    json_error "No file data received"
fi

if [ "$CONTENT_LENGTH" -gt "$MAX_SIZE" ] 2>/dev/null; then
    json_error "File too large (max 50MB)"
fi

QS_FILENAME=""
QS_SUBFOLDER=""
OLDIFS="$IFS"
IFS='&'
for PARAM in $QUERY_STRING; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        filename) QS_FILENAME=$(urldecode "$PVAL") ;;
        subfolder) QS_SUBFOLDER=$(urldecode "$PVAL") ;;
    esac
done
IFS="$OLDIFS"

FILENAME="$QS_FILENAME"
if [ -z "$FILENAME" ]; then
    json_error "No filename provided"
fi

FILENAME=$(basename "$FILENAME" | tr -d '\r\n')
if [ -z "$FILENAME" ] || [ "$FILENAME" = "." ] || [ "$FILENAME" = ".." ]; then
    json_error "Invalid filename"
fi

EXT=$(echo "$FILENAME" | sed 's/.*\.//' | tr 'A-Z' 'a-z')
case "$EXT" in
    azw3|azw|mobi|kfx|epub|pdf) ;;
    *) json_error "Unsupported format: .$EXT" ;;
esac

SUBFOLDER=""
if [ -n "$QS_SUBFOLDER" ]; then
    SUBFOLDER=$(echo "$QS_SUBFOLDER" | sed 's|\\|/|g' | tr -d '\r\n')
    case "$SUBFOLDER" in
        *..*|/*) json_error "Invalid subfolder" ;;
    esac
fi

if [ -n "$SUBFOLDER" ]; then
    TARGET_DIR="$DOC_DIR/$SUBFOLDER"
    mkdir -p "$TARGET_DIR"
else
    TARGET_DIR="$DOC_DIR"
fi

TMPFILE="/tmp/book_upload_$$.tmp"
head -c "$CONTENT_LENGTH" | base64 -d > "$TMPFILE" 2>/dev/null

if [ ! -s "$TMPFILE" ]; then
    rm -f "$TMPFILE"
    json_error "Failed to decode file data"
fi

TARGET="$TARGET_DIR/$FILENAME"
if [ -f "$TARGET" ]; then
    BASE=$(echo "$FILENAME" | sed 's/\.[^.]*$//')
    NUM=1
    while [ -f "$TARGET_DIR/${BASE}_${NUM}.${EXT}" ]; do
        NUM=$((NUM + 1))
    done
    FILENAME="${BASE}_${NUM}.${EXT}"
    TARGET="$TARGET_DIR/$FILENAME"
fi

cp "$TMPFILE" "$TARGET"
rm -f "$TMPFILE"

if [ -f "$TARGET" ]; then
    FSIZE=$(wc -c < "$TARGET" | tr -d ' ')
    json_ok "$TARGET" "$FILENAME" "$FSIZE"
else
    json_error "Failed to save file"
fi
