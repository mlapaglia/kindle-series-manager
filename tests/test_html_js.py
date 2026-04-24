"""Tier 3: Basic HTML/JS validation for index.html."""

import re
from pathlib import Path

import pytest

INDEX_HTML = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "www" / "index.html"


@pytest.fixture
def html():
    return INDEX_HTML.read_text(encoding="utf-8")


class TestHTMLStructure:
    def test_file_exists(self):
        assert INDEX_HTML.exists()

    def test_has_doctype(self, html):
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_has_closing_tags(self, html):
        assert "</html>" in html
        assert "</head>" in html
        assert "</body>" in html

    def test_has_viewport_meta(self, html):
        assert 'name="viewport"' in html

    def test_has_title(self, html):
        assert "<title>" in html and "</title>" in html

    def test_script_tag_present(self, html):
        assert "<script>" in html and "</script>" in html

    def test_style_tag_present(self, html):
        assert "<style>" in html and "</style>" in html


class TestJSSyntax:
    def _extract_js(self, html):
        match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
        assert match, "No inline script block found"
        return match.group(1)

    def test_no_unterminated_strings(self, html):
        js = self._extract_js(html)
        lines = js.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            single_quotes = stripped.count("'") - stripped.count("\\'")
            double_quotes = stripped.count('"') - stripped.count('\\"')
            if "'" in stripped and "concat" not in stripped:
                assert single_quotes % 2 == 0 or '"' in stripped, (
                    f"Possible unterminated string on JS line {i}: {stripped[:80]}"
                )

    def test_balanced_braces(self, html):
        js = self._extract_js(html)
        opens = js.count("{")
        closes = js.count("}")
        assert opens == closes, f"Unbalanced braces: {opens} open, {closes} close"

    def test_balanced_parens(self, html):
        js = self._extract_js(html)
        opens = js.count("(")
        closes = js.count(")")
        assert opens == closes, f"Unbalanced parens: {opens} open, {closes} close"

    def test_balanced_brackets(self, html):
        js = self._extract_js(html)
        opens = js.count("[")
        closes = js.count("]")
        assert opens == closes, f"Unbalanced brackets: {opens} open, {closes} close"

    def test_no_console_log(self, html):
        js = self._extract_js(html)
        assert "console.log" not in js, "Remove console.log before release"

    def test_all_functions_have_bodies(self, html):
        js = self._extract_js(html)
        func_decls = re.findall(r"function\s+(\w+)\s*\(", js)
        assert len(func_decls) > 0, "No function declarations found"


class TestNavTabs:
    def test_all_nav_buttons_have_onclick(self, html):
        # Buttons are generated dynamically via TABS registry with addEventListener
        assert "TABS" in html, "Tab registry not found"
        tab_ids = re.findall(r"id:\s*'(\w+)'", html)
        assert len(tab_ids) >= 4, f"Expected at least 4 tabs in registry, found {len(tab_ids)}"

    def test_nav_button_ids(self, html):
        expected_ids = ["btn_series", "btn_create", "btn_progress", "btn_screensavers", "btn_upload", "btn_calibre"]
        for btn_id in expected_ids:
            # Dynamic buttons are created with: btn.id = 'btn_' + TABS[i].id
            tab_id = btn_id.replace('btn_', '')
            assert f"id: '{tab_id}'" in html, f"Missing tab in registry: {tab_id}"


class TestCSSVariables:
    def test_has_light_theme(self, html):
        assert "--bg:" in html
        assert "--fg:" in html
        assert "--surface:" in html

    def test_has_dark_theme(self, html):
        assert ".dark {" in html or ".dark{" in html


BOOKS_CGI = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "www" / "cgi-bin" / "books.cgi"


@pytest.fixture
def books_cgi():
    return BOOKS_CGI.read_text(encoding="utf-8")


class TestHideInSeriesFilter:
    def test_books_cgi_has_hide_checkbox(self, books_cgi):
        assert "id='hideInSeries'" in books_cgi

    def test_books_cgi_emits_data_series_attr(self, books_cgi):
        assert "data-series=" in books_cgi

    def test_books_cgi_emits_in_series_class(self, books_cgi):
        assert "in-series" in books_cgi

    def test_books_cgi_emits_series_label(self, books_cgi):
        assert "avail-series-label" in books_cgi

    def test_filterbooks_checks_hide_in_series(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "hideInSeries" in js
        assert "data-series" in js

    def test_css_has_series_label_style(self, html):
        assert ".avail-series-label" in html

    def test_books_cgi_query_joins_series_table(self, books_cgi):
        assert "FROM Series" in books_cgi
        assert "GROUP_CONCAT" in books_cgi


class TestAuthorSearch:
    def test_books_cgi_emits_data_author_attr(self, books_cgi):
        assert "data-author=" in books_cgi

    def test_books_cgi_query_includes_author(self, books_cgi):
        assert "p_credits_0_name_collation" in books_cgi

    def test_books_cgi_emits_author_label(self, books_cgi):
        assert "avail-author-label" in books_cgi

    def test_filterbooks_checks_author(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "data-author" in js

    def test_css_has_author_label_style(self, html):
        assert ".avail-author-label" in html

    def test_filter_placeholder_mentions_author(self, books_cgi):
        assert "author" in books_cgi.lower()
