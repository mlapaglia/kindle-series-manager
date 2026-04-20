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
echo "<input type='text' id='bookFilter' class='input-field input-small' placeholder='Filter...' oninput='filterBooks()'>"
echo "<label style='display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted);margin-bottom:8px;cursor:pointer;user-select:none;'><input type='checkbox' id='hideInSeries' onchange='filterBooks()'> Hide books already in a series</label>"
echo "<div class='avail-list'>"

sqlite3 "$DB" "SELECT p_cdeKey || '	' || p_titles_0_nominal || '	' || COALESCE((SELECT GROUP_CONCAT(COALESCE((SELECT p_titles_0_nominal FROM Entries e2 WHERE e2.p_cdeKey=REPLACE(s.d_seriesId,'urn:collection:1:asin-','') AND e2.p_type='Entry:Item:Series'), '?'), ', ') FROM Series s WHERE s.d_itemCdeKey=Entries.p_cdeKey), '') FROM Entries WHERE p_type='Entry:Item' AND p_isVisibleInHome=1 AND p_location LIKE '/mnt/us/documents/%' ORDER BY p_titles_0_nominal;" | while IFS='	' read -r KEY TITLE SERIES; do
    SAFE_KEY=$(echo "$KEY" | sed "s/'/\&#39;/g;s/\"/\&quot;/g")
    SAFE_TITLE=$(echo "$TITLE" | sed "s/'/\&#39;/g;s/\"/\&quot;/g;s/</\&lt;/g;s/>/\&gt;/g")
    SAFE_SERIES=$(echo "$SERIES" | sed "s/'/\&#39;/g;s/\"/\&quot;/g;s/</\&lt;/g;s/>/\&gt;/g")
    if [ -n "$SERIES" ]; then
        echo "<div class='avail-book in-series' data-key='$SAFE_KEY' data-title='$SAFE_TITLE' data-series='$SAFE_SERIES' onclick='addBook(this)'>$SAFE_TITLE<span class='avail-series-label'>$SAFE_SERIES</span></div>"
    else
        echo "<div class='avail-book' data-key='$SAFE_KEY' data-title='$SAFE_TITLE' data-series='' onclick='addBook(this)'>$SAFE_TITLE</div>"
    fi
done

echo "</div>"
echo "</div>"

echo "</div>"
echo "</div>"
