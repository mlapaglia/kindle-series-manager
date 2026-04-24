#!/bin/sh
echo "Content-Type: application/json"
echo ""

DB="/var/local/cc.db"

if [ ! -f "$DB" ]; then
    echo '{"current":null,"all":[]}'
    exit 0
fi

# Current book (most recently accessed)
CURRENT=$(sqlite3 -separator '	' "$DB" \
    "SELECT p_cdeKey, p_titles_0_nominal, p_thumbnail FROM Entries WHERE p_type='Entry:Item' AND p_location IS NOT NULL AND p_thumbnail IS NOT NULL ORDER BY p_lastAccess DESC LIMIT 1;" 2>/dev/null)

# All books with covers
ALL=$(sqlite3 -separator '	' "$DB" \
    "SELECT p_cdeKey, p_titles_0_nominal, p_thumbnail FROM Entries WHERE p_type='Entry:Item' AND p_location IS NOT NULL AND p_thumbnail IS NOT NULL ORDER BY p_titles_0_nominal;" 2>/dev/null)

json_escape() {
    echo "$1" | sed 's/\\/\\\\/g;s/"/\\"/g;s/	/\\t/g'
}

# Build current object
if [ -n "$CURRENT" ]; then
    C_KEY=$(echo "$CURRENT" | cut -f1)
    C_TITLE=$(echo "$CURRENT" | cut -f2)
    C_THUMB=$(echo "$CURRENT" | cut -f3)
    C_KEY_ESC=$(json_escape "$C_KEY")
    C_TITLE_ESC=$(json_escape "$C_TITLE")
    C_THUMB_ESC=$(json_escape "$C_THUMB")
    CURRENT_JSON="{\"key\":\"$C_KEY_ESC\",\"title\":\"$C_TITLE_ESC\",\"thumbnail\":\"$C_THUMB_ESC\"}"
else
    CURRENT_JSON="null"
fi

# Build all array
ALL_JSON=""
FIRST=1
echo "$ALL" | while IFS='	' read -r KEY TITLE THUMB; do
    [ -z "$KEY" ] && continue
    KEY_ESC=$(json_escape "$KEY")
    TITLE_ESC=$(json_escape "$TITLE")
    THUMB_ESC=$(json_escape "$THUMB")
    if [ "$FIRST" = "1" ]; then
        FIRST=0
    else
        printf ","
    fi
    printf '{"key":"%s","title":"%s","thumbnail":"%s"}' "$KEY_ESC" "$TITLE_ESC" "$THUMB_ESC"
done > /tmp/ss_bookcovers_all.json

printf '{"current":%s,"all":[' "$CURRENT_JSON"
cat /tmp/ss_bookcovers_all.json 2>/dev/null
printf ']}'
rm -f /tmp/ss_bookcovers_all.json
