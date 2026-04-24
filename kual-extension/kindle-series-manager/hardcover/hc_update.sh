#!/bin/sh
#
# Push a reading progress update to Hardcover.
# Usage: hc_update.sh <book_id> <progress_percent>
#   book_id           Hardcover book ID (integer)
#   progress_percent  Reading progress 0-100
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/hc_config.json"

BOOK_ID="$1"
PROGRESS="$2"

if [ -z "$BOOK_ID" ] || [ -z "$PROGRESS" ]; then
    echo "Usage: hc_update.sh <book_id> <progress_percent>"
    echo "  book_id           Hardcover book ID"
    echo "  progress_percent  Reading progress 0-100"
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

# Convert percent to 0.0-1.0 float for Hardcover API
PROGRESS_FLOAT=$(awk "BEGIN {printf \"%.2f\", $PROGRESS / 100}")

BODY="{\"query\":\"mutation { insert_user_book_read_one(object: { book_id: $BOOK_ID, progress: $PROGRESS_FLOAT, started_at: \\\"now()\\\" }, on_conflict: { constraint: user_book_reads_pkey, update_columns: [progress] }) { id } }\"}"

HTTP_CODE=$(curl -s -w "%{http_code}" -o "$SCRIPT_DIR/hc_response.tmp" \
    -X POST "$API_URL" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$BODY")

RESPONSE=$(cat "$SCRIPT_DIR/hc_response.tmp" 2>/dev/null)
rm -f "$SCRIPT_DIR/hc_response.tmp"

echo "HTTP Status: $HTTP_CODE"
echo "Response: $RESPONSE"

if [ "$HTTP_CODE" = "200" ]; then
    # Check for GraphQL errors
    case "$RESPONSE" in
        *'"errors"'*) echo "ERROR: GraphQL error in response"; exit 1 ;;
    esac
    exit 0
else
    exit 1
fi
