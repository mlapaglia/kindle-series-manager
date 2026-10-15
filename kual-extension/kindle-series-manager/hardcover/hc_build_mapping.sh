#!/bin/sh
#
# Build a mapping of currently-reading Kindle books to Hardcover book IDs.
# Matches by comparing Kindle titles (from cc.db) against Hardcover search results.
# Only maps books that are actively being read (p_readState=1 or partial progress).
#
# Requires: hc_config.json with a valid API token
# Output: hc_mapping.json
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="${DB:-/var/local/cc.db}"
CONFIG="$SCRIPT_DIR/hc_config.json"
MAPPING_FILE="$SCRIPT_DIR/hc_mapping.json"

if [ ! -f "$DB" ]; then
    echo "ERROR: $DB not found"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    echo "ERROR: $CONFIG not found"
    exit 1
fi

TOKEN=$(grep '"token"' "$CONFIG" | sed 's/.*"token".*"\([^"]*\)".*/\1/')
API_URL=$(grep '"api_url"' "$CONFIG" | sed 's/.*"api_url".*"\([^"]*\)".*/\1/')

if [ -z "$TOKEN" ]; then
    echo "ERROR: token not configured in $CONFIG"
    exit 1
fi

echo "=== Step 1: Get currently-reading books from cc.db ==="

