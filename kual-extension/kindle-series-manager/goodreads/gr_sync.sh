#!/bin/sh
#
# Goodreads progress sync daemon.
# Listens for book open/close and screen saver events, then pushes
# progress updates to Goodreads for mapped books when progress changes.
#
# Prerequisites:
#   - /mnt/us/ENABLE_GR_SYNC flag file exists
#   - gr_creds.json has email, password, and goodreads_user_id
#   - gr_login.sh has been run (gr_cookies.txt + gr_session.txt exist)
#   - gr_build_mapping.sh has been run (gr_mapping.json exists)
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="/var/local/cc.db"
CREDS_FILE="$SCRIPT_DIR/gr_creds.json"
MAPPING_FILE="$SCRIPT_DIR/gr_mapping.json"
COOKIE_JAR="$SCRIPT_DIR/gr_cookies.txt"
SESSION_FILE="$SCRIPT_DIR/gr_session.txt"
PROGRESS_FILE="$SCRIPT_DIR/gr_last_progress.txt"
PAGES_FILE="$SCRIPT_DIR/gr_total_pages.txt"
LOG="$SCRIPT_DIR/gr_sync.log"
UPDATE_URL="https://www.goodreads.com/user_status.json"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
    echo "$1"
}

FLAG_FILE="/mnt/us/ENABLE_GR_SYNC"
if [ ! -f "$FLAG_FILE" ]; then
    log "Sync disabled: $FLAG_FILE not found"
    exit 0
fi

if [ ! -f "$CREDS_FILE" ]; then
    log "ERROR: $CREDS_FILE not found"
    exit 1
fi

GR_EMAIL=$(grep '"email"' "$CREDS_FILE" | sed 's/.*"email".*"\([^"]*\)".*/\1/')
GR_USER_ID=$(grep '"goodreads_user_id"' "$CREDS_FILE" | sed 's/.*"goodreads_user_id".*"\([^"]*\)".*/\1/')

if [ -z "$GR_EMAIL" ] || [ "$GR_EMAIL" = "you@example.com" ]; then
    log "ERROR: email not configured in $CREDS_FILE"
    exit 1
fi

if [ -z "$GR_USER_ID" ]; then
    log "ERROR: goodreads_user_id not configured in $CREDS_FILE"
    exit 1
fi

if [ ! -f "$COOKIE_JAR" ] || [ ! -f "$SESSION_FILE" ]; then
    log "Not logged in, attempting login..."
    bash "$SCRIPT_DIR/gr_login.sh" >> "$LOG" 2>&1
    if [ ! -f "$COOKIE_JAR" ] || [ ! -f "$SESSION_FILE" ]; then
        log "ERROR: Login failed. Run gr_login.sh manually to troubleshoot."
        exit 1
    fi
fi

if [ ! -f "$MAPPING_FILE" ]; then
    log "No mapping found, building..."
    bash "$SCRIPT_DIR/gr_build_mapping.sh" >> "$LOG" 2>&1
    if [ ! -f "$MAPPING_FILE" ]; then
        log "ERROR: Failed to build mapping. Run gr_build_mapping.sh manually."
        exit 1
    fi
fi

if [ ! -f "$PROGRESS_FILE" ]; then
    touch "$PROGRESS_FILE"
fi

if [ ! -f "$PAGES_FILE" ]; then
    touch "$PAGES_FILE"
fi

get_last_synced_percent() {
    grep "^$1	" "$PROGRESS_FILE" | cut -d'	' -f2
}

set_last_synced_percent() {
    grep -v "^$1	" "$PROGRESS_FILE" > "$PROGRESS_FILE.tmp" 2>/dev/null
    echo "$1	$2" >> "$PROGRESS_FILE.tmp"
    mv "$PROGRESS_FILE.tmp" "$PROGRESS_FILE"
}

lookup_gr_book_id() {
    grep "\"cdeKey\":\"$1\"" "$MAPPING_FILE" | grep -o '"grBookId":"[^"]*"' | sed 's/"grBookId":"//;s/"//'
}

lookup_kindle_title() {
    grep "\"cdeKey\":\"$1\"" "$MAPPING_FILE" | grep -o '"kindleTitle":"[^"]*"' | sed 's/"kindleTitle":"//;s/"//'
}

get_total_pages() {
    grep "^$1	" "$PAGES_FILE" | cut -d'	' -f2
}

set_total_pages() {
    grep -v "^$1	" "$PAGES_FILE" > "$PAGES_FILE.tmp" 2>/dev/null
    echo "$1	$2" >> "$PAGES_FILE.tmp"
    mv "$PAGES_FILE.tmp" "$PAGES_FILE"
}

