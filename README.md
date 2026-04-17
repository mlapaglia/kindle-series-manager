![Kindle Series Manager](assets/banner.png)
# Kindle Series Manager

Group sideloaded books into series on jailbroken Kindle devices, just like Amazon-purchased books.

Amazon's "Group Series in Library" feature (firmware 5.13.4+) only works with store-purchased content. This KUAL extension lets you create, manage, and remove series groupings for sideloaded books through a web interface served from the Kindle itself.

<img width="1073" height="755" alt="Screenshot 2026-04-17 055404" src="https://github.com/user-attachments/assets/b08981b2-8697-4567-b346-be7627ac1d6d" />

## Quick Start

1. Copy the `kindle-series-manager` folder inside `kual-extension/` to your Kindle at `Internal Storage/extensions/kindle-series-manager/`
3. Open KUAL, tap **Start Web UI** under "Kindle Series Manager"
4. Note the URL shown on the Kindle screen (e.g. `http://10.0.0.224:8080/`)
5. Open that URL on your phone or PC (same WiFi network)
6. Tap **Create Series**, name it, select your books, drag them into reading order, and hit Create

<img width="1069" height="843" alt="Screenshot 2026-04-17 055426" src="https://github.com/user-attachments/assets/e573c6fb-ef1f-47ca-b429-c755c5631a91" />

### Grouped Series
Books will appear grouped in the Kindle library within a few seconds.

<img height="800" alt="image" src="https://github.com/user-attachments/assets/4e2eebce-bf5d-4506-b43b-6c2fb6bc66e0" />

### KU and PR Badges
You can also control the appearance of the "Kindle Unlimited" and "Prime Reading" badges when creating or modifying a series.

<img width="511" height="200" alt="Screenshot 2026-04-17 055525" src="https://github.com/user-attachments/assets/f430fe48-9e44-4cfd-a9d7-fd6c23e2caf9" />

## Back Up Your Database

This tool modifies your Kindle's content catalogue database (`/var/local/cc.db`) directly. If something goes wrong, a corrupt or incorrect database can cause books to disappear from your library until the database is fixed. **Always create a backup before making changes.**

The KUAL menu includes **Backup Database** and **Restore Database** actions:

- **Backup Database** copies `/var/local/cc.db` to `/var/local/cc.db.bak`
- **Restore Database** stops `ccat`, copies the backup back over `cc.db`, and restarts `ccat`

Run **Backup Database** before your first series operation. If anything goes wrong, tap **Restore Database** to revert.

## Requirements

- Jailbroken Kindle with KUAL installed
- WiFi connection (Kindle and phone/PC on the same network)
- "Group Series in Library" enabled in Kindle Settings

## How It Works

The extension runs a lightweight HTTP server on the Kindle (a static busybox binary bundled with the extension). You access the web UI from your phone or PC browser. The web UI reads and modifies the Kindle's content catalogue database (`/var/local/cc.db`) through shell CGI scripts, creating the same database structures that Amazon uses for store-purchased series.

### Web UI Features

- **My Series** — view all series on the device with book lists; edit or remove series with one tap
- **Create Series** — two-panel interface: pick books from your library on the right, they appear in the reading order panel on the left. Drag to reorder. Optionally provide an Amazon series ASIN for better firmware integration. Control program badge display (KU/Prime Reading)
- **Progress Tracking** — configure Goodreads credentials, sign in, build book mappings, and monitor the sync service status and logs

## Usage

### Starting the web UI

1. Make sure WiFi is on
2. Open KUAL, tap **Start Web UI**
3. The Kindle screen shows the URL (e.g. `http://10.0.0.224:8080/`)
4. Open that URL on your phone or PC

### Creating a series

1. Tap **Create Series** in the web UI
2. Enter a series name
3. Optionally enter the Amazon series ASIN (find it in the URL of the series page on amazon.com, e.g. `amazon.com/dp/B09DD17H3N`)
4. Click books from the **Available Books** panel to add them to the reading order
5. Drag books up/down to reorder; click X to remove
6. Tap **Create Series**
7. Wait a few seconds for `ccat` to restart, then check your Kindle library

### Editing a series
1. Tap **Edit** on the series in the web UI
2. Change the ordering, remove/add books to the series.
3. Tap **Save**

