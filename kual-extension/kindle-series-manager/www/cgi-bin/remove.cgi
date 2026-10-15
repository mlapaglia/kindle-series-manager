#!/bin/sh
echo "Content-Type: text/plain"
echo ""

DB="${DB:-/var/local/cc.db}"
LOG="/mnt/us/extensions/kindle-series-manager/series.log"

logit() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [remove] $1" >> "$LOG"
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

SERIES_ID=$(echo "$QUERY_STRING" | sed 's/id=//;s/%3A/:/g;s/%2F/\//g;s/+/ /g')

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

# All writes are collected here and run in one transaction (run_write_tx).
WRITES="/tmp/kindle_series_remove_$$.sql"

if [ "$COUNT" -eq 0 ] 2>/dev/null; then
    ORPHAN=$(sqlite3 "$DB" "SELECT 1 FROM Entries WHERE p_cdeKey='$ESC_S_CDE_KEY' AND p_type='Entry:Item:Series' LIMIT 1;")
    if [ -z "$ORPHAN" ]; then
        echo "Error: series not found"
        exit 0
    fi
    printf '%s\n' "DELETE FROM Entries WHERE p_cdeKey='$ESC_S_CDE_KEY' AND p_type='Entry:Item:Series';" > "$WRITES"
    DONE_LOG="Cleaned up orphaned series entry $SERIES_ID"
    DONE_MSG="Cleaned up orphaned series entry."
else
    MEMBER_KEYS=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$ESC_SERIES_ID';")
    printf '%s\n' "DELETE FROM Series WHERE d_seriesId='$ESC_SERIES_ID';" > "$WRITES"
    for KEY in $MEMBER_KEYS; do
        # still in another series once this one is gone?
        REMAINING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_itemCdeKey='$KEY' AND d_seriesId<>'$ESC_SERIES_ID';")
        if [ "$REMAINING" -eq 0 ] 2>/dev/null; then
            printf '%s\n' "UPDATE Entries SET p_seriesState=1 WHERE p_cdeKey='$KEY' AND p_type='Entry:Item';" >> "$WRITES"
        fi
    done
    printf '%s\n' "DELETE FROM Entries WHERE p_cdeKey='$ESC_S_CDE_KEY' AND p_type='Entry:Item:Series';" >> "$WRITES"
    DONE_LOG="Removed series $SERIES_ID ($COUNT books)"
    DONE_MSG="Removed $COUNT books from series."
fi

mntroot rw
stop com.lab126.ccat 2>/dev/null

sqlite3 "$DB" 2>/dev/null <<'SQLSCHEMA'
.dbconfig defensive off
PRAGMA writable_schema=ON;
UPDATE sqlite_master SET sql=REPLACE(sql, ' COLLATE icu', '') WHERE type='table' AND name='Entries';
DROP INDEX IF EXISTS EntriesCredit0CollationIndex;
DROP INDEX IF EXISTS EntriesTitles0Index;
PRAGMA writable_schema=OFF;
SQLSCHEMA

run_write_tx "$WRITES"

sqlite3 "$DB" 2>/dev/null <<'SQLSCHEMA'
.dbconfig defensive off
PRAGMA writable_schema=ON;
UPDATE sqlite_master SET sql=REPLACE(REPLACE(sql, 'p_titles_0_collation,', 'p_titles_0_collation COLLATE icu,'), 'p_credits_0_name_collation,', 'p_credits_0_name_collation COLLATE icu,') WHERE type='table' AND name='Entries';
PRAGMA writable_schema=OFF;
SQLSCHEMA

rm -f "$WRITES"
start com.lab126.ccat 2>/dev/null

if [ "$TX_RC" -ne 0 ]; then
    echo "Error: could not remove the series; nothing was changed (see series.log)."
    exit 0
fi

logit "$DONE_LOG"
echo "$DONE_MSG"