KINDLE_BOOKS=$(sqlite3 -separator '	' "$DB" \
    "SELECT e.p_cdeKey, e.p_titles_0_nominal, COALESCE(e.j_credits, '')
     FROM Entries e
     WHERE e.p_type='Entry:Item'
       AND e.p_location IS NOT NULL
       AND e.p_location LIKE '/mnt/us/documents/%'
       AND e.p_isVisibleInHome=1
       AND (e.p_readState=1 OR (e.p_percentFinished > 0 AND e.p_percentFinished < 100))
     GROUP BY e.p_cdeKey
     ORDER BY e.p_lastAccess DESC;")

KINDLE_COUNT=$(echo "$KINDLE_BOOKS" | grep -c '.')
echo "Found $KINDLE_COUNT currently-reading books on Kindle"

echo ""
echo "=== Step 2: Search Hardcover for each book ==="

echo "[" > "$MAPPING_FILE"
FIRST=1
MATCH_COUNT=0

echo "$KINDLE_BOOKS" | while IFS='	' read -r CDE_KEY TITLE CREDITS; do
    if [ -z "$CDE_KEY" ]; then
        continue
    fi

    AUTHOR=$(echo "$CREDITS" | grep -o '"display":"[^"]*"' | head -1 | sed 's/"display":"//;s/"//')

    # Clean title for search: remove subtitles and series info
    SEARCH_TITLE=$(echo "$TITLE" | sed 's/ ([^)]*)//g;s/:.*//;s/  */ /g;s/^ *//;s/ *$//')
    SEARCH_QUERY=$(echo "$SEARCH_TITLE" | sed 's/"/\\"/g')

    echo "  Searching: $SEARCH_TITLE"

    BODY="{\"query\":\"query { search(query: \\\"$SEARCH_QUERY\\\", query_type: \\\"Book\\\", per_page: 3) { results } }\"}"

    echo "    [DEBUG] POST $API_URL"
    echo "    [DEBUG] Body: $BODY"

    RESPONSE=$(curl -s -X POST "$API_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$BODY")

    echo "    [DEBUG] Response: $RESPONSE"

    # Book IDs are strings ("id":"446730") while author/image/series IDs are ints ("id":241306)
    # "title":"..." only matches document titles (in highlights, title is an object: "title":{...})
    HC_ID=$(echo "$RESPONSE" | grep -o '"id":"[0-9]*"' | head -1 | sed 's/"id":"//;s/"//')
    HC_TITLE=$(echo "$RESPONSE" | grep -o '"title":"[^"]*"' | head -1 | sed 's/"title":"//;s/"//')

    if [ -z "$HC_ID" ]; then
        echo "    -> No match found"
        continue
    fi

    # Compare cleaned titles for basic validation
    CLEAN_KINDLE=$(echo "$SEARCH_TITLE" | tr 'A-Z' 'a-z' | sed "s/'//g;s/  */ /g")
    CLEAN_HC=$(echo "$HC_TITLE" | tr 'A-Z' 'a-z' | sed "s/'//g;s/  */ /g")

    MATCHED=0
    case "$CLEAN_HC" in
        *"$CLEAN_KINDLE"*) MATCHED=1 ;;
    esac
    if [ "$MATCHED" = "0" ]; then
        case "$CLEAN_KINDLE" in
            *"$CLEAN_HC"*) MATCHED=1 ;;
        esac
    fi

    if [ "$MATCHED" = "0" ]; then
        echo "    -> Title mismatch: '$HC_TITLE' (skipped)"
        continue
    fi

    # --- Ensure book is in user's library as "currently reading" (status_id=2) ---
    echo "    Ensuring book is in library..."
    INSERT_UB_BODY="{\"query\":\"mutation { insert_user_book(object: { book_id: $HC_ID, status_id: 2 }) { user_book { id } error } }\"}"
    INSERT_UB_RESP=$(curl -s -X POST "$API_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$INSERT_UB_BODY")
    echo "    [DEBUG] insert_user_book response: $INSERT_UB_RESP"
    sleep 1

    # --- Query user_book_read ID and page count ---
    echo "    Fetching read record and page count..."
    ME_BODY="{\"query\":\"{ me { user_books(where: { book_id: { _eq: $HC_ID } }) { id user_book_reads { id progress_pages } book { pages } } } }\"}"
    ME_RESP=$(curl -s -X POST "$API_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$ME_BODY")
    echo "    [DEBUG] me query response: $ME_RESP"

    HC_PAGES=$(echo "$ME_RESP" | grep -o '"pages":[0-9]*' | head -1 | sed 's/"pages"://')
    UBR_ID=$(echo "$ME_RESP" | grep -o '"user_book_reads":\[{"id":[0-9]*' | head -1 | sed 's/.*"id"://')

    # If no user_book_read exists yet, create one
    if [ -z "$UBR_ID" ]; then
        echo "    No read record found, creating one..."
        USER_BOOK_ID=$(echo "$ME_RESP" | grep -o '"user_books":\[{"id":[0-9]*' | head -1 | sed 's/.*"id"://')
        if [ -n "$USER_BOOK_ID" ]; then
            INSERT_READ_BODY="{\"query\":\"mutation { insert_user_book_read(object: { user_book_id: $USER_BOOK_ID, started_at: \\\"$(date -u '+%Y-%m-%d')\\\" }) { id error } }\"}"
            INSERT_READ_RESP=$(curl -s -X POST "$API_URL" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d "$INSERT_READ_BODY")
            echo "    [DEBUG] insert_user_book_read response: $INSERT_READ_RESP"
            UBR_ID=$(echo "$INSERT_READ_RESP" | grep -o '"id":[0-9]*' | head -1 | sed 's/"id"://')
            sleep 1
        fi
    fi

    if [ -z "$HC_PAGES" ] || [ "$HC_PAGES" = "0" ] || [ "$HC_PAGES" = "null" ]; then
        echo "    -> WARNING: No page count for $HC_TITLE, progress sync will be skipped"
        HC_PAGES="0"
    fi
    if [ -z "$UBR_ID" ]; then
        echo "    -> WARNING: Could not get/create read record for $HC_TITLE"
        UBR_ID=""
    fi

    SAFE_TITLE=$(echo "$TITLE" | sed 's/\\/\\\\/g;s/"/\\"/g')
    SAFE_AUTHOR=$(echo "$AUTHOR" | sed 's/\\/\\\\/g;s/"/\\"/g')
    SAFE_HC_TITLE=$(echo "$HC_TITLE" | sed 's/\\/\\\\/g;s/"/\\"/g')

    if [ "$FIRST" = "1" ]; then
        FIRST=0
    else
        echo "," >> "$MAPPING_FILE"
    fi
    printf '  {"cdeKey":"%s","kindleTitle":"%s","author":"%s","hcBookId":"%s","hcTitle":"%s","hcPages":%s,"userBookReadId":%s}' \
        "$CDE_KEY" "$SAFE_TITLE" "$SAFE_AUTHOR" "$HC_ID" "$SAFE_HC_TITLE" \
        "${HC_PAGES:-0}" "${UBR_ID:-null}" >> "$MAPPING_FILE"

    MATCH_COUNT=$((MATCH_COUNT + 1))
    echo "    -> MATCHED: $HC_TITLE (id:$HC_ID, pages:${HC_PAGES:-0}, readId:${UBR_ID:-none})"

    # Rate limit: avoid hammering the API
    sleep 1
done

echo "" >> "$MAPPING_FILE"
echo "]" >> "$MAPPING_FILE"

echo ""
echo "Mapping saved to $MAPPING_FILE"
