#!/bin/sh
#
# Search Hardcover for a book by title.
# Usage: hc_search.sh "Book Title"
# Returns JSON response from Hardcover GraphQL API.
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/hc_config.json"

if [ -z "$1" ]; then
    echo "Usage: hc_search.sh \"book title\""
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

QUERY=$(echo "$1" | sed 's/"/\\"/g')
BODY="{\"query\":\"query { search(query: \\\"$QUERY\\\", query_type: \\\"books\\\", per_page: 5) { results { hits { document { id title author_names } } } } }\"}"

curl -s -X POST "$API_URL" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$BODY"
