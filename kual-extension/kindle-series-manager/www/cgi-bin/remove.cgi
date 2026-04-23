#!/bin/sh
echo "Content-Type: text/plain"
echo ""

DB="${DB:-/var/local/cc.db}"
LOG="/mnt/us/extensions/kindle-series-manager/series.log"

SERIES_ID=$(echo "$QUERY_STRING" | sed 's/id=//;s/%3A/:/g;s/%2F/\//g;s/+/ /g')

if [ -z "$SERIES_ID" ]; then
    echo "Error: no series ID provided"
    exit 0
fi

S_CDE_KEY=$(echo "$SERIES_ID" | sed 's/urn:collection:1:asin-//')
COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_seriesId='$SERIES_ID';")

if [ "$COUNT" -eq 0 ] 2>/dev/null; then
    ORPHAN=$(sqlite3 "$DB" "SELECT p_uuid FROM Entries WHERE p_cdeKey='$S_CDE_KEY' AND p_type='Entry:Item:Series';")
    if [ -z "$ORPHAN" ]; then
        echo "Error: series not found"
        exit 0
    fi

    mntroot rw
    stop com.lab126.ccat 2>/dev/null

    sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries'; DROP INDEX IF EXISTS EntriesCredit0CollationIndex; DROP INDEX IF EXISTS EntriesTitles0Index; PRAGMA writable_schema=OFF;"
    sqlite3 "$DB" "DELETE FROM Entries WHERE p_cdeKey='$S_CDE_KEY' AND p_type='Entry:Item:Series';"
    sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries'; PRAGMA writable_schema=OFF;"

    start com.lab126.ccat 2>/dev/null

    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleaned up orphaned series entry $SERIES_ID" >> "$LOG"
    echo "Cleaned up orphaned series entry."
    exit 0
fi

mntroot rw

stop com.lab126.ccat 2>/dev/null

MEMBER_KEYS=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$SERIES_ID';")
sqlite3 "$DB" "DELETE FROM Series WHERE d_seriesId='$SERIES_ID';"

for KEY in $MEMBER_KEYS; do
    REMAINING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_itemCdeKey='$KEY';")
    if [ "$REMAINING" -eq 0 ] 2>/dev/null; then
        sqlite3 "$DB" "UPDATE Entries SET p_seriesState=1 WHERE p_cdeKey='$KEY' AND p_type='Entry:Item';"
    fi
done

sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries'; DROP INDEX IF EXISTS EntriesCredit0CollationIndex; DROP INDEX IF EXISTS EntriesTitles0Index; PRAGMA writable_schema=OFF;"

sqlite3 "$DB" "DELETE FROM Entries WHERE p_cdeKey='$S_CDE_KEY' AND p_type='Entry:Item:Series';"

sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries'; PRAGMA writable_schema=OFF;"

start com.lab126.ccat 2>/dev/null

echo "$(date '+%Y-%m-%d %H:%M:%S') Removed series $SERIES_ID ($COUNT books)" >> "$LOG"
echo "Removed $COUNT books from series."
