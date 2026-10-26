"""Tests for the calibre plugin's matching and planning (calibre-plugin/engine.py).

engine.py has no calibre imports, so it is loaded straight from its file."""

import importlib.util
from pathlib import Path

import pytest

ENGINE = Path(__file__).parent.parent / "calibre-plugin" / "engine.py"
_spec = importlib.util.spec_from_file_location("ksm_engine", ENGINE)
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)

SID = "urn:collection:1:asin-SL-DCC"


def kbook(key, title, author="", location=None, series="", position=""):
    return {"key": key, "type": "EBOK", "title": title, "author": author,
            "location": location or "/mnt/us/documents/%s.azw3" % key,
            "series": series, "position": position}


def cbook(bid, title, series="DCC", index=1.0, uuid="", authors=(),
          identifiers=None, lpaths=()):
    return {"id": bid, "title": title, "authors": list(authors),
            "author_sort": "", "uuid": uuid, "identifiers": identifiers or {},
            "series": series, "series_index": index, "lpaths": list(lpaths)}


@pytest.fixture
def kindle():
    return {"books": [
        kbook("aaaa-1111", "Dungeon Crawler Carl", "Matt Dinniman"),
        kbook("B08PBCD9Y7", "Carl's Doomsday Scenario", "Matt Dinniman"),
        kbook("cccc-3333", "The Dungeon Anarchist's Cookbook", "Matt Dinniman",
              location="/mnt/us/documents/Anarchist - Matt Dinniman.azw3"),
        kbook("dddd-4444", "Dune", "Frank Herbert"),
        kbook("eeee-5555", "Dune", "Brian Herbert"),
    ], "series": []}


class TestNormalize:
    def test_case_punctuation_spacing(self):
        assert engine.norm("Carl's  Doomsday-Scenario!") == engine.norm("carls doomsday scenario")

    def test_accents(self):
        assert engine.norm("Café") == engine.norm("cafe")

    def test_hebrew_kept(self):
        assert engine.norm("המעניק") == "המעניק"

    def test_author_word_order(self):
        assert engine.author_keys(["Le Guin, Ursula K."]) == engine.author_keys(["Ursula K. Le Guin"])


class TestMatch:
    def idx(self, kindle):
        return engine.index_kindle(kindle["books"])

    def test_by_uuid_any_case(self, kindle):
        hit, how = engine.match_book(cbook(1, "x", uuid="AAAA-1111"), self.idx(kindle))
        assert (hit["key"], how) == ("aaaa-1111", "key")

    def test_by_amazon_identifier(self, kindle):
        b = cbook(1, "x", identifiers={"mobi-asin": "B08PBCD9Y7"})
        hit, how = engine.match_book(b, self.idx(kindle))
        assert (hit["key"], how) == ("B08PBCD9Y7", "key")

    def test_by_device_path(self, kindle):
        b = cbook(1, "x", lpaths=["documents/Anarchist - Matt Dinniman.azw3"])
        hit, how = engine.match_book(b, self.idx(kindle))
        assert (hit["key"], how) == ("cccc-3333", "path")

    def test_by_title(self, kindle):
        hit, how = engine.match_book(cbook(1, "dungeon crawler carl"), self.idx(kindle))
        assert (hit["key"], how) == ("aaaa-1111", "title")

    def test_title_off(self, kindle):
        hit, _ = engine.match_book(cbook(1, "Dungeon Crawler Carl"), self.idx(kindle),
                                   match_title=False)
        assert hit is None

    def test_repeated_title_needs_author(self, kindle):
        hit, how = engine.match_book(cbook(1, "Dune"), self.idx(kindle))
        assert hit is None and "several" in how
        hit, _ = engine.match_book(cbook(1, "Dune", authors=["Herbert, Frank"]),
                                   self.idx(kindle))
        assert hit["key"] == "dddd-4444"


class TestSeriesKey:
    def test_matches_create_cgi(self):
        # create.cgi: tr 'a-z ' 'A-Z-' | tr -d "'" | sed 's/^/SL-/'
        assert engine.series_key("Carl's dungeon crawl") == "SL-CARLS-DUNGEON-CRAWL"

    def test_non_ascii_unchanged(self):
        assert engine.series_key("המעניק ab") == "SL-המעניק-AB"


class TestPositions:
    def test_whole_numbers_kept(self):
        assert engine.positions([1.0, 2.0, 4.0]) == [1, 2, 4]

    def test_fraction_renumbers(self):
        assert engine.positions([1.0, 1.5, 2.0]) == [1, 2, 3]

    def test_duplicates_renumber(self):
        assert engine.positions([1.0, 1.0]) == [1, 2]

    def test_zero_renumbers(self):
        assert engine.positions([0.0, 1.0]) == [1, 2]


