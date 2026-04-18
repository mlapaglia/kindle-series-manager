"""
Kindle Series Manager

Manages series grouping for sideloaded books in the Kindle cc.db database.
Works by inserting rows into the Series table, creating Entry:Item:Series
entries, and updating p_seriesState on member Entries.

Usage:
  1. Copy cc.db from your Kindle (/var/local/cc.db) to this directory
  2. Run: python kindle_series.py diagnose
  3. Run: python kindle_series.py add-series --name "My Series" --books "cdeKey1,cdeKey2,cdeKey3"
     OR: python kindle_series.py import-calibre --calibre-db "path/to/metadata.db"
  4. Copy the modified cc.db back to the Kindle

IMPORTANT: Back up your cc.db before modifying it. Stop the Kindle's ccat service
before replacing the file:
    stop ccat
    cp /var/local/cc.db /var/local/cc.db.bak
    # ... copy modified cc.db to /var/local/cc.db ...
    start ccat
"""

import sqlite3
import sys
import json
import argparse
import uuid
from pathlib import Path


DB_PATH = Path(__file__).parent / "tests" / "cc.db"


def get_db(path=None):
    db_path = path or DB_PATH
    if not db_path.exists():
        print(f"ERROR: {db_path} not found.")
        print("Copy cc.db from your Kindle (/var/local/cc.db) to this directory.")
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    conn.create_collation("icu", lambda a, b: (a > b) - (a < b))
    return conn


def diagnose(args):
    """Show existing series data and list sideloaded books."""
    conn = get_db(args.db)
    conn.row_factory = sqlite3.Row

    print("=" * 80)
    print("EXISTING SERIES TABLE DATA")
    print("=" * 80)

    cur = conn.execute("SELECT * FROM Series ORDER BY d_seriesId, d_itemPosition")
    rows = cur.fetchall()
    if not rows:
        print("  (empty - no series data found)")
    else:
        current_series = None
        for row in rows:
            if row["d_seriesId"] != current_series:
                current_series = row["d_seriesId"]
                print(f"\n  Series: {current_series}")
                print(f"    orderType: {row['d_seriesOrderType']}")
            title = _get_title_by_cdekey(conn, row["d_itemCdeKey"])
            print(
                f"    [{row['d_itemPosition']}] "
                f"({row['d_itemPositionLabel'] or 'no label'}) "
                f"cdeKey={row['d_itemCdeKey']}  "
                f"type={row['d_itemType']}  "
                f"title={title}"
            )

    print("\n" + "=" * 80)
    print("ENTRY:ITEM:SERIES ENTRIES (series container rows)")
    print("=" * 80)

    cur = conn.execute(
        "SELECT p_uuid, p_cdeKey, p_cdeType, p_type, p_titles_0_nominal, "
        "p_seriesState, p_isVisibleInHome, p_memberCount "
        "FROM Entries WHERE p_type = 'Entry:Item:Series' "
        "ORDER BY p_titles_0_nominal"
    )
    rows = cur.fetchall()
    if not rows:
        print("  (none)")
    else:
        for row in rows:
            print(
                f"  uuid={row['p_uuid']}  "
                f"cdeKey={row['p_cdeKey']}  "
                f"cdeType={row['p_cdeType']}  "
                f"seriesState={row['p_seriesState']}  "
                f"visible={row['p_isVisibleInHome']}  "
                f"members={row['p_memberCount']}  "
                f"title={row['p_titles_0_nominal']}"
            )

    print("\n" + "=" * 80)
    print("SERIES MEMBER BOOKS (p_seriesState = 0)")
    print("=" * 80)

    cur = conn.execute(
        "SELECT p_cdeKey, p_cdeType, p_type, p_seriesState, "
        "p_titles_0_nominal "
        "FROM Entries WHERE p_seriesState = 0 AND p_type = 'Entry:Item' "
        "ORDER BY p_titles_0_nominal"
    )
    rows = cur.fetchall()
    if not rows:
        print("  (none)")
    else:
        for row in rows:
            print(
                f"  cdeKey={row['p_cdeKey']}  "
                f"cdeType={row['p_cdeType']}  "
                f"title={row['p_titles_0_nominal']}"
            )

    print("\n" + "=" * 80)
    print("ALL SIDELOADED BOOKS")
    print("=" * 80)

    cur = conn.execute(
        "SELECT p_uuid, p_cdeKey, p_cdeType, p_type, p_titles_0_nominal, "
        "p_seriesState, p_location, p_contentState "
        "FROM Entries "
        "WHERE p_type = 'Entry:Item' "
        "AND p_location LIKE '/mnt/us/documents/%' "
        "ORDER BY p_titles_0_nominal"
    )
    rows = cur.fetchall()
    if not rows:
        print("  (no sideloaded books found)")
    else:
        for row in rows:
            in_series = _series_membership(conn, row["p_cdeKey"])
            print(
                f"  cdeKey={row['p_cdeKey']}  "
                f"cdeType={row['p_cdeType']}  "
                f"title={row['p_titles_0_nominal']}{in_series}"
            )

    conn.close()


