#!/usr/bin/env python
"""Persistent settings + the configuration widget."""
from calibre.utils.config import JSONConfig

from qt.core import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                     QLineEdit, QComboBox, QLabel, QPushButton, QCheckBox,
                     QSpinBox)

# stored under the calibre config dir as plugins/kindle_series_manager.json
prefs = JSONConfig("plugins/kindle_series_manager")

prefs.defaults["host"] = ""              # Kindle IP, as shown in the KUAL menu
prefs.defaults["port"] = 8080
prefs.defaults["badge_mode"] = "none"    # none | ku | kupr
prefs.defaults["match_by_title"] = True
prefs.defaults["min_books"] = 2          # smallest series worth grouping

BADGES = [
    ("none", "None"),
    ("ku", "Kindle Unlimited"),
    ("kupr", "Kindle Unlimited + Prime Reading"),
]

HELP_HTML = (
    "Needs a jailbroken Kindle (firmware 5.13.4 or later) with the "
    "<a href='https://github.com/mlapaglia/kindle-series-manager'>Kindle Series "
    "Manager</a> KUAL extension. On the Kindle open <i>KUAL &gt; Kindle Series "
    "Manager &gt; Start Web UI</i>; the menu then shows the address "
    "(e.g. <code>http://192.168.1.20:8080/</code>). Enter it below. The Kindle "
    "and this computer must be on the same network. Also turn on "
    "<i>Settings &gt; Group Series in Library</i> on the Kindle.")


class ConfigWidget(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        lay = QVBoxLayout(self)

        help_lbl = QLabel(HELP_HTML)
        help_lbl.setWordWrap(True)
        help_lbl.setOpenExternalLinks(True)
        lay.addWidget(help_lbl)

        form = QFormLayout()
        lay.addLayout(form)

        row = QHBoxLayout()
        self.host = QLineEdit(prefs["host"])
        self.host.setPlaceholderText("192.168.1.20")
        row.addWidget(self.host, 1)
        row.addWidget(QLabel("Port:"))
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(prefs["port"]))
        row.addWidget(self.port)
        self.test_btn = QPushButton("Test connection")
        self.test_btn.clicked.connect(self.test_connection)
        row.addWidget(self.test_btn)
        form.addRow("Kindle address:", row)

        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        form.addRow("", self.test_result)

        self.badge = QComboBox()
        for key, label in BADGES:
            self.badge.addItem(label, key)
        i = self.badge.findData(prefs["badge_mode"])
        self.badge.setCurrentIndex(max(i, 0))
        form.addRow("Program badges:", self.badge)

        self.min_books = QSpinBox()
        self.min_books.setRange(1, 99)
        self.min_books.setValue(int(prefs["min_books"]))
        self.min_books.setSuffix(" books on the Kindle")
        self.min_books.setToolTip(
            "Series with fewer books on the Kindle are not grouped: a group with "
            "one book only hides that book one level deeper.")
        form.addRow("Group series with at least:", self.min_books)

        self.match_title = QCheckBox(
            "Also match books by title (and author when titles repeat)")
        self.match_title.setChecked(bool(prefs["match_by_title"]))
        self.match_title.setToolTip(
            "Books calibre sent are found by their calibre id or the file path. "
            "Title matching also finds books copied to the Kindle another way.")
        form.addRow("", self.match_title)
        lay.addStretch(1)

    def test_connection(self):
        from calibre_plugins.kindle_series_manager.engine import (
            KindleClient, KindleError)
        try:
            data = KindleClient(self.host.text(), self.port.value(),
                                timeout=8).library()
            self.test_result.setText(
                "Connected: %d books, %d series on the Kindle."
                % (len(data.get("books") or []), len(data.get("series") or [])))
        except KindleError as e:
            self.test_result.setText(str(e))

    def save_settings(self):
        prefs["host"] = self.host.text().strip()
        prefs["port"] = self.port.value()
        prefs["badge_mode"] = self.badge.currentData() or "none"
        prefs["min_books"] = self.min_books.value()
        prefs["match_by_title"] = self.match_title.isChecked()
