#!/bin/sh
echo "Content-Type: application/json"
echo ""

STATS_DB="${STATS_DB:-/mnt/us/extensions/kindle-series-manager/ksm_stats.db}"

if [ ! -f "$STATS_DB" ]; then
    echo '{"snapshots":[],"bookProgress":[]}'
    exit 0
fi

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g;s/"/\\"/g;s/	/\\t/g'
}

SNAPSHOTS_JSON=$(sqlite3 -separator '	' "$STATS_DB" "
SELECT timestamp, total_books, reading, finished, unread
FROM library_snapshots
ORDER BY timestamp DESC
LIMIT 100;
" | awk -F'	' '
BEGIN { first=1 }
{
    if (!first) printf ","
    first=0
    printf "{\"timestamp\":%s,\"totalBooks\":%s,\"reading\":%s,\"finished\":%s,\"unread\":%s}",
        ($1+0), ($2+0), ($3+0), ($4+0), ($5+0)
}')

BOOK_PROGRESS_JSON=$(sqlite3 -separator '	' "$STATS_DB" "
SELECT title, GROUP_CONCAT(timestamp || ':' || percent_finished, '|')
FROM reading_snapshots
WHERE read_state=1
GROUP BY cde_key
ORDER BY MAX(timestamp) DESC
LIMIT 20;
" | awk -F'	' '
function jesc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
BEGIN { first=1 }
{
    if (!first) printf ","
    first=0
    printf "{\"title\":\"%s\",\"snapshots\":[", jesc($1)
    n = split($2, pairs, "|")
    for (i = 1; i <= n; i++) {
        split(pairs[i], kv, ":")
        if (i > 1) printf ","
        printf "{\"timestamp\":%s,\"percent\":%s}", (kv[1]+0), (kv[2]+0)
    }
    printf "]}"
}')

printf '{"snapshots":[%s],"bookProgress":[%s]}' \
    "$SNAPSHOTS_JSON" "$BOOK_PROGRESS_JSON"
