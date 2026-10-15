#!/bin/sh

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
REPO="mlapaglia/kindle-series-manager"
API_URL="https://api.github.com/repos/$REPO/releases/latest"
LOG="$EXT_DIR/update.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [check] $1" >> "$LOG"
}

CURRENT=$(tr -d '\r\n' < "$EXT_DIR/VERSION" 2>/dev/null)
if [ -z "$CURRENT" ]; then
    CURRENT="unknown"
fi
log "Current version: $CURRENT"

TMPFILE="/tmp/ksm_update_check.tmp"
log "Fetching $API_URL"
curl -fsSL --connect-timeout 10 -H "User-Agent: kindle-series-manager" -o "$TMPFILE" "$API_URL" 2>/dev/null

if [ ! -s "$TMPFILE" ]; then
    log "Fetch failed (empty response)"
    rm -f "$TMPFILE" "$EXT_DIR/LATEST_VERSION"
    . "$EXT_DIR/bin/refresh_menu.sh"
    exit 0
fi

LATEST=$(grep '"tag_name"' "$TMPFILE" | sed 's/.*"tag_name"[^"]*"\([^"]*\)".*/\1/')
rm -f "$TMPFILE"

if [ -z "$LATEST" ]; then
    log "Failed to parse tag_name from response"
    rm -f "$EXT_DIR/LATEST_VERSION"
    . "$EXT_DIR/bin/refresh_menu.sh"
    exit 0
fi

log "Latest version: $LATEST"

echo "$LATEST" > "$EXT_DIR/LATEST_VERSION"

if [ "$CURRENT" = "$LATEST" ]; then
    log "Up to date"
else
    log "Update available: $CURRENT -> $LATEST"
fi

. "$EXT_DIR/bin/refresh_menu.sh"
