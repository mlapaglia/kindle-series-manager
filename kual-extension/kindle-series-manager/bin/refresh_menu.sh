#!/bin/sh
#
# Rebuild menu.json based on current app state.
# Called by webapp.sh, stopweb.sh, update_check.sh, etc.
# Single source of truth for the KUAL menu structure.
#

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
MENU="$EXT_DIR/menu.json"
PIDFILE="/tmp/kindle_series_manager_httpd.pid"
PORT=8080
PRIORITY=0

# --- Detect state ---

WEB_RUNNING=false
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then
    WEB_RUNNING=true
fi

IP=""
if [ "$WEB_RUNNING" = "true" ]; then
    IP=$(ifconfig wlan0 2>/dev/null | grep 'inet addr' | sed 's/.*inet addr:\([0-9.]*\).*/\1/')
    [ -z "$IP" ] && IP="(WiFi not connected)"
fi

CURRENT=$(tr -d '\r\n' < "$EXT_DIR/VERSION" 2>/dev/null)
LATEST=""
if [ -f "$EXT_DIR/LATEST_VERSION" ]; then
    LATEST=$(tr -d '\r\n' < "$EXT_DIR/LATEST_VERSION" 2>/dev/null)
fi

# --- Build menu items ---

# Helper: append a comma before each item except the first
ITEMS=""
add_item() {
    if [ -n "$ITEMS" ]; then
        ITEMS="$ITEMS,"
    fi
    ITEMS="$ITEMS
        $1"
}

# Web UI
if [ "$WEB_RUNNING" = "true" ]; then
    PRIORITY=$((PRIORITY + 1))
    add_item "{
          \"name\": \"=> http://$IP:$PORT/\",
          \"action\": \":\",
          \"priority\": $PRIORITY
        }"
    PRIORITY=$((PRIORITY + 1))
    add_item "{
          \"name\": \"Stop Web UI\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/stopweb.sh\",
          \"refresh\": true,
          \"exitmenu\": false
        }"
else
    PRIORITY=$((PRIORITY + 1))
    add_item "{
          \"name\": \"Start Web UI\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/webapp.sh\",
          \"refresh\": true,
          \"exitmenu\": false
        }"
fi

# Goodreads Sync toggle
PRIORITY=$((PRIORITY + 1))
add_item "{
          \"name\": \"Disable Goodreads Sync\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/gr_toggle.sh\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/mnt/us/ENABLE_GR_SYNC\\\" -f\"
        }"
add_item "{
          \"name\": \"Enable Goodreads Sync\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/gr_toggle.sh\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/mnt/us/ENABLE_GR_SYNC\\\" -f !\"
        }"

# Hardcover Sync toggle
PRIORITY=$((PRIORITY + 1))
add_item "{
          \"name\": \"Disable Hardcover Sync\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/hc_toggle.sh\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/mnt/us/ENABLE_HC_SYNC\\\" -f\"
        }"
add_item "{
          \"name\": \"Enable Hardcover Sync\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/hc_toggle.sh\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/mnt/us/ENABLE_HC_SYNC\\\" -f !\"
        }"

# Stats Daemon toggle
PRIORITY=$((PRIORITY + 1))
add_item "{
          \"name\": \"Disable Reading Stats\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/stats_toggle.sh\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/mnt/us/ENABLE_KSM_STATS\\\" -f\"
        }"
add_item "{
          \"name\": \"Enable Reading Stats\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/stats_toggle.sh\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/mnt/us/ENABLE_KSM_STATS\\\" -f !\"
        }"

# Backup / Restore
PRIORITY=$((PRIORITY + 1))
add_item "{
          \"name\": \"Backup Database\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/backup.sh\",
          \"exitmenu\": true
        }"
PRIORITY=$((PRIORITY + 1))
add_item "{
          \"name\": \"Restore Database\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/restore.sh\",
          \"exitmenu\": true
        }"

# FBInk Screensaver toggle
PRIORITY=$((PRIORITY + 1))
add_item "{
          \"name\": \"Disable FBInk Screensaver\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/fbink_ss_toggle.sh disable\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/tmp/fbink_ss_daemon.pid\\\" -f\"
        }"
add_item "{
          \"name\": \"Enable FBInk Screensaver\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/fbink_ss_toggle.sh enable\",
          \"refresh\": true,
          \"exitmenu\": false,
          \"if\": \"\\\"/tmp/fbink_ss_daemon.pid\\\" -f !\"
        }"

# Updates
PRIORITY=99
if [ -n "$LATEST" ] && [ "$LATEST" != "$CURRENT" ]; then
    add_item "{
          \"name\": \"Update to $LATEST (current: $CURRENT)\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/update_apply.sh $LATEST\",
          \"refresh\": false,
          \"exitmenu\": true
        }"
elif [ -n "$LATEST" ] && [ "$LATEST" = "$CURRENT" ]; then
    add_item "{
          \"name\": \"Up to date ($CURRENT)\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/update_check.sh\",
          \"refresh\": true,
          \"exitmenu\": false
        }"
else
    add_item "{
          \"name\": \"Check for Updates\",
          \"priority\": $PRIORITY,
          \"action\": \"bin/update_check.sh\",
          \"refresh\": true,
          \"exitmenu\": false
        }"
fi

# --- Write menu.json ---

cat > "$MENU" << EOF
{
  "items": [
    {
      "name": "Kindle Series Manager",
      "priority": -99,
      "items": [$ITEMS
      ]
    }
  ]
}
EOF
