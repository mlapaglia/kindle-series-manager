#!/bin/sh
#
# Watch a "dropbox" folder and move completed files to documents.
# Skips files that are still being written by another process.
#

WATCH_DIR="/mnt/us/documents/Downloads/Items01"
DEST_DIR="/mnt/us/dumps"
INTERVAL=5
LOG="/mnt/us/extensions/kindle-series-manager/dropbox.log"

logit() {
    echo "[dropbox] $1"
}

mkdir -p "$WATCH_DIR" "$DEST_DIR"

logit "Started watching $WATCH_DIR -> $DEST_DIR"

should_skip() {
    case "$(basename "$1")" in
        *.kfx|voucher) return 1 ;;
    esac
    return 0
}

sync_tree() {
    local SRC="$1"
    local DST="$2"

    for ITEM in "$SRC"/*; do
        [ -e "$ITEM" ] || continue

        local NAME=$(basename "$ITEM")

        if [ -d "$ITEM" ]; then
            if [ ! -d "$DST/$NAME" ]; then
                mkdir -p "$DST/$NAME"
                logit "Created dir: $DST/$NAME"
            fi
            sync_tree "$ITEM" "$DST/$NAME"
        else
            should_skip "$NAME" && continue
            if [ ! -f "$DST/$NAME" ]; then
                logit "Copying: $NAME"
                if cp "$ITEM" "$DST/$NAME"; then
                    logit "Done: $NAME"
                else
                    logit "Failed: $NAME"
                fi
            fi
        fi
    done
}

while true; do
    sync_tree "$WATCH_DIR" "$DEST_DIR"
    sleep "$INTERVAL"
done
