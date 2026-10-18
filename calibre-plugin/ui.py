#!/usr/bin/env python
"""The toolbar action: send series to the Kindle / open the web UI / configure."""
from calibre.gui2 import Dispatcher, error_dialog, info_dialog, open_url
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.threaded_jobs import ThreadedJob

from qt.core import (QDialog, QVBoxLayout, QLabel, QTreeWidget,
                     QTreeWidgetItem, QDialogButtonBox, QTimer, QUrl, Qt,
                     QMenu)

from calibre_plugins.kindle_series_manager.config import prefs

STATUS_LABEL = {
    "new": "New",
    "update": "Update",
    "unchanged": "Already on the Kindle",
    "too_few": "Too few books on the Kindle",
}
HOW_LABEL = {"key": "calibre id", "path": "file path", "title": "title"}


class KindleSeriesAction(InterfaceAction):

    name = "Kindle Series Manager"
    action_spec = ("Kindle Series", "series.png",
                   "Group the selected books' series on your Kindle", None)
    action_type = "current"

    def genesis(self):
        m = self.qaction.menu()
        if m is None:
            m = QMenu(self.gui)
            self.qaction.setMenu(m)
        self.menu = m
        m.addAction("Send series of selected books to Kindle…",
                    lambda: self.start(selected=True))
        m.addAction("Send all series to Kindle…",
                    lambda: self.start(selected=False))
        m.addAction("Open Kindle Series Manager web UI", self.open_web_ui)
        m.addSeparator()
        m.addAction("Configure…", self.show_config)
        # triggered emits a `checked` bool; do not pass it on
        self.qaction.triggered.connect(lambda checked=False: self.start(selected=True))

    # ---------------------------------------------------------------- simple
    def show_config(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def _client(self, timeout=15):
        from calibre_plugins.kindle_series_manager.engine import KindleClient
        return KindleClient(prefs["host"], prefs["port"], timeout=timeout)

    def _check_host(self):
        if prefs["host"].strip():
            return True
        error_dialog(self.gui, "Kindle Series Manager",
                     "Set the Kindle's address first (Configure). It is shown "
                     "on the Kindle in KUAL > Kindle Series Manager after "
                     "Start Web UI.", show=True)
        self.show_config()
        return bool(prefs["host"].strip())

    def open_web_ui(self):
        if self._check_host():
            open_url(QUrl(self._client().base + "/"))

    # ------------------------------------------------------ collect calibre
    def _calibre_books(self, selected):
        """The library books to send, with what matching needs. With a
        selection, every book of the selected books' series is included: a
        series is sent whole, else the Kindle copy would lose its other books."""
        db = self.gui.current_db.new_api
        if selected:
            ids = list(self.gui.library_view.get_selected_ids())
            if not ids:
                return None
        series = db.all_field_for("series", db.all_book_ids())
        if selected:
            names = {series.get(i) for i in ids} - {None, ""}
            ids = [i for i, s in series.items() if s in names]
        else:
            ids = [i for i, s in series.items() if s]

        lpaths = self._device_lpaths()
        out = []
        for i in ids:
            out.append({
                "id": i,
                "title": db.field_for("title", i) or "",
                "authors": list(db.field_for("authors", i) or ()),
                "author_sort": db.field_for("author_sort", i) or "",
                "uuid": db.field_for("uuid", i) or "",
                "identifiers": dict(db.field_for("identifiers", i) or {}),
                "series": db.field_for("series", i) or "",
                "series_index": db.field_for("series_index", i) or 0,
                "lpaths": lpaths.get(i, []),
            })
        return out

    def _device_lpaths(self):
        """{library id: [path on the device]} from calibre's own matching of a
        connected device's books (the Device view)."""
        out = {}
        try:
            if not self.gui.device_manager.is_device_connected:
                return out
            booklists = self.gui.booklists()
        except Exception:  # noqa
            return out
        for bl in booklists or ():
            for book in (bl or ()):
                bid = getattr(book, "application_id", None)
                lpath = getattr(book, "lpath", None)
                if bid is not None and lpath and getattr(book, "in_library", None):
                    out.setdefault(bid, []).append(lpath)
        return out

    # ---------------------------------------------------------- step 1: read
    def start(self, selected=True):
        if not self._check_host():
            return
        books = self._calibre_books(selected)
        if books is None:
            return error_dialog(self.gui, "No selection",
                                "Select one or more books in the library first.",
                                show=True)
        if not books:
            return info_dialog(
                self.gui, "No series",
                "None of these books is part of a series in calibre.", show=True)
        job = ThreadedJob(
            "kindle_series_read", "Kindle Series: read the Kindle library",
            self._do_read, (), {},
            # the callback runs in the worker thread; Dispatcher moves it to
            # the GUI thread
            Dispatcher(self._read_done))
        job.ksm_books = books
        self.gui.job_manager.run_threaded_job(job)
        self.gui.status_bar.show_message("Reading the Kindle library…", 3000)

    def _do_read(self, notifications=None, abort=None, log=None):
        return self._client().library()

    def _read_done(self, job):
        if job.failed:
            return self._failed(job)
        from calibre_plugins.kindle_series_manager.engine import plan
        entries, unmatched = plan(job.ksm_books, job.result or {},
                                  match_title=bool(prefs["match_by_title"]),
                                  min_books=int(prefs["min_books"]))
        # open the dialog after this callback has returned
        QTimer.singleShot(0, lambda: self._preview(entries, unmatched))

    def _failed(self, job):
        msg = str(getattr(job, "exception", "") or "Failed.")
        QTimer.singleShot(0, lambda: error_dialog(
            self.gui, "Kindle Series Manager", msg,
            det_msg=getattr(job, "traceback", "") or "", show=True))

    # ------------------------------------------------------- step 2: confirm
    def _preview(self, entries, unmatched):
        if not entries:
            return info_dialog(
                self.gui, "Nothing to send",
                "None of these series' books were found on the Kindle "
                "(%d books not found). Send the books to the Kindle first."
                % len(unmatched), show=True)
        d = PreviewDialog(self.gui, entries)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = d.chosen()
        if not chosen:
            return
        job = ThreadedJob(
            "kindle_series_send", "Kindle Series: send %d series" % len(chosen),
            self._do_send, (chosen, prefs["badge_mode"]), {},
            Dispatcher(self._send_done))
        self.gui.job_manager.run_threaded_job(job)
        self.gui.status_bar.show_message(
            "Sending %d series to the Kindle…" % len(chosen), 3000)

    # ---------------------------------------------------------- step 3: send
    def _do_send(self, entries, badge_mode, notifications=None, abort=None,
                 log=None):
        from calibre_plugins.kindle_series_manager.engine import KindleError
        client = self._client()
        results = []
        for n, e in enumerate(entries):
            if abort is not None and abort.is_set():
                break
            if notifications is not None:
                notifications.put((n / float(len(entries)), e["name"]))
            try:
                msg = client.send_series(e["name"], e["books"], e["edit_id"],
                                         badge_mode, e["asin"])
                results.append((e["name"], True, msg))
            except KindleError as err:
                results.append((e["name"], False, str(err)))
            if log is not None:
                log(("OK   " if results[-1][1] else "FAIL ")
                    + e["name"] + ": " + results[-1][2])
        return results

    def _send_done(self, job):
        if job.failed:
            return self._failed(job)
        results = job.result or []
        ok = [r for r in results if r[1]]
        bad = [r for r in results if not r[1]]
        det = "\n".join("%s %s: %s" % ("OK  " if r[1] else "FAIL", r[0], r[2])
                        for r in results)
        if bad:
            QTimer.singleShot(0, lambda: error_dialog(
                self.gui, "Kindle Series Manager",
                "%d series sent, %d failed. See the details." % (len(ok), len(bad)),
                det_msg=det, show=True))
        else:
            self.gui.status_bar.show_message(
                "Kindle Series: %d series sent. The Kindle library refreshes "
                "in a few seconds." % len(ok), 10000)


class PreviewDialog(QDialog):
    """Lists the series to send; the user picks which ones."""

    def __init__(self, parent, entries):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Send series to Kindle")
        self.resize(720, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Ticked series are created on the Kindle, or replaced when a series "
            "with the same name is already there. Books not on the Kindle are "
            "left out."))

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Series / book", "Status"])
        self.tree.setColumnWidth(0, 470)
        lay.addWidget(self.tree, 1)

        self.items = []
        for e in entries:
            it = QTreeWidgetItem(self.tree, [
                "%s  (%d)" % (e["name"], len(e["books"])),
                STATUS_LABEL.get(e["status"], e["status"])])
            if e["status"] == "too_few":
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsUserCheckable
                            & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(0, Qt.CheckState.Checked
                                 if e["status"] in ("new", "update")
                                 else Qt.CheckState.Unchecked)
            for pos, title, _bid, how in e["titles"]:
                QTreeWidgetItem(it, ["%d. %s" % (pos, title),
                                     "matched by " + HOW_LABEL.get(how, how)])
            for title in e["missing"]:
                c = QTreeWidgetItem(it, ["%s" % title, "not on the Kindle"])
                c.setDisabled(True)
            if e["other_series"]:
                QTreeWidgetItem(it, [
                    "Some of these books are also in another Kindle series", ""])
            self.items.append((it, e))

        self.summary = QLabel()
        lay.addWidget(self.summary)
        self.tree.itemChanged.connect(self._update_summary)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        self.ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._update_summary()

    def chosen(self):
        return [e for it, e in self.items
                if (it.flags() & Qt.ItemFlag.ItemIsUserCheckable)
                and it.checkState(0) == Qt.CheckState.Checked]

    def _update_summary(self, *args):
        n = len(self.chosen())
        self.ok.setText("Send %d series" % n)
        self.ok.setEnabled(n > 0)
        self.summary.setText(
            "The Kindle's library service restarts once per series while it "
            "is written; this takes a few seconds each.")
