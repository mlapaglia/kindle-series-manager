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

SERIES_IDS=$(sqlite3 "$DB" "SELECT DISTINCT d_seriesId FROM Series ORDER BY d_seriesId;")

if [ -z "$SERIES_IDS" ]; then
    echo "<div class='empty-state'>No series on device yet. Tap <b>Create Series</b> to get started.</div>"
    exit 0
fi

for SID in $SERIES_IDS; do
    S_KEY=$(echo "$SID" | sed 's/urn:collection:1:asin-//')
    TITLE=$(sqlite3 "$DB" "SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey='$S_KEY' AND p_type='Entry:Item:Series';")
    COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_seriesId='$SID';")

    FIRST_KEY=$(sqlite3 "$DB" "SELECT d_itemCdeKey FROM Series WHERE d_seriesId='$SID' ORDER BY d_itemPosition LIMIT 1;")

    if [ -z "$TITLE" ]; then
        TITLE="$S_KEY"
    fi

    echo "<div class='card'>"
    echo "<div class='card-header'>"
    echo "<div><span class='card-title'>$TITLE</span> <span class='card-subtitle'>$COUNT books</span></div>"
    echo "<div style='display:flex;gap:8px;'><button class='btn btn-toggle' onclick='toggleCard(this)'>Show</button><button class='btn' onclick=\"editSeries('$SID')\">Edit</button><button class='btn btn-danger' onclick=\"removeSeries('$SID')\">Remove</button></div>"
    echo "</div>"

    echo "<div class='card-body' style='display:none;'>"
    echo "<div class='card-body-inner'>"
    if [ -n "$FIRST_KEY" ]; then
        echo "<img class='series-thumb' src='/cgi-bin/book_thumb.cgi?key=$FIRST_KEY' alt='' onerror='this.style.display=\"none\"'>"
    fi
    echo "<div class='series-books'>"
    sqlite3 "$DB" "SELECT '<div class=\"book-item\"><span class=\"book-num\">' || d_itemPositionLabel || '</span>' || COALESCE((SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey=d_itemCdeKey AND p_type='Entry:Item' LIMIT 1), '(unknown)') || '</div>' FROM Series WHERE d_seriesId='$SID' ORDER BY d_itemPosition;"
    echo "</div>"
    echo "</div>"
    echo "</div>"

    echo "</div>"
done
