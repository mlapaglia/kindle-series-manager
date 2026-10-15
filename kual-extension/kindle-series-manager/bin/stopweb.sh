#!/bin/sh
#
# Stop the series manager web server and restore firewall.
#

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
PORT=8080
PIDFILE="/tmp/kindle_series_manager_httpd.pid"
HTTPD_BIN="busybox-httpd"

if [ -f "$PIDFILE" ]; then
    kill $(cat "$PIDFILE") 2>/dev/null
fi

killall "$HTTPD_BIN" 2>/dev/null

rm -f "$PIDFILE"

iptables -D INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null

. "$EXT_DIR/bin/refresh_menu.sh"
