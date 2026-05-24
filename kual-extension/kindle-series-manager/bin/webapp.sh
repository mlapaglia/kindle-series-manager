#!/bin/sh
#
# Start the series manager web server.
# Access from your phone/PC on the same WiFi network.
#

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
WWW_DIR="$EXT_DIR/www"
HTTPD="$EXT_DIR/bin/busybox-httpd"
PORT=8080
PIDFILE="/tmp/kindle_series_manager_httpd.pid"

mntroot rw

chmod +x "$HTTPD"
chmod +x "$EXT_DIR/bin/"*.sh 2>/dev/null
chmod +x "$WWW_DIR/cgi-bin/"*.cgi 2>/dev/null

if [ -f "$PIDFILE" ]; then
    kill $(cat "$PIDFILE") 2>/dev/null
    sleep 1
fi

iptables -I INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null

"$HTTPD" httpd -p $PORT -h "$WWW_DIR" -c /dev/null
echo $! > "$PIDFILE"

. "$EXT_DIR/bin/refresh_menu.sh"
