#!/bin/sh

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
REPO="mlapaglia/kindle-series-manager"
API_URL="https://api.github.com/repos/$REPO/releases/latest"
LOG="$EXT_DIR/update.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [check] $1" >> "$LOG"
}

CURRENT=$(cat "$EXT_DIR/VERSION" 2>/dev/null | tr -d '\r\n')
if [ -z "$CURRENT" ]; then
    CURRENT="unknown"
fi
log "Current version: $CURRENT"

TMPFILE="/tmp/ksm_update_check.tmp"
log "Fetching $API_URL"
curl -fsSL --connect-timeout 10 -H "User-Agent: kindle-series-manager" -o "$TMPFILE" "$API_URL" 2>/dev/null

if [ ! -s "$TMPFILE" ]; then
    log "Fetch failed (empty response)"
    rm -f "$TMPFILE"
    sed -i 's/"name": "Check for Updates"/"name": "Update check failed (no WiFi?)"/' "$EXT_DIR/menu.json"
    exit 0
fi

LATEST=$(grep '"tag_name"' "$TMPFILE" | sed 's/.*"tag_name"[^"]*"\([^"]*\)".*/\1/')
rm -f "$TMPFILE"

if [ -z "$LATEST" ]; then
    log "Failed to parse tag_name from response"
    sed -i 's/"name": "Check for Updates"/"name": "Update check failed"/' "$EXT_DIR/menu.json"
    exit 0
fi

log "Latest version: $LATEST"

if [ "$CURRENT" = "$LATEST" ]; then
    log "Up to date"
    sed -i 's/"name": "Check for Updates"/"name": "Up to date ('"$CURRENT"')"/' "$EXT_DIR/menu.json"
    exit 0
fi

log "Update available: $CURRENT -> $LATEST, rewriting menu"

cat > "$EXT_DIR/menu.json" << EOF
{
  "items": [
    {
      "name": "Kindle Series Manager",
      "priority": -99,
      "items": [
        {
          "name": "Start Web UI",
          "priority": 0,
          "action": "bin/webapp.sh",
          "refresh": true,
          "exitmenu": false
        },
        {
          "name": "Disable Goodreads Sync",
          "priority": 1,
          "action": "bin/gr_toggle.sh",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/mnt/us/ENABLE_GR_SYNC\" -f"
        },
        {
          "name": "Enable Goodreads Sync",
          "priority": 1,
          "action": "bin/gr_toggle.sh",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/mnt/us/ENABLE_GR_SYNC\" -f !"
        },
        {
          "name": "Backup Database",
          "priority": 2,
          "action": "bin/backup.sh",
          "exitmenu": true
        },
        {
          "name": "Restore Database",
          "priority": 3,
          "action": "bin/restore.sh",
          "exitmenu": true
        },
        {
          "name": "Disable FBInk Screensaver",
          "priority": 4,
          "action": "bin/fbink_ss_toggle.sh disable",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/tmp/fbink_ss_daemon.pid\" -f"
        },
        {
          "name": "Enable FBInk Screensaver",
          "priority": 4,
          "action": "bin/fbink_ss_toggle.sh enable",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/tmp/fbink_ss_daemon.pid\" -f !"
        },
        {
          "name": "Update to $LATEST (current: $CURRENT)",
          "priority": 10,
          "action": "bin/update_apply.sh $LATEST",
          "refresh": false,
          "exitmenu": true
        }
      ]
    }
  ]
}
EOF