def list_books(args):
    """List all books with optional title filter."""
    conn = get_db(args.db)
    conn.row_factory = sqlite3.Row

    query = (
        "SELECT p_cdeKey, p_cdeType, p_type, p_titles_0_nominal, "
        "p_seriesState, p_contentState "
        "FROM Entries WHERE p_type = 'Entry:Item' "
    )
    params = []
    if args.filter:
        query += "AND p_titles_0_nominal LIKE ? "
        params.append(f"%{args.filter}%")
    query += "ORDER BY p_titles_0_nominal"

    cur = conn.execute(query, params)
    for row in cur:
        in_series = _series_membership(conn, row["p_cdeKey"])
        print(
            f"  cdeKey={row['p_cdeKey']}  "
            f"cdeType={row['p_cdeType']}  "
            f"title={row['p_titles_0_nominal']}{in_series}"
        )
    conn.close()


def add_series(args):
    """Add books to a series."""
    conn = get_db(args.db)
    conn.row_factory = sqlite3.Row

    series_name = args.name
    cde_keys = [k.strip() for k in args.books.split(",")]

    for key in cde_keys:
        cur = conn.execute(
            "SELECT p_cdeKey, p_type, p_titles_0_nominal FROM Entries "
            "WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
            (key,),
        )
        row = cur.fetchone()
        if not row:
            print(f"ERROR: No book found with cdeKey '{key}'")
            conn.close()
            sys.exit(1)

    series_cde_key = args.asin if args.asin else _make_series_cde_key(series_name)
    series_id = f"urn:collection:1:asin-{series_cde_key}"

    print(f"Series: {series_name}")
    print(f"  seriesId:  {series_id}")
    print(f"  cdeKey:    {series_cde_key}")
    print()

    for i, key in enumerate(cde_keys):
        position = i
        position_label = str(i + 1)

        cur = conn.execute(
            "SELECT p_titles_0_nominal FROM Entries "
            "WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
            (key,),
        )
        title = cur.fetchone()["p_titles_0_nominal"]

        conn.execute(
            "INSERT OR REPLACE INTO Series "
            "(d_seriesId, d_itemCdeKey, d_itemPosition, d_itemPositionLabel, "
            "d_itemType, d_seriesOrderType) VALUES (?, ?, ?, ?, ?, ?)",
            (series_id, key, float(position), position_label, "Entry:Item", "ordered"),
        )

        conn.execute(
            "UPDATE Entries SET p_seriesState = 0 "
            "WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
            (key,),
        )

        print(f"  [{position_label}] {title} (cdeKey={key})")

    _upsert_series_entry(conn, series_cde_key, series_name, len(cde_keys))

    conn.commit()
    conn.close()
    print(f"\nDone. {len(cde_keys)} books added to series '{series_name}'.")


