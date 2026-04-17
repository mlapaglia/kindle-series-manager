#!/bin/sh
#
# Goodreads progress update. Uses stored session from gr_login.sh.
# Usage: gr_update.sh <book_id> <page> [body]
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COOKIE_JAR="$SCRIPT_DIR/gr_cookies.txt"
SESSION_FILE="$SCRIPT_DIR/gr_session.txt"
UPDATE_URL="https://www.goodreads.com/user_status.json"

BOOK_ID="$1"
PAGE="$2"
BODY="${3:-}"

if [ -z "$BOOK_ID" ] || [ -z "$PAGE" ]; then
    echo "Usage: gr_update.sh <book_id> <page> [body]"
    echo "  book_id  Goodreads book ID"
    echo "  page     Current page number"
    echo "  body     Optional status text"
    exit 1
fi

if [ ! -f "$COOKIE_JAR" ]; then
    echo "ERROR: $COOKIE_JAR not found. Run gr_login.sh first."
    exit 1
fi

if [ ! -f "$SESSION_FILE" ]; then
    echo "ERROR: $SESSION_FILE not found. Run gr_login.sh first."
    exit 1
fi

CSRF_TOKEN=$(cat "$SESSION_FILE")

if [ -z "$CSRF_TOKEN" ]; then
    echo "ERROR: CSRF token is empty"
    exit 1
fi

echo "Sending progress update..."
echo "  book_id: $BOOK_ID"
echo "  page: $PAGE"
echo "  body: $BODY"
echo ""

TMPFILE="$SCRIPT_DIR/gr_response.tmp"

HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TMPFILE" \
    -b "$COOKIE_JAR" \
    -H "X-CSRF-Token: $CSRF_TOKEN" \
    -H "X-Requested-With: XMLHttpRequest" \
    -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
    --data-urlencode "user_status[book_id]=$BOOK_ID" \
    --data-urlencode "user_status[body]=$BODY" \
    --data-urlencode "user_status[page]=$PAGE" \
    "$UPDATE_URL")

RESPONSE=$(cat "$TMPFILE")
rm -f "$TMPFILE"

echo "HTTP Status: $HTTP_CODE"
echo "Response:"
echo "$RESPONSE"
