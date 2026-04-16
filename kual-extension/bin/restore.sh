#!/bin/sh
DB="/var/local/cc.db"
BAK="/var/local/cc.db.bak"

if [ ! -f "$BAK" ]; then
    eips -c
    eips 3 10 "  ERROR: No backup found at"
    eips 3 11 "  $BAK"
    exit 1
fi

stop com.lab126.ccat 2>/dev/null

cp "$BAK" "$DB"

start com.lab126.ccat 2>/dev/null

eips -c
eips 3 8  "==================================="
eips 3 10 "  Database restored from backup"
eips 3 12 "  $BAK"
eips 3 13 "  ->  $DB"
eips 3 15 "  ccat restarted"
eips 3 17 "==================================="
