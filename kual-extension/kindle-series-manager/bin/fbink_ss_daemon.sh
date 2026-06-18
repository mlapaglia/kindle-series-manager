#!/bin/sh

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
SS_SHIELD="$EXT_DIR/bin/ss_shield"

# Pick the bundled FBInk for this device's ABI...
if [ -f /lib/ld-linux-armhf.so.3 ]; then
    BUNDLED_FBINK="$EXT_DIR/bin/fbink_hf"
elif grep -q 'v[7-9]' /proc/cpuinfo 2>/dev/null; then
    BUNDLED_FBINK="$EXT_DIR/bin/fbink_sf"
else
    BUNDLED_FBINK="$EXT_DIR/bin/fbink_k5"
fi

# ...but a usable FBInk MUST exist AND support image display. A missing
# bundled binary (or a build with "Image support is disabled") means the
# screensaver image never gets drawn and the stock screensaver shows
# instead. Probe candidates and fall back to any system FBInk that works.
fbink_ok() {
    [ -x "$1" ] || return 1
    "$1" -g file=/proc/ksm_probe_missing -f 2>&1 | grep -q "Image support is disabled" && return 1
    return 0
}
FBINK=""
for _c in "$BUNDLED_FBINK" \
          /mnt/us/libkh/bin/fbink \
          /mnt/us/extensions/MRInstaller/bin/KHF/fbink \
          /usr/bin/fbink \
          /mnt/us/koreader/fbink; do
    if fbink_ok "$_c"; then FBINK="$_c"; break; fi
done
[ -z "$FBINK" ] && FBINK="$BUNDLED_FBINK"

PIDFILE="/tmp/fbink_ss_daemon.pid"
SHIELD_PIDFILE="/tmp/ss_shield.pid"
LOG="$EXT_DIR/fbink_ss.log"
SS_DIR="$EXT_DIR/screensavers"
STATE_FILE="/tmp/fbink_ss_last"

mkdir -p "$SS_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

shield_up() {
    DISPLAY=:0 "$SS_SHIELD" >> "$LOG" 2>&1 &
    echo $! > "$SHIELD_PIDFILE"
    log "Shield window up (PID $!)"
}

shield_down() {
    if [ -f "$SHIELD_PIDFILE" ]; then
        kill "$(cat "$SHIELD_PIDFILE")" 2>/dev/null
        rm -f "$SHIELD_PIDFILE"
        log "Shield window down"
    fi
}

echo $$ > "$PIDFILE"
log "=== FBInk screensaver daemon started (PID $$) ==="
log "Using FBInk: ${FBINK:-<none found!>}"

chmod +x "$SS_SHIELD" "$EXT_DIR/bin/fbink_hf" "$EXT_DIR/bin/fbink_sf" "$EXT_DIR/bin/fbink_k5" 2>/dev/null
lipc-set-prop com.lab126.blanket unload screensaver
lipc-set-prop com.lab126.blanket unload ad_screensaver
log "Unloaded screensaver module"

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

    $FBINK -g file=$IMG -f >> "$LOG" 2>&1
    log "FBInk draw rc=$?"
}

FIFO="/tmp/fbink_ss_events.fifo"
rm -f "$FIFO"
mkfifo "$FIFO"
exec 3<>"$FIFO"

lipc-wait-event -m com.lab126.powerd goingToScreenSaver >&3 2>/dev/null &
SLEEP_PID=$!

lipc-wait-event -m com.lab126.powerd outOfScreenSaver >&3 2>/dev/null &
WAKE_PID=$!

# shellcheck disable=SC2064
trap "kill $SLEEP_PID $WAKE_PID 2>/dev/null; shield_down; exec 3>&-; exec 3<&-; rm -f \"$FIFO\" \"$PIDFILE\" \"$STATE_FILE\"; lipc-set-prop com.lab126.blanket load screensaver; lipc-set-prop com.lab126.blanket load ad_screensaver; log 'Daemon stopped, screensaver restored'; exit 0" INT TERM

while read -r LINE <&3; do
    log "Event: $LINE"
    case "$LINE" in
        *goingToScreenSaver*)
            shield_up;
            draw_screensaver
            log "Wrote screensaver with shield"
            ;;
        *outOfScreenSaver*)
            shield_down
            $FBINK -k -f -W GC16
            DISPLAY=:0 xrefresh
            log "Woke up, shield down, xrefresh sent"
            ;;
    esac
done
