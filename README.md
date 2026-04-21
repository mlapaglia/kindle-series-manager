![Kindle Series Manager](assets/banner.png)
# Kindle Series Manager

[![Documentation](https://app.readthedocs.org/projects/kindle-series-manager/badge/?version=latest)](https://kindle-series-manager.readthedocs.io/en/latest/)

Group sideloaded books into series on jailbroken Kindle devices, just like Amazon-purchased books.

Amazon's "Group Series in Library" feature (firmware 5.13.4+) only works with store-purchased content. This KUAL extension lets you create, manage, and remove series groupings for sideloaded books through a web interface served from the Kindle itself.

> **Full documentation is available at [kindle-series-manager.readthedocs.io](https://kindle-series-manager.readthedocs.io/en/latest/)**

<img width="775" height="760" alt="image" src="https://github.com/user-attachments/assets/8b76584b-d612-4be2-8518-6abbfb014630" />

## Features

- **Series Management** — Create, edit, and remove series groupings for sideloaded books via a two-panel web UI with drag-and-drop reading order. Optionally attach Amazon ASINs and control KU/Prime Reading badge display.
- **Goodreads Progress Sync** — Automatically sync reading progress to Goodreads when you open/close a book or the Kindle sleeps. Background daemon with auto-start on boot.
- **Custom Screensavers** — Upload images with a crop editor; auto-resize, grayscale conversion, and proper PNG encoding for your Kindle's resolution. Manage active/disabled screensavers. Enable FBInk Screensaver mode in KUAL for safer rendering that won't freeze the device on malformed images.
- **Book Upload** — Upload compatible books from your local device.
- **Calibre Integration** — Search and download books through your Calibre web server. 
- **Database Backup/Restore** — One-tap backup and restore of the Kindle's `cc.db` via KUAL menu.
- **Standalone CLI** — `kindle_series.py` for direct database manipulation on a PC (list, inspect, create, and remove series).

## Quick Start

1. Copy the `kindle-series-manager` folder inside `kual-extension/` to your Kindle at `Internal Storage/extensions/kindle-series-manager/`
3. Open KUAL, tap **Start Web UI** under "Kindle Series Manager"
4. Note the URL shown on the Kindle screen (e.g. `http://10.0.0.224:8080/`)
5. Open that URL on your phone or PC (same WiFi network)
6. Tap **Create Series**, name it, select your books, drag them into reading order, and hit Create

<img width="834" height="838" alt="image" src="https://github.com/user-attachments/assets/021322b6-d6f0-4811-84fa-db8ed8475805" />

## Requirements

- Jailbroken Kindle with KUAL installed
- WiFi connection (Kindle and phone/PC on the same network)
- "Group Series in Library" enabled in Kindle Settings

## How It Works

The extension runs a lightweight HTTP server on the Kindle (a static busybox binary bundled with the extension). You access the web UI from your phone or PC browser. The web UI reads and modifies the Kindle's content catalogue database (`/var/local/cc.db`) through shell CGI scripts, creating the same database structures that Amazon uses for store-purchased series.

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
