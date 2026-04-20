#!/bin/sh
echo "Content-Type: application/json"
echo ""

CONF="/mnt/us/extensions/kindle-series-manager/calibre.conf"

json_escape() {
    echo "$1" | sed 's/\\/\\\\/g;s/"/\\"/g;s/	/ /g'
}

QS_URL=""
QS_SEARCH=""
QS_SORT="date"
QS_ORDER="descending"
QS_NUM="25"
QS_START="1"

OLDIFS="$IFS"
IFS='&'
for PARAM in $QUERY_STRING; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        url)    QS_URL=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        search) QS_SEARCH=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        sort)   QS_SORT="$PVAL" ;;
        order)  QS_ORDER="$PVAL" ;;
        num)    QS_NUM="$PVAL" ;;
        start)  QS_START="$PVAL" ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$QS_URL" ] && [ -f "$CONF" ]; then
    QS_URL=$(tr -d '\r\n' < "$CONF")
fi

if [ -z "$QS_URL" ]; then
    printf '{"error":"No Calibre URL configured"}'
    exit 0
fi

QS_URL=$(echo "$QS_URL" | sed 's|/$||')

FETCH_URL="${QS_URL}/mobile?num=${QS_NUM}&start=${QS_START}&sort=${QS_SORT}&order=${QS_ORDER}&search=$(echo "$QS_SEARCH" | sed 's/ /+/g')"

HTML=$(wget -q -O - --timeout=10 "$FETCH_URL" 2>/dev/null)
if [ -z "$HTML" ]; then
    printf '{"error":"Failed to reach Calibre at %s"}' "$(json_escape "$QS_URL")"
    exit 0
fi

TOTAL=$(echo "$HTML" | sed -n 's/.*Books [0-9]* to [0-9]* of \([0-9]*\).*/\1/p' | head -1)
RANGE_START=$(echo "$HTML" | sed -n 's/.*Books \([0-9]*\) to [0-9]* of [0-9]*.*/\1/p' | head -1)
RANGE_END=$(echo "$HTML" | sed -n 's/.*Books [0-9]* to \([0-9]*\) of [0-9]*.*/\1/p' | head -1)

LIBRARY_ID=$(echo "$HTML" | sed -n 's/.*library_id" .*value="\([^"]*\)".*/\1/p' | head -1)

if [ -z "$TOTAL" ]; then
    TOTAL=0
    RANGE_START=0
    RANGE_END=0
fi

printf '{"total":%s,"start":%s,"end":%s,"num":%s,"library_id":"%s","calibre_url":"%s","books":[' \
    "$TOTAL" "${RANGE_START:-0}" "${RANGE_END:-0}" "$QS_NUM" \
    "$(json_escape "$LIBRARY_ID")" "$(json_escape "$QS_URL")"

echo "$HTML" | awk '
BEGIN { first=1 }
/<tr>/ { in_row=1; thumb=""; dl_url=""; dl_fmt=""; title=""; date="" }
in_row && /src="\/get\/thumb\// {
    match($0, /src="\/get\/thumb\/[^"]*/)
    thumb = substr($0, RSTART+5, RLENGTH-5)
}
in_row && /href="\/legacy\/get\// {
    match($0, /href="\/legacy\/get\/[^"]*/)
    dl_url = substr($0, RSTART+6, RLENGTH-6)
    match($0, /\/legacy\/get\/[^\/]*/)
    dl_fmt = substr($0, RSTART+12, RLENGTH-12)
}
in_row && /class="first-line"/ {
    gsub(/.*class="first-line">/, "")
    gsub(/<\/span>.*/, "")
    gsub(/\\/, "\\\\")
    gsub(/"/, "\\\"")
    title = $0
}
in_row && /class="second-line"/ {
    gsub(/.*class="second-line">/, "")
    gsub(/<\/span>.*/, "")
    gsub(/^[ \t]+/, "")
    gsub(/[ \t]+$/, "")
    gsub(/\\/, "\\\\")
    gsub(/"/, "\\\"")
    date = $0
}
/<\/tr>/ {
    if (in_row && title != "") {
        if (!first) printf ","
        printf "{\"title\":\"%s\",\"date\":\"%s\",\"format\":\"%s\",\"download\":\"%s\",\"thumb\":\"%s\"}", title, date, dl_fmt, dl_url, thumb
        first=0
    }
    in_row=0
}
'

printf ']}'
