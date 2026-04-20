#!/bin/sh
#
# Stop the series manager web server and restore firewall.
#

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
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
          "name": "Disable Goodreads Sync",
          "priority": 1,
          "action": "bin/gr_toggle.sh",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/mnt/us/ENABLE_GR_SYNC\" -f"
        },
        {
          "name": "Enable Goodreads Sync",
          "priority": 1,
          "action": "bin/gr_toggle.sh",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/mnt/us/ENABLE_GR_SYNC\" -f !"
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
        },
        {
          "name": "Disable FBInk Screensaver",
          "priority": 4,
          "action": "bin/fbink_ss_toggle.sh disable",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/tmp/fbink_ss_daemon.pid\" -f"
        },
        {
          "name": "Enable FBInk Screensaver",
          "priority": 4,
          "action": "bin/fbink_ss_toggle.sh enable",
          "refresh": true,
          "exitmenu": false,
          "if": "\"/tmp/fbink_ss_daemon.pid\" -f !"
        }
      ]
    }
  ]
}
EOF
