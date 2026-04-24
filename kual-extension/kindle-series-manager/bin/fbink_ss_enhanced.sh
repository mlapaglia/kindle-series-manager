#!/bin/sh
# Enhanced screensaver selection logic.
# Sourced by fbink_ss_daemon.sh to provide draw_screensaver().
# Requires: EXT_DIR, FBINK, SS_DIR, STATE_FILE already set by the daemon.
# FBInk handles JPEG/PNG display and scaling natively — no ImageMagick needed.

CONFIG="$EXT_DIR/ss_config.json"
DB="${DB:-/var/local/cc.db}"
COVERS_STATE="/tmp/fbink_ss_covers_last"

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
    sqlite3 "$DB" \
        "SELECT p_thumbnail FROM Entries WHERE p_type='Entry:Item' AND p_location IS NOT NULL AND p_thumbnail IS NOT NULL ORDER BY p_lastAccess DESC LIMIT 1;" \
        2>/dev/null
}

# Display an image via FBInk. Book covers are scaled to fit the screen;
# custom PNGs (already screen-sized) are displayed as-is.
# $1 = image path, $2 = "scale" to request fit-to-screen scaling
show_image() {
    IMG="$1"
    [ -z "$IMG" ] || [ ! -f "$IMG" ] && return 1
    if [ "$2" = "scale" ]; then
        # w=-2,h=-2: scale to largest size that fits screen, preserving aspect ratio
        $FBINK -c -g file="$IMG",w=-2,h=-2,halign=CENTER,valign=CENTER -f
    else
        $FBINK -g file="$IMG" -f
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

pick_next_cover() {
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
    echo "$COVERS" | sed -n "$((IDX + 1))p"
}

# Show a cover image (scaled to screen), falling back to a custom PNG.
show_cover_or_fallback() {
    THUMB="$1"
    if [ -n "$THUMB" ] && [ -f "$THUMB" ]; then
        show_image "$THUMB" scale && return 0
    fi
    # Fallback to custom screensaver
    IMG=$(pick_next_custom)
    [ -n "$IMG" ] && show_image "$IMG"
}

# Main draw function — overrides the daemon's built-in draw_screensaver.
draw_screensaver() {
    read_config

    case "$MODE" in
        custom)
            IMG=$(pick_next_custom)
            if [ -n "$IMG" ]; then
                show_image "$IMG"
                log "Showing custom: $IMG"
            else
                log "No screensaver images found in $SS_DIR"
            fi
            ;;
        bookcover)
            THUMB=$(get_current_book_cover)
            show_cover_or_fallback "$THUMB"
            log "Showing book cover: ${THUMB:-fallback}"
            ;;
        allcovers)
            THUMB=$(pick_next_cover)
            show_cover_or_fallback "$THUMB"
            log "Showing cover: ${THUMB:-fallback}"
            ;;
        mixed)
            ROLL=$((RANDOM % 100))
            if [ "$ROLL" -lt "$MIXED_RATIO" ]; then
                IMG=$(pick_next_custom)
                if [ -n "$IMG" ]; then
                    show_image "$IMG"
                    log "Showing custom (mixed): $IMG"
                fi
            else
                THUMB=$(pick_next_cover)
                show_cover_or_fallback "$THUMB"
                log "Showing cover (mixed): ${THUMB:-fallback}"
            fi
            ;;
        *)
            IMG=$(pick_next_custom)
            [ -n "$IMG" ] && show_image "$IMG"
            log "Showing custom (default): $IMG"
            ;;
    esac
}
