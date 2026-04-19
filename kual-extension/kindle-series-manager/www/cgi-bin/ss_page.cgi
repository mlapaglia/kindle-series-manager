#!/bin/sh
echo "Content-Type: text/html"
echo ""

SS_DIR="/usr/share/blanket/screensaver"
DISABLED_DIR="/mnt/us/screensaver_disabled"

html_escape() {
    echo "$1" | sed 's/&/\&amp;/g;s/</\&lt;/g;s/>/\&gt;/g;s/"/\&quot;/g'
}

SERIAL=$(cat /proc/usid 2>/dev/null)

MODEL_NAME="Unknown"
SS_WIDTH=0
SS_HEIGHT=0

FIRST_CHAR=$(echo "$SERIAL" | cut -c1)
if [ "$FIRST_CHAR" = "G" ]; then
    DEVICE_CODE=$(echo "$SERIAL" | cut -c4-6)
else
    DEVICE_CODE=$(echo "$SERIAL" | cut -c3-4)
fi

case "$DEVICE_CODE" in
    01) MODEL_NAME="Kindle 1"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    02|03) MODEL_NAME="Kindle 2"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    04|05|09) MODEL_NAME="Kindle DX"; SS_WIDTH=824; SS_HEIGHT=1200 ;;
    06|08|0A) MODEL_NAME="Kindle Keyboard"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    0E|23) MODEL_NAME="Kindle 4"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    0F|10|11|12) MODEL_NAME="Kindle Touch"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    1B|1C|1D|1F|20|24) MODEL_NAME="Kindle PW1"; SS_WIDTH=758; SS_HEIGHT=1024 ;;
    5A|D4|D5|D6|D7|D8|F2|17|5F|60|61|62|F4|F9) MODEL_NAME="Kindle PW2"; SS_WIDTH=1072; SS_HEIGHT=1448 ;;
    13|54|2A|4F|52|53) MODEL_NAME="Kindle Voyage"; SS_WIDTH=1072; SS_HEIGHT=1448 ;;
    C6|DD) MODEL_NAME="Kindle Basic (7th gen)"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    0G1|0G2|0G4|0G5|0G6|0G7|0KB|0KC|0KD|0KE|0KF|0KG|0LK|0LL|TTT) MODEL_NAME="Kindle PW3"; SS_WIDTH=1072; SS_HEIGHT=1448 ;;
    0GC|0GD|0GR|0GS|0GT|0GU) MODEL_NAME="Kindle Oasis"; SS_WIDTH=1072; SS_HEIGHT=1448 ;;
    0DU|0K9|0KA) MODEL_NAME="Kindle Basic 2"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    0LM|0LN|0LP|0LQ|0P1|0P2|0P6|0P7|0P8|0S1|0S2|0S3|0S4|0S7|0SA) MODEL_NAME="Kindle Oasis 2"; SS_WIDTH=1264; SS_HEIGHT=1680 ;;
    0PP|0T1|0T2|0T3|0T4|0T5|0T6|0T7|0TJ|0TK|0TL|0TM|0TN|102|103|16Q|16R|16S|16T|16U|16V|0PL) MODEL_NAME="Kindle PW4"; SS_WIDTH=1072; SS_HEIGHT=1448 ;;
    10L|0WF|0WG|0WH|0WJ|0VB) MODEL_NAME="Kindle Basic 3"; SS_WIDTH=600; SS_HEIGHT=800 ;;
    11L|0WQ|0WP|0WN|0WM|0WL) MODEL_NAME="Kindle Oasis 3"; SS_WIDTH=1264; SS_HEIGHT=1680 ;;
    1LG|1Q0|1PX|1VD|219|21A|2BH|2BJ|2DK) MODEL_NAME="Kindle PW5"; SS_WIDTH=1236; SS_HEIGHT=1648 ;;
    22D|25T|23A|2AQ|2AP|1XH|22C) MODEL_NAME="Kindle (11th gen)"; SS_WIDTH=1072; SS_HEIGHT=1448 ;;
    27J|2BL|263|227|2BM|23L|23M|270) MODEL_NAME="Kindle Scribe"; SS_WIDTH=1860; SS_HEIGHT=2480 ;;
    3L5|3L6|3L4|3L3|A89|3L2|3KM) MODEL_NAME="Kindle (2024)"; SS_WIDTH=1072; SS_HEIGHT=1448 ;;
    349|346|33X|33W|3HA|3H5|3H3|3H8|3J5|3JS) MODEL_NAME="Kindle PW6 (12th gen)"; SS_WIDTH=1264; SS_HEIGHT=1680 ;;
    3V0|3V1|3X5|3UV|3X4|3X3|41E|41D) MODEL_NAME="Kindle Scribe 2"; SS_WIDTH=1860; SS_HEIGHT=2480 ;;
    3H9|3H4|3HB|3H6|3H2|34X|3H7|3JT|3J6|456|455|4EP) MODEL_NAME="Kindle Colorsoft"; SS_WIDTH=1264; SS_HEIGHT=1680 ;;
    4PG|4PE|4PL|4F8|4FA|454) MODEL_NAME="Kindle Scribe 3"; SS_WIDTH=1860; SS_HEIGHT=2480 ;;
    4VX|4PF|4PH|4F9|4FB|46P) MODEL_NAME="Kindle Scribe Colorsoft"; SS_WIDTH=1860; SS_HEIGHT=2480 ;;