def remove_series(args):
    """Remove books from a series or delete an entire series."""
    conn = get_db(args.db)
    conn.row_factory = sqlite3.Row

    series_id = args.series_id

    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM Series WHERE d_seriesId = ?",
        (series_id,),
    ).fetchone()["cnt"]
    if existing == 0:
        print(f"ERROR: No series found with id '{series_id}'")
        known = conn.execute(
            "SELECT DISTINCT d_seriesId FROM Series ORDER BY d_seriesId"
        ).fetchall()
        if known:
            print("\nKnown series IDs:")
            for row in known:
                print(f"  {row['d_seriesId']}")
        conn.close()
        sys.exit(1)

    if args.books:
        cde_keys = [k.strip() for k in args.books.split(",")]
        for key in cde_keys:
            conn.execute(
                "DELETE FROM Series WHERE d_seriesId = ? AND d_itemCdeKey = ?",
                (series_id, key),
            )
            remaining = conn.execute(
                "SELECT COUNT(*) as cnt FROM Series WHERE d_itemCdeKey = ?",
                (key,),
            ).fetchone()["cnt"]
            if remaining == 0:
                conn.execute(
                    "UPDATE Entries SET p_seriesState = 1 "
                    "WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
                    (key,),
                )
            print(f"  Removed cdeKey={key} from series '{series_id}'")
    else:
        cur = conn.execute(
            "SELECT d_itemCdeKey FROM Series WHERE d_seriesId = ?",
            (series_id,),
        )
        keys = [row["d_itemCdeKey"] for row in cur]
        conn.execute("DELETE FROM Series WHERE d_seriesId = ?", (series_id,))
        for key in keys:
            remaining = conn.execute(
                "SELECT COUNT(*) as cnt FROM Series WHERE d_itemCdeKey = ?",
                (key,),
            ).fetchone()["cnt"]
            if remaining == 0:
                conn.execute(
                    "UPDATE Entries SET p_seriesState = 1 "
                    "WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
                    (key,),
                )

        # Also remove the Entry:Item:Series row
        series_cde_key = series_id.replace("urn:collection:1:asin-", "")
        conn.execute(
            "DELETE FROM Entries WHERE p_cdeKey = ? AND p_type = 'Entry:Item:Series'",
            (series_cde_key,),
        )

        print(f"Deleted series '{series_id}' ({len(keys)} books removed)")

    conn.commit()
    conn.close()


def import_calibre(args):
    """
    Import series data from a Calibre library database (metadata.db).
    Matches books by title between Calibre and the Kindle cc.db.
    """
    calibre_db_path = Path(args.calibre_db)
    if not calibre_db_path.exists():
        print(f"ERROR: Calibre database not found at {calibre_db_path}")
        sys.exit(1)

    kindle_conn = get_db(args.db)
    kindle_conn.row_factory = sqlite3.Row

    calibre_conn = sqlite3.connect(str(calibre_db_path))
    calibre_conn.row_factory = sqlite3.Row

    calibre_cur = calibre_conn.execute("""
        SELECT b.id, b.title, s.name as series_name,
               bs.series_index as series_index
        FROM books b
        JOIN books_series_link bs ON b.id = bs.book
        JOIN series s ON bs.series = s.id
        ORDER BY s.name, bs.series_index
    """)

    # Group calibre books by series
    series_map = {}
    for row in calibre_cur:
        sname = row["series_name"]
        if sname not in series_map:
            series_map[sname] = []
        series_map[sname].append({
            "title": row["title"],
            "index": row["series_index"],
        })

    added = 0
    skipped = 0
    not_found = 0

    for series_name, books in series_map.items():
        series_cde_key = _make_series_cde_key(series_name)
        series_id = f"urn:collection:1:asin-{series_cde_key}"

        print(f"\nSeries: {series_name}  (id: {series_id})")

        matched_keys = []

        for book in books:
            calibre_title = book["title"]
            position = book["index"]

            kindle_cur = kindle_conn.execute(
                "SELECT p_cdeKey, p_titles_0_nominal FROM Entries "
                "WHERE p_type = 'Entry:Item' AND p_titles_0_nominal LIKE ?",
                (f"%{calibre_title}%",),
            )
            kindle_row = kindle_cur.fetchone()

            if not kindle_row:
                print(f"  [{position}] '{calibre_title}' - NOT FOUND on Kindle")
                not_found += 1
                continue

            cde_key = kindle_row["p_cdeKey"]

            existing = kindle_conn.execute(
                "SELECT 1 FROM Series WHERE d_seriesId = ? AND d_itemCdeKey = ?",
                (series_id, cde_key),
            ).fetchone()

            if existing and not args.force:
                print(
                    f"  [{position}] '{kindle_row['p_titles_0_nominal']}' "
                    f"- already in series (use --force to overwrite)"
                )
                skipped += 1
                matched_keys.append(cde_key)
                continue

            # Series table positions are 0-indexed; labels are 1-indexed
            pos_0 = position - 1
            pos_label = str(int(position)) if position == int(position) else str(position)

            kindle_conn.execute(
                "INSERT OR REPLACE INTO Series "
                "(d_seriesId, d_itemCdeKey, d_itemPosition, d_itemPositionLabel, "
                "d_itemType, d_seriesOrderType) VALUES (?, ?, ?, ?, ?, ?)",
                (series_id, cde_key, float(pos_0), pos_label, "Entry:Item", "ordered"),
            )
            kindle_conn.execute(
                "UPDATE Entries SET p_seriesState = 0 "
                "WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
                (cde_key,),
            )
            print(
                f"  [{pos_label}] '{kindle_row['p_titles_0_nominal']}' "
                f"- ADDED (cdeKey={cde_key})"
            )
            matched_keys.append(cde_key)
            added += 1

        if matched_keys:
            total_in_series = kindle_conn.execute(
                "SELECT COUNT(*) as cnt FROM Series WHERE d_seriesId = ?",
                (series_id,),
            ).fetchone()["cnt"]
            _upsert_series_entry(
                kindle_conn, series_cde_key, series_name, total_in_series
            )

    kindle_conn.commit()
    kindle_conn.close()
    calibre_conn.close()

    print(f"\nDone: {added} added, {skipped} already present, {not_found} not found on Kindle")