class TestPlan:
    def books(self):
        return [
            cbook(1, "Dungeon Crawler Carl", index=1, uuid="aaaa-1111"),
            cbook(2, "Carl's Doomsday Scenario", index=2,
                  identifiers={"amazon": "B08PBCD9Y7"}),
            cbook(3, "Book Not On Kindle", index=3),
        ]

    def test_new_series(self, kindle):
        entries, unmatched = engine.plan(self.books(), kindle)
        assert len(entries) == 1
        e = entries[0]
        assert e["status"] == engine.NEW and e["edit_id"] == ""
        assert e["books"] == [("aaaa-1111", 1), ("B08PBCD9Y7", 2)]
        assert e["missing"] == ["Book Not On Kindle"]
        assert unmatched == [("DCC", "Book Not On Kindle", "not found")]

    def test_too_few(self, kindle):
        entries, _ = engine.plan(self.books()[:1], kindle, min_books=2)
        assert entries[0]["status"] == engine.TOO_FEW
        entries, _ = engine.plan(self.books()[:1], kindle, min_books=1)
        assert entries[0]["status"] == engine.NEW

    def test_nothing_on_kindle_skipped(self, kindle):
        entries, unmatched = engine.plan([cbook(9, "Nope", series="X")], kindle)
        assert entries == [] and len(unmatched) == 1

    def test_unchanged(self, kindle):
        for b in kindle["books"][:2]:
            b["series"] = SID
        kindle["books"][0]["position"] = "1"
        kindle["books"][1]["position"] = "2"
        kindle["series"] = [{"id": SID, "name": "DCC", "count": 2}]
        entries, _ = engine.plan(self.books(), kindle)
        assert entries[0]["status"] == engine.UNCHANGED
        assert entries[0]["edit_id"] == SID

    def test_update_by_name(self, kindle):
        sid = "urn:collection:1:asin-B0ABCDEF"
        kindle["books"][0].update(series=sid, position="1")
        kindle["series"] = [{"id": sid, "name": "dcc", "count": 1}]
        entries, _ = engine.plan(self.books(), kindle)
        e = entries[0]
        assert e["status"] == engine.UPDATE and e["edit_id"] == sid
        # a real Amazon ASIN is sent back so the series keeps its id
        assert e["asin"] == "B0ABCDEF"

    def test_update_by_generated_key(self, kindle):
        # series entry without a name row: found through its SL- key
        kindle["books"][0].update(series=SID, position="1")
        entries, _ = engine.plan(self.books(), kindle)
        assert entries[0]["status"] == engine.UPDATE
        assert entries[0]["edit_id"] == SID and entries[0]["asin"] == ""

    def test_other_series_reported(self, kindle):
        kindle["books"][0].update(series="urn:collection:1:asin-SL-OTHER", position="1")
        kindle["series"] = [{"id": "urn:collection:1:asin-SL-OTHER", "name": "Other", "count": 1}]
        entries, _ = engine.plan(self.books(), kindle)
        assert entries[0]["other_series"] == ["urn:collection:1:asin-SL-OTHER"]

    def test_one_kindle_book_used_once(self, kindle):
        books = [cbook(1, "Dungeon Crawler Carl", index=1),
                 cbook(2, "Dungeon Crawler Carl", index=2)]
        entries, unmatched = engine.plan(books, kindle, min_books=1)
        assert len(entries[0]["books"]) == 1
        assert unmatched[0][2] == "matched another book of the series"


class TestClient:
    def test_base_url(self):
        assert engine.KindleClient("192.168.1.5").base == "http://192.168.1.5:8080"
        assert engine.KindleClient("http://k:9000/").base == "http://k:9000"

    def test_no_host(self):
        with pytest.raises(engine.KindleError):
            engine.KindleClient(" ")

    def test_send_reads_last_line(self, monkeypatch):
        c = engine.KindleClient("k")
        sent = {}

        def fake(path, data=None, timeout=None):
            sent["path"], sent["data"] = path, data
            return "system: I mntroot:def:Making root filesystem writeable\n" \
                   "  defensive off\nCreated 'DCC' with 2 books.\n"
        monkeypatch.setattr(c, "_request", fake)
        assert c.send_series("DCC", [("a", 1), ("b", 2)]) == "Created 'DCC' with 2 books."
        assert sent["path"] == "/cgi-bin/create.cgi"
        assert b"books=a%3A1%2Cb%3A2" in sent["data"]

    def test_send_error_anywhere(self, monkeypatch):
        c = engine.KindleClient("k")
        monkeypatch.setattr(c, "_request", lambda *a, **k:
                            "noise\nError: could not save the series\n")
        with pytest.raises(engine.KindleError, match="could not save"):
            c.send_series("DCC", [("a", 1)])

    def test_library_error(self, monkeypatch):
        c = engine.KindleClient("k")
        monkeypatch.setattr(c, "_request", lambda *a, **k: '{"error":"old firmware"}')
        with pytest.raises(engine.KindleError, match="old firmware"):
            c.library()
