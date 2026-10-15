#!/bin/sh
echo "Content-Type: application/json"
echo ""

DB="${DB:-/var/local/cc.db}"

printf '{"books":['

sqlite3 -separator '	' "$DB" "SELECT p_cdeKey, p_titles_0_nominal, COALESCE(p_credits_0_name_collation, '') FROM Entries WHERE p_type='Entry:Item' AND p_isVisibleInHome=1 AND p_location LIKE '/mnt/us/documents/%' ORDER BY p_titles_0_nominal;" | awk -F'	' '
function jesc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
{ if (NR > 1) printf ","
  printf "{\"key\":\"%s\",\"title\":\"%s\",\"author\":\"%s\"}", jesc($1), jesc($2), jesc($3)
}'

printf ']}'
