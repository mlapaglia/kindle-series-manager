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
    echo "Your firmware: $FW_VERSION"
    echo "</div>"
    exit 0
fi

DB="${DB:-/var/local/cc.db}"

echo "<div>"

echo "<div style='margin-bottom:16px;'>"
echo "<div class='panel-header'>Series Details</div>"
echo "<input type='text' id='newSeriesName' class='input-field' placeholder='Series name'>"
echo "<input type='text' id='newSeriesAsin' class='input-field input-small' placeholder='ASIN (optional, e.g. B09DD17H3N)'>"
echo "<div class='panel-header' style='margin-top:8px;'>Program Badges</div>"
echo "<label style='display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#666;margin-right:16px;cursor:pointer;'><input type='radio' name='badgeMode' id='badgeNone' value='none' checked> None</label>"
echo "<label style='display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#666;margin-right:16px;cursor:pointer;'><input type='radio' name='badgeMode' id='badgeKU' value='ku'> Kindle Unlimited</label>"
echo "<label style='display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#666;cursor:pointer;'><input type='radio' name='badgeMode' id='badgeKUPR' value='kupr'> KU + Prime Reading</label>"
echo "</div>"

echo "<div class='create-layout'>"

echo "<div>"
echo "<div class='panel-header'>Reading Order <span id='selectedCount' style='font-weight:400;'>0</span> books</div>"
echo "<div id='selectedBooks' class='selected-list'>"
echo "<div class='empty-state'>Click books from the right to add them</div>"
echo "</div>"
echo "<br>"
echo "<button id='btnSave' class='btn btn-primary' onclick='saveSeries()' style='width:100%;padding:12px;font-size:15px;'>Create Series</button>"
echo "</div>"

echo "<div>"
echo "<div class='panel-header'>Available Books</div>"
echo "<input type='text' id='bookFilter' class='input-field input-small' placeholder='Filter by title or author...' oninput='filterBooks()'>"
echo "<label style='display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted);margin-bottom:8px;cursor:pointer;user-select:none;'><input type='checkbox' id='hideInSeries' onchange='filterBooks()'> Hide books already in a series</label>"
echo "<div class='avail-list'>"

sqlite3 "$DB" "SELECT p_cdeKey || '	' || p_titles_0_nominal || '	' || COALESCE((SELECT GROUP_CONCAT(COALESCE((SELECT p_titles_0_nominal FROM Entries e2 WHERE e2.p_cdeKey=REPLACE(s.d_seriesId,'urn:collection:1:asin-','') AND e2.p_type='Entry:Item:Series'), '?'), ', ') FROM Series s WHERE s.d_itemCdeKey=Entries.p_cdeKey), '') || '	' || COALESCE(p_credits_0_name_collation, '') FROM Entries WHERE p_type='Entry:Item' AND p_isVisibleInHome=1 AND p_location LIKE '/mnt/us/documents/%' ORDER BY p_titles_0_nominal;" | awk -F'	' '
function hesc(s) { gsub(/&/,"\\&amp;",s); gsub(/</,"\\&lt;",s); gsub(/>/,"\\&gt;",s); gsub(/"/,"\\&quot;",s); gsub(/'\''/,"\\&#39;",s); return s }
{
    key = hesc($1); title = hesc($2); series = hesc($3); author = hesc($4)
    meta = ""
    if (author != "") meta = "<span class=\"avail-author-label\">" author "</span>"
    if (series != "") meta = meta "<span class=\"avail-series-label\">" series "</span>"
    if (meta != "") {
        printf "<div class=\"avail-book%s\" data-key=\"%s\" data-title=\"%s\" data-author=\"%s\" data-series=\"%s\" onclick=\"addBook(this)\">%s%s</div>\n", (series != "" ? " in-series" : ""), key, title, author, series, title, meta
    } else {
        printf "<div class=\"avail-book\" data-key=\"%s\" data-title=\"%s\" data-author=\"\" data-series=\"\" onclick=\"addBook(this)\">%s</div>\n", key, title, title
    }
}'

echo "</div>"
echo "</div>"

echo "</div>"
echo "</div>"
