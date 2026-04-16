#!/bin/sh
#
# Start the series manager web server.
# Access from your phone/PC on the same WiFi network.
#

EXT_DIR="/mnt/base-us/extensions/kindle-series-manager"
WWW_DIR="$EXT_DIR/www"
HTTPD="$EXT_DIR/bin/busybox-httpd"
PORT=8080
PIDFILE="/tmp/kindle_series_manager_httpd.pid"

mntroot rw

chmod +x "$HTTPD"
chmod +x "$EXT_DIR/bin/"*.sh 2>/dev/null
chmod +x "$WWW_DIR/cgi-bin/"*.cgi 2>/dev/null

# Kill any previous instance
if [ -f "$PIDFILE" ]; then
    kill $(cat "$PIDFILE") 2>/dev/null
    sleep 1
fi

# Open firewall for the web server port
iptables -I INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null

# Start busybox httpd
"$HTTPD" httpd -p $PORT -h "$WWW_DIR" -c /dev/null
echo $! > "$PIDFILE"

# Get the Kindle's IP address
IP=$(ifconfig wlan0 2>/dev/null | grep 'inet addr' | sed 's/.*inet addr:\([0-9.]*\).*/\1/')

if [ -z "$IP" ]; then
    IP="(WiFi not connected)"
fi

eips -c
eips 3 5  "==================================="
eips 3 7  "  Kindle Series Manager"
eips 3 9  "==================================="
eips 3 12 "  Server running on port $PORT"
eips 3 14 "  Open in your phone/PC browser:"
eips 3 17 "  http://$IP:$PORT/"
eips 3 20 "  Tap 'Stop Server' in KUAL"
eips 3 21 "  when finished."
eips 3 23 "==================================="
