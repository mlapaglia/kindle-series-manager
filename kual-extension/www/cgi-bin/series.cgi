#!/bin/sh
echo "Content-Type: text/html"
echo ""

DB="/var/local/cc.db"

SERIES_IDS=$(sqlite3 "$DB" "SELECT DISTINCT d_seriesId FROM Series ORDER BY d_seriesId;")

if [ -z "$SERIES_IDS" ]; then
    echo "<div class='empty-state'>No series on device yet. Tap <b>Create Series</b> to get started.</div>"
    exit 0
fi

for SID in $SERIES_IDS; do
    S_KEY=$(echo "$SID" | sed 's/urn:collection:1:asin-//')
    TITLE=$(sqlite3 "$DB" "SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey='$S_KEY' AND p_type='Entry:Item:Series';")
    COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Series WHERE d_seriesId='$SID';")

    if [ -z "$TITLE" ]; then
        TITLE="$S_KEY"
    fi

    echo "<div class='card'>"
    echo "<div class='card-header'>"
    echo "<div><span class='card-title'>$TITLE</span> <span class='card-subtitle'>$COUNT books</span></div>"
    echo "<button class='btn btn-danger' onclick=\"removeSeries('$SID')\">Remove</button>"
    echo "</div>"

    sqlite3 "$DB" "SELECT '<div class=\"book-item\"><span class=\"book-num\">' || d_itemPositionLabel || '</span>' || COALESCE((SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey=d_itemCdeKey AND p_type='Entry:Item' LIMIT 1), '(unknown)') || '</div>' FROM Series WHERE d_seriesId='$SID' ORDER BY d_itemPosition;"

    echo "</div>"
done