fetch_total_pages() {
    CSRF_TOKEN=$(cat "$SESSION_FILE")
    TMPFILE="$SCRIPT_DIR/gr_response.tmp"

    curl -s -o "$TMPFILE" \
        -b "$COOKIE_JAR" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -H "X-Requested-With: XMLHttpRequest" \
        -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
        --data-urlencode "user_status[book_id]=$1" \
        --data-urlencode "user_status[body]=" \
        --data-urlencode "user_status[page]=0" \
        "$UPDATE_URL"

    TOTAL=$(cat "$TMPFILE" | grep -o '"finalPosition":[0-9]*' | sed 's/"finalPosition"://')
    rm -f "$TMPFILE"
    echo "$TOTAL"
}

check_and_sync() {
    MOST_RECENT=$(sqlite3 "$DB" "SELECT p_cdeKey, p_percentFinished FROM Entries WHERE p_type='Entry:Item' AND p_location IS NOT NULL ORDER BY p_lastAccess DESC LIMIT 1;" 2>/dev/null)

    CDE_KEY=$(echo "$MOST_RECENT" | cut -d'|' -f1)
    CURRENT_PERCENT=$(echo "$MOST_RECENT" | cut -d'|' -f2)

    log "Most recent book: cdeKey=$CDE_KEY percent=$CURRENT_PERCENT"

    if [ -z "$CDE_KEY" ]; then
        log "No book found in cc.db"
        return
    fi

    GR_BOOK_ID=$(lookup_gr_book_id "$CDE_KEY")
    if [ -z "$GR_BOOK_ID" ]; then
        TITLE_DBG=$(sqlite3 "$DB" "SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey='$CDE_KEY' AND p_type='Entry:Item' LIMIT 1;" 2>/dev/null)
        log "Book not in mapping: $CDE_KEY ($TITLE_DBG)"
        return
    fi

    TITLE=$(lookup_kindle_title "$CDE_KEY")
    CURRENT_PERCENT_INT=$(printf "%.0f" "$CURRENT_PERCENT" 2>/dev/null || echo "0")
    LAST_PERCENT=$(get_last_synced_percent "$CDE_KEY")
    LAST_PERCENT=${LAST_PERCENT:-0}

    if [ "$CURRENT_PERCENT_INT" = "$LAST_PERCENT" ]; then
        log "No change: $TITLE ($CURRENT_PERCENT_INT%)"
        return
    fi

    TOTAL_PAGES=$(get_total_pages "$GR_BOOK_ID")
    if [ -z "$TOTAL_PAGES" ] || [ "$TOTAL_PAGES" = "0" ]; then
        log "Fetching total page count for $TITLE from Goodreads..."
        TOTAL_PAGES=$(fetch_total_pages "$GR_BOOK_ID")
        if [ -z "$TOTAL_PAGES" ] || [ "$TOTAL_PAGES" = "0" ]; then
            log "FAILED: Could not get total pages for $TITLE"
            return
        fi
        set_total_pages "$GR_BOOK_ID" "$TOTAL_PAGES"
        log "Total pages: $TOTAL_PAGES"
    fi

    CURRENT_PAGE=$(awk "BEGIN {printf \"%.0f\", $CURRENT_PERCENT * $TOTAL_PAGES / 100}")

    log "Progress changed: $TITLE $LAST_PERCENT% -> $CURRENT_PERCENT_INT% (page $CURRENT_PAGE of $TOTAL_PAGES)"

    CSRF_TOKEN=$(cat "$SESSION_FILE")
    TMPFILE="$SCRIPT_DIR/gr_response.tmp"

    HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TMPFILE" \
        -b "$COOKIE_JAR" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -H "X-Requested-With: XMLHttpRequest" \
        -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
        --data-urlencode "user_status[book_id]=$GR_BOOK_ID" \
        --data-urlencode "user_status[body]=" \
        --data-urlencode "user_status[page]=$CURRENT_PAGE" \
        "$UPDATE_URL")

    RESPONSE=$(cat "$TMPFILE" 2>/dev/null)
    rm -f "$TMPFILE"

    if [ "$HTTP_CODE" = "200" ]; then
        set_last_synced_percent "$CDE_KEY" "$CURRENT_PERCENT_INT"
        log "Synced: $TITLE page $CURRENT_PAGE of $TOTAL_PAGES (HTTP $HTTP_CODE)"
    else
        log "FAILED: $TITLE (HTTP $HTTP_CODE) $RESPONSE"
    fi
}

log "=== Goodreads sync daemon started ==="
log "Listening for book switch and screen saver events..."

check_and_sync

FIFO="$SCRIPT_DIR/gr_events.fifo"
rm -f "$FIFO"
mkfifo "$FIFO"

lipc-wait-event -m com.lab126.appmgrd appActivating >> "$FIFO" 2>/dev/null &
APPMGR_PID=$!

lipc-wait-event -m com.lab126.powerd goingToScreenSaver >> "$FIFO" 2>/dev/null &
POWERD_PID=$!

trap "kill $APPMGR_PID $POWERD_PID 2>/dev/null; rm -f $FIFO; exit 0" INT TERM

while read -r LINE; do
    case "$LINE" in
        "appActivating 1 "*) continue ;;
    esac
    log "Event: $LINE"
    sleep 2
    check_and_sync
done < "$FIFO"
