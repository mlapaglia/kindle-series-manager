#!/bin/sh
echo "Content-Type: text/plain"
echo ""

DB="/var/local/cc.db"
LOG="/mnt/base-us/extensions/kindle-series-manager/series.log"

logit() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [create] $1" >> "$LOG"
}

escape_sql() {
    echo "$1" | sed "s/'/''/g"
}

# Read POST body
read -r POST_BODY
logit "POST body: $POST_BODY"

# Simple URL decode: handle the common escapes we'll see
urldecode() {
    echo "$1" | sed 's/+/ /g;s/%20/ /g;s/%3A/:/g;s/%2C/,/g;s/%2F/\//g;s/%27/'"'"'/g;s/%28/(/g;s/%29/)/g;s/%26/\&/g;s/%3D/=/g;s/%25/%/g'
}

# Parse: name=...&asin=...&books=key1:1,key2:2,...
SERIES_NAME=""
SERIES_ASIN=""
BOOKS_RAW=""
EDIT_ID=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        name)    SERIES_NAME=$(urldecode "$PVAL") ;;
        asin)    SERIES_ASIN=$(urldecode "$PVAL") ;;
        books)   BOOKS_RAW=$(urldecode "$PVAL") ;;
        edit_id) EDIT_ID=$(urldecode "$PVAL") ;;
    esac
done
IFS="$OLDIFS"

logit "Parsed: name='$SERIES_NAME' asin='$SERIES_ASIN' books='$BOOKS_RAW' edit_id='$EDIT_ID'"

if [ -z "$SERIES_NAME" ]; then
    echo "Error: series name is required"
    exit 0
fi

if [ -z "$BOOKS_RAW" ]; then
    echo "Error: select at least one book"
    exit 0
fi

# Generate series key
if [ -n "$SERIES_ASIN" ]; then
    S_KEY="$SERIES_ASIN"
else
    S_KEY=$(echo "$SERIES_NAME" | tr 'a-z ' 'A-Z-' | tr -d "'" | sed 's/^/SL-/')
fi
S_ID="urn:collection:1:asin-$S_KEY"
ESC_S_ID=$(escape_sql "$S_ID")

logit "Series key: $S_KEY  id: $S_ID"

mntroot rw
stop com.lab126.ccat 2>/dev/null
logit "Stopped ccat"

if [ -n "$EDIT_ID" ]; then
    ESC_EDIT_ID=$(escape_sql "$EDIT_ID")
    logit "Editing: removing old series $EDIT_ID"
    OLD_MEMBER_KEYS=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$ESC_EDIT_ID';")
    sqlite3 "$DB" "DELETE FROM Series WHERE d_seriesId='$ESC_EDIT_ID';"
    for KEY in $OLD_MEMBER_KEYS; do
        ESC_OLD_KEY=$(escape_sql "$KEY")
        REMAINING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_itemCdeKey='$ESC_OLD_KEY';")
        if [ "$REMAINING" -eq 0 ] 2>/dev/null; then
            sqlite3 "$DB" "UPDATE Entries SET p_seriesState=1 WHERE p_cdeKey='$ESC_OLD_KEY' AND p_type='Entry:Item';"
        fi
    done
fi

BOOK_COUNT=0

# Parse books: format is cdeKey:position,cdeKey:position,...
OLDIFS="$IFS"
IFS=','
for ENTRY in $BOOKS_RAW; do
    CDE_KEY=$(echo "$ENTRY" | cut -d':' -f1)
    POS=$(echo "$ENTRY" | cut -d':' -f2)
    ESC_KEY=$(escape_sql "$CDE_KEY")
    POS_0=$((POS - 1))

    logit "  Book: key=$CDE_KEY pos=$POS"

    sqlite3 "$DB" "INSERT OR REPLACE INTO Series (d_seriesId, d_itemCdeKey, d_itemPosition, d_itemPositionLabel, d_itemType, d_seriesOrderType) VALUES ('$ESC_S_ID', '$ESC_KEY', $POS_0.0, '$POS', 'Entry:Item', 'ordered');" 2>> "$LOG"

    sqlite3 "$DB" "UPDATE Entries SET p_seriesState=0 WHERE p_cdeKey='$ESC_KEY' AND p_type='Entry:Item';" 2>> "$LOG"

    BOOK_COUNT=$((BOOK_COUNT + 1))
done
IFS="$OLDIFS"

logit "Inserted $BOOK_COUNT books into Series table"

# Create Entry:Item:Series container
ESC_NAME=$(escape_sql "$SERIES_NAME")
TITLES_JSON="[{\"display\":\"$ESC_NAME\",\"collation\":\"$ESC_NAME\",\"language\":\"en\",\"pronunciation\":\"$ESC_NAME\"}]"
ESC_TITLES_JSON=$(echo "$TITLES_JSON" | sed "s/'/''/g")

