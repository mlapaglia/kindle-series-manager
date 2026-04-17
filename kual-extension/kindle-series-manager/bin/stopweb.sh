#!/bin/sh
#
# Stop the series manager web server and restore firewall.
#

EXT_DIR="/mnt/base-us/extensions/kindle-series-manager"
PORT=8080
PIDFILE="/tmp/kindle_series_httpd.pid"
HTTPD_BIN="busybox-httpd"

if [ -f "$PIDFILE" ]; then
    kill $(cat "$PIDFILE") 2>/dev/null
fi

killall "$HTTPD_BIN" 2>/dev/null

rm -f "$PIDFILE"

iptables -D INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null

cat > "$EXT_DIR/menu.json" << 'EOF'
{
  "items": [
    {
      "name": "Kindle Series Manager",
      "priority": -99,
      "items": [
        {
          "name": "Start Web UI",
          "priority": 0,
          "action": "bin/webapp.sh",
          "refresh": true,
          "exitmenu": false
        },
        {
          "name": "Backup Database",
          "priority": 2,
          "action": "bin/backup.sh",
          "exitmenu": true
        },
        {
          "name": "Restore Database",
          "priority": 3,
          "action": "bin/restore.sh",
          "exitmenu": true
        }
      ]
    }
  ]
}
EOF
