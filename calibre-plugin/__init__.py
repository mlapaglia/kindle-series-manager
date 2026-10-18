#!/usr/bin/env python
"""
Kindle Series Manager - Calibre plugin.

Sends the series of your calibre books to a jailbroken Kindle, so sideloaded
books are grouped into series in the Kindle library the same way as books
bought from Amazon. It talks to the Kindle Series Manager KUAL extension's web
UI over WiFi, which does the actual writes to the Kindle's cc.db.
"""
from calibre.customize import InterfaceActionBase

__license__ = "Apache-2.0"


class KindleSeriesManagerPlugin(InterfaceActionBase):
    name = "Kindle Series Manager"
    description = ("Group sideloaded books into series on a jailbroken Kindle, "
                   "using the series from your calibre library.")
    supported_platforms = ["windows", "osx", "linux"]
    author = "Kindle Series Manager contributors"
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)

    # the InterfaceAction lives in ui.py
    actual_plugin = "calibre_plugins.kindle_series_manager.ui:KindleSeriesAction"

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.kindle_series_manager.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