FIRST_BOOK_KEY=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$ESC_S_ID' ORDER BY d_itemPosition LIMIT 1;")
CREDITS=$(sqlite3 "$DB" "SELECT j_credits FROM Entries WHERE p_cdeKey='$FIRST_BOOK_KEY' AND p_type='Entry:Item' LIMIT 1;" | sed "s/'/''/g")
CREDIT_COLL=$(sqlite3 "$DB" "SELECT p_credits_0_name_collation FROM Entries WHERE p_cdeKey='$FIRST_BOOK_KEY' AND p_type='Entry:Item' LIMIT 1;" | sed "s/'/''/g")
CREDIT_PRON=$(sqlite3 "$DB" "SELECT p_credits_0_name_pronunciation FROM Entries WHERE p_cdeKey='$FIRST_BOOK_KEY' AND p_type='Entry:Item' LIMIT 1;" | sed "s/'/''/g")
THUMBNAIL=$(sqlite3 "$DB" "SELECT p_thumbnail FROM Entries WHERE p_cdeKey='$FIRST_BOOK_KEY' AND p_type='Entry:Item' LIMIT 1;" | sed "s/'/''/g")

CREDIT_COUNT=0
if [ -n "$CREDITS" ]; then
    CREDIT_COUNT=1
fi

ESC_S_KEY=$(escape_sql "$S_KEY")

logit "Stripping ICU for INSERT..."

# Strip ICU, insert, restore
sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries'; DROP INDEX IF EXISTS EntriesCredit0CollationIndex; DROP INDEX IF EXISTS EntriesTitles0Index; PRAGMA writable_schema=OFF;" 2>> "$LOG"

if [ -n "$EDIT_ID" ]; then
    OLD_S_KEY=$(echo "$EDIT_ID" | sed 's/urn:collection:1:asin-//')
    if [ "$OLD_S_KEY" != "$S_KEY" ]; then
        ESC_OLD_S_KEY=$(escape_sql "$OLD_S_KEY")
        logit "Series key changed from $OLD_S_KEY to $S_KEY, removing old Entry"
        sqlite3 "$DB" "DELETE FROM Entries WHERE p_cdeKey='$ESC_OLD_S_KEY' AND p_type='Entry:Item:Series';" 2>> "$LOG"
    fi
fi

EXISTING=$(sqlite3 "$DB" "SELECT p_uuid FROM Entries WHERE p_cdeKey='$ESC_S_KEY' AND p_type='Entry:Item:Series';")
SQL_FILE="/tmp/kindle_series_create_$$.sql"
VC_COUNT=$((BOOK_COUNT + 1))

if [ -n "$EXISTING" ]; then
    cat > "$SQL_FILE" << ENDSQL
UPDATE Entries SET
    p_titles_0_nominal='$ESC_NAME',
    j_titles='$ESC_TITLES_JSON',
    j_credits='$CREDITS',
    p_credits_0_name_pronunciation='$CREDIT_PRON',
    p_creditCount=$CREDIT_COUNT,
    p_memberCount=$BOOK_COUNT,
    p_homeMemberCount=$BOOK_COUNT,
    p_thumbnail='$THUMBNAIL'
    WHERE p_cdeKey='$ESC_S_KEY' AND p_type='Entry:Item:Series';
ENDSQL
else
    NEW_UUID=$(cat /proc/sys/kernel/random/uuid)
    cat > "$SQL_FILE" << ENDSQL
INSERT INTO Entries (
    p_uuid, p_type, p_cdeKey, p_cdeType, p_cdeGroup,
    p_titles_0_nominal, p_titles_0_collation, p_titles_0_pronunciation,
    j_titles, p_titleCount,
    p_credits_0_name_collation, p_credits_0_name_pronunciation,
    j_credits, p_creditCount,
    j_members, p_memberCount, p_homeMemberCount,
    p_mimeType, p_thumbnail,
    j_displayObjects,
    p_isArchived, p_isVisibleInHome, p_isLatestItem,
    p_isUpdateAvailable, p_isTestData,
    p_seriesState, p_visibilityState, p_isProcessed,
    p_contentState, p_ownershipType, p_originType,
    p_contentIndexedState, p_noteIndexedState,
    p_collectionSyncCounter, p_collectionDataSetName,
    p_subType, j_languages, p_languageCount,
    p_virtualCollectionCount
) VALUES (
    '$NEW_UUID', 'Entry:Item:Series', '$ESC_S_KEY', 'series', '$ESC_S_ID',
    '$ESC_NAME', '$ESC_NAME', '$ESC_NAME',
    '$ESC_TITLES_JSON', 1,
    '$CREDIT_COLL', '$CREDIT_PRON',
    '$CREDITS', $CREDIT_COUNT,
    '[]', $BOOK_COUNT, $BOOK_COUNT,
    'application/x-kindle-series', '$THUMBNAIL',
    '[{"ref":"titles"},{"ref":"credits"}]',
    1, 1, 1,
    0, 0,
    1, 1, 1,
    0, 0, -1,
    2147483647, 0,
    0, '0',
    0, '[]', 0,
    $VC_COUNT
);
ENDSQL
fi

logit "Running SQL file..."
sqlite3 "$DB" < "$SQL_FILE" 2>> "$LOG"
logit "SQL done"

# Restore ICU
sqlite3 "$DB" "PRAGMA writable_schema=ON; UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries'; PRAGMA writable_schema=OFF;" 2>> "$LOG"

rm -f "$SQL_FILE"

start com.lab126.ccat 2>/dev/null
logit "Started ccat. Done."

BOOK_COUNT_FINAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_seriesId='$ESC_S_ID';")
if [ -n "$EDIT_ID" ]; then
    echo "Updated '$SERIES_NAME' with $BOOK_COUNT_FINAL books."
else
    echo "Created '$SERIES_NAME' with $BOOK_COUNT_FINAL books."
fi
