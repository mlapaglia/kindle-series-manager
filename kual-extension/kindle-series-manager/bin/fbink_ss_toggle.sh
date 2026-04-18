#!/bin/sh

PIDFILE="/tmp/fbink_ss_daemon.pid"
EXT_DIR="/mnt/base-us/extensions/kindle-series-manager"
DAEMON="$EXT_DIR/bin/fbink_ss_daemon.sh"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    kill "$(cat "$PIDFILE")" 2>/dev/null
    rm -f "$PIDFILE"
else
    sh "$DAEMON" &
fi
