#!/bin/sh

PIDFILE="/tmp/fbink_ss_daemon.pid"
EXT_DIR="/mnt/us/extensions/kindle-series-manager"
DAEMON="$EXT_DIR/bin/fbink_ss_daemon.sh"
ACTION="$1"

stop_daemon() {
    if [ -f "$PIDFILE" ]; then
        kill "$(cat "$PIDFILE")" 2>/dev/null
        rm -f "$PIDFILE"
    fi
}

case "$ACTION" in
    enable)
        stop_daemon
        sh "$DAEMON" &
        ;;
    disable)
        stop_daemon
        ;;
esac
