#!/bin/sh
#
# Toggle KSM reading statistics daemon on/off by creating/removing the flag file.
# Also installs the upstart conf if not present.
#

FLAG_FILE="/mnt/us/ENABLE_KSM_STATS"
EXT_DIR="/mnt/us/extensions/kindle-series-manager"
UPSTART_SRC="$EXT_DIR/upstart/ksm-stats.conf"
UPSTART_DST="/etc/upstart/ksm-stats.conf"

mntroot rw

if [ -f "$FLAG_FILE" ]; then
    rm -f "$FLAG_FILE"
    stop ksm-stats 2>/dev/null
else
    touch "$FLAG_FILE"

    if [ -f "$UPSTART_SRC" ] && [ ! -f "$UPSTART_DST" ]; then
        cp "$UPSTART_SRC" "$UPSTART_DST"
    fi

    start ksm-stats 2>/dev/null
fi
