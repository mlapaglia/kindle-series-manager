#!/bin/sh
# Enhanced screensaver selection logic.
# Sourced by fbink_ss_daemon.sh to provide select_screensaver_image().
# Requires: EXT_DIR, FBINK, SS_DIR, STATE_FILE already set by the daemon.

CONFIG="$EXT_DIR/ss_config.json"
DB="${DB:-/var/local/cc.db}"
COVERS_CACHE="/tmp/book_covers"
COVERS_STATE="/tmp/fbink_ss_covers_last"

mkdir -p "$COVERS_CACHE"

# Detect device screen dimensions for cover conversion.
# Re-use the daemon's SS_DIR parent for EXT_DIR.
_ss_detect_resolution() {
    SERIAL=$(cat /proc/usid 2>/dev/null)
    FIRST_CHAR=$(echo "$SERIAL" | cut -c1)
    if [ "$FIRST_CHAR" = "G" ]; then
        DCODE=$(echo "$SERIAL" | cut -c4-6)
    else
        DCODE=$(echo "$SERIAL" | cut -c3-4)
    fi
    # Default PW2 resolution
    TARGET_W=1072
    TARGET_H=1448
    case "$DCODE" in
        01|02|03|06|08|0A|0E|23|0F|10|11|12|C6|DD|0DU|0K9|0KA|10L|0WF|0WG|0WH|0WJ|0VB)
            TARGET_W=600; TARGET_H=800 ;;
        1B|1C|1D|1F|20|24)
            TARGET_W=758; TARGET_H=1024 ;;
        1LG|1Q0|1PX|1VD|219|21A|2BH|2BJ|2DK)
            TARGET_W=1236; TARGET_H=1648 ;;
        0LM|0LN|0LP|0LQ|0P1|0P2|0P6|0P7|0P8|0S1|0S2|0S3|0S4|0S7|0SA|11L|0WQ|0WP|0WN|0WM|0WL|349|346|33X|33W|3HA|3H5|3H3|3H8|3J5|3JS|3H9|3H4|3HB|3H6|3H2|34X|3H7|3JT|3J6|456|455|4EP)
            TARGET_W=1264; TARGET_H=1680 ;;
        27J|2BL|263|227|2BM|23L|23M|270|3V0|3V1|3X5|3UV|3X4|3X3|41E|41D|4PG|4PE|4PL|4F8|4FA|454|4VX|4PF|4PH|4F9|4FB|46P)
            TARGET_W=1860; TARGET_H=2480 ;;
    esac
}

_ss_detect_resolution

read_config() {
    if [ -f "$CONFIG" ]; then
        MODE=$(grep '"mode"' "$CONFIG" | sed 's/.*"mode"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
        ORDER=$(grep '"order"' "$CONFIG" | sed 's/.*"order"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
        MIXED_RATIO=$(grep '"mixed_ratio"' "$CONFIG" | sed 's/.*"mixed_ratio"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/')
    fi
    MODE=${MODE:-custom}
    ORDER=${ORDER:-sequential}
    MIXED_RATIO=${MIXED_RATIO:-50}
}

get_current_book_cover() {
    THUMB=$(sqlite3 "$DB" \
        "SELECT p_thumbnail FROM Entries WHERE p_type='Entry:Item' AND p_location IS NOT NULL AND p_thumbnail IS NOT NULL ORDER BY p_lastAccess DESC LIMIT 1;" \
        2>/dev/null)
    echo "$THUMB"
}

prepare_cover_image() {
    JPEG="$1"
    [ -z "$JPEG" ] && return
    [ -f "$JPEG" ] || return

    HASH=$(md5sum "$JPEG" 2>/dev/null | cut -d' ' -f1)
    [ -z "$HASH" ] && HASH=$(basename "$JPEG" .jpg)
    OUTFILE="$COVERS_CACHE/${HASH}_${TARGET_W}x${TARGET_H}.png"

    # Use cached version if source hasn't changed
    if [ -f "$OUTFILE" ] && [ "$OUTFILE" -nt "$JPEG" ]; then
        echo "$OUTFILE"
        return
    fi

    # Try convert (ImageMagick)
    if command -v convert >/dev/null 2>&1; then
        convert "$JPEG" -colorspace Gray -depth 8 \
            -resize "${TARGET_W}x${TARGET_H}^" \
            -gravity center -extent "${TARGET_W}x${TARGET_H}" \
            PNG8:"$OUTFILE" 2>/dev/null
    # Try ffmpeg
    elif command -v ffmpeg >/dev/null 2>&1; then
        ffmpeg -y -i "$JPEG" \
            -vf "scale=${TARGET_W}:${TARGET_H}:force_original_aspect_ratio=increase,crop=${TARGET_W}:${TARGET_H},format=gray" \
            "$OUTFILE" 2>/dev/null
    else
        # No converter available
        echo ""
        return
    fi

    if [ -f "$OUTFILE" ]; then
        echo "$OUTFILE"
    else
        echo ""
    fi
}

pick_next_custom() {
    IMAGES=$(ls "$SS_DIR"/bg_ss*.png 2>/dev/null)
    if [ -z "$IMAGES" ]; then echo ""; return; fi
    COUNT=$(echo "$IMAGES" | wc -l)

    if [ "$ORDER" = "random" ]; then
        IDX=$((RANDOM % COUNT))
    else
        LAST=$(cat "$STATE_FILE" 2>/dev/null || echo "0")
        IDX=$(( (LAST + 1) % COUNT ))
    fi
    echo "$IDX" > "$STATE_FILE"
    echo "$IMAGES" | sed -n "$((IDX + 1))p"
}

pick_next_allcovers() {
    COVERS=$(sqlite3 "$DB" \
        "SELECT p_thumbnail FROM Entries WHERE p_type='Entry:Item' AND p_location IS NOT NULL AND p_thumbnail IS NOT NULL ORDER BY p_titles_0_nominal;" \
        2>/dev/null)
    if [ -z "$COVERS" ]; then echo ""; return; fi
    COUNT=$(echo "$COVERS" | wc -l)

    if [ "$ORDER" = "random" ]; then
        IDX=$((RANDOM % COUNT))
    else
        LAST=$(cat "$COVERS_STATE" 2>/dev/null || echo "0")
        IDX=$(( (LAST + 1) % COUNT ))
    fi
    echo "$IDX" > "$COVERS_STATE"
    THUMB=$(echo "$COVERS" | sed -n "$((IDX + 1))p")
    prepare_cover_image "$THUMB"
}

# Main selection function — called by the daemon's draw_screensaver.
select_screensaver_image() {
    read_config

    case "$MODE" in
        custom)
            pick_next_custom
            ;;
        bookcover)
            THUMB=$(get_current_book_cover)
            if [ -n "$THUMB" ] && [ -f "$THUMB" ]; then
                IMG=$(prepare_cover_image "$THUMB")
                if [ -n "$IMG" ]; then echo "$IMG"; else pick_next_custom; fi
            else
                pick_next_custom
            fi
            ;;
        allcovers)
            IMG=$(pick_next_allcovers)
            if [ -n "$IMG" ]; then echo "$IMG"; else pick_next_custom; fi
            ;;
        mixed)
            ROLL=$((RANDOM % 100))
            if [ "$ROLL" -lt "$MIXED_RATIO" ]; then
                pick_next_custom
            else
                IMG=$(pick_next_allcovers)
                if [ -n "$IMG" ]; then echo "$IMG"; else pick_next_custom; fi
            fi
            ;;
        *)
            pick_next_custom
            ;;
    esac
}
