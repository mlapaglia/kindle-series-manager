#!/bin/sh
#
# Stop the series manager web server and restore firewall.
#

PORT=8080
PIDFILE="/tmp/kindle_series_httpd.pid"
HTTPD_BIN="busybox-httpd"

if [ -f "$PIDFILE" ]; then
    kill $(cat "$PIDFILE") 2>/dev/null
fi

# Kill any remaining httpd processes from our binary
killall "$HTTPD_BIN" 2>/dev/null

rm -f "$PIDFILE"

# Remove the firewall rule we added
iptables -D INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null

eips -c
eips 3 10 "  Server stopped."
sleep 2
