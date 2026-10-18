# Kindle Series Manager: calibre plugin

Sends the series of your calibre books to the Kindle, so sideloaded books are
grouped into series in the Kindle library. It works together with the Kindle
Series Manager KUAL extension: the plugin reads the Kindle's library over
WiFi, works out which calibre series are on the Kindle, and asks the
extension's web UI to create them. The extension does the database writes,
the same way as when you create a series in the web UI.

## Requirements

- A jailbroken Kindle on firmware 5.13.4 or later, with the Kindle Series
  Manager KUAL extension installed (a release that includes
  `library_json.cgi`).
- *Settings > Group Series in Library* turned on on the Kindle.
- calibre 6.0 or later.
- The Kindle and the computer on the same network.

## Install

Download `kindle-series-manager-calibre-plugin-<version>.zip` from the
[releases](https://github.com/mlapaglia/kindle-series-manager/releases), or build it:

```bash
cd calibre-plugin
python build.py                                  # -> kindle_series_manager.zip
calibre-customize -a kindle_series_manager.zip   # or: Preferences > Plugins > Load plugin from file
```

Restart calibre. Add the **Kindle Series** button to a toolbar if calibre
does not show it (Preferences > Toolbars & menus).

## Use

1. On the Kindle: KUAL > Kindle Series Manager > **Start Web UI**. The menu
   shows the address, e.g. `http://192.168.1.20:8080/`.
2. In calibre: Kindle Series > **Configure…**, enter that address and click
   **Test connection**.
3. Select books and click **Kindle Series** (or *Send series of selected books
   to Kindle…*). Every book of the selected books' series is included, so a
   series always goes to the Kindle whole. *Send all series to Kindle…* does
   the whole library.
4. A preview lists each series with the books found on the Kindle, how each
   was matched, and the books that are not on the Kindle. Tick the series to
   send and click **Send**.

Status in the preview:

| Status | Meaning |
|---|---|
| New | Created on the Kindle. |
| Update | A Kindle series with this name exists; its books and order are replaced. |
| Already on the Kindle | Same books in the same order; unticked. Tick it to send it again. |
| Too few books on the Kindle | Fewer books on the Kindle than the minimum set in Configure. |

The Kindle's library service restarts once for every series written, so each
one takes a few seconds.

## How books are matched

1. **cdeKey**: calibre writes the book's calibre id (uuid), or its Amazon id,
   into the files it sends, and the Kindle uses it as the book's key. This
   finds books that calibre sent, whatever their title on the Kindle.
2. **File path**: when the Kindle is also connected to calibre over USB, the
   paths calibre matched in the Device view.
3. **Title** (can be turned off in Configure): only when it is unambiguous.
   If several Kindle books have the title, the author has to match too.

## Series order

calibre's series numbers are kept when they are distinct whole numbers
(books 1, 2 and 4 on the Kindle stay 1, 2, 4). Otherwise, for example with
book 1.5, the books are numbered 1, 2, 3, … in calibre's order.

## Settings

- **Kindle address / port**: as shown in the KUAL menu (port 8080).
- **Program badges**: None, Kindle Unlimited, or KU + Prime Reading, as in the
  web UI.
- **Group series with at least N books on the Kindle**: default 2. A group
  with one book only hides that book one level deeper.
- **Also match books by title**: on by default.
