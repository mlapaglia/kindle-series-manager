#!/bin/sh
echo "Content-Type: application/json"
echo ""

DB="${DB:-/var/local/cc.db}"

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g;s/"/\\"/g;s/	/\\t/g'
}

BASE_WHERE="p_type='Entry:Item' AND p_location IS NOT NULL"

TOTAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE;")
READING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE AND p_readState=1;")
FINISHED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE AND p_readState=2;")
UNREAD=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Entries WHERE $BASE_WHERE AND (p_readState=0 OR p_readState IS NULL);")

CURRENTLY_JSON=$(sqlite3 -separator '	' "$DB" "
SELECT p_titles_0_nominal, p_credits_0_name_collation, p_percentFinished, p_lastAccess
FROM Entries
WHERE $BASE_WHERE AND p_readState=1
ORDER BY p_lastAccess DESC
LIMIT 20;
" | awk -F'	' '
function jesc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
BEGIN { first=1 }
{
    if (!first) printf ","
    first=0
    printf "{\"title\":\"%s\",\"author\":\"%s\",\"percent\":%s,\"lastAccess\":%s}",
        jesc($1), jesc($2), ($3+0), ($4+0)
}')

RECENT_JSON=$(sqlite3 -separator '	' "$DB" "
SELECT p_titles_0_nominal, p_credits_0_name_collation, p_lastAccess
FROM Entries
WHERE $BASE_WHERE AND p_readState=2
ORDER BY p_lastAccess DESC
LIMIT 10;
" | awk -F'	' '
function jesc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
BEGIN { first=1 }
{
    if (!first) printf ","
    first=0
    printf "{\"title\":\"%s\",\"author\":\"%s\",\"lastAccess\":%s}",
        jesc($1), jesc($2), ($3+0)
}')

AUTHORS_JSON=$(sqlite3 -separator '	' "$DB" "
SELECT p_credits_0_name_collation, COUNT(*) as total,
       SUM(CASE WHEN p_readState=2 THEN 1 ELSE 0 END) as finished
FROM Entries
WHERE $BASE_WHERE AND p_credits_0_name_collation IS NOT NULL
GROUP BY p_credits_0_name_collation
ORDER BY total DESC
LIMIT 10;
" | awk -F'	' '
function jesc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
BEGIN { first=1 }
{
    if (!first) printf ","
    first=0
    printf "{\"author\":\"%s\",\"count\":%s,\"finished\":%s}",
        jesc($1), ($2+0), ($3+0)
}')

printf '{"totalBooks":%s,"reading":%s,"finished":%s,"unread":%s,"currentlyReading":[%s],"recentlyFinished":[%s],"topAuthors":[%s]}' \
    "${TOTAL:-0}" "${READING:-0}" "${FINISHED:-0}" "${UNREAD:-0}" \
    "$CURRENTLY_JSON" "$RECENT_JSON" "$AUTHORS_JSON"
