#!/bin/sh

FBINK="/mnt/us/libkh/bin/fbink"
PIDFILE="/tmp/fbink_ss_daemon.pid"
LOG="/mnt/base-us/extensions/kindle-series-manager/fbink_ss.log"
SS_DIR="/usr/share/blanket/screensaver"
STATE_FILE="/tmp/fbink_ss_last"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

echo $$ > "$PIDFILE"
log "=== FBInk screensaver daemon started (PID $$) ==="

draw_screensaver() {
    IMAGES=$(ls "$SS_DIR"/bg_ss*.png 2>/dev/null)
    if [ -z "$IMAGES" ]; then
        log "No screensaver images found in $SS_DIR"
        return
    fi

    COUNT=$(echo "$IMAGES" | wc -l)
    LAST=$(cat "$STATE_FILE" 2>/dev/null || echo "0")
    NEXT=$(( (LAST + 1) % COUNT ))
    echo "$NEXT" > "$STATE_FILE"

    IMG=$(echo "$IMAGES" | sed -n "$((NEXT + 1))p")
    log "Showing image $((NEXT + 1)) of $COUNT: $IMG"

    $FBINK -g file=$IMG -f
}

lipc-set-prop com.lab126.blanket unload screensaver
log "Unloaded screensaver module"

FIFO="/tmp/fbink_ss_events.fifo"
rm -f "$FIFO"
mkfifo "$FIFO"
exec 3<>"$FIFO"

lipc-wait-event -m com.lab126.powerd goingToScreenSaver >&3 2>/dev/null &
SLEEP_PID=$!

lipc-wait-event -m com.lab126.powerd outOfScreenSaver >&3 2>/dev/null &
WAKE_PID=$!

trap "kill $SLEEP_PID $WAKE_PID 2>/dev/null; exec 3>&-; exec 3<&-; rm -f \"$FIFO\" \"$PIDFILE\" \"$STATE_FILE\"; start pillow 2>/dev/null; lipc-set-prop com.lab126.blanket load screensaver; log 'Daemon stopped, pillow and screensaver restored'; exit 0" INT TERM

while read -r LINE <&3; do
    log "Event: $LINE"
    case "$LINE" in
        *goingToScreenSaver*)
            stop pillow 2>/dev/null
            draw_screensaver
            log "Wrote screensaver, pillow stopped"
            ;;
        *outOfScreenSaver*)
            start pillow 2>/dev/null
            $FBINK -k -f -W GC16
            DISPLAY=:0 xrefresh
            log "Woke up, pillow started, xrefresh sent"
            ;;
    esac
done
