#!/bin/sh
echo "Content-Type: application/json"
echo ""

DB="${DB:-/var/local/cc.db}"

json_escape() {
    echo "$1" | sed 's/\\/\\\\/g;s/"/\\"/g'
}

TMP=$(mktemp /tmp/ksm_coll_XXXXXX) || exit 1
trap 'rm -f "$TMP"' EXIT

# Build JSON array of collections with embedded books
sqlite3 -separator '	' "$DB" "SELECT p_cdeKey, p_titles_0_nominal FROM Entries WHERE p_type='Collection' ORDER BY p_titles_0_nominal;" > "$TMP"

printf '{"collections":['

FIRST=1
while IFS='	' read -r COLL_KEY COLL_NAME; do
    if [ "$FIRST" -eq 1 ]; then
        FIRST=0
    else
        printf ','
    fi

    SAFE_NAME=$(json_escape "$COLL_NAME")
    COLL_URN="urn:collection:1:$COLL_KEY"
    SAFE_URN=$(json_escape "$COLL_URN")

    ESC_KEY=$(echo "$COLL_KEY" | sed "s/'/''/g")

    printf '{"id":"%s","name":"%s","books":[' "$SAFE_URN" "$SAFE_NAME"

    sqlite3 -separator '	' "$DB" "SELECT e.p_cdeKey, e.p_titles_0_nominal, COALESCE(e.p_credits_0_name_collation, '') FROM Entries e WHERE e.p_type='Entry:Item' AND e.j_collections LIKE '%${ESC_KEY}%';" | awk -F'	' '
    function jesc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
    { if (NR > 1) printf ","
      printf "{\"key\":\"%s\",\"title\":\"%s\",\"author\":\"%s\"}", jesc($1), jesc($2), jesc($3)
    }'

    printf ']}'
done < "$TMP"

printf ']}'
