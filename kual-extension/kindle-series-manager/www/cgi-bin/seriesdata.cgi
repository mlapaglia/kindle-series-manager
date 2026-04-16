#!/bin/sh
echo "Content-Type: application/json"
echo ""

DB="/var/local/cc.db"

SERIES_ID=$(echo "$QUERY_STRING" | sed 's/id=//;s/%3A/:/g;s/%2F/\//g;s/+/ /g')

if [ -z "$SERIES_ID" ]; then
    echo '{"error":"no series ID"}'
    exit 0
fi

S_KEY=$(echo "$SERIES_ID" | sed 's/urn:collection:1:asin-//')
TITLE=$(sqlite3 "$DB" "SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey='$S_KEY' AND p_type='Entry:Item:Series';")

ASIN=""
case "$S_KEY" in
    SL-*) ;;
    *) ASIN="$S_KEY" ;;
esac

BOOKS_JSON=$(sqlite3 -separator '	' "$DB" "SELECT d_itemCdeKey, COALESCE((SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey=d_itemCdeKey AND p_type='Entry:Item' LIMIT 1), '(unknown)') FROM Series WHERE d_seriesId='$SERIES_ID' ORDER BY d_itemPosition;" | awk -F'	' '{
    gsub(/"/, "\\\"", $1)
    gsub(/"/, "\\\"", $2)
    if (NR > 1) printf ","
    printf "{\"key\":\"%s\",\"title\":\"%s\"}", $1, $2
}')

SAFE_TITLE=$(echo "$TITLE" | sed 's/\\/\\\\/g;s/"/\\"/g')
SAFE_ID=$(echo "$SERIES_ID" | sed 's/\\/\\\\/g;s/"/\\"/g')
SAFE_ASIN=$(echo "$ASIN" | sed 's/\\/\\\\/g;s/"/\\"/g')

echo "{\"id\":\"$SAFE_ID\",\"asin\":\"$SAFE_ASIN\",\"name\":\"$SAFE_TITLE\",\"books\":[$BOOKS_JSON]}"
