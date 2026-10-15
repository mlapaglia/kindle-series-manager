#!/bin/sh
echo "Content-Type: text/plain"
echo ""

FW_VERSION=$(cat /etc/version.txt 2>/dev/null || echo "0.0.0")
FW_MAJOR=$(echo "$FW_VERSION" | cut -d'.' -f1)
FW_MINOR=$(echo "$FW_VERSION" | cut -d'.' -f2)
FW_PATCH=$(echo "$FW_VERSION" | cut -d'.' -f3)

if [ "$FW_MAJOR" -lt 5 ] 2>/dev/null || \
   { [ "$FW_MAJOR" -eq 5 ] && [ "$FW_MINOR" -lt 13 ]; } 2>/dev/null || \
   { [ "$FW_MAJOR" -eq 5 ] && [ "$FW_MINOR" -eq 13 ] && [ "${FW_PATCH:-0}" -lt 4 ]; } 2>/dev/null; then
    echo "Error: Series grouping requires firmware 5.13.4 or later (current: $FW_VERSION)"
    exit 0
fi

DB="${DB:-/var/local/cc.db}"
LOG="/mnt/us/extensions/kindle-series-manager/series.log"

logit() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [create] $1" >> "$LOG"
}

# --- FW 5.19+ audit triggers -------------------------------------------------
# cc.db carries AuditLog/CompanionRelation triggers on Entries, Series and
# Collections that call SQL functions only the framework's own sqlite
# connection registers (get_entry_external_id(), get_series_relation_external_id(),
# ...). Any write that would fire them fails in the sqlite3 CLI at prepare time
# ("no such function"). run_write_tx parks exactly those triggers (nothing else),
# runs the writes and recreates the triggers in ONE transaction: if any step
# fails, sqlite rolls all of it back and the triggers are left untouched.
FW_TRIGGERS="type='trigger' AND tbl_name IN ('Entries','Series','Collections') AND instr(sql, '_external_id(') > 0"
TRIG_BACKUP="/mnt/us/extensions/kindle-series-manager/triggers_backup.sql"
[ -d "${TRIG_BACKUP%/*}" ] || TRIG_BACKUP="/tmp/ksm_triggers_backup.sql"

fw_trigger_count() {
    sqlite3 "$DB" "SELECT COUNT(*) FROM sqlite_master WHERE $FW_TRIGGERS;"
}

# run_write_tx FILE: run the SQL statements in FILE. Call with ccat stopped.
# Sets TX_RC (sqlite3's exit status; non-zero = rolled back, nothing changed).
run_write_tx() {
    TX_SQL="/tmp/ksm_tx_$$.sql"
    TRIG_WANT=$(fw_trigger_count)
    sqlite3 "$DB" "SELECT replace(sql, 'CREATE TRIGGER ', 'CREATE TRIGGER IF NOT EXISTS ')||';' FROM sqlite_master WHERE $FW_TRIGGERS;" > "$TRIG_BACKUP"
    {
        echo ".bail on"
        echo "BEGIN IMMEDIATE;"
        sqlite3 "$DB" "SELECT 'DROP TRIGGER \"'||replace(name, '\"', '\"\"')||'\";' FROM sqlite_master WHERE $FW_TRIGGERS;"
        cat "$1"
        cat "$TRIG_BACKUP"
        echo "COMMIT;"
    } > "$TX_SQL"
    sqlite3 "$DB" < "$TX_SQL" 2>> "$LOG"
    TX_RC=$?
    rm -f "$TX_SQL"
    [ "$TX_RC" -eq 0 ] || logit "ERROR: write transaction failed (rc=$TX_RC), rolled back"
    check_triggers
}

# check_triggers: every parked trigger must be back. If not, recreate them
# from the backup; if that fails too, keep the backup file and say so.
check_triggers() {
    if [ "$(fw_trigger_count)" = "$TRIG_WANT" ]; then
        rm -f "$TRIG_BACKUP"
        return 0
    fi
    logit "ERROR: audit triggers missing after write; restoring from $TRIG_BACKUP"
    sqlite3 "$DB" < "$TRIG_BACKUP" 2>> "$LOG"
    if [ "$(fw_trigger_count)" = "$TRIG_WANT" ]; then
        logit "audit triggers restored from backup"
        rm -f "$TRIG_BACKUP"
        return 0
    fi
    logit "ERROR: could not restore audit triggers; backup kept at $TRIG_BACKUP"
    echo "Error: could not restore the library database's audit triggers; backup kept at $TRIG_BACKUP"
    return 1
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
BADGE_MODE="none"

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        name)    SERIES_NAME=$(urldecode "$PVAL") ;;
        asin)    SERIES_ASIN=$(urldecode "$PVAL") ;;
        books)   BOOKS_RAW=$(urldecode "$PVAL") ;;
        edit_id)    EDIT_ID=$(urldecode "$PVAL") ;;
        badge_mode) BADGE_MODE=$(urldecode "$PVAL") ;;
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

# All writes are collected here and run in one transaction (run_write_tx).
WRITES="/tmp/kindle_series_writes_$$.sql"
: > "$WRITES"

