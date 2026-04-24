#!/bin/sh
#
# Push a reading progress update to Hardcover.
# Usage: hc_update.sh <user_book_read_id> <progress_pages>
#   user_book_read_id  Hardcover user_book_read ID (from mapping)
#   progress_pages     Number of pages read
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/hc_config.json"

UBR_ID="$1"
PROGRESS_PAGES="$2"

if [ -z "$UBR_ID" ] || [ -z "$PROGRESS_PAGES" ]; then
    echo "Usage: hc_update.sh <user_book_read_id> <progress_pages>"
    echo "  user_book_read_id  Hardcover user_book_read ID (from mapping)"
    echo "  progress_pages     Number of pages read"
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

BODY="{\"query\":\"mutation { update_user_book_read(id: $UBR_ID, object: { progress_pages: $PROGRESS_PAGES }) { id error } }\"}"

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
