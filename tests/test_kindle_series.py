"""Tests for kindle_series.py CLI tool."""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = str(Path(__file__).parent.parent / "kindle_series.py")


def run_cli(*args, db=None):
    cmd = [sys.executable, SCRIPT]
    if db:
        cmd += ["--db", str(db)]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def get_conn(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


class TestDiagnose:
    def test_diagnose_runs(self, test_db):
        result = run_cli("diagnose", db=test_db)
        assert result.returncode == 0
        assert "EXISTING SERIES TABLE DATA" in result.stdout
        assert "ALL SIDELOADED BOOKS" in result.stdout

    def test_diagnose_shows_books(self, test_db):
        result = run_cli("diagnose", db=test_db)
        assert "Dungeon Crawler Carl" in result.stdout
        assert "Legionnaire" in result.stdout

    def test_diagnose_empty_series(self, test_db):
        result = run_cli("diagnose", db=test_db)
        assert "(empty - no series data found)" in result.stdout


class TestList:
    def test_list_all(self, test_db):
        result = run_cli("list", db=test_db)
        assert result.returncode == 0
        assert "B08BKGYQXW" in result.stdout

    def test_list_filter(self, test_db):
        result = run_cli("list", "--filter", "Dungeon", db=test_db)
        assert result.returncode == 0
        assert "Dungeon Crawler Carl" in result.stdout
        assert "Legionnaire" not in result.stdout

    def test_list_filter_no_match(self, test_db):
        result = run_cli("list", "--filter", "NONEXISTENT", db=test_db)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestAddSeries:
    def test_add_series_basic(self, test_db):
        result = run_cli(
            "add-series", "--name", "Dungeon Crawler Carl",
            "--books", "B08BKGYQXW,B08PBCD9Y7,B08V4QSV6W",
            db=test_db,
        )
        assert result.returncode == 0
        assert "3 books added to series" in result.stdout

        conn = get_conn(test_db)
        rows = conn.execute("SELECT * FROM Series ORDER BY d_itemPosition").fetchall()
        assert len(rows) == 3
        assert rows[0]["d_itemCdeKey"] == "B08BKGYQXW"
        assert rows[1]["d_itemCdeKey"] == "B08PBCD9Y7"
        assert rows[2]["d_itemCdeKey"] == "B08V4QSV6W"

        series_entry = conn.execute(
            "SELECT * FROM Entries WHERE p_type = 'Entry:Item:Series'"
        ).fetchone()
        assert series_entry is not None
        assert series_entry["p_titles_0_nominal"] == "Dungeon Crawler Carl"
        assert series_entry["p_memberCount"] == 3
        conn.close()

    def test_add_series_with_asin(self, test_db):
        result = run_cli(
            "add-series", "--name", "DCC", "--asin", "B09DD17H3N",
            "--books", "B08BKGYQXW,B08PBCD9Y7",
            db=test_db,
        )
        assert result.returncode == 0

        conn = get_conn(test_db)
        row = conn.execute(
            "SELECT * FROM Series WHERE d_seriesId = 'urn:collection:1:asin-B09DD17H3N'"
        ).fetchone()
        assert row is not None
        conn.close()

    def test_add_series_invalid_book(self, test_db):
        result = run_cli(
            "add-series", "--name", "Bad Series",
            "--books", "NONEXISTENT_KEY",
            db=test_db,
        )
        assert result.returncode != 0
        assert "No book found" in result.stderr or "No book found" in result.stdout

    def test_add_series_sets_series_state(self, test_db):
        run_cli(
            "add-series", "--name", "Test",
            "--books", "B08BKGYQXW,B08PBCD9Y7",
            db=test_db,
        )
        conn = get_conn(test_db)
        for key in ["B08BKGYQXW", "B08PBCD9Y7"]:
            row = conn.execute(
                "SELECT p_seriesState FROM Entries WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
                (key,),
            ).fetchone()
            assert row["p_seriesState"] == 0
        unaffected = conn.execute(
            "SELECT p_seriesState FROM Entries WHERE p_cdeKey = 'B071GN8Y4G' AND p_type = 'Entry:Item'"
        ).fetchone()
        assert unaffected["p_seriesState"] == 1
        conn.close()

    def test_add_series_positions(self, test_db):
        run_cli(
            "add-series", "--name", "Ordered",
            "--books", "B08V4QSV6W,B08BKGYQXW",
            db=test_db,
        )
        conn = get_conn(test_db)
        rows = conn.execute(
            "SELECT d_itemCdeKey, d_itemPosition, d_itemPositionLabel "
            "FROM Series ORDER BY d_itemPosition"
        ).fetchall()
        assert rows[0]["d_itemCdeKey"] == "B08V4QSV6W"
        assert rows[0]["d_itemPosition"] == 0.0
        assert rows[0]["d_itemPositionLabel"] == "1"
        assert rows[1]["d_itemCdeKey"] == "B08BKGYQXW"
        assert rows[1]["d_itemPosition"] == 1.0
        assert rows[1]["d_itemPositionLabel"] == "2"
        conn.close()


class TestRemoveSeries:
    def _create_series(self, test_db):
        run_cli(
            "add-series", "--name", "DCC",
            "--books", "B08BKGYQXW,B08PBCD9Y7,B08V4QSV6W",
            db=test_db,
        )

    def test_remove_entire_series(self, test_db):
        self._create_series(test_db)
        result = run_cli(
            "remove-series", "--series-id", "urn:collection:1:asin-SL-DCC",
            db=test_db,
        )
        assert result.returncode == 0
        assert "Deleted series" in result.stdout

        conn = get_conn(test_db)
        assert conn.execute("SELECT COUNT(*) FROM Series").fetchone()[0] == 0
        series_entry = conn.execute(
            "SELECT * FROM Entries WHERE p_type = 'Entry:Item:Series'"
        ).fetchone()
        assert series_entry is None
        for key in ["B08BKGYQXW", "B08PBCD9Y7", "B08V4QSV6W"]:
            row = conn.execute(
                "SELECT p_seriesState FROM Entries WHERE p_cdeKey = ? AND p_type = 'Entry:Item'",
                (key,),
            ).fetchone()
            assert row["p_seriesState"] == 1
        conn.close()

    def test_remove_single_book(self, test_db):
        self._create_series(test_db)
        result = run_cli(
            "remove-series", "--series-id", "urn:collection:1:asin-SL-DCC",
            "--books", "B08PBCD9Y7",
            db=test_db,
        )
        assert result.returncode == 0

        conn = get_conn(test_db)
        remaining = conn.execute("SELECT COUNT(*) FROM Series").fetchone()[0]
        assert remaining == 2
        removed_state = conn.execute(
            "SELECT p_seriesState FROM Entries WHERE p_cdeKey = 'B08PBCD9Y7' AND p_type = 'Entry:Item'"
        ).fetchone()
        assert removed_state["p_seriesState"] == 1
        conn.close()

    def test_remove_nonexistent_series(self, test_db):
        result = run_cli(
            "remove-series", "--series-id", "urn:collection:1:asin-FAKE",
            db=test_db,
        )
        assert result.returncode != 0


class TestDump:
    def test_dump_existing(self, test_db):
        result = run_cli("dump", "B08BKGYQXW", db=test_db)
        assert result.returncode == 0
        assert "p_type=Entry:Item" in result.stdout.replace(" ", "").replace("=", "=")
        assert "Dungeon Crawler Carl" in result.stdout

    def test_dump_nonexistent(self, test_db):
        result = run_cli("dump", "NONEXISTENT", db=test_db)
        assert result.returncode == 0
        assert "No entry found" in result.stdout


class TestSeriesKeyGeneration:
    def test_generated_key_format(self, test_db):
        run_cli(
            "add-series", "--name", "The Expanse",
            "--books", "B08BKGYQXW",
            db=test_db,
        )
        conn = get_conn(test_db)
        row = conn.execute("SELECT d_seriesId FROM Series").fetchone()
        assert row["d_seriesId"] == "urn:collection:1:asin-SL-THE-EXPANSE"
        conn.close()

    def test_asin_overrides_generated_key(self, test_db):
        run_cli(
            "add-series", "--name", "The Expanse", "--asin", "B09DD17H3N",
            "--books", "B08BKGYQXW",
            db=test_db,
        )
        conn = get_conn(test_db)
        row = conn.execute("SELECT d_seriesId FROM Series").fetchone()
        assert row["d_seriesId"] == "urn:collection:1:asin-B09DD17H3N"
        conn.close()


class TestBooksSeriesQuery:
    """Validate that the SQL query used by books.cgi correctly reports series membership."""

    BOOKS_QUERY = (
        "SELECT p_cdeKey, p_titles_0_nominal, "
        "COALESCE((SELECT GROUP_CONCAT("
        "COALESCE((SELECT p_titles_0_nominal FROM Entries e2 "
        "WHERE e2.p_cdeKey=REPLACE(s.d_seriesId,'urn:collection:1:asin-','') "
        "AND e2.p_type='Entry:Item:Series'), '?'), ', ') "
        "FROM Series s WHERE s.d_itemCdeKey=Entries.p_cdeKey), '') "
        "FROM Entries WHERE p_type='Entry:Item' AND p_isVisibleInHome=1 "
        "AND p_location LIKE '/mnt/us/documents/%' ORDER BY p_titles_0_nominal"
    )

    def test_no_series_returns_empty_string(self, test_db):
        conn = sqlite3.connect(str(test_db))
        rows = conn.execute(self.BOOKS_QUERY).fetchall()
        conn.close()
        assert len(rows) == 5
        for _key, _title, series in rows:
            assert series == ""

    def test_books_in_series_return_series_name(self, test_db):
        run_cli(
            "add-series", "--name", "Dungeon Crawler Carl",
            "--books", "B08BKGYQXW,B08PBCD9Y7,B08V4QSV6W",
            db=test_db,
        )
        conn = sqlite3.connect(str(test_db))
        rows = conn.execute(self.BOOKS_QUERY).fetchall()
        conn.close()

        result = {key: series for key, _title, series in rows}
        assert result["B08BKGYQXW"] == "Dungeon Crawler Carl"
        assert result["B08PBCD9Y7"] == "Dungeon Crawler Carl"
        assert result["B08V4QSV6W"] == "Dungeon Crawler Carl"
        assert result["B071GN8Y4G"] == ""
        assert result["B09DD17H3N"] == ""

    def test_book_in_multiple_series(self, test_db):
        run_cli(
            "add-series", "--name", "Series A",
            "--books", "B08BKGYQXW,B08PBCD9Y7",
            db=test_db,
        )
        run_cli(
            "add-series", "--name", "Series B",
            "--books", "B08BKGYQXW,B08V4QSV6W",
            db=test_db,
        )
        conn = sqlite3.connect(str(test_db))
        rows = conn.execute(self.BOOKS_QUERY).fetchall()
        conn.close()

        result = {key: series for key, _title, series in rows}
        parts = set(result["B08BKGYQXW"].split(", "))
        assert parts == {"Series A", "Series B"}
        assert result["B08PBCD9Y7"] == "Series A"
        assert result["B08V4QSV6W"] == "Series B"
        assert result["B071GN8Y4G"] == ""


class TestMissingDb:
    def test_missing_db_exits(self, tmp_path):
        result = run_cli("diagnose", db=tmp_path / "nonexistent.db")
        assert result.returncode != 0
