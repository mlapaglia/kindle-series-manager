#!/bin/sh
echo "Content-Type: text/html"
echo ""

EXT_DIR="/mnt/us/extensions/kindle-series-manager"
FONTS_DIR="$EXT_DIR/fonts"
DISABLED_DIR="$EXT_DIR/fonts-disabled"
SYSTEM_FONTS_DIR="/mnt/us/fonts"
mkdir -p "$FONTS_DIR" "$DISABLED_DIR" "$SYSTEM_FONTS_DIR"

html_escape() {
    echo "$1" | sed 's/&/\&amp;/g;s/</\&lt;/g;s/>/\&gt;/g;s/"/\&quot;/g'
}

format_size() {
    SIZE=$1
    if [ "$SIZE" -ge 1048576 ] 2>/dev/null; then
        echo "$((SIZE / 1048576)).$((SIZE % 1048576 * 10 / 1048576)) MB"
    elif [ "$SIZE" -ge 1024 ] 2>/dev/null; then
        echo "$((SIZE / 1024)).$((SIZE % 1024 * 10 / 1024)) KB"
    else
        echo "${SIZE} B"
    fi
}

echo "<div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Upload Font</span></div>"
echo "<div id='fontDropZone' style='border:2px dashed var(--input-border);border-radius:8px;padding:32px 16px;text-align:center;color:var(--fg-fainter);font-size:14px;cursor:pointer;transition:border-color 0.15s;'>"
echo "Drag and drop a font file here, or click to select"
echo "<input type='file' id='fontFileInput' accept='.ttf,.otf,.ttc' style='display:none;'>"
echo "</div>"
echo "<div id='fontUploadStatus' style='margin-top:8px;font-size:13px;color:var(--fg-muted);'></div>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Active Fonts</span></div>"
echo "<div id='fontActiveGrid' style='display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;'>"
ACTIVE_COUNT=0
for FONT in "$FONTS_DIR"/*.ttf "$FONTS_DIR"/*.otf "$FONTS_DIR"/*.ttc "$FONTS_DIR"/*.TTF "$FONTS_DIR"/*.OTF "$FONTS_DIR"/*.TTC; do
    [ -f "$FONT" ] || continue
    FNAME=$(basename "$FONT")
    SAFE_FNAME=$(html_escape "$FNAME")
    FSIZE=$(wc -c < "$FONT" 2>/dev/null || echo "0")
    FSIZE_FMT=$(format_size "$FSIZE")
    ACTIVE_COUNT=$((ACTIVE_COUNT + 1))
    echo "<div style='padding:8px;border:1px solid var(--border);border-radius:6px;'>"
    echo "<div style='font-size:13px;font-weight:bold;word-break:break-all;'>$SAFE_FNAME</div>"
    echo "<div style='font-size:11px;color:var(--fg-muted);margin:4px 0;'>$FSIZE_FMT</div>"
    echo "<div style='display:flex;gap:4px;'>"
    echo "<button class='btn' style='font-size:11px;padding:2px 8px;' onclick=\"fontDisable('$SAFE_FNAME')\">Disable</button>"
    echo "<button class='btn btn-danger' style='font-size:11px;padding:2px 8px;' onclick=\"fontDelete('active','$SAFE_FNAME')\">Delete</button>"
    echo "</div>"
    echo "</div>"
done
if [ "$ACTIVE_COUNT" -eq 0 ]; then
    echo "<div style='grid-column:1/-1;color:var(--fg-fainter);font-size:13px;text-align:center;padding:16px;'>No active fonts</div>"
fi
echo "</div>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>Disabled Fonts</span></div>"
echo "<div id='fontDisabledGrid' style='display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;'>"
DISABLED_COUNT=0
for FONT in "$DISABLED_DIR"/*.ttf "$DISABLED_DIR"/*.otf "$DISABLED_DIR"/*.ttc "$DISABLED_DIR"/*.TTF "$DISABLED_DIR"/*.OTF "$DISABLED_DIR"/*.TTC; do
    [ -f "$FONT" ] || continue
    FNAME=$(basename "$FONT")
    SAFE_FNAME=$(html_escape "$FNAME")
    FSIZE=$(wc -c < "$FONT" 2>/dev/null || echo "0")
    FSIZE_FMT=$(format_size "$FSIZE")
    DISABLED_COUNT=$((DISABLED_COUNT + 1))
    echo "<div style='padding:8px;border:1px solid var(--border);border-radius:6px;opacity:0.6;'>"
    echo "<div style='font-size:13px;font-weight:bold;word-break:break-all;'>$SAFE_FNAME</div>"
    echo "<div style='font-size:11px;color:var(--fg-muted);margin:4px 0;'>$FSIZE_FMT</div>"
    echo "<div style='display:flex;gap:4px;'>"
    echo "<button class='btn' style='font-size:11px;padding:2px 8px;' onclick=\"fontEnable('$SAFE_FNAME')\">Enable</button>"
    echo "<button class='btn btn-danger' style='font-size:11px;padding:2px 8px;' onclick=\"fontDelete('disabled','$SAFE_FNAME')\">Delete</button>"
    echo "</div>"
    echo "</div>"
done
if [ "$DISABLED_COUNT" -eq 0 ]; then
    echo "<div style='grid-column:1/-1;color:var(--fg-fainter);font-size:13px;text-align:center;padding:16px;'>No disabled fonts</div>"
fi
echo "</div>"
echo "</div>"

echo "<div class='card'>"
echo "<div class='card-header'><span class='card-title'>How It Works</span></div>"
echo "<ul style='font-size:13px;color:var(--fg-muted);margin:0;padding-left:20px;'>"
echo "<li>Upload <strong>TTF</strong>, <strong>OTF</strong>, or <strong>TTC</strong> font files (max 100MB each).</li>"
echo "<li>Enabled fonts are symlinked to <code>/mnt/us/fonts/</code> where Kindle picks them up automatically.</li>"
echo "<li>Disable a font to remove it from Kindle without deleting the file.</li>"
echo "<li>Bad fonts won't cause bootloops — they simply fail to render.</li>"
echo "</ul>"
echo "</div>"

echo "</div>"
