#!/bin/sh
echo "Content-Type: application/json"
echo ""

DB="${DB:-/var/local/cc.db}"

# Full URL decode: + -> space, then every %XX -> raw byte (UTF-8 safe), so
# series names in any language survive instead of staying as literal "%XX".
# awk rather than printf '%b' "\xHH": dash's printf has no \x escapes.
urldecode() {
    printf '%s' "$1" | LC_ALL=C awk '
        BEGIN { for (i = 0; i < 256; i++) hex[sprintf("%02x", i)] = i }
        {
            s = $0; gsub(/\+/, " ", s); out = ""
            while (match(s, /%[0-9A-Fa-f][0-9A-Fa-f]/)) {
                out = out substr(s, 1, RSTART - 1) sprintf("%c", hex[tolower(substr(s, RSTART + 1, 2))])
                s = substr(s, RSTART + 3)
            }
            printf "%s", out s
        }'
}

# The id embeds the (possibly non-ASCII) series name.
SERIES_ID=$(urldecode "$(echo "$QUERY_STRING" | sed 's/^id=//')")

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

FIRST_BOOK_KEY=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$SERIES_ID' ORDER BY d_itemPosition LIMIT 1;")
ORIGIN_TYPE=$(sqlite3 "$DB" "SELECT COALESCE(p_originType, '') FROM Entries WHERE p_cdeKey='$FIRST_BOOK_KEY' AND p_type='Entry:Item' LIMIT 1;")
case "$ORIGIN_TYPE" in
    21) BADGE_MODE="ku" ;;
    0)  BADGE_MODE="none" ;;
    *)  BADGE_MODE="kupr" ;;
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

echo "{\"id\":\"$SAFE_ID\",\"asin\":\"$SAFE_ASIN\",\"name\":\"$SAFE_TITLE\",\"badgeMode\":\"$BADGE_MODE\",\"books\":[$BOOKS_JSON]}"
