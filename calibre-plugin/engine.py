#!/usr/bin/env python
"""Talks to the Kindle Series Manager web UI and plans the series to send.

No calibre imports here, so the matching and planning logic can be tested on
its own (tests/test_calibre_plugin.py).

The Kindle side is the KUAL extension's web server:
  GET  /cgi-bin/library_json.cgi   sideloaded books + existing series (JSON)
  POST /cgi-bin/create.cgi         create or replace one series
"""
import json
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SERIES_ID_PREFIX = "urn:collection:1:asin-"

# plan statuses
NEW = "new"
UPDATE = "update"
UNCHANGED = "unchanged"
TOO_FEW = "too_few"


class KindleError(Exception):
    pass


# ---------------------------------------------------------------- HTTP client

class KindleClient:

    def __init__(self, host, port=8080, timeout=15):
        host = (host or "").strip()
        if not host:
            raise KindleError("Set the Kindle's address in Configure first.")
        host = re.sub(r"^https?://", "", host).rstrip("/")
        if ":" not in host:
            host = "%s:%s" % (host, port)
        self.base = "http://" + host
        self.timeout = timeout

    def _request(self, path, data=None, timeout=None):
        req = Request(self.base + path, data=data)
        if data is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urlopen(req, timeout=timeout or self.timeout) as r:
                return r.read().decode("utf-8", "replace")
        except HTTPError as e:
            if e.code == 404:
                raise KindleError(
                    "%s was not found on the Kindle. Update the Kindle Series "
                    "Manager KUAL extension to the latest release." % path)
            raise KindleError("The Kindle answered HTTP %d for %s." % (e.code, path))
        except (URLError, OSError) as e:
            raise KindleError(
                "Could not reach the Kindle at %s (%s).\n\nOn the Kindle, open "
                "KUAL > Kindle Series Manager > Start Web UI, and check that the "
                "address in Configure matches the one shown in that menu."
                % (self.base, getattr(e, "reason", e)))

    def library(self):
        """{'books': [...], 'series': [...]} from library_json.cgi."""
        text = self._request("/cgi-bin/library_json.cgi")
        try:
            # strict=False: titles may contain control characters
            data = json.loads(text, strict=False)
        except ValueError:
            raise KindleError("The Kindle sent an unreadable library list:\n"
                              + text[:300])
        if data.get("error"):
            raise KindleError(data["error"])
        return data

    def send_series(self, name, books, edit_id="", badge_mode="none", asin=""):
        """Create (or with edit_id, replace) one series.

        books: [(cdeKey, position)] with integer positions starting at 1.
        create.cgi stops the Kindle's library service while it writes, so this
        gets a longer timeout than a read."""
        body = urlencode([
            ("name", name),
            ("asin", asin or ""),
            ("books", ",".join("%s:%d" % (k, p) for k, p in books)),
            ("edit_id", edit_id or ""),
            ("badge_mode", badge_mode or "none"),
        ]).encode("utf-8")
        text = self._request("/cgi-bin/create.cgi", data=body,
                             timeout=max(self.timeout, 120))
        # the reply can start with noise from mntroot/sqlite3; the result is
        # the last line, and any "Error: ..." line means nothing was saved
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in lines:
            if ln.lower().startswith("error"):
                raise KindleError(ln)
        if not lines:
            raise KindleError("The Kindle did not answer.")
        return lines[-1]


# ------------------------------------------------------------------- matching

def norm(s):
    """Loose comparison key: case, accents, punctuation and spacing ignored."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    # apostrophes and quotes join words ("Carl's", Hebrew ג'ון, צה"ל)
    s = re.sub("['\"‘’“”׳״]", "", s)
    s = re.sub(r"[\W_]+", " ", s.casefold(), flags=re.UNICODE)
    return " ".join(s.split())


def author_keys(names):
    """Comparison keys for author names, word order ignored, so that
    "Le Guin, Ursula K." matches "Ursula K. Le Guin"."""
    out = set()
    for n in names or ():
        k = norm(n)
        if k:
            out.add(" ".join(sorted(k.split())))
    return out


def index_kindle(kindle_books):
    """Lookup tables over the Kindle's books."""
    by_key, by_loc, by_title = {}, {}, {}
    for b in kindle_books:
        key = b.get("key") or ""
        if not key:
            continue
        by_key[key.upper()] = b
        loc = b.get("location") or ""
        if loc:
            by_loc[loc] = b
        by_title.setdefault(norm(b.get("title")), []).append(b)
    return {"key": by_key, "location": by_loc, "title": by_title}


