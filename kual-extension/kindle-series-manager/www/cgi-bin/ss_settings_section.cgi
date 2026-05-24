#!/bin/sh
echo "Content-Type: text/html"
echo ""

cat <<'HTML'
<div class="card">
  <div class="card-header"><span class="card-title">Screensaver Mode</span></div>
  <div style="margin-bottom:12px;">
    <label style="display:block;padding:6px 0;cursor:pointer;">
      <input type="radio" name="ssMode" value="custom" checked onchange="ssUpdateModeUI()"> Custom Images Only
    </label>
    <label style="display:block;padding:6px 0;cursor:pointer;">
      <input type="radio" name="ssMode" value="bookcover" onchange="ssUpdateModeUI()"> Current Book Cover
    </label>
    <label style="display:block;padding:6px 0;cursor:pointer;">
      <input type="radio" name="ssMode" value="allcovers" onchange="ssUpdateModeUI()"> All Book Covers
    </label>
    <label style="display:block;padding:6px 0;cursor:pointer;">
      <input type="radio" name="ssMode" value="mixed" onchange="ssUpdateModeUI()"> Mixed (Custom + Book Covers)
    </label>
  </div>
  <div id="ssMixedRatioSection" style="display:none;margin-bottom:12px;">
    <div style="font-size:13px;color:var(--fg-muted);margin-bottom:4px;">Custom Image Ratio: <span id="ssMixedRatioLabel">50</span>%</div>
    <input type="range" id="ssMixedRatio" min="0" max="100" value="50" style="width:100%;" oninput="document.getElementById('ssMixedRatioLabel').textContent=this.value">
  </div>
  <div style="margin-bottom:12px;">
    <div class="panel-header">Display Order</div>
    <label style="display:inline-block;margin-right:16px;cursor:pointer;">
      <input type="radio" name="ssOrder" value="sequential" checked> Sequential
    </label>
    <label style="cursor:pointer;">
      <input type="radio" name="ssOrder" value="random"> Random
    </label>
  </div>
  <button class="btn btn-primary" onclick="ssSaveSettings()">Save Settings</button>
  <span id="ssSettingsStatus" style="font-size:13px;color:var(--fg-muted);margin-left:8px;"></span>
</div>
HTML