esac

echo "<div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Device Info</span></div>"
FBINK_SS_PIDFILE="/tmp/fbink_ss_daemon.pid"
if [ -f "$FBINK_SS_PIDFILE" ] && kill -0 "$(cat "$FBINK_SS_PIDFILE")" 2>/dev/null; then
    FBINK_SS_STATUS="running"
else
    FBINK_SS_STATUS="stopped"
fi

if [ "$SS_WIDTH" != "0" ]; then
    echo "<div style='font-size:14px;margin-bottom:4px;'>Model: <strong>$(html_escape "$MODEL_NAME")</strong></div>"
    echo "<div style='font-size:14px;margin-bottom:4px;'>Screen: <strong>${SS_WIDTH}x${SS_HEIGHT}</strong></div>"
    echo "<div style='font-size:14px;margin-bottom:8px;'>FBInk Screensaver: <strong>"
    if [ "$FBINK_SS_STATUS" = "running" ]; then
        echo "<span style='color:#27ae60;'>Enabled</span>"
    else
        echo "<span style='color:var(--fg-muted);'>Disabled</span>"
    fi
    echo "</strong> <span style='font-size:12px;color:var(--fg-fainter);'>(toggle in KUAL)</span></div>"
else
    echo "<div style='font-size:14px;margin-bottom:8px;color:var(--danger);'>Could not detect model (serial: $(html_escape "$SERIAL"))</div>"
    echo "<div class='panel-header'>Select your model</div>"
    echo "<select id='ssModelSelect' class='input-field input-small' onchange='ssModelChanged(this)' style='max-width:400px;'>"
    echo "<option value='600x800'>Kindle Basic (600x800)</option>"
    echo "<option value='758x1024'>Kindle PW1 (758x1024)</option>"
    echo "<option value='1072x1448' selected>Kindle PW2-4 / Voyage / Oasis 1 / Kindle 11th (1072x1448)</option>"
    echo "<option value='1236x1648'>Kindle PW5 (1236x1648)</option>"
    echo "<option value='1264x1680'>Kindle PW 12th / Oasis 2-3 / Colorsoft (1264x1680)</option>"
    echo "<option value='1860x2480'>Kindle Scribe (1860x2480)</option>"
    echo "</select>"
fi
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Upload Screensaver</span></div>"
echo "<div id='ssDropZone' data-width='$SS_WIDTH' data-height='$SS_HEIGHT' style='border:2px dashed var(--input-border);border-radius:8px;padding:32px 16px;text-align:center;color:var(--fg-fainter);font-size:14px;cursor:pointer;transition:border-color 0.15s;'>"
echo "Drag and drop an image here, or click to select"
echo "<input type='file' id='ssFileInput' accept='image/*' style='display:none;'>"
echo "</div>"
echo "<div id='ssUploadStatus' style='margin-top:8px;font-size:13px;color:var(--fg-muted);'></div>"
echo "<div id='ssPreview' style='margin-top:8px;display:none;'></div>"
echo "</div>"

