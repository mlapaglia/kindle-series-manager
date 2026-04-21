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

IP=$(ifconfig wlan0 2>/dev/null | grep 'inet addr' | sed 's/.*inet addr:\([0-9.]*\).*/\1/')

if [ -z "$IP" ]; then
    IP="(WiFi not connected)"
fi

cat > "$EXT_DIR/menu.json" << EOF
{
  "items": [
    {
      "name": "Kindle Series Manager",
      "priority": -99,
      "items": [
        {
          "name": "=> http://$IP:$PORT/",
          "action": ":",
          "priority": -1
        },
        {
          "name": "Stop Web UI",
          "priority": 1,
          "action": "bin/stopweb.sh",
          "refresh": true,
          "exitmenu": false
        },
        {
          "name": "Disable Goodreads Sync",
          "priority": 2,
          "action": "bin/gr_toggle.sh",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/mnt/us/ENABLE_GR_SYNC\" -f"
        },
        {
          "name": "Enable Goodreads Sync",
          "priority": 2,
          "action": "bin/gr_toggle.sh",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/mnt/us/ENABLE_GR_SYNC\" -f !"
        },
        {
          "name": "Backup Database",
          "priority": 3,
          "action": "bin/backup.sh",
          "exitmenu": true
        },
        {
          "name": "Restore Database",
          "priority": 4,
          "action": "bin/restore.sh",
          "exitmenu": true
        },
        {
          "name": "Disable FBInk Screensaver",
          "priority": 5,
          "action": "bin/fbink_ss_toggle.sh disable",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/tmp/fbink_ss_daemon.pid\" -f"
        },
        {
          "name": "Enable FBInk Screensaver",
          "priority": 5,
          "action": "bin/fbink_ss_toggle.sh enable",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/tmp/fbink_ss_daemon.pid\" -f !"
        },
        {
          "name": "Check for Updates",
          "priority": 10,
          "action": "bin/update_check.sh",
          "refresh": true,
          "exitmenu": false
        }
      ]
    }
  ]
}
EOF

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