def match_book(book, index, match_title=True):
    """The Kindle book for one calibre book, as (kindle_book, how) or
    (None, reason).

    book: {'uuid', 'identifiers', 'lpaths', 'title', 'authors', 'author_sort'}
    1. cdeKey: calibre writes the book's uuid (or its Amazon id) into the
       files it sends, and the Kindle uses that as the book's cdeKey.
    2. file path: the paths calibre's device view matched to this book.
    3. title, only when unambiguous; with several hits the author decides."""
    candidates = [book.get("uuid") or ""]
    for k, v in (book.get("identifiers") or {}).items():
        if k in ("amazon", "mobi-asin") or k.startswith("amazon_"):
            candidates.append(str(v))
    for c in candidates:
        hit = index["key"].get(c.strip().upper()) if c else None
        if hit:
            return hit, "key"

    for lpath in book.get("lpaths") or ():
        lp = lpath.replace("\\", "/").lstrip("/")
        for loc in ("/mnt/us/" + lp, "/mnt/us/documents/" + lp):
            hit = index["location"].get(loc)
            if hit:
                return hit, "path"

    if not match_title:
        return None, "not found"
    hits = index["title"].get(norm(book.get("title")), [])
    if len(hits) == 1:
        return hits[0], "title"
    if hits:
        mine = author_keys(list(book.get("authors") or ()) + [book.get("author_sort") or ""])
        same = [h for h in hits if author_keys([h.get("author")]) & mine]
        if len(same) == 1:
            return same[0], "title"
        return None, "same title on several Kindle books"
    return None, "not found"


# ------------------------------------------------------------------- planning

def series_key(name):
    """The series cdeKey create.cgi derives from a name (no ASIN)."""
    up = "".join(chr(ord(c) - 32) if "a" <= c <= "z" else c for c in name)
    return "SL-" + up.replace(" ", "-").replace("'", "")


def positions(indices):
    """Kindle positions (whole numbers from 1) for books in reading order.
    calibre's own numbers are kept when they are distinct whole numbers;
    otherwise (1.5, duplicates, ...) the books are numbered 1, 2, 3, ..."""
    try:
        whole = [int(i) for i in indices]
    except (TypeError, ValueError):
        whole = []
    if (whole and all(float(i) == w and w >= 1 for i, w in zip(indices, whole))
            and len(set(whole)) == len(whole)):
        return whole
    return list(range(1, len(indices) + 1))


def plan(calibre_books, kindle, match_title=True, min_books=2):
    """What to send: one entry per calibre series that has books on the Kindle.

    calibre_books: dicts with 'id', 'title', 'authors', 'author_sort', 'uuid',
        'identifiers', 'lpaths', 'series', 'series_index'
    kindle: library_json.cgi data
    Returns (entries, unmatched) where entries are dicts:
        name, status, edit_id, asin, books [(cdeKey, position)],
        titles [(position, kindle title, calibre id, how)],
        missing [calibre titles not found on the Kindle], other_series
    """
    index = index_kindle(kindle.get("books") or [])
    existing = {}  # norm(name) -> series id
    for s in kindle.get("series") or []:
        if s.get("name"):
            existing.setdefault(norm(s["name"]), s["id"])
    members = {}   # series id -> {cdeKey: position label}
    for b in kindle.get("books") or []:
        if b.get("series"):
            members.setdefault(b["series"], {})[b["key"]] = b.get("position") or ""

    groups = {}
    for b in calibre_books:
        if b.get("series"):
            groups.setdefault(b["series"], []).append(b)

    entries, unmatched = [], []
    for name in sorted(groups, key=norm):
        books = sorted(groups[name], key=lambda b: (b.get("series_index") or 0,
                                                    norm(b.get("title"))))
        found, missing, used = [], [], set()
        for b in books:
            kb, how = match_book(b, index, match_title)
            if kb is None or kb["key"] in used:
                missing.append(b.get("title") or "")
                unmatched.append((name, b.get("title") or "", how if kb is None
                                  else "matched another book of the series"))
                continue
            used.add(kb["key"])
            found.append((b, kb, how))

        if not found:
            continue
        pos = positions([b.get("series_index") or 0 for b, _, _ in found])
        send = [(kb["key"], p) for (_, kb, _), p in zip(found, pos)]

        sid = existing.get(norm(name)) or ""
        if not sid:
            guess = SERIES_ID_PREFIX + series_key(name)
            if guess in members:
                sid = guess
        if len(found) < min_books:
            status = TOO_FEW
        elif not sid:
            status = NEW
        elif members.get(sid) == {k: str(p) for k, p in send}:
            status = UNCHANGED
        else:
            status = UPDATE

        other = sorted({kb.get("series") for _, kb, _ in found
                        if kb.get("series") and kb.get("series") != sid})
        # keep a series' real Amazon ASIN, else create.cgi would re-key it
        key = sid[len(SERIES_ID_PREFIX):] if sid.startswith(SERIES_ID_PREFIX) else ""
        entries.append({
            "name": name,
            "status": status,
            "edit_id": sid,
            "asin": key if key and not key.startswith("SL-") else "",
            "books": send,
            "titles": [(p, kb.get("title") or "", b.get("id"), how)
                       for (b, kb, how), p in zip(found, pos)],
            "missing": missing,
            "other_series": other,
        })
    return entries, unmatched