CACHE_BUST=$(date +%s)

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Active Screensavers</span></div>"
echo "<div id='ssActiveGrid' style='display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;'>"
if [ -d "$SS_DIR" ]; then
    for IMG in "$SS_DIR"/bg_ss*.png; do
        [ -f "$IMG" ] || continue
        FNAME=$(basename "$IMG")
        SAFE_FNAME=$(html_escape "$FNAME")
        echo "<div style='text-align:center;'>"
        echo "<img src='/cgi-bin/ss_thumb.cgi?src=active&name=$SAFE_FNAME&t=$CACHE_BUST' style='width:100%;border-radius:4px;border:1px solid var(--border);' alt='$SAFE_FNAME'>"
        echo "<div style='font-size:11px;color:var(--fg-muted);margin:4px 0;'>$SAFE_FNAME</div>"
        echo "<div style='display:flex;gap:4px;justify-content:center;'>"
        echo "<button class='btn' style='font-size:11px;padding:2px 8px;' onclick=\"ssDisable('$SAFE_FNAME')\">Disable</button>"
        echo "<button class='btn btn-danger' style='font-size:11px;padding:2px 8px;' onclick=\"ssDelete('active','$SAFE_FNAME')\">Delete</button>"
        echo "</div>"
        echo "</div>"
    done
    ACTIVE_COUNT=$(ls "$SS_DIR"/bg_ss*.png 2>/dev/null | wc -l)
    if [ "$ACTIVE_COUNT" -eq 0 ]; then
        echo "<div style='grid-column:1/-1;color:var(--fg-fainter);font-size:13px;text-align:center;padding:16px;'>No screensavers found</div>"
    fi
else
    echo "<div style='grid-column:1/-1;color:var(--fg-fainter);font-size:13px;text-align:center;padding:16px;'>Screensaver directory not found</div>"
fi
echo "</div>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Disabled Screensavers</span></div>"
echo "<div id='ssDisabledGrid' style='display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;'>"
if [ -d "$DISABLED_DIR" ]; then
    for IMG in "$DISABLED_DIR"/*.png; do
        [ -f "$IMG" ] || continue
        FNAME=$(basename "$IMG")
        SAFE_FNAME=$(html_escape "$FNAME")
        echo "<div style='text-align:center;'>"
        echo "<img src='/cgi-bin/ss_thumb.cgi?src=disabled&name=$SAFE_FNAME&t=$CACHE_BUST' style='width:100%;border-radius:4px;border:1px solid var(--border);opacity:0.5;' alt='$SAFE_FNAME'>"
        echo "<div style='font-size:11px;color:var(--fg-muted);margin:4px 0;'>$SAFE_FNAME</div>"
        echo "<div style='display:flex;gap:4px;justify-content:center;'>"
        echo "<button class='btn' style='font-size:11px;padding:2px 8px;' onclick=\"ssEnable('$SAFE_FNAME')\">Enable</button>"
        echo "<button class='btn btn-danger' style='font-size:11px;padding:2px 8px;' onclick=\"ssDelete('disabled','$SAFE_FNAME')\">Delete</button>"
        echo "</div>"
        echo "</div>"
    done
    DISABLED_COUNT=$(ls "$DISABLED_DIR"/*.png 2>/dev/null | wc -l)
    if [ "$DISABLED_COUNT" -eq 0 ]; then
        echo "<div style='grid-column:1/-1;color:var(--fg-fainter);font-size:13px;text-align:center;padding:16px;'>No disabled screensavers</div>"
    fi
else
    echo "<div style='grid-column:1/-1;color:var(--fg-fainter);font-size:13px;text-align:center;padding:16px;'>No disabled screensavers</div>"
fi
echo "</div>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Important Notes</span></div>"
echo "<ul style='font-size:13px;color:var(--fg-muted);margin:0;padding-left:20px;'>"
echo "<li><strong>Disable \"Show covers on lock screen\"</strong> in Kindle Settings &gt; Screen &amp; Brightness, otherwise custom screensavers won't appear.</li>"
echo "<li>Images must be <strong>8-bit grayscale PNG</strong> at the exact device resolution. The upload tool converts and resizes automatically.</li>"
echo "<li><strong>Ads/Special Offers</strong> must be removed first for custom screensavers to work.</li>"
echo "<li>Factory screensavers can be restored by re-enabling them from the Disabled section.</li>"
echo "</ul>"
echo "</div>"

echo "</div>"
