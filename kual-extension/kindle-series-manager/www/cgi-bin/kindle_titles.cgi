#!/bin/sh
echo "Content-Type: application/json"
echo ""

DB="${DB:-/var/local/cc.db}"

TITLES=$(sqlite3 "$DB" "SELECT p_titles_0_nominal FROM Entries WHERE p_type='Entry:Item' AND p_isVisibleInHome=1 AND p_location LIKE '/mnt/us/documents/%' ORDER BY p_titles_0_nominal;" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$TITLES" ]; then
    printf '[]'
    exit 0
fi

printf '['
echo "$TITLES" | awk '{
    gsub(/\\/, "\\\\")
    gsub(/"/, "\\\"")
    gsub(/\t/, " ")
    gsub(/\r/, "")
    if (NR > 1) printf ","
    printf "\"%s\"", $0
}'
printf ']'
