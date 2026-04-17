#!/bin/sh
#
# Toggle Goodreads sync on/off by creating/removing the flag file.
# Also installs the upstart conf if not present.
#

FLAG_FILE="/mnt/us/ENABLE_GR_SYNC"
EXT_DIR="/mnt/base-us/extensions/kindle-series-manager"
UPSTART_SRC="$EXT_DIR/upstart/gr-sync.conf"
UPSTART_DST="/etc/upstart/gr-sync.conf"

mntroot rw

if [ -f "$FLAG_FILE" ]; then
    rm -f "$FLAG_FILE"
    stop gr-sync 2>/dev/null
else
    touch "$FLAG_FILE"

    if [ -f "$UPSTART_SRC" ] && [ ! -f "$UPSTART_DST" ]; then
        cp "$UPSTART_SRC" "$UPSTART_DST"
    fi

    start gr-sync 2>/dev/null
fi
