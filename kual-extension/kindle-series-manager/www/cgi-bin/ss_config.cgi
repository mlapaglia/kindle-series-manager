#!/bin/sh
EXT_DIR="/mnt/us/extensions/kindle-series-manager"
CONFIG="$EXT_DIR/ss_config.json"

if [ "$REQUEST_METHOD" = "POST" ]; then
    echo "Content-Type: text/plain"
    echo ""

    read -r POST_BODY

    MODE=$(echo "$POST_BODY" | sed -n 's/.*mode=\([^&]*\).*/\1/p')
    ORDER=$(echo "$POST_BODY" | sed -n 's/.*order=\([^&]*\).*/\1/p')
    MIXED_RATIO=$(echo "$POST_BODY" | sed -n 's/.*mixed_ratio=\([^&]*\).*/\1/p')

    # URL-decode (busybox compatible)
    MODE=$(echo "$MODE" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g' | xargs -0 printf "%b" 2>/dev/null || echo "$MODE")
    ORDER=$(echo "$ORDER" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g' | xargs -0 printf "%b" 2>/dev/null || echo "$ORDER")
    MIXED_RATIO=$(echo "$MIXED_RATIO" | sed 's/+/ /g;s/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g' | xargs -0 printf "%b" 2>/dev/null || echo "$MIXED_RATIO")

    # Validate mode
    case "$MODE" in
        custom|bookcover|allcovers|mixed) ;;
        *) echo "Error: invalid mode"; exit 0 ;;
    esac

    # Validate order
    case "$ORDER" in
        sequential|random) ;;
        *) echo "Error: invalid order"; exit 0 ;;
    esac

    # Validate mixed_ratio is integer 0-100
    case "$MIXED_RATIO" in
        ''|*[!0-9]*) echo "Error: invalid ratio"; exit 0 ;;
    esac
    if [ "$MIXED_RATIO" -lt 0 ] 2>/dev/null || [ "$MIXED_RATIO" -gt 100 ] 2>/dev/null; then
        echo "Error: ratio must be 0-100"
        exit 0
    fi

    # Write config
    cat > "$CONFIG" <<EOF
{"mode":"$MODE","order":"$ORDER","mixed_ratio":$MIXED_RATIO}
EOF

    echo "Settings saved"
else
    echo "Content-Type: application/json"
    echo ""

    if [ -f "$CONFIG" ]; then
        cat "$CONFIG"
    else
        echo '{"mode":"custom","order":"sequential","mixed_ratio":50}'
    fi
fi
