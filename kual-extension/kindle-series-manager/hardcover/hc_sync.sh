#!/bin/sh
#
# Hardcover progress sync daemon.
# Listens for book open/close and screen saver events, then pushes
# progress updates to Hardcover for mapped books when progress changes.
#
# Prerequisites:
#   - /mnt/us/ENABLE_HC_SYNC flag file exists
#   - hc_config.json has a valid API token
#   - hc_build_mapping.sh has been run (hc_mapping.json exists)
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="${DB:-/var/local/cc.db}"
CONFIG="$SCRIPT_DIR/hc_config.json"
MAPPING_FILE="$SCRIPT_DIR/hc_mapping.json"
PROGRESS_FILE="$SCRIPT_DIR/hc_last_progress.txt"
LOG="$SCRIPT_DIR/hc_sync.log"
PID_FILE="/tmp/hc_sync.pid"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
    echo "$1"
}

FLAG_FILE="/mnt/us/ENABLE_HC_SYNC"
if [ ! -f "$FLAG_FILE" ]; then
    log "Sync disabled: $FLAG_FILE not found"
    exit 0
fi

if [ ! -f "$CONFIG" ]; then
    log "ERROR: $CONFIG not found"
    exit 1
fi

TOKEN=$(grep '"token"' "$CONFIG" | sed 's/.*"token".*"\([^"]*\)".*/\1/')
API_URL=$(grep '"api_url"' "$CONFIG" | sed 's/.*"api_url".*"\([^"]*\)".*/\1/')

if [ -z "$TOKEN" ]; then
    log "ERROR: token not configured in $CONFIG"
    exit 1
fi

if [ ! -f "$MAPPING_FILE" ]; then
    log "No mapping found, building..."
    sh "$SCRIPT_DIR/hc_build_mapping.sh" >> "$LOG" 2>&1
    if [ ! -f "$MAPPING_FILE" ]; then
        log "ERROR: Failed to build mapping. Run hc_build_mapping.sh manually."
        exit 1
    fi
fi

if [ ! -f "$PROGRESS_FILE" ]; then
    touch "$PROGRESS_FILE"
fi

echo $$ > "$PID_FILE"

get_last_synced_percent() {
    grep "^$1	" "$PROGRESS_FILE" | cut -d'	' -f2
}

set_last_synced_percent() {
    grep -v "^$1	" "$PROGRESS_FILE" > "$PROGRESS_FILE.tmp" 2>/dev/null
    echo "$1	$2" >> "$PROGRESS_FILE.tmp"
    mv "$PROGRESS_FILE.tmp" "$PROGRESS_FILE"
}

lookup_hc_book_id() {
    grep "\"cdeKey\":\"$1\"" "$MAPPING_FILE" | grep -o '"hcBookId":"[^"]*"' | sed 's/"hcBookId":"//;s/"//'
}

lookup_kindle_title() {
    grep "\"cdeKey\":\"$1\"" "$MAPPING_FILE" | grep -o '"kindleTitle":"[^"]*"' | sed 's/"kindleTitle":"//;s/"//'
}

lookup_hc_pages() {
    grep "\"cdeKey\":\"$1\"" "$MAPPING_FILE" | grep -o '"hcPages":[0-9]*' | sed 's/"hcPages"://'
}

lookup_user_book_read_id() {
    grep "\"cdeKey\":\"$1\"" "$MAPPING_FILE" | grep -o '"userBookReadId":[0-9]*' | sed 's/"userBookReadId"://'
}

check_and_sync() {
    MOST_RECENT=$(sqlite3 "$DB" "SELECT p_cdeKey, p_percentFinished FROM Entries WHERE p_type='Entry:Item' AND p_location IS NOT NULL AND p_location LIKE '/mnt/us/documents/%' AND p_isVisibleInHome=1 ORDER BY p_lastAccess DESC LIMIT 1;" 2>/dev/null)

    CDE_KEY=$(echo "$MOST_RECENT" | cut -d'|' -f1)
    CURRENT_PERCENT=$(echo "$MOST_RECENT" | cut -d'|' -f2)

    log "Most recent book: cdeKey=$CDE_KEY percent=$CURRENT_PERCENT"

    if [ -z "$CDE_KEY" ]; then
        log "No book found in cc.db"
        return
    fi

    HC_BOOK_ID=$(lookup_hc_book_id "$CDE_KEY")
    if [ -z "$HC_BOOK_ID" ]; then
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

    log "Progress changed: $TITLE $LAST_PERCENT% -> $CURRENT_PERCENT_INT%"

    # Look up page count and read record ID from mapping
    HC_PAGES=$(lookup_hc_pages "$CDE_KEY")
    UBR_ID=$(lookup_user_book_read_id "$CDE_KEY")

    if [ -z "$HC_PAGES" ] || [ "$HC_PAGES" = "0" ]; then
        log "SKIPPED: $TITLE - no page count in mapping (re-run hc_build_mapping.sh)"
        return
    fi

    if [ -z "$UBR_ID" ]; then
        log "SKIPPED: $TITLE - no read record ID in mapping (re-run hc_build_mapping.sh)"
        return
    fi

    # Convert Kindle percentage to pages
    PROGRESS_PAGES=$(awk "BEGIN {printf \"%d\", $CURRENT_PERCENT_INT * $HC_PAGES / 100}")

    BODY="{\"query\":\"mutation { update_user_book_read(id: $UBR_ID, object: { progress_pages: $PROGRESS_PAGES }) { id error } }\"}"

    TMPFILE="$SCRIPT_DIR/hc_response.tmp"

    HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TMPFILE" \
        -X POST "$API_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$BODY")

    RESPONSE=$(cat "$TMPFILE" 2>/dev/null)
    rm -f "$TMPFILE"

    if [ "$HTTP_CODE" = "200" ]; then
        # Check for GraphQL errors
        case "$RESPONSE" in
            *'"errors"'*)
                log "FAILED: $TITLE (GraphQL error) $RESPONSE"
                ;;
            *)
                set_last_synced_percent "$CDE_KEY" "$CURRENT_PERCENT_INT"
                log "Synced: $TITLE $CURRENT_PERCENT_INT% (HTTP $HTTP_CODE)"
                ;;
        esac
    else
        log "FAILED: $TITLE (HTTP $HTTP_CODE) $RESPONSE"
    fi
}

log "=== Hardcover sync daemon started ==="
log "Listening for book switch and screen saver events..."

check_and_sync

FIFO="$SCRIPT_DIR/hc_events.fifo"
rm -f "$FIFO"
mkfifo "$FIFO"
exec 3<>"$FIFO"

lipc-wait-event -m com.lab126.appmgrd appActivating >&3 2>/dev/null &
APPMGR_PID=$!

lipc-wait-event -m com.lab126.powerd goingToScreenSaver >&3 2>/dev/null &
POWERD_PID=$!

# shellcheck disable=SC2064
trap "kill $APPMGR_PID $POWERD_PID 2>/dev/null; exec 3>&-; exec 3<&-; rm -f \"$FIFO\" \"$PID_FILE\"; exit 0" INT TERM

while read -r LINE <&3; do
    case "$LINE" in
        "appActivating 1 "*) continue ;;
    esac
    log "Event: $LINE"
    sleep 2
    check_and_sync
done
