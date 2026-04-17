#!/bin/sh
#
# Build a mapping of currently-reading Kindle books to Goodreads book IDs.
# Matches by comparing Kindle titles (from cc.db) against the user's
# Goodreads "currently-reading" shelf (via the public widget endpoint).
#
# Requires: gr_creds.json with a "goodreads_user_id" field
# Output: gr_mapping.json
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="/var/local/cc.db"
CREDS_FILE="$SCRIPT_DIR/gr_creds.json"
MAPPING_FILE="$SCRIPT_DIR/gr_mapping.json"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"

if [ ! -f "$DB" ]; then
    echo "ERROR: $DB not found"
    exit 1
fi

GR_USER_ID=$(grep '"goodreads_user_id"' "$CREDS_FILE" | sed 's/.*"goodreads_user_id".*"\([^"]*\)".*/\1/')

if [ -z "$GR_USER_ID" ]; then
    echo "ERROR: goodreads_user_id not found in $CREDS_FILE"
    echo "Add it like: \"goodreads_user_id\": \"183958037\""
    exit 1
fi

echo "=== Step 1: Fetch Goodreads currently-reading shelf ==="
WIDGET_URL="https://www.goodreads.com/review/grid_widget/$GR_USER_ID?shelf=currently-reading"

WIDGET_HTML=$(curl -s -L \
    -H "User-Agent: $UA" \
    -H "Accept: */*" \
    "$WIDGET_URL")

GR_TEMP="$SCRIPT_DIR/gr_shelf.tmp"
rm -f "$GR_TEMP"

CLEAN_HTML=$(echo "$WIDGET_HTML" | sed 's/\\"/"/g;s/\\//g')

echo "$CLEAN_HTML" | grep -o 'title="[^"]*"[^>]*href="[^"]*review/show/[0-9]*[^"]*"' | while read -r LINK; do
    GR_TITLE=$(echo "$LINK" | grep -o 'title="[^"]*"' | sed 's/title="//;s/"//')
    GR_REVIEW_ID=$(echo "$LINK" | grep -o 'review/show/[0-9]*' | sed 's/review\/show\///')

    GR_BOOK_ID=$(echo "$CLEAN_HTML" | grep -o "review/show/${GR_REVIEW_ID}[^<]*<img[^>]*src=[^>]*" | grep -o 'books/[0-9]*l/[0-9]*' | head -1 | sed 's/books\/[0-9]*l\///')

    if [ -z "$GR_BOOK_ID" ]; then
        GR_BOOK_ID=$(echo "$CLEAN_HTML" | grep -o "review/show/${GR_REVIEW_ID}[^<]*<img[^>]*src=[^>]*" | grep -o '/[0-9][0-9]*\._S' | head -1 | sed 's/^\///;s/\._S//')
    fi

    if [ -n "$GR_TITLE" ] && [ -n "$GR_REVIEW_ID" ]; then
        GR_CLEAN=$(echo "$GR_TITLE" | sed "s/'//g" | sed 's/ ([^)]*)//g;s/:.*//;s/  */ /g;s/^ *//;s/ *$//' | tr 'A-Z' 'a-z')
        echo "$GR_CLEAN	$GR_TITLE	$GR_REVIEW_ID	$GR_BOOK_ID" >> "$GR_TEMP"
    fi
done

if [ ! -f "$GR_TEMP" ] || [ ! -s "$GR_TEMP" ]; then
    echo "ERROR: No books found on shelf. Check your goodreads_user_id."
    echo "Widget URL: $WIDGET_URL"
    exit 1
fi

GR_COUNT=$(wc -l < "$GR_TEMP")
echo "Found $GR_COUNT books on Goodreads currently-reading shelf"

echo ""
echo "Goodreads shelf:"
cat "$GR_TEMP" | while IFS='	' read -r CLEAN FULL RID BID; do
    echo "  - $FULL"
    echo "    [review:$RID book:$BID]"
done

echo ""
echo "=== Step 2: Get currently-reading books from cc.db ==="

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
echo "=== Step 3: Match Kindle books to Goodreads shelf ==="

echo "Goodreads shelf (cleaned):"
cat "$GR_TEMP" | while IFS='	' read -r CLEAN FULL RID BID; do
    echo "  [review:$RID book:$BID] $CLEAN"
done
echo ""

echo "[" > "$MAPPING_FILE"
FIRST=1

echo "$KINDLE_BOOKS" | while IFS='	' read -r CDE_KEY TITLE CREDITS; do
    CLEAN_TITLE=$(echo "$TITLE" | sed "s/'//g;s/ ([^)]*)//g;s/:.*//;s/  */ /g;s/^ *//;s/ *$//")
    CLEAN_LOWER=$(echo "$CLEAN_TITLE" | tr 'A-Z' 'a-z')

    MATCHED_LINE=""
    while IFS='	' read -r GR_CLEAN GR_FULL GR_RID GR_BID; do
        GR_CMP=$(echo "$GR_CLEAN" | sed "s/\\\\//g;s/'//g")
        if [ "$CLEAN_LOWER" = "$GR_CMP" ]; then
            MATCHED_LINE="$GR_CLEAN	$GR_FULL	$GR_RID	$GR_BID"
            break
        fi
        case "$GR_CMP" in
            *"$CLEAN_LOWER"*) MATCHED_LINE="$GR_CLEAN	$GR_FULL	$GR_RID	$GR_BID"; break ;;
        esac
        case "$CLEAN_LOWER" in
            *"$GR_CMP"*) MATCHED_LINE="$GR_CLEAN	$GR_FULL	$GR_RID	$GR_BID"; break ;;
        esac
    done < "$GR_TEMP"

    if [ -n "$MATCHED_LINE" ]; then
        GR_TITLE=$(echo "$MATCHED_LINE" | cut -d'	' -f2)
        GR_REVIEW_ID=$(echo "$MATCHED_LINE" | cut -d'	' -f3)
        GR_BOOK_ID=$(echo "$MATCHED_LINE" | cut -d'	' -f4)
        AUTHOR=$(echo "$CREDITS" | grep -o '"display":"[^"]*"' | head -1 | sed 's/"display":"//;s/"//')

        SAFE_TITLE=$(echo "$TITLE" | sed 's/\\/\\\\/g;s/"/\\"/g')
        SAFE_AUTHOR=$(echo "$AUTHOR" | sed 's/\\/\\\\/g;s/"/\\"/g')
        SAFE_GR_TITLE=$(echo "$GR_TITLE" | sed "s/\\\\\'/'/g;s/\\\\/\\\\\\\\/g;s/\"/\\\\\"/g")

        if [ "$FIRST" = "1" ]; then
            FIRST=0
        else
            echo "," >> "$MAPPING_FILE"
        fi
        printf '  {"cdeKey":"%s","kindleTitle":"%s","author":"%s","grBookId":"%s","grReviewId":"%s","grTitle":"%s"}' \
            "$CDE_KEY" "$SAFE_TITLE" "$SAFE_AUTHOR" "$GR_BOOK_ID" "$GR_REVIEW_ID" "$SAFE_GR_TITLE" >> "$MAPPING_FILE"

        echo "  MATCHED: $CLEAN_TITLE -> $GR_TITLE (book:$GR_BOOK_ID review:$GR_REVIEW_ID)"
    fi
done

rm -f "$GR_TEMP"

echo "" >> "$MAPPING_FILE"
echo "]" >> "$MAPPING_FILE"

echo ""
echo "Mapping saved to $MAPPING_FILE"
