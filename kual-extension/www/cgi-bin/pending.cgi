#!/bin/sh
echo "Content-Type: text/html"
echo ""

DB="/var/local/cc.db"
PENDING="/mnt/base-us/extensions/kindle-series-manager/pending.txt"

if [ ! -f "$PENDING" ]; then
    echo "<div class='empty-state'>No pending.txt found. Use the Calibre plugin to generate one.</div>"
    exit 0
fi

CURRENT_SERIES=""

while IFS='	' read -r RTYPE FIELD1 FIELD2; do
    case "$RTYPE" in
        SERIES)
            if [ -n "$CURRENT_SERIES" ]; then
                echo "</div></div>"
            fi
            CURRENT_SERIES="$FIELD1"
            ASIN="$FIELD2"
            echo "<div class='card'>"
            echo "<div class='card-header'>"
            if [ -n "$ASIN" ]; then
                echo "<div><span class='card-title'>$CURRENT_SERIES</span> <span class='card-subtitle'>ASIN: $ASIN</span></div>"
            else
                echo "<div><span class='card-title'>$CURRENT_SERIES</span></div>"
            fi
            echo "</div>"
            echo "<div>"
            ;;
        BOOK)
            TITLE="$FIELD1"
            INDEX="$FIELD2"
            ESC_TITLE=$(echo "$TITLE" | sed "s/'/''/g")
            POS=$(echo "$INDEX" | awk '{printf "%d", $1}')

            CDE_KEY=$(sqlite3 "$DB" "SELECT p_cdeKey FROM Entries WHERE p_type='Entry:Item' AND p_titles_0_nominal LIKE '%${ESC_TITLE}%' AND p_isVisibleInHome=1 LIMIT 1;")

            if [ -n "$CDE_KEY" ]; then
                DB_TITLE=$(sqlite3 "$DB" "SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey='$CDE_KEY' AND p_type='Entry:Item' LIMIT 1;")
                echo "<div class='book-item'><span class='book-num'>$POS</span>$DB_TITLE</div>"
            else
                echo "<div class='book-item' style='color:#c0392b;'><span class='book-num' style='background:#fde8e8;color:#c0392b;'>!</span>Not found: $TITLE</div>"
            fi
            ;;
    esac
done < "$PENDING"

if [ -n "$CURRENT_SERIES" ]; then
    echo "</div></div>"
fi
