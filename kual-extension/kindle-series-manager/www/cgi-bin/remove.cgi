#!/bin/sh
echo "Content-Type: text/plain"
echo ""

DB="${DB:-/var/local/cc.db}"
LOG="/mnt/us/extensions/kindle-series-manager/series.log"

# Full URL decode: + -> space, then every %XX -> raw byte (UTF-8 safe), so
# series names in any language survive instead of staying as literal "%XX".
# awk rather than printf '%b' "\xHH": dash's printf has no \x escapes.
urldecode() {
    printf '%s' "$1" | LC_ALL=C awk '
        BEGIN { for (i = 0; i < 256; i++) hex[sprintf("%02x", i)] = i }
        {
            s = $0; gsub(/\+/, " ", s); out = ""
            while (match(s, /%[0-9A-Fa-f][0-9A-Fa-f]/)) {
                out = out substr(s, 1, RSTART - 1) sprintf("%c", hex[tolower(substr(s, RSTART + 1, 2))])
                s = substr(s, RSTART + 3)
            }
            printf "%s", out s
        }'
}

# The id embeds the (possibly non-ASCII) series name.
SERIES_ID=$(urldecode "$(echo "$QUERY_STRING" | sed 's/^id=//')")

if [ -z "$SERIES_ID" ]; then
    echo "Error: no series ID provided"
    exit 0
fi

escape_sql() {
    echo "$1" | sed "s/'/''/g"
}

S_CDE_KEY=$(echo "$SERIES_ID" | sed 's/^urn:collection:1:asin-//')
ESC_SERIES_ID=$(escape_sql "$SERIES_ID")
ESC_S_CDE_KEY=$(escape_sql "$S_CDE_KEY")

COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_seriesId='$ESC_SERIES_ID';")

if [ "$COUNT" -eq 0 ] 2>/dev/null; then
    ORPHAN=$(sqlite3 "$DB" "SELECT 1 FROM Entries WHERE p_cdeKey='$ESC_S_CDE_KEY' AND p_type='Entry:Item:Series' LIMIT 1;")
    if [ -z "$ORPHAN" ]; then
        echo "Error: series not found"
        exit 0
    fi

    mntroot rw
    stop com.lab126.ccat 2>/dev/null

    sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries'; DROP INDEX IF EXISTS EntriesCredit0CollationIndex; DROP INDEX IF EXISTS EntriesTitles0Index; PRAGMA writable_schema=OFF;"
    sqlite3 "$DB" "DELETE FROM Entries WHERE p_cdeKey='$ESC_S_CDE_KEY' AND p_type='Entry:Item:Series';"
    sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries'; PRAGMA writable_schema=OFF;"

    start com.lab126.ccat 2>/dev/null

    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleaned up orphaned series entry $SERIES_ID" >> "$LOG"
    echo "Cleaned up orphaned series entry."
    exit 0
fi

mntroot rw

stop com.lab126.ccat 2>/dev/null

MEMBER_KEYS=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$ESC_SERIES_ID';")
sqlite3 "$DB" "DELETE FROM Series WHERE d_seriesId='$ESC_SERIES_ID';"

for KEY in $MEMBER_KEYS; do
    REMAINING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_itemCdeKey='$KEY';")
    if [ "$REMAINING" -eq 0 ] 2>/dev/null; then
        sqlite3 "$DB" "UPDATE Entries SET p_seriesState=1 WHERE p_cdeKey='$KEY' AND p_type='Entry:Item';"
    fi
done

sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries'; DROP INDEX IF EXISTS EntriesCredit0CollationIndex; DROP INDEX IF EXISTS EntriesTitles0Index; PRAGMA writable_schema=OFF;"

sqlite3 "$DB" "DELETE FROM Entries WHERE p_cdeKey='$ESC_S_CDE_KEY' AND p_type='Entry:Item:Series';"

sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries'; PRAGMA writable_schema=OFF;"

start com.lab126.ccat 2>/dev/null

echo "$(date '+%Y-%m-%d %H:%M:%S') Removed series $SERIES_ID ($COUNT books)" >> "$LOG"
echo "Removed $COUNT books from series."