def dump_entry(args):
    """Dump full details of a specific entry by cdeKey."""
    conn = get_db(args.db)
    conn.row_factory = sqlite3.Row

    cur = conn.execute("SELECT * FROM Entries WHERE p_cdeKey = ?", (args.cde_key,))
    rows = cur.fetchall()
    if not rows:
        print(f"No entry found with cdeKey '{args.cde_key}'")
        conn.close()
        return

    for row in rows:
        print(f"--- Entry (p_type={row['p_type']}) ---")
        for key in row.keys():
            val = row[key]
            if val is not None:
                print(f"  {key} = {val}")

    cur2 = conn.execute(
        "SELECT * FROM Series WHERE d_itemCdeKey = ?", (args.cde_key,)
    )
    series_rows = cur2.fetchall()
    if series_rows:
        print(f"\n--- Series membership ---")
        for srow in series_rows:
            for key in srow.keys():
                print(f"  {key} = {srow[key]}")

    conn.close()


def _make_series_cde_key(series_name):
    """Generate a deterministic cdeKey for a series based on its name."""
    return "SL-" + series_name.upper().replace(" ", "-").replace("'", "")


def _get_first_book_metadata(conn, series_id):
    """Get credit and thumbnail info from the first book in a series."""
    row = conn.execute(
        "SELECT e.j_credits, e.p_credits_0_name_collation, "
        "e.p_credits_0_name_pronunciation, e.p_thumbnail, e.p_cdeKey, e.p_cdeType "
        "FROM Series s "
        "JOIN Entries e ON e.p_cdeKey = s.d_itemCdeKey AND e.p_type = 'Entry:Item' "
        "WHERE s.d_seriesId = ? "
        "ORDER BY s.d_itemPosition LIMIT 1",
        (series_id,),
    ).fetchone()
    return row


