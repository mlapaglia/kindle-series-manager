#!/bin/sh
DB="/var/local/cc.db"
BAK="/var/local/cc.db.bak"

if [ ! -f "$DB" ]; then
    eips -c
    eips 3 10 "  ERROR: $DB not found"
    exit 1
fi

cp "$DB" "$BAK"

eips -c
eips 3 8  "==================================="
eips 3 10 "  Database backed up"
eips 3 12 "  $DB"
eips 3 13 "  ->  $BAK"
eips 3 15 "==================================="