### Removing a series

1. Tap **My Series** in the web UI
2. Click **Remove** on the series you want to delete
3. Books return to the main library within a few seconds

### Stopping the server

Open KUAL and tap **Stop Web UI**. This kills the HTTP server and removes the firewall rule.

## Goodreads Progress Sync

The extension can automatically sync your reading progress to Goodreads whenever you open or close a book, or when the Kindle goes to sleep. This uses Goodreads' internal progress update endpoint to set your current page.

### Setup

1. Start the web UI and go to the **Progress Tracking** tab
2. Enter your Goodreads email, password, and user ID, then click **Save Credentials**
   - Your Goodreads user ID is the number in your profile URL: `goodreads.com/user/show/183958037` → `183958037`
3. Click **Sign In to Goodreads** — the output panel shows the login flow. On success you'll see "Login successful!"
4. Click **Build Mapping** — this fetches your Goodreads "currently-reading" shelf and matches those books against your Kindle library by title. The results table shows which books were matched.
5. In KUAL, tap **Enable Goodreads Sync** to start the background sync daemon

### How it works

A background daemon listens for two Kindle system events:
- `appActivating` from `com.lab126.appmgrd` — fires when you open or close a book
- `goingToScreenSaver` from `com.lab126.powerd` — fires when the Kindle goes to sleep

When either event fires, the daemon queries `cc.db` for the most recently accessed book, checks if it's in the Goodreads mapping, compares the current `p_percentFinished` against the last synced value, and if it changed, calculates the page number and pushes an update to Goodreads.

Page numbers are calculated as `round(percentFinished * totalPages / 100)` where `totalPages` comes from Goodreads' `finalPosition` field (fetched once per book and cached).

### Auto-start on boot

When you enable Goodreads Sync via KUAL, the extension installs an upstart job (`/etc/upstart/gr-sync.conf`) that starts the daemon automatically after the Kindle boots and WiFi connects. A flag file at `/mnt/us/ENABLE_GR_SYNC` controls whether the daemon runs — remove it to disable auto-start.

### Troubleshooting

- Check the **Sync Log** section in the Progress Tracking tab for error messages
- If login fails, check that your credentials are correct and that you're using email login (not Amazon SSO)
- If books don't match, make sure they're on your Goodreads "currently-reading" shelf with titles that closely match the Kindle book titles
- Session cookies may expire — if syncs start failing, click **Sign In to Goodreads** again from the web UI
- Log file location on the Kindle: `/mnt/base-us/extensions/kindle-series-manager/goodreads/gr_sync.log`

## Standalone CLI Tool

The `kindle_series.py` script can be used independently on a PC for direct database manipulation. Copy `cc.db` from the Kindle, modify it locally, and push it back.

```bash
# Copy cc.db from Kindle
scp root@<kindle-ip>:/var/local/cc.db ./cc.db

# Inspect the database
python kindle_series.py diagnose
python kindle_series.py list --filter "Expanse"
python kindle_series.py dump B08BX5D4LC

# Create a series
python kindle_series.py add-series --name "The Expanse" --books "key1,key2,key3"
python kindle_series.py add-series --name "The Expanse" --asin B09DD17H3N --books "key1,key2,key3"

# Remove a series
python kindle_series.py remove-series --series-id "urn:collection:1:asin-SL-THE-EXPANSE"

# Push back to Kindle
ssh root@<kindle-ip> "stop com.lab126.ccat"
scp cc.db root@<kindle-ip>:/var/local/cc.db
ssh root@<kindle-ip> "start com.lab126.ccat"
```

## Sources

- [Kindle cc.db schema documentation](https://sighery.github.io/kindlewiki/kindle-hacking/cc.html)
- [Transferring books and progress between Kindles](https://sighery.com/posts/transferring-content-between-kindles/)
- [Rekreate](https://github.com/Sighery/rekreate)
- [MobileRead: Group by series](https://www.mobileread.com/forums/showthread.php?p=4424834)
- [Kindles Now Have "Group Series in Library" Option](https://blog.the-ebook-reader.com/2020/12/16/kindles-now-have-group-series-in-library-option-in-settings/)
