#!/bin/sh
#
# Build a mapping of Kindle books to Hardcover book IDs.
# Matches by comparing Kindle titles (from cc.db) against Hardcover search results.
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

echo "=== Step 1: Get books from cc.db ==="

KINDLE_BOOKS=$(sqlite3 -separator '	' "$DB" \
    "SELECT e.p_cdeKey, e.p_titles_0_nominal, COALESCE(e.j_credits, '')
     FROM Entries e
     WHERE e.p_type='Entry:Item'
       AND e.p_location IS NOT NULL
       AND e.p_location LIKE '/mnt/us/documents/%'
       AND e.p_isVisibleInHome=1
     GROUP BY e.p_cdeKey
     ORDER BY e.p_titles_0_nominal;")

KINDLE_COUNT=$(echo "$KINDLE_BOOKS" | grep -c '.')
echo "Found $KINDLE_COUNT books on Kindle"

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

    BODY="{\"query\":\"query { search(query: \\\"$SEARCH_QUERY\\\", query_type: \\\"books\\\", per_page: 3) { results { hits { document { id title author_names } } } } }\"}"

    RESPONSE=$(curl -s -X POST "$API_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$BODY")

    # Extract first hit's ID and title
    HC_ID=$(echo "$RESPONSE" | grep -o '"id":[0-9]*' | head -1 | sed 's/"id"://')
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

    SAFE_TITLE=$(echo "$TITLE" | sed 's/\\/\\\\/g;s/"/\\"/g')
    SAFE_AUTHOR=$(echo "$AUTHOR" | sed 's/\\/\\\\/g;s/"/\\"/g')
    SAFE_HC_TITLE=$(echo "$HC_TITLE" | sed 's/\\/\\\\/g;s/"/\\"/g')

    if [ "$FIRST" = "1" ]; then
        FIRST=0
    else
        echo "," >> "$MAPPING_FILE"
    fi
    printf '  {"cdeKey":"%s","kindleTitle":"%s","author":"%s","hcBookId":%s,"hcTitle":"%s"}' \
        "$CDE_KEY" "$SAFE_TITLE" "$SAFE_AUTHOR" "$HC_ID" "$SAFE_HC_TITLE" >> "$MAPPING_FILE"

    MATCH_COUNT=$((MATCH_COUNT + 1))
    echo "    -> MATCHED: $HC_TITLE (id:$HC_ID)"

    # Rate limit: avoid hammering the API
    sleep 1
done

echo "" >> "$MAPPING_FILE"
echo "]" >> "$MAPPING_FILE"

echo ""
echo "Mapping saved to $MAPPING_FILE"
