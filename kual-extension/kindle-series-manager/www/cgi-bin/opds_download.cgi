#!/bin/sh
echo "Content-Type: application/json"
echo ""

DOC_DIR="/mnt/us/documents"

json_escape() {
    echo "$1" | sed 's/\\/\\\\/g;s/"/\\"/g'
}

json_ok() {
    printf '{"status":"ok","filename":"%s"}' "$(json_escape "$1")"
    exit 0
}

json_error() {
    printf '{"status":"error","message":"%s"}' "$(json_escape "$1")"
    exit 0
}

read -r POST_BODY

DL_URL=""
DL_FILENAME=""
AUTH=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        url)      DL_URL=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        filename) DL_FILENAME=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        auth)     AUTH=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$DL_URL" ]; then
    json_error "No download URL provided"
fi

case "$DL_URL" in
    http://*|https://*) ;;
    *) json_error "Invalid URL (must be http or https)" ;;
esac

if [ -z "$DL_FILENAME" ]; then
    DL_FILENAME=$(basename "$DL_URL" | sed 's/?.*//' | sed 's/%20/ /g;s/%28/(/g;s/%29/)/g;s/%26/\&/g;s/%27/'"'"'/g;s/%2C/,/g')
fi

FILENAME=$(basename "$(echo "$DL_FILENAME" | tr -d '\r\n')")

case "$FILENAME" in
    *..*|*/*|*\\*) json_error "Invalid filename" ;;
esac
FILENAME=$(echo "$FILENAME" | tr -d '\r\n')
if [ -z "$FILENAME" ] || [ "$FILENAME" = "." ] || [ "$FILENAME" = ".." ]; then
    json_error "Invalid filename"
fi

EXT=$(echo "$FILENAME" | sed 's/.*\.//' | tr 'A-Z' 'a-z')
case "$EXT" in
    azw3|azw|mobi|kfx|epub|pdf) ;;
    *) json_error "Unsupported format: .$EXT" ;;
esac

TMPFILE=$(mktemp /tmp/opds_dl_XXXXXX) || json_error "Failed to create temp file"
trap 'rm -f "$TMPFILE"' EXIT

if [ -n "$AUTH" ]; then
    DL_USER=$(echo "$AUTH" | cut -d: -f1)
    DL_PASS=$(echo "$AUTH" | cut -d: -f2-)
    wget -q -O "$TMPFILE" --timeout=30 --user="$DL_USER" --password="$DL_PASS" "$DL_URL" 2>/dev/null
else
    wget -q -O "$TMPFILE" --timeout=30 "$DL_URL" 2>/dev/null
fi
if [ ! -s "$TMPFILE" ]; then
    json_error "Download failed"
fi

TARGET="$DOC_DIR/$FILENAME"
if [ -f "$TARGET" ]; then
    BASE=$(echo "$FILENAME" | sed 's/\.[^.]*$//')
    NUM=1
    while [ -f "$DOC_DIR/${BASE}_${NUM}.${EXT}" ]; do
        NUM=$((NUM + 1))
    done
    FILENAME="${BASE}_${NUM}.${EXT}"
    TARGET="$DOC_DIR/$FILENAME"
fi

if ! cp "$TMPFILE" "$TARGET" 2>/dev/null; then
    json_error "Failed to save to documents"
fi

json_ok "$FILENAME"
