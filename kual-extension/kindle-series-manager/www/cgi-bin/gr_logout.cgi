#!/bin/sh
echo "Content-Type: text/plain"
echo ""

GR_DIR="/mnt/us/extensions/kindle-series-manager/goodreads"

rm -f "$GR_DIR/gr_cookies.txt"
rm -f "$GR_DIR/gr_session.txt"

echo "Logged out."
