#!/bin/sh

TAG="$1"
EXT_DIR="/mnt/us/extensions/kindle-series-manager"
LOG="$EXT_DIR/update.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [apply] $1" >> "$LOG"
}

if [ -z "$TAG" ]; then
    log "ERROR: no version specified"
    eips 0 0 "Error: no version specified"
    exit 1
fi

REPO="mlapaglia/kindle-series-manager"
ZIP_URL="https://github.com/$REPO/releases/download/$TAG/kindle-series-manager-${TAG}.zip"
TMPDIR="/tmp/ksm_update"

log "=== Starting update to $TAG ==="
log "Download URL: $ZIP_URL"

eips -c
eips 3 5 "Kindle Series Manager"
eips 3 7 "Updating to $TAG..."

if [ -f /tmp/fbink_ss_daemon.pid ]; then
    kill "$(cat /tmp/fbink_ss_daemon.pid)" 2>/dev/null
    rm -f /tmp/fbink_ss_daemon.pid /tmp/ss_shield.pid /tmp/fbink_ss_events.fifo /tmp/fbink_ss_last
    lipc-set-prop com.lab126.blanket load screensaver 2>/dev/null
    log "Stopped screensaver daemon"
    eips 3 9 "  Stopped screensaver daemon"
fi

if [ -f /tmp/kindle_series_manager_httpd.pid ]; then
    kill "$(cat /tmp/kindle_series_manager_httpd.pid)" 2>/dev/null
    rm -f /tmp/kindle_series_manager_httpd.pid
fi
killall busybox-httpd 2>/dev/null
iptables -D INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null
log "Stopped web server"
eips 3 10 "  Stopped web server"

stop gr-sync 2>/dev/null
log "Stopped Goodreads sync"

eips 3 12 "  Downloading $TAG..."

rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"

log "Downloading..."
curl -fSL --connect-timeout 30 -o "$TMPDIR/update.zip" "$ZIP_URL" 2>/dev/null

if [ ! -s "$TMPDIR/update.zip" ]; then
    log "ERROR: Download failed (empty file)"
    eips 3 14 "  Download failed!"
    eips 3 16 "Check WiFi and try again."
    rm -rf "$TMPDIR"
    exit 1
fi
log "Downloaded $(wc -c < "$TMPDIR/update.zip" | tr -d ' ') bytes"

eips 3 13 "  Extracting..."
log "Extracting..."

cd "$TMPDIR" || exit 1
unzip -qo update.zip 2>/dev/null

if [ ! -d "$TMPDIR/kual-extension/kindle-series-manager" ]; then
    log "ERROR: Invalid package (missing kual-extension/kindle-series-manager)"
    eips 3 14 "  Invalid package!"
    rm -rf "$TMPDIR"
    exit 1
fi

eips 3 14 "  Installing..."
log "Installing to $EXT_DIR"

cp -r "$TMPDIR/kual-extension/kindle-series-manager/"* "$EXT_DIR/"

chmod +x "$EXT_DIR/bin/"*.sh 2>/dev/null
chmod +x "$EXT_DIR/bin/busybox-httpd" 2>/dev/null
chmod +x "$EXT_DIR/bin/ss_shield" 2>/dev/null
chmod +x "$EXT_DIR/bin/fbink_hf" "$EXT_DIR/bin/fbink_sf" "$EXT_DIR/bin/fbink_k5" 2>/dev/null
chmod +x "$EXT_DIR/www/cgi-bin/"*.cgi 2>/dev/null

rm -rf "$TMPDIR"

NEW_VER=$(cat "$EXT_DIR/VERSION" 2>/dev/null | tr -d '\r\n')
log "Update complete. VERSION file: $NEW_VER"

eips -c
eips 3 5 "==================================="
eips 3 7 "  Update complete!"
eips 3 9 "  Version: $TAG"
eips 3 11 "  Reopen KUAL to use the"
eips 3 12 "  updated app."
eips 3 14 "==================================="
