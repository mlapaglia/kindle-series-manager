#!/bin/sh

DB="${DB:-/var/local/cc.db}"

KEY=$(echo "$QUERY_STRING" | sed 's/.*key=//;s/&.*//' | sed 's/[^a-zA-Z0-9._-]//g')

if [ -z "$KEY" ]; then
    echo "Content-Type: text/plain"
    echo ""
    echo "No key"
    exit 0
fi

FILE=$(sqlite3 "$DB" "SELECT p_thumbnail FROM Entries WHERE p_cdeKey='$KEY' AND p_type='Entry:Item' LIMIT 1;")

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "Content-Type: text/plain"
    echo "Status: 404"
    echo ""
    echo "Not found"
    exit 0
fi

FILE_SIZE=$(wc -c < "$FILE" | tr -d ' ')
echo "Content-Type: image/jpeg"
echo "Content-Length: $FILE_SIZE"
echo "Cache-Control: public, max-age=86400"
echo ""
cat "$FILE"
