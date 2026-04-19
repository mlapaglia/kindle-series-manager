# ss_shield

A tiny X11 utility for Kindle that creates a full-screen override-redirect window, preventing the system status bar from painting over FBInk's framebuffer content during custom screensaver mode.

## The problem

When the FBInk screensaver daemon draws to the Kindle's framebuffer, the system status bar (`JunoStatusBarDriver`) continues refreshing its X11 window on a timer. The clock updates every minute, the wifi icon updates when wifi disconnects (~30 seconds after sleep), and the battery indicator updates periodically. Because FBInk writes directly to the Linux framebuffer (`/dev/fb0`) underneath the X11 window stack, these status bar repaints overwrite portions of the custom screensaver image.

The stock screensaver avoids this by creating its window through `libblanket.so` at the `L:SS` (screensaver) layer — the highest Z-order in the Kindle's window manager. This blanket API is not accessible from shell scripts or standalone programs without linking against the proprietary library.

## How it works

`ss_shield` creates an **override-redirect** X11 window that covers the entire screen. Override-redirect is a core X11 attribute that tells the X server to bypass the window manager for window placement. The X server composites override-redirect windows on top of all managed windows, so the status bar's repaints happen behind the shield and never reach the visible display.

The daemon's sleep/wake flow:

1. **On sleep**: launch `ss_shield` (creates the shield window), then FBInk draws the screensaver image to the framebuffer underneath
2. **While sleeping**: the status bar repaints behind the shield — invisible to the user
3. **On wake**: kill `ss_shield` (removes the shield window), then `xrefresh` triggers the app to repaint

## Building

Requires Docker. The binary is cross-compiled as a static ARMv6 soft-float build, which runs on every Kindle with X11 (firmware 5.x) — ARMv6, ARMv7, and ARMv8 processors are all backwards compatible.

```sh
# From the repository root:
bash tools/ss_shield/build.sh

# Or manually:
cd tools/ss_shield
docker build -f Dockerfile.build -t ss_shield-build .
CONTAINER_ID=$(docker create ss_shield-build)
docker cp $CONTAINER_ID:/build/ss_shield ../../kual-extension/kindle-series-manager/bin/ss_shield
docker rm $CONTAINER_ID
```

The build produces a single statically linked binary (~1.6MB) with no runtime dependencies.

## Usage

```sh
# Start the shield (blocks the status bar)
DISPLAY=:0 /path/to/ss_shield &
SHIELD_PID=$!

# Draw with FBInk (underneath the shield, but visible since the shield is black/transparent to the e-ink controller)
fbink -g file=screensaver.png -f

# Stop the shield (reveals the app underneath)
kill $SHIELD_PID
```

In practice, `ss_shield` is managed by `fbink_ss_daemon.sh` and is not invoked directly.

## Why not other approaches?

| Approach | Result |
|----------|--------|
| `lipc-set-prop com.lab126.chromebar configureClock 1` | Hides the clock but not wifi/battery indicators |
| `stop pillow` | Pillow handles alerts/dialogs, not the status bar |
| `killall JunoStatusBarDriver` | Respawns immediately (monitored by pmond) |
| `lipc-set-prop com.lab126.blanket uiQuery ...` | Crashes the blanket process |
| Keep screensaver module loaded + overwrite with FBInk | Stock screensaver briefly visible before FBInk draws |
| Regular X11 window via `xev`/`xfd` | Window manager places it below the status bar (`VisibilityFullyObscured`) |
| **Override-redirect X11 window (ss_shield)** | **Bypasses window manager, always on top** |