if [ -n "$EDIT_ID" ]; then
    ESC_EDIT_ID=$(escape_sql "$EDIT_ID")
    logit "Editing: removing old series $EDIT_ID"
    OLD_MEMBER_KEYS=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$ESC_EDIT_ID';")
    printf '%s\n' "DELETE FROM Series WHERE d_seriesId='$ESC_EDIT_ID';" >> "$WRITES"
    for KEY in $OLD_MEMBER_KEYS; do
        ESC_OLD_KEY=$(escape_sql "$KEY")
        REMAINING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_itemCdeKey='$ESC_OLD_KEY' AND d_seriesId<>'$ESC_EDIT_ID';")
        if [ "$REMAINING" -eq 0 ] 2>/dev/null; then
            printf '%s\n' "UPDATE Entries SET p_seriesState=1 WHERE p_cdeKey='$ESC_OLD_KEY' AND p_type='Entry:Item';" >> "$WRITES"
        fi
    done
fi

BOOK_COUNT=0
FIRST_BOOK_KEY=""
FIRST_POS=""

# Parse books: format is cdeKey:position,cdeKey:position,...
OLDIFS="$IFS"
IFS=','
for ENTRY in $BOOKS_RAW; do
    CDE_KEY=$(echo "$ENTRY" | cut -d':' -f1)
    POS=$(echo "$ENTRY" | cut -d':' -f2)
    ESC_KEY=$(escape_sql "$CDE_KEY")
    POS_0=$((POS - 1))

    logit "  Book: key=$CDE_KEY pos=$POS"

    printf '%s\n' "INSERT OR REPLACE INTO Series (d_seriesId, d_itemCdeKey, d_itemPosition, d_itemPositionLabel, d_itemType, d_seriesOrderType) VALUES ('$ESC_S_ID', '$ESC_KEY', $POS_0.0, '$POS', 'Entry:Item', 'ordered');" >> "$WRITES"
    if [ -z "$FIRST_POS" ] || [ "$POS" -lt "$FIRST_POS" ] 2>/dev/null; then
        FIRST_POS="$POS"
        FIRST_BOOK_KEY="$ESC_KEY"
    fi

    case "$BADGE_MODE" in
        ku)   ORIGIN_VAL=21; CONTENT_VAL=1 ;;
        kupr) ORIGIN_VAL="NULL"; CONTENT_VAL=0 ;;
        *)    ORIGIN_VAL=0; CONTENT_VAL=1 ;;
    esac
    printf '%s\n' "UPDATE Entries SET p_seriesState=0, p_originType=$ORIGIN_VAL, p_contentState=$CONTENT_VAL WHERE p_cdeKey='$ESC_KEY' AND p_type='Entry:Item';" >> "$WRITES"

    BOOK_COUNT=$((BOOK_COUNT + 1))
done
IFS="$OLDIFS"

logit "Queued $BOOK_COUNT books for the Series table"

# Create Entry:Item:Series container
ESC_NAME=$(escape_sql "$SERIES_NAME")
TITLES_JSON="[{\"display\":\"$ESC_NAME\",\"collation\":\"$ESC_NAME\",\"language\":\"en\",\"pronunciation\":\"$ESC_NAME\"}]"
ESC_TITLES_JSON=$(echo "$TITLES_JSON" | sed "s/'/''/g")

# FIRST_BOOK_KEY comes from the request (the Series rows are not written yet)
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
sqlite3 "$DB" 2>> "$LOG" <<'SQLICUOFF'
.dbconfig defensive off
PRAGMA writable_schema=ON;
UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries';
DROP INDEX IF EXISTS EntriesCredit0CollationIndex;
DROP INDEX IF EXISTS EntriesTitles0Index;
PRAGMA writable_schema=OFF;
SQLICUOFF

if [ -n "$EDIT_ID" ]; then
    OLD_S_KEY=$(echo "$EDIT_ID" | sed 's/urn:collection:1:asin-//')
    if [ "$OLD_S_KEY" != "$S_KEY" ]; then
        ESC_OLD_S_KEY=$(escape_sql "$OLD_S_KEY")
        logit "Series key changed from $OLD_S_KEY to $S_KEY, removing old Entry"
        printf '%s\n' "DELETE FROM Entries WHERE p_cdeKey='$ESC_OLD_S_KEY' AND p_type='Entry:Item:Series';" >> "$WRITES"
    fi
fi

EXISTING=$(sqlite3 "$DB" "SELECT p_uuid FROM Entries WHERE p_cdeKey='$ESC_S_KEY' AND p_type='Entry:Item:Series';")
SQL_FILE="/tmp/kindle_series_create_$$.sql"
VC_COUNT=$BOOK_COUNT

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
    p_virtualCollectionCount=$VC_COUNT,
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

logit "Running write transaction..."
cat "$SQL_FILE" >> "$WRITES"
run_write_tx "$WRITES"
logit "Write transaction done (rc=$TX_RC)"

# Restore ICU
sqlite3 "$DB" 2>> "$LOG" <<'SQLICUON'
.dbconfig defensive off
PRAGMA writable_schema=ON;
UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries';
PRAGMA writable_schema=OFF;
SQLICUON

rm -f "$SQL_FILE" "$WRITES"

start com.lab126.ccat 2>/dev/null
logit "Started ccat. Done."

if [ "$TX_RC" -ne 0 ]; then
    echo "Error: could not save the series; nothing was changed (see series.log)."
    exit 0
fi

BOOK_COUNT_FINAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_seriesId='$ESC_S_ID';")
if [ -n "$EDIT_ID" ]; then
    echo "Updated '$SERIES_NAME' with $BOOK_COUNT_FINAL books."
else
    echo "Created '$SERIES_NAME' with $BOOK_COUNT_FINAL books."
fi
