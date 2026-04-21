#!/bin/sh
echo "Content-Type: text/html"
echo ""

FW_VERSION=$(cat /etc/version.txt 2>/dev/null || echo "0.0.0")
FW_MAJOR=$(echo "$FW_VERSION" | cut -d'.' -f1)
FW_MINOR=$(echo "$FW_VERSION" | cut -d'.' -f2)
FW_PATCH=$(echo "$FW_VERSION" | cut -d'.' -f3)

if [ "$FW_MAJOR" -lt 5 ] 2>/dev/null || \
   { [ "$FW_MAJOR" -eq 5 ] && [ "$FW_MINOR" -lt 13 ]; } 2>/dev/null || \
   { [ "$FW_MAJOR" -eq 5 ] && [ "$FW_MINOR" -eq 13 ] && [ "${FW_PATCH:-0}" -lt 4 ]; } 2>/dev/null; then
    echo "<div class='empty-state'>"
    echo "<strong>Series grouping requires firmware 5.13.4 or later.</strong><br>"
    echo "Your firmware: $FW_VERSION<br>"
    echo "This feature uses database structures that don't exist on older firmware. Modifying your database could cause issues."
    echo "</div>"
    exit 0
fi

DB="${DB:-/var/local/cc.db}"

sqlite3 "$DB" "
SELECT
    s.d_seriesId,
    COALESCE(e_series.p_titles_0_nominal, REPLACE(s.d_seriesId, 'urn:collection:1:asin-', '')),
    s.d_itemPositionLabel,
    COALESCE(e_book.p_titles_0_nominal, '(unknown)'),
    s.d_itemCdeKey
FROM Series s
LEFT JOIN Entries e_book ON e_book.p_cdeKey = s.d_itemCdeKey AND e_book.p_type = 'Entry:Item'
LEFT JOIN Entries e_series ON e_series.p_cdeKey = REPLACE(s.d_seriesId, 'urn:collection:1:asin-', '') AND e_series.p_type = 'Entry:Item:Series'
ORDER BY COALESCE(e_series.p_titles_0_nominal, s.d_seriesId), s.d_itemPosition;
" | awk -F'|' '
function hesc(s) { gsub(/&/,"\\&amp;",s); gsub(/</,"\\&lt;",s); gsub(/>/,"\\&gt;",s); return s }
function emit() {
    if (n == 0) return
    sid = save_sid; gsub(/"/, "\\&quot;", sid)
    print "<div class=\"card\"><div class=\"card-header\">"
    print "<div><span class=\"card-title\">" hesc(save_title) "</span> <span class=\"card-subtitle\">" n " books</span></div>"
    print "<div style=\"display:flex;gap:8px;\"><button class=\"btn btn-toggle\" onclick=\"toggleCard(this)\">Show</button><button class=\"btn\" onclick=\"editSeries(\x27" save_sid "\x27)\">Edit</button><button class=\"btn btn-danger\" onclick=\"removeSeries(\x27" save_sid "\x27)\">Remove</button></div>"
    print "</div><div class=\"card-body\" style=\"display:none;\"><div class=\"card-body-inner\">"
    if (save_fk != "") print "<img class=\"series-thumb\" src=\"/cgi-bin/book_thumb.cgi?key=" save_fk "\" alt=\"\" onerror=\"this.style.display=&quot;none&quot;\">"
    print "<div class=\"series-books\">"
    printf "%s", book_html
    print "</div></div></div></div>"
}
BEGIN { n = 0; cur = "" }
{
    if ($1 != cur) {
        emit()
        cur = $1; save_sid = $1; save_title = $2; save_fk = $5; n = 0; book_html = ""
    }
    n++
    book_html = book_html "<div class=\"book-item\"><span class=\"book-num\">" hesc($3) "</span>" hesc($4) "</div>"
}
END {
    emit()
    if (n == 0 && cur == "") print "<div class=\"empty-state\">No series on device yet. Tap <b>Create Series</b> to get started.</div>"
}'
