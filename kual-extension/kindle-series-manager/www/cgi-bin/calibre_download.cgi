#!/bin/sh
echo "Content-Type: application/json"
echo ""

CONF="/mnt/us/extensions/kindle-series-manager/calibre.conf"
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

CALIBRE_URL=""
DL_PATH=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        calibre_url) CALIBRE_URL=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        download)    DL_PATH=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$CALIBRE_URL" ] && [ -f "$CONF" ]; then
    CALIBRE_URL=$(tr -d '\r\n' < "$CONF")
fi

if [ -z "$CALIBRE_URL" ]; then
    json_error "No Calibre URL configured"
fi
if [ -z "$DL_PATH" ]; then
    json_error "No download path provided"
fi

CALIBRE_URL=$(echo "$CALIBRE_URL" | sed 's|/$||')
FULL_URL="${CALIBRE_URL}${DL_PATH}"

FILENAME=$(basename "$DL_PATH" | sed 's/%20/ /g;s/%28/(/g;s/%29/)/g;s/%26/\&/g;s/%27/'"'"'/g;s/%2C/,/g')

EXT=$(echo "$FILENAME" | sed 's/.*\.//' | tr 'A-Z' 'a-z')
case "$EXT" in
    azw3|azw|mobi|kfx|epub|pdf) ;;
    *) json_error "Unsupported format: .$EXT" ;;
esac

TMPFILE=$(mktemp /tmp/calibre_dl_XXXXXX) || json_error "Failed to create temp file"
trap 'rm -f "$TMPFILE"' EXIT

wget -q -O "$TMPFILE" --timeout=30 "$FULL_URL" 2>/dev/null
if [ ! -s "$TMPFILE" ]; then
    json_error "Download failed from Calibre"
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
