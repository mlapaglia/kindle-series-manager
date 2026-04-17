![Kindle Series Manager](assets/banner.png)
# Kindle Series Manager

Group sideloaded books into series on jailbroken Kindle devices, just like Amazon-purchased books.

Amazon's "Group Series in Library" feature (firmware 5.13.4+) only works with store-purchased content. This KUAL extension lets you create, manage, and remove series groupings for sideloaded books through a web interface served from the Kindle itself.

<img width="834" height="594" alt="image" src="https://github.com/user-attachments/assets/cca7067a-4591-42cc-9730-2f264757f27a" />

## Quick Start

1. Copy the `kindle-series-manager` folder inside `kual-extension/` to your Kindle at `Internal Storage/extensions/kindle-series-manager/`
3. Open KUAL, tap **Start Web UI** under "Kindle Series Manager"
4. Note the URL shown on the Kindle screen (e.g. `http://10.0.0.224:8080/`)
5. Open that URL on your phone or PC (same WiFi network)
6. Tap **Create Series**, name it, select your books, drag them into reading order, and hit Create

<img width="843" height="767" alt="image" src="https://github.com/user-attachments/assets/2899c76b-cc75-44e8-ad8f-07523b273930" />

Books will appear grouped in the Kindle library within a few seconds.

<img width="3072" height="4080" alt="image" src="https://github.com/user-attachments/assets/4e2eebce-bf5d-4506-b43b-6c2fb6bc66e0" />

You can also control the appearance of the "Kindle Unlimited" and "Prime Reading" badges when creating or modifying a series.

<img width="502" height="362" alt="Screenshot 2026-04-16 235907" src="https://github.com/user-attachments/assets/fd345fb4-e93c-498c-ac9d-0caf014bc173" />

## Back Up Your Database

This tool modifies your Kindle's content catalogue database (`/var/local/cc.db`) directly. If something goes wrong, a corrupt or incorrect database can cause books to disappear from your library until the database is fixed. **Always create a backup before making changes.**

The KUAL menu includes **Backup Database** and **Restore Database** actions:

- **Backup Database** copies `/var/local/cc.db` to `/var/local/cc.db.bak`
- **Restore Database** stops `ccat`, copies the backup back over `cc.db`, and restarts `ccat`

Run **Backup Database** before your first series operation. If anything goes wrong, tap **Restore Database** to revert.

You can also back up manually over SSH:

```bash
scp root@<kindle-ip>:/var/local/cc.db ./cc.db.bak
```

And restore manually:

```bash
ssh root@<kindle-ip> "stop com.lab126.ccat"
scp ./cc.db.bak root@<kindle-ip>:/var/local/cc.db
ssh root@<kindle-ip> "start com.lab126.ccat"
```

## Requirements

- Jailbroken Kindle with KUAL installed
- WiFi connection (Kindle and phone/PC on the same network)
- "Group Series in Library" enabled in Kindle Settings

## How It Works

The extension runs a lightweight HTTP server on the Kindle (a static busybox binary bundled with the extension). You access the web UI from your phone or PC browser. The web UI reads and modifies the Kindle's content catalogue database (`/var/local/cc.db`) through shell CGI scripts, creating the same database structures that Amazon uses for store-purchased series.

### Web UI Features

- **My Series** — view all series on the device with book lists; remove series with one tap
- **Create Series** — two-panel interface: pick books from your library on the right, they appear in the reading order panel on the left. Drag to reorder. Optionally provide an Amazon series ASIN for better firmware integration
### Architecture

Series grouping in `cc.db` requires three things:

1. **`Series` table rows** — each maps a book (`d_itemCdeKey`) to a series (`d_seriesId`) with a position
2. **`Entry:Item:Series` row in `Entries`** — the series container with title, author, thumbnail, and metadata matching the format Amazon uses
3. **`p_seriesState = 0` on member books** — flags them as series members so the firmware hides them from the main library and shows them inside the series

The CGI scripts handle all of this, including a workaround for the ICU collation issue (the `Entries` table uses `COLLATE icu` which the standalone `sqlite3` CLI doesn't support — the scripts temporarily strip the collation from the schema, perform the INSERT, then restore it).

## Installation

### Copy files to Kindle

Connect the Kindle via USB and copy the `kual-extension/` folder to:

```
Internal Storage/extensions/kindle-series-manager/
```

The folder should contain:

```
kindle-series-manager/
  config.xml
  menu.json
  bin/
    busybox-httpd      (static ARM binary, ~1MB)
    webapp.sh
    stopweb.sh
    backup.sh
    restore.sh
  www/
    index.html
    cgi-bin/
      series.cgi
      books.cgi
      create.cgi
      remove.cgi
```

### Verify

Open KUAL. You should see "Kindle Series Manager" with "Start Web UI", "Stop Web UI", "Backup Database", and "Restore Database" buttons.

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

### Removing a series

1. Tap **My Series** in the web UI
2. Click **Remove** on the series you want to delete
3. Books return to the main library within a few seconds

### Stopping the server

Open KUAL and tap **Stop Web UI**. This kills the HTTP server and removes the firewall rule.

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

## Technical Details

### Database location

`/var/local/cc.db` — managed by the `com.lab126.ccat` service.

### ICU collation workaround

The `Entries` table has columns with `COLLATE icu` in their definition. The Kindle's standalone `sqlite3` CLI doesn't include the ICU extension, so any INSERT into `Entries` fails. The workaround:

1. `PRAGMA writable_schema=ON` to temporarily strip `COLLATE icu` from the table definition
2. Drop the ICU-dependent indexes
3. Perform the INSERT (in a separate `sqlite3` session that reads the modified schema)
4. Restore the original schema with `COLLATE icu`
5. `ccat` rebuilds the indexes when it starts

The Python CLI tool (`kindle_series.py`) avoids this by registering a stub collation: `conn.create_collation("icu", lambda a, b: (a > b) - (a < b))`

### Series ID format

Amazon uses `urn:collection:1:asin-{ASIN}` for series IDs. When no ASIN is provided, a synthetic key is generated: `SL-SERIES-NAME` (uppercase, spaces replaced with hyphens).

### Firewall

The Kindle's iptables policy is `DROP` by default. The `webapp.sh` script adds a rule to allow traffic on port 8080 when starting the server, and `stopweb.sh` removes it when stopping.

## Sources

- [Kindle cc.db schema documentation](https://sighery.github.io/kindlewiki/kindle-hacking/cc.html)
- [Transferring books and progress between Kindles](https://sighery.com/posts/transferring-content-between-kindles/)
- [Rekreate](https://github.com/Sighery/rekreate)
- [MobileRead: Group by series](https://www.mobileread.com/forums/showthread.php?p=4424834)
- [Kindles Now Have "Group Series in Library" Option](https://blog.the-ebook-reader.com/2020/12/16/kindles-now-have-group-series-in-library-option-in-settings/)

## Known Limitations

- **KU/Prime badges:** Using a real Amazon ASIN causes Kindle Unlimited or Prime Reading logos to appear on the series if the series is in those programs. These badges are resolved at runtime by the firmware, not stored in the database.
- **Cloud sync:** If cloud collections sync is enabled, Amazon's sync may overwrite manually created series data. Consider disabling WiFi after creating series if this is a concern.
- **No Python on Kindle:** The Kindle doesn't ship with Python. The web UI uses pure shell scripts and the `sqlite3` CLI. The Python `kindle_series.py` tool is for PC-side use only.
