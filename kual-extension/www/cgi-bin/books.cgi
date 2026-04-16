#!/bin/sh
echo "Content-Type: text/html"
echo ""

DB="/var/local/cc.db"

echo "<div>"

echo "<div style='margin-bottom:16px;'>"
echo "<div class='panel-header'>Series Details</div>"
echo "<input type='text' id='newSeriesName' class='input-field' placeholder='Series name'>"
echo "<input type='text' id='newSeriesAsin' class='input-field input-small' placeholder='ASIN (optional, e.g. B09DD17H3N)'>"
echo "</div>"

echo "<div class='create-layout'>"

echo "<div>"
echo "<div class='panel-header'>Reading Order <span id='selectedCount' style='font-weight:400;'>0</span> books</div>"
echo "<div id='selectedBooks' class='selected-list'>"
echo "<div class='empty-state'>Click books from the right to add them</div>"
echo "</div>"
echo "<br>"
echo "<button class='btn btn-primary' onclick='createSeries()' style='width:100%;padding:12px;font-size:15px;'>Create Series</button>"
echo "</div>"

echo "<div>"
echo "<div class='panel-header'>Available Books</div>"
echo "<input type='text' id='bookFilter' class='input-field input-small' placeholder='Filter...' oninput='filterBooks()'>"
echo "<div class='avail-list'>"

sqlite3 "$DB" "SELECT p_cdeKey || '	' || p_titles_0_nominal FROM Entries WHERE p_type='Entry:Item' AND p_isVisibleInHome=1 AND p_location LIKE '/mnt/us/documents/%' ORDER BY p_titles_0_nominal;" | while IFS='	' read -r KEY TITLE; do
    SAFE_KEY=$(echo "$KEY" | sed "s/'/\&#39;/g;s/\"/\&quot;/g")
    SAFE_TITLE=$(echo "$TITLE" | sed "s/'/\&#39;/g;s/\"/\&quot;/g;s/</\&lt;/g;s/>/\&gt;/g")
    echo "<div class='avail-book' data-key='$SAFE_KEY' data-title='$SAFE_TITLE' onclick='addBook(this)'>$SAFE_TITLE</div>"
done

echo "</div>"
echo "</div>"

echo "</div>"
echo "</div>"
