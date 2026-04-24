#!/bin/sh
#
# Toggle Hardcover sync on/off by creating/removing the flag file.
# Also installs the upstart conf if not present.
#

FLAG_FILE="/mnt/us/ENABLE_HC_SYNC"
EXT_DIR="/mnt/us/extensions/kindle-series-manager"
UPSTART_SRC="$EXT_DIR/upstart/hc-sync.conf"
UPSTART_DST="/etc/upstart/hc-sync.conf"

mntroot rw

if [ -f "$FLAG_FILE" ]; then
    rm -f "$FLAG_FILE"
    stop hc-sync 2>/dev/null
else
    touch "$FLAG_FILE"

    if [ -f "$UPSTART_SRC" ] && [ ! -f "$UPSTART_DST" ]; then
        cp "$UPSTART_SRC" "$UPSTART_DST"
    fi

    start hc-sync 2>/dev/null
fi
