#!/bin/sh
# Machine-readable view of the sideloaded library for the Calibre plugin:
#   {"version":1,"books":[...],"series":[...]}
# books:  key, type, title, author, location, series (id or ""), position
# series: id, name, count
echo "Content-Type: application/json; charset=utf-8"
echo ""

DB="${DB:-/var/local/cc.db}"

FW_VERSION=$(cat /etc/version.txt 2>/dev/null || echo "0.0.0")
FW_MAJOR=$(echo "$FW_VERSION" | cut -d'.' -f1)
FW_MINOR=$(echo "$FW_VERSION" | cut -d'.' -f2)
FW_PATCH=$(echo "$FW_VERSION" | cut -d'.' -f3)

if [ "$FW_MAJOR" -lt 5 ] 2>/dev/null || \
   { [ "$FW_MAJOR" -eq 5 ] && [ "$FW_MINOR" -lt 13 ]; } 2>/dev/null || \
   { [ "$FW_MAJOR" -eq 5 ] && [ "$FW_MINOR" -eq 13 ] && [ "${FW_PATCH:-0}" -lt 4 ]; } 2>/dev/null; then
    echo '{"error":"Series grouping requires firmware 5.13.4 or later"}'
    exit 0
fi

# js EXPR: SQL that renders EXPR as a JSON string literal. Escaping happens in
# SQL (no awk/sed quoting pitfalls); control characters become spaces.
js() {
    printf '%s\n' "'\"' || replace(replace(replace(replace(replace(COALESCE($1, ''), '\\', '\\\\'), '\"', '\\\"'), char(10), ' '), char(13), ' '), char(9), ' ') || '\"'"
}

SERIES_OF="(SELECT s.d_seriesId FROM Series s WHERE s.d_itemCdeKey = e.p_cdeKey ORDER BY s.d_seriesId LIMIT 1)"
POS_OF="(SELECT s.d_itemPositionLabel FROM Series s WHERE s.d_itemCdeKey = e.p_cdeKey ORDER BY s.d_seriesId LIMIT 1)"
SERIES_NAME="(SELECT x.p_titles_0_nominal FROM Entries x WHERE x.p_cdeKey = REPLACE(g.d_seriesId, 'urn:collection:1:asin-', '') AND x.p_type = 'Entry:Item:Series' LIMIT 1)"

BOOKS=$(sqlite3 "$DB" "
SELECT COALESCE(GROUP_CONCAT(j, ','), '') FROM (
  SELECT '{\"key\":' || $(js e.p_cdeKey)
      || ',\"type\":' || $(js e.p_cdeType)
      || ',\"title\":' || $(js e.p_titles_0_nominal)
      || ',\"author\":' || $(js e.p_credits_0_name_collation)
      || ',\"location\":' || $(js e.p_location)
      || ',\"series\":' || $(js "$SERIES_OF")
      || ',\"position\":' || $(js "$POS_OF")
      || '}' AS j
  FROM Entries e
  WHERE e.p_type = 'Entry:Item' AND e.p_isVisibleInHome = 1
    AND e.p_location LIKE '/mnt/us/documents/%'
  ORDER BY e.p_titles_0_nominal
);" 2>/dev/null) || {
    echo '{"error":"could not read the library database"}'
    exit 0
}

SERIES=$(sqlite3 "$DB" "
SELECT COALESCE(GROUP_CONCAT(j, ','), '') FROM (
  SELECT '{\"id\":' || $(js g.d_seriesId)
      || ',\"name\":' || $(js "$SERIES_NAME")
      || ',\"count\":' || COUNT(*)
      || '}' AS j
  FROM Series g
  GROUP BY g.d_seriesId
  ORDER BY g.d_seriesId
);" 2>/dev/null)

printf '{"version":1,"books":[%s],"series":[%s]}\n' "$BOOKS" "$SERIES"