def _upsert_series_entry(conn, series_cde_key, series_name, member_count):
    """Create or update the Entry:Item:Series row in the Entries table."""
    series_id = f"urn:collection:1:asin-{series_cde_key}"
    first_book = _get_first_book_metadata(conn, series_id)

    titles_json = json.dumps([{
        "display": series_name,
        "collation": series_name,
        "language": "en",
        "pronunciation": series_name,
    }])

    credits_json = None
    credit_collation = None
    credit_pronunciation = None
    thumbnail = None
    metadata_words = series_name.lower() + "\ufffc" + series_name.lower()

    if first_book:
        credits_json = first_book["j_credits"]
        credit_collation = first_book["p_credits_0_name_collation"]
        credit_pronunciation = first_book["p_credits_0_name_pronunciation"]
        thumb = first_book["p_thumbnail"]
        if thumb:
            thumbnail = thumb
        if credit_pronunciation:
            metadata_words += (
                "\ufffc" + credit_pronunciation.lower()
                + "\ufffc" + credit_pronunciation.lower()
            )

    existing = conn.execute(
        "SELECT p_uuid FROM Entries "
        "WHERE p_cdeKey = ? AND p_type = 'Entry:Item:Series'",
        (series_cde_key,),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE Entries SET "
            "p_titles_0_nominal = ?, j_titles = ?, "
            "p_credits_0_name_collation = ?, j_credits = ?, "
            "p_credits_0_name_pronunciation = ?, "
            "p_creditCount = ?, "
            "p_memberCount = ?, p_homeMemberCount = ?, "
            "p_thumbnail = ?, p_metadataUnicodeWords = ? "
            "WHERE p_cdeKey = ? AND p_type = 'Entry:Item:Series'",
            (
                series_name, titles_json,
                credit_collation, credits_json,
                credit_pronunciation,
                1 if credits_json else 0,
                member_count, member_count,
                thumbnail, metadata_words,
                series_cde_key,
            ),
        )
    else:
        entry_uuid = str(uuid.uuid4())
        display_objects = json.dumps([{"ref": "titles"}, {"ref": "credits"}])
        conn.execute(
            "INSERT INTO Entries ("
            "p_uuid, p_type, p_cdeKey, p_cdeType, p_cdeGroup, "
            "p_titles_0_nominal, p_titles_0_collation, p_titles_0_pronunciation, "
            "j_titles, p_titleCount, "
            "p_credits_0_name_collation, p_credits_0_name_pronunciation, "
            "j_credits, p_creditCount, "
            "j_members, p_memberCount, p_homeMemberCount, "
            "p_mimeType, p_thumbnail, "
            "j_displayObjects, p_metadataUnicodeWords, "
            "p_isArchived, p_isVisibleInHome, p_isLatestItem, "
            "p_isUpdateAvailable, p_isTestData, "
            "p_seriesState, p_visibilityState, p_isProcessed, "
            "p_contentState, p_ownershipType, p_originType, "
            "p_contentIndexedState, p_noteIndexedState, "
            "p_collectionSyncCounter, p_collectionDataSetName, "
            "p_subType, j_languages, p_languageCount, "
            "p_virtualCollectionCount"
            ") VALUES ("
            "?, ?, ?, ?, ?, "
            "?, ?, ?, "
            "?, ?, "
            "?, ?, "
            "?, ?, "
            "?, ?, ?, "
            "?, ?, "
            "?, ?, "
            "?, ?, ?, "
            "?, ?, "
            "?, ?, ?, "
            "?, ?, ?, "
            "?, ?, "
            "?, ?, "
            "?, ?, ?, "
            "?"
            ")",
            (
                entry_uuid, "Entry:Item:Series", series_cde_key, "series", series_id,
                series_name, series_name, series_name,
                titles_json, 1,
                credit_collation, credit_pronunciation,
                credits_json, 1 if credits_json else 0,
                "[]", member_count, member_count,
                "application/x-kindle-series", thumbnail,
                display_objects, metadata_words,
                1, 1, 1,
                0, 0,
                1, 1, 1,
                0, 0, -1,
                2147483647, 0,
                0, "0",
                0, "[]", 0,
                member_count + 1,
            ),
        )


def _get_title_by_cdekey(conn, cde_key):
    cur = conn.execute(
        "SELECT p_titles_0_nominal FROM Entries WHERE p_cdeKey = ?",
        (cde_key,),
    )
    row = cur.fetchone()
    return row["p_titles_0_nominal"] if row else "(unknown)"


def _series_membership(conn, cde_key):
    cur = conn.execute(
        "SELECT d_seriesId FROM Series WHERE d_itemCdeKey = ?",
        (cde_key,),
    )
    row = cur.fetchone()
    if row:
        return f"  [IN SERIES: {row['d_seriesId']}]"
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Kindle Series Manager - manage series grouping in cc.db"
    )
    parser.add_argument(
        "--db", type=Path, default=DB_PATH, help="Path to cc.db (default: ./cc.db)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("diagnose", help="Show existing series data and list books")

    p_list = sub.add_parser("list", help="List books with optional filter")
    p_list.add_argument("--filter", "-f", help="Filter by title substring")

    p_add = sub.add_parser("add-series", help="Add books to a series")
    p_add.add_argument("--name", required=True, help="Series display name")
    p_add.add_argument(
        "--books", required=True,
        help="Comma-separated list of p_cdeKey values (in series order)",
    )
    p_add.add_argument(
        "--asin", help="Use a real Amazon series ASIN as the cdeKey instead of generating one",
    )

    p_rm = sub.add_parser("remove-series", help="Remove a series or books from it")
    p_rm.add_argument(
        "--series-id", required=True,
        help="Full series ID (urn:collection:1:asin-...)",
    )
    p_rm.add_argument(
        "--books",
        help="Comma-separated cdeKeys to remove (omit to delete whole series)",
    )

    p_import = sub.add_parser(
        "import-calibre", help="Import series from Calibre metadata.db"
    )
    p_import.add_argument(
        "--calibre-db", required=True, help="Path to Calibre metadata.db",
    )
    p_import.add_argument(
        "--force", action="store_true", help="Overwrite existing series entries"
    )

    p_dump = sub.add_parser("dump", help="Dump full entry details by cdeKey")
    p_dump.add_argument("cde_key", help="The p_cdeKey value")

    args = parser.parse_args()

    commands = {
        "diagnose": diagnose,
        "list": list_books,
        "add-series": add_series,
        "remove-series": remove_series,
        "import-calibre": import_calibre,
        "dump": dump_entry,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
