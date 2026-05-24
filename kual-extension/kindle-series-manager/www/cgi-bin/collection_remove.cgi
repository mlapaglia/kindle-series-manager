#!/bin/sh
echo "Content-Type: text/plain"
echo ""

DB="${DB:-/var/local/cc.db}"
LOG="/mnt/us/extensions/kindle-series-manager/series.log"

logit() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [collection_remove] $1" >> "$LOG"
}

escape_sql() {
    echo "$1" | sed "s/'/''/g"
}

urldecode() {
    echo "$1" | sed 's/+/ /g;s/%20/ /g;s/%3A/:/g;s/%2C/,/g;s/%2F/\//g;s/%27/'"'"'/g;s/%28/(/g;s/%29/)/g;s/%26/\&/g;s/%3D/=/g;s/%25/%/g'
}

# Read POST body
read -r POST_BODY
logit "POST body: $POST_BODY"

COLL_ID=""
BOOK_KEY=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        id)   COLL_ID=$(urldecode "$PVAL") ;;
        book) BOOK_KEY=$(urldecode "$PVAL") ;;
    esac
done
IFS="$OLDIFS"

logit "Parsed: id='$COLL_ID' book='$BOOK_KEY'"

if [ -z "$COLL_ID" ]; then
    echo "Error: collection ID is required"
    exit 0
fi

# Extract collection key from URN
COLL_KEY=$(echo "$COLL_ID" | sed 's/^urn:collection:1://')
ESC_COLL_KEY=$(escape_sql "$COLL_KEY")

mntroot rw
stop com.lab126.ccat 2>/dev/null
logit "Stopped ccat"

# Strip ICU collation for writes
sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries'; DROP INDEX IF EXISTS EntriesCredit0CollationIndex; DROP INDEX IF EXISTS EntriesTitles0Index; PRAGMA writable_schema=OFF;" 2>> "$LOG"

if [ -n "$BOOK_KEY" ]; then
    # Remove single book from collection
    ESC_BOOK_KEY=$(escape_sql "$BOOK_KEY")
    CURRENT=$(sqlite3 "$DB" "SELECT j_collections FROM Entries WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';")

    if [ -n "$CURRENT" ]; then
        # Remove this collection URN from the JSON
        # Handle: only item, first item, middle item, last item
        NEW_COLLS=$(echo "$CURRENT" | sed "s/,\"$COLL_ID\"//;s/\"$COLL_ID\",//;s/\"$COLL_ID\"//")
        ESC_NEW_COLLS=$(escape_sql "$NEW_COLLS")

        # Check if items array is now empty
        case "$NEW_COLLS" in
            *'"items":[]'*)
                sqlite3 "$DB" "UPDATE Entries SET j_collections=NULL, p_collectionCount=0 WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';" 2>> "$LOG"
                ;;
            *)
                NUM=$(echo "$NEW_COLLS" | grep -o 'urn:collection:1:' | wc -l)
                sqlite3 "$DB" "UPDATE Entries SET j_collections='$ESC_NEW_COLLS', p_collectionCount=$NUM WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';" 2>> "$LOG"
                ;;
        esac
    fi

    # Update collection count
    TOTAL_BOOKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE p_type='Entry:Item' AND j_collections LIKE '%${ESC_COLL_KEY}%';")
    sqlite3 "$DB" "UPDATE Entries SET p_collectionCount=$TOTAL_BOOKS WHERE p_cdeKey='$ESC_COLL_KEY' AND p_type='Collection';" 2>> "$LOG"

    logit "Removed book $BOOK_KEY from collection $COLL_ID"
    MSG="Removed book from collection."
else
    # Delete entire collection
    # Remove collection URN from all books
    TMP=$(mktemp /tmp/ksm_collrm_XXXXXX) || exit 1
    trap 'rm -f "$TMP"' EXIT

    sqlite3 -separator '	' "$DB" "SELECT p_cdeKey, j_collections FROM Entries WHERE p_type='Entry:Item' AND j_collections LIKE '%${ESC_COLL_KEY}%';" > "$TMP"

    while IFS='	' read -r BKEY BCOLL; do
        ESC_BKEY=$(escape_sql "$BKEY")
        NEW_COLLS=$(echo "$BCOLL" | sed "s/,\"$COLL_ID\"//;s/\"$COLL_ID\",//;s/\"$COLL_ID\"//")
        ESC_NEW_COLLS=$(escape_sql "$NEW_COLLS")

        case "$NEW_COLLS" in
            *'"items":[]'*)
                sqlite3 "$DB" "UPDATE Entries SET j_collections=NULL, p_collectionCount=0 WHERE p_cdeKey='$ESC_BKEY' AND p_type='Entry:Item';" 2>> "$LOG"
                ;;
            *)
                NUM=$(echo "$NEW_COLLS" | grep -o 'urn:collection:1:' | wc -l)
                sqlite3 "$DB" "UPDATE Entries SET j_collections='$ESC_NEW_COLLS', p_collectionCount=$NUM WHERE p_cdeKey='$ESC_BKEY' AND p_type='Entry:Item';" 2>> "$LOG"
                ;;
        esac
    done < "$TMP"

    # Delete the collection container entry
    sqlite3 "$DB" "DELETE FROM Entries WHERE p_cdeKey='$ESC_COLL_KEY' AND p_type='Collection';" 2>> "$LOG"

    logit "Deleted entire collection $COLL_ID"
    MSG="Collection deleted."
fi

# Restore ICU collation
sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries'; PRAGMA writable_schema=OFF;" 2>> "$LOG"

start com.lab126.ccat 2>/dev/null
mntroot ro

echo "$MSG"
