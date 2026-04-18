#!/bin/sh
echo "Content-Type: application/json"
echo ""

DOC_DIR="/mnt/us/documents"
FIRST=1

printf '['
for DIR in "$DOC_DIR"/*/; do
    [ -d "$DIR" ] || continue
    NAME=$(basename "$DIR")
    case "$NAME" in
        .*|*.sdr) continue ;;
    esac
    if [ "$FIRST" = "1" ]; then
        FIRST=0
    else
        printf ','
    fi
    ENAME=$(echo "$NAME" | sed 's/\\/\\\\/g;s/"/\\"/g')
    printf '"%s"' "$ENAME"
done
printf ']'
