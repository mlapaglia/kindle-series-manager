#!/bin/sh
#
# Search Goodreads for a book by title/author and return the book ID.
# Usage: gr_search.sh "book title" ["author name"]
# No auth required - uses public search page.
#

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"

QUERY="$1"
AUTHOR="$2"

if [ -z "$QUERY" ]; then
    echo "Usage: gr_search.sh \"book title\" [\"author name\"]"
    exit 1
fi

if [ -n "$AUTHOR" ]; then
    QUERY="$QUERY $AUTHOR"
fi

SEARCH_URL="https://www.goodreads.com/search?q=$(echo "$QUERY" | sed 's/ /+/g')&search_type=books"

HTML=$(curl -s -L \
    -H "User-Agent: $UA" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.9" \
    "$SEARCH_URL")

echo "$HTML" | grep -o 'href="/book/show/[0-9]*[^"]*"' | head -5 | while read -r MATCH; do
    BOOK_URL=$(echo "$MATCH" | sed 's/href="//;s/"//')
    BOOK_ID=$(echo "$BOOK_URL" | grep -o '/book/show/[0-9]*' | sed 's/\/book\/show\///')
    BOOK_TITLE=$(echo "$MATCH" | sed 's/.*">//;s/<.*//')

    TITLE_CHUNK=$(echo "$BOOK_URL" | sed 's/.*[0-9]\.//' | sed 's/-/ /g;s/\./ /g' | sed 's/^ *//')
    echo "$BOOK_ID|$TITLE_CHUNK"
done
