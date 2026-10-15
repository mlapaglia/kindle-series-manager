#!/bin/sh
#
# KSM reading statistics daemon.
# Samples cc.db every 30 minutes and records snapshots into ksm_stats.db.
#
# Prerequisites:
#   - /mnt/us/ENABLE_KSM_STATS flag file exists
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DB="/var/local/cc.db"
STATS_DB="$EXT_DIR/ksm_stats.db"
PID_FILE="/tmp/ksm_stats_daemon.pid"
LOG="$EXT_DIR/ksm_stats.log"
FLAG_FILE="/mnt/us/ENABLE_KSM_STATS"
INTERVAL=1800

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

cleanup() {
    rm -f "$PID_FILE"
    log "Daemon stopped"
    exit 0
}

trap cleanup INT TERM

if [ ! -f "$FLAG_FILE" ]; then
    log "Stats disabled: $FLAG_FILE not found"
    exit 0
fi

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log "Daemon already running (PID $OLD_PID)"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

echo $$ > "$PID_FILE"
log "Daemon started (PID $$)"

# Create database and tables if they don't exist
sqlite3 "$STATS_DB" "
CREATE TABLE IF NOT EXISTS reading_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    cde_key TEXT NOT NULL,
    title TEXT,
    author TEXT,
    percent_finished REAL,
    read_state INTEGER
);
CREATE TABLE IF NOT EXISTS library_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    total_books INTEGER,
    reading INTEGER,
    finished INTEGER,
    unread INTEGER
);
"

take_snapshot() {
    NOW=$(date +%s)
    BASE_WHERE="p_type='Entry:Item' AND p_location IS NOT NULL"

    TOTAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE;")
    READING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE AND p_readState=1;")
    FINISHED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE AND p_readState=2;")
    UNREAD=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE AND (p_readState=0 OR p_readState IS NULL);")

    sqlite3 "$STATS_DB" "INSERT INTO library_snapshots (timestamp, total_books, reading, finished, unread) VALUES ($NOW, ${TOTAL:-0}, ${READING:-0}, ${FINISHED:-0}, ${UNREAD:-0});"

    sqlite3 -separator '	' "$DB" "
    SELECT p_cdeKey, p_titles_0_nominal, p_credits_0_name_collation, p_percentFinished, p_readState
    FROM Entries
    WHERE $BASE_WHERE AND (p_readState=1 OR p_readState=2);
    " | while IFS='	' read -r CDE_KEY TITLE AUTHOR PERCENT READ_STATE; do
        SAFE_KEY=$(printf '%s' "$CDE_KEY" | sed "s/'/''/g")
        SAFE_TITLE=$(printf '%s' "$TITLE" | sed "s/'/''/g")
        SAFE_AUTHOR=$(printf '%s' "$AUTHOR" | sed "s/'/''/g")
        sqlite3 "$STATS_DB" "INSERT INTO reading_snapshots (timestamp, cde_key, title, author, percent_finished, read_state) VALUES ($NOW, '$SAFE_KEY', '$SAFE_TITLE', '$SAFE_AUTHOR', ${PERCENT:-0}, ${READ_STATE:-0});"
    done

    log "Snapshot taken: total=$TOTAL reading=$READING finished=$FINISHED unread=$UNREAD"
}

# Take initial snapshot immediately
take_snapshot

# Main loop
while true; do
    if [ ! -f "$FLAG_FILE" ]; then
        log "Flag file removed, exiting"
        cleanup
    fi
    sleep $INTERVAL
    take_snapshot
done
