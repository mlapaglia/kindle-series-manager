# Kindle Series Manager

A tool to add series grouping for sideloaded books on jailbroken Kindle devices. Amazon-purchased books automatically group by series in the Kindle library, but sideloaded books (via Calibre or USB) never do — even if series metadata is embedded in the file. This tool fixes that by directly modifying the Kindle's content catalogue database.

**Requires a jailbroken Kindle with SSH access.**

## Background

Kindle firmware 5.13.4+ introduced a "Group Series in Library" setting. This feature works exclusively with Amazon-purchased content because the series metadata is populated by Amazon's servers during sync. Sideloaded books are indexed locally by the `com.lab126.ccat` service, which never populates the series fields.

No existing tool (Calibre plugin, KUAL extension, or otherwise) addressed this — the closest community discussion was a [May 2024 MobileRead thread](https://www.mobileread.com/forums/showthread.php?p=4424834) that confirmed it was theoretically possible via direct database manipulation but noted nobody had built it.

## How It Works

### The Database

The Kindle stores its content catalogue in a SQLite database at `/var/local/cc.db`, managed by the `com.lab126.ccat` service. The full schema is [documented on kindlewiki](https://sighery.github.io/kindlewiki/kindle-hacking/cc.html).

### Investigation

I dumped the schema and examined how Amazon-purchased series (Dungeon Crawler Carl, 7 books) are structured in the database. The investigation revealed three components that make series grouping work:

#### 1. The `Series` Table

Each book-to-series mapping is a row in this table:

| Column | Example Value | Purpose |
|---|---|---|
| `d_seriesId` | `urn:collection:1:asin-B08BX5D4LC` | URN containing the series ASIN |
| `d_itemCdeKey` | `B08BKGYQXW` | The book's `p_cdeKey` from `Entries` |
| `d_itemPosition` | `0` | 0-indexed position in the series |
| `d_itemPositionLabel` | `1` | 1-indexed display label |
| `d_itemType` | `Entry:Item` | Matches `p_type` in `Entries` |
| `d_seriesOrderType` | `ordered` | Sort behavior |

#### 2. The `Entry:Item:Series` Row in `Entries`

Each series has its own row in the `Entries` table acting as the series container. Key fields:

| Field | Value |
|---|---|
| `p_type` | `Entry:Item:Series` |
| `p_cdeKey` | The series ASIN (e.g. `B08BX5D4LC`) |
| `p_cdeType` | `series` |
| `p_cdeGroup` | `urn:collection:1:asin-{series ASIN}` |
| `p_mimeType` | `application/x-kindle-series` |
| `j_titles` | JSON array: `[{"display":"...","collation":"...","language":"en","pronunciation":"..."}]` |
| `j_credits` | Pulled from the first book's author |
| `p_thumbnail` | Path to first book's cover thumbnail |
| `j_members` | `[]` (empty — membership tracked via `Series` table) |
| `p_memberCount` | Total books in the series |
| `p_isVisibleInHome` | `1` |
| `p_isArchived` | `1` |
| `p_seriesState` | `1` |
| `p_visibilityState` | `1` |
| `p_originType` | `-1` |
| `p_contentIndexedState` | `2147483647` (INT_MAX — not applicable) |
| `j_displayObjects` | `[{"ref":"titles"},{"ref":"credits"}]` |

#### 3. `p_seriesState` on Member Books

Books that belong to a series have `p_seriesState = 0` on their `Entries` row. The value `1` is the default for non-series entries (dictionaries, collections, system items, etc.) and does not indicate series membership.

### Gotchas Encountered

**ICU collation:** The `Entries` table defines `p_titles_0_collation COLLATE icu` and `p_credits_0_name_collation COLLATE icu`. The Kindle's SQLite build includes ICU, but standard desktop SQLite does not. Any query that touches these columns (including INSERTs that update indexes) fails with `no such collation sequence: icu`. Solved by registering a stub collation:

```python
conn.create_collation("icu", lambda a, b: (a > b) - (a < b))
```

**Metadata separator character:** The `p_metadataUnicodeWords` field uses U+FFFC (OBJECT REPLACEMENT CHARACTER) as a separator between searchable terms. Python's `"\u00fffc"` is **wrong** (that's `\u00ff` + literal "fc"); the correct escape is `"\ufffc"`.

**Series position indexing:** Positions in the `Series` table are 0-indexed (`d_itemPosition`), while display labels (`d_itemPositionLabel`) are 1-indexed strings.

## Usage

### Prerequisites

- Jailbroken Kindle with SSH access
- Python 3.6+
- The `cc.db` file copied from your Kindle

### Setup

```bash
# Copy cc.db from Kindle to your working directory
scp root@<kindle-ip>:/var/local/cc.db ./cc.db
```

### Commands

#### Diagnose

Inspect existing series data, series container entries, and list all sideloaded books with their `p_cdeKey` values:

```bash
python kindle_series.py diagnose
```

#### List Books

List all books on the device, optionally filtered by title:

```bash
python kindle_series.py list
python kindle_series.py list --filter "Expanse"
```

#### Add Series

Group books into a series. Pass `p_cdeKey` values in reading order:

```bash
python kindle_series.py add-series \
  --name "The Expanse" \
  --books "key1,key2,key3"
```

Use `--asin` to assign the real Amazon series ASIN instead of a generated key. You can find the series ASIN by searching for the series on [amazon.com](https://www.amazon.com) — the ASIN is the alphanumeric ID in the URL of the series page (e.g. `amazon.com/dp/B09DD17H3N` → `B09DD17H3N`). Alternatively, search for `"series name" site:amazon.com kindle series` and look for the "X book series" result:

```bash
python kindle_series.py add-series \
  --name "The Expanse" \
  --asin B09DD17H3N \
  --books "key1,key2,key3"
```

#### Remove Series

Remove an entire series or specific books from one:

```bash
# Remove entire series
python kindle_series.py remove-series \
  --series-id "urn:collection:1:asin-B09DD17H3N"

# Remove specific books
python kindle_series.py remove-series \
  --series-id "urn:collection:1:asin-B09DD17H3N" \
  --books "key1,key2"
```

#### Import from Calibre

Batch-import series metadata from a Calibre library. Matches books by title:

```bash
python kindle_series.py import-calibre \
  --calibre-db "/path/to/Calibre Library/metadata.db"
```

#### Dump Entry

Inspect all fields of a specific database entry:

```bash
python kindle_series.py dump B08BX5D4LC
```

### Deploy to Kindle

```bash
# SSH into Kindle
ssh root@<kindle-ip>

# Stop the catalogue service
stop com.lab126.ccat

# Back up the original
cp /var/local/cc.db /var/local/cc.db.bak

# Exit SSH, copy modified db
scp cc.db root@<kindle-ip>:/var/local/cc.db

# SSH back in, restart service
ssh root@<kindle-ip>
start com.lab126.ccat
```

The series grouping should appear in the library within a few seconds of restarting `ccat`.

## Sources

- [Kindle cc.db schema documentation](https://sighery.github.io/kindlewiki/kindle-hacking/cc.html) — full table/column reference
- [Transferring books and progress between Kindles](https://sighery.com/posts/transferring-content-between-kindles/) — detailed writeup on cc.db internals and the `com.lab126.ccat` service
- [Rekreate](https://github.com/Sighery/rekreate) — Go tool for backing up/restoring Kindle content (books, collections, thumbnails)
- [MobileRead: Group by series](https://www.mobileread.com/forums/showthread.php?p=4424834) — community discussion confirming series manipulation is theoretically possible
- [Kindles Now Have "Group Series in Library" Option](https://blog.the-ebook-reader.com/2020/12/16/kindles-now-have-group-series-in-library-option-in-settings/) — feature announcement (firmware 5.13.4+)

## Known Limitations

- **KU/Prime badges:** The Kindle Unlimited and Prime Reading logos on series entries appear to be resolved at runtime by the firmware based on Amazon account data, not stored in cc.db. Using a real Amazon ASIN for the series key will cause these badges to appear if the series is in KU/Prime.
- **Cloud sync conflicts:** If cloud collections sync is enabled, Amazon's sync may overwrite or conflict with manually created series data.
- **Calibre import matching:** The `import-calibre` command matches books by title substring, which may produce false matches for books with similar names.
