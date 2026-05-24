#!/bin/sh
echo "Content-Type: text/plain"
echo ""

DB="${DB:-/var/local/cc.db}"
LOG="/mnt/us/extensions/kindle-series-manager/series.log"

logit() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [collection_create] $1" >> "$LOG"
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

COLL_NAME=""
BOOKS_RAW=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        name)  COLL_NAME=$(urldecode "$PVAL") ;;
        books) BOOKS_RAW=$(urldecode "$PVAL") ;;
    esac
done
IFS="$OLDIFS"

logit "Parsed: name='$COLL_NAME' books='$BOOKS_RAW'"

if [ -z "$COLL_NAME" ]; then
    echo "Error: collection name is required"
    exit 0
fi

if [ -z "$BOOKS_RAW" ]; then
    echo "Error: select at least one book"
    exit 0
fi

# Generate collection key from name
COLL_KEY=$(echo "$COLL_NAME" | tr 'a-z ' 'A-Z-' | tr -d "'" | sed 's/^/CL-/')
COLL_URN="urn:collection:1:$COLL_KEY"
ESC_COLL_KEY=$(escape_sql "$COLL_KEY")
ESC_COLL_NAME=$(escape_sql "$COLL_NAME")

logit "Collection key: $COLL_KEY  urn: $COLL_URN"

mntroot rw
stop com.lab126.ccat 2>/dev/null
logit "Stopped ccat"

# Strip ICU collation for writes
sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries'; DROP INDEX IF EXISTS EntriesCredit0CollationIndex; DROP INDEX IF EXISTS EntriesTitles0Index; PRAGMA writable_schema=OFF;" 2>> "$LOG"

# Create collection container entry if not exists
EXISTING=$(sqlite3 "$DB" "SELECT p_cdeKey FROM Entries WHERE p_cdeKey='$ESC_COLL_KEY' AND p_type='Collection';")
if [ -z "$EXISTING" ]; then
    NEW_UUID=$(cat /proc/sys/kernel/random/uuid)
    sqlite3 "$DB" "INSERT INTO Entries (p_cdeKey, p_type, p_titles_0_nominal, p_collectionCount, p_uuid, p_isVisibleInHome, p_contentState) VALUES ('$ESC_COLL_KEY', 'Collection', '$ESC_COLL_NAME', 0, '$NEW_UUID', 1, 1);" 2>> "$LOG"
    logit "Created collection entry: $COLL_KEY"
else
    sqlite3 "$DB" "UPDATE Entries SET p_titles_0_nominal='$ESC_COLL_NAME' WHERE p_cdeKey='$ESC_COLL_KEY' AND p_type='Collection';" 2>> "$LOG"
    logit "Updated existing collection entry: $COLL_KEY"
fi

# Add books to collection
BOOK_COUNT=0
OLDIFS="$IFS"
IFS=','
for BOOK_KEY in $BOOKS_RAW; do
    ESC_BOOK_KEY=$(escape_sql "$BOOK_KEY")

    # Get current j_collections value
    CURRENT=$(sqlite3 "$DB" "SELECT j_collections FROM Entries WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';")

    if [ -z "$CURRENT" ] || [ "$CURRENT" = "null" ]; then
        # No collections yet - create new JSON
        sqlite3 "$DB" "UPDATE Entries SET j_collections='{\"items\":[\"$COLL_URN\"]}' WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';" 2>> "$LOG"
    else
        # Check if already in this collection
        case "$CURRENT" in
            *"$COLL_URN"*) logit "  Book $BOOK_KEY already in collection, skipping" ;;
            *)
                # Append to existing items array
                NEW_COLLS=$(echo "$CURRENT" | sed "s/\"]}/\",\"$COLL_URN\"\"]/;s/\"]\$/\"]}/")
                ESC_NEW_COLLS=$(escape_sql "$NEW_COLLS")
                sqlite3 "$DB" "UPDATE Entries SET j_collections='$ESC_NEW_COLLS' WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';" 2>> "$LOG"
                ;;
        esac
    fi

    # Update p_collectionCount for the book
    CCOUNT=$(sqlite3 "$DB" "SELECT j_collections FROM Entries WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';")
    if [ -n "$CCOUNT" ]; then
        NUM=$(echo "$CCOUNT" | grep -o 'urn:collection:1:' | wc -l)
        sqlite3 "$DB" "UPDATE Entries SET p_collectionCount=$NUM WHERE p_cdeKey='$ESC_BOOK_KEY' AND p_type='Entry:Item';" 2>> "$LOG"
    fi

    BOOK_COUNT=$((BOOK_COUNT + 1))
    logit "  Added book: $BOOK_KEY"
done
IFS="$OLDIFS"

# Update collection container's p_collectionCount with total books
TOTAL_BOOKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE p_type='Entry:Item' AND j_collections LIKE '%${ESC_COLL_KEY}%';")
sqlite3 "$DB" "UPDATE Entries SET p_collectionCount=$TOTAL_BOOKS WHERE p_cdeKey='$ESC_COLL_KEY' AND p_type='Collection';" 2>> "$LOG"

# Restore ICU collation
sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries'; PRAGMA writable_schema=OFF;" 2>> "$LOG"

start com.lab126.ccat 2>/dev/null
mntroot ro
logit "Done. Added $BOOK_COUNT books to collection '$COLL_NAME'"

echo "Created collection '$COLL_NAME' with $BOOK_COUNT books."
