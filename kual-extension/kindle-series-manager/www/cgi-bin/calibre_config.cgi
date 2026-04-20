#!/bin/sh
echo "Content-Type: application/json"
echo ""

CONF="/mnt/us/extensions/kindle-series-manager/calibre.conf"

json_escape() {
    echo "$1" | sed 's/\\/\\\\/g;s/"/\\"/g'
}

if [ "$REQUEST_METHOD" = "POST" ]; then
    read -r POST_BODY
    URL=""
    OLDIFS="$IFS"
    IFS='&'
    for PARAM in $POST_BODY; do
        PKEY=$(echo "$PARAM" | cut -d'=' -f1)
        PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
        case "$PKEY" in
            url) URL=$(printf '%b' "$(echo "$PVAL" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')") ;;
        esac
    done
    IFS="$OLDIFS"

    URL=$(echo "$URL" | sed 's|/$||')
    echo "$URL" > "$CONF"
    printf '{"status":"ok","url":"%s"}' "$(json_escape "$URL")"
else
    if [ -f "$CONF" ]; then
        SAVED=$(cat "$CONF" | tr -d '\r\n')
        printf '{"url":"%s"}' "$(json_escape "$SAVED")"
    else
        printf '{"url":""}'
    fi
fi
