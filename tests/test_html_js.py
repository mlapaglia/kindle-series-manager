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


CGI_DIR = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "www" / "cgi-bin"
BIN_DIR = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "bin"


class TestEnhancedScreensavers:
    def test_ss_config_cgi_exists(self):
        assert (CGI_DIR / "ss_config.cgi").exists()

    def test_ss_bookcovers_cgi_exists(self):
        assert (CGI_DIR / "ss_bookcovers.cgi").exists()

    def test_enhanced_daemon_exists(self):
        assert (BIN_DIR / "fbink_ss_enhanced.sh").exists()

    def test_ss_settings_section_cgi_exists(self):
        assert (CGI_DIR / "ss_settings_section.cgi").exists()

    def test_ss_save_settings_function(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function ssSaveSettings(" in js

    def test_ss_update_mode_ui_function(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function ssUpdateModeUI(" in js

    def test_ss_apply_config_function(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function ssApplyConfig(" in js

    def test_ss_config_cgi_validates_mode(self):
        content = (CGI_DIR / "ss_config.cgi").read_text(encoding="utf-8")
        assert "custom|bookcover|allcovers|mixed" in content

    def test_ss_config_cgi_validates_order(self):
        content = (CGI_DIR / "ss_config.cgi").read_text(encoding="utf-8")
        assert "sequential|random" in content

    def test_enhanced_daemon_has_select_function(self):
        content = (BIN_DIR / "fbink_ss_enhanced.sh").read_text(encoding="utf-8")
        assert "select_screensaver_image()" in content

    def test_settings_section_has_mode_radios(self):
        content = (CGI_DIR / "ss_settings_section.cgi").read_text(encoding="utf-8")
        assert 'name="ssMode"' in content
        assert 'value="custom"' in content
        assert 'value="bookcover"' in content
        assert 'value="allcovers"' in content
        assert 'value="mixed"' in content

    def test_settings_section_has_order_radios(self):
        content = (CGI_DIR / "ss_settings_section.cgi").read_text(encoding="utf-8")
        assert 'name="ssOrder"' in content
        assert 'value="sequential"' in content
        assert 'value="random"' in content

    def test_settings_section_has_ratio_slider(self):
        content = (CGI_DIR / "ss_settings_section.cgi").read_text(encoding="utf-8")
        assert 'id="ssMixedRatio"' in content

    def test_load_screensavers_fetches_config(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "ss_config.cgi" in js
        assert "ss_settings_section.cgi" in js


CGI_DIR = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "www" / "cgi-bin"


class TestFontsTab:
    def test_fonts_tab_in_registry(self, html):
        assert "id: 'fonts'" in html
        assert "label: 'Fonts'" in html

    def test_load_fonts_function_exists(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function loadFonts" in js

    def test_font_page_cgi_exists(self):
        assert (CGI_DIR / "font_page.cgi").exists()

    def test_font_upload_cgi_exists(self):
        assert (CGI_DIR / "font_upload.cgi").exists()

    def test_font_magic_validation(self):
        upload_cgi = (CGI_DIR / "font_upload.cgi").read_text(encoding="utf-8")
        assert "00010000" in upload_cgi
        assert "74727565" in upload_cgi
        assert "4f54544f" in upload_cgi
        assert "74746366" in upload_cgi
        assert "xxd" in upload_cgi or "od" in upload_cgi


OPDS_JS = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "www" / "opds.js.txt"


@pytest.fixture
def opds_js():
    return OPDS_JS.read_text(encoding="utf-8")


class TestOpdsTab:
    def test_opds_proxy_cgi_exists(self):
        assert (CGI_DIR / "opds_proxy.cgi").exists()

    def test_opds_download_cgi_exists(self):
        assert (CGI_DIR / "opds_download.cgi").exists()

    def test_opds_sources_cgi_exists(self):
        assert (CGI_DIR / "opds_sources.cgi").exists()

    def test_opds_proxy_cgi_validates_url(self):
        content = (CGI_DIR / "opds_proxy.cgi").read_text(encoding="utf-8")
        assert "http://*|https://*" in content

    def test_opds_download_cgi_validates_url(self):
        content = (CGI_DIR / "opds_download.cgi").read_text(encoding="utf-8")
        assert "http://*|https://*" in content

    def test_opds_download_cgi_validates_extension(self):
        content = (CGI_DIR / "opds_download.cgi").read_text(encoding="utf-8")
        assert "azw3|azw|mobi|kfx|epub|pdf" in content

    def test_opds_js_reference_exists(self):
        assert OPDS_JS.exists()

    def test_load_opds_function_exists(self, opds_js):
        assert "function loadOpds(" in opds_js or "function loadOpds()" in opds_js

    def test_opds_parse_xml_exists(self, opds_js):
        assert "function opdsParseXml(" in opds_js or "function opdsParseXml()" in opds_js

    def test_opds_browse_function_exists(self, opds_js):
        assert "function opdsBrowse(" in opds_js

    def test_opds_download_function_exists(self, opds_js):
        assert "function opdsDownload(" in opds_js

    def test_opds_state_object_exists(self, opds_js):
        assert "var opdsState" in opds_js

    def test_opds_tabs_entry_comment(self, opds_js):
        assert "id: 'opds'" in opds_js

    def test_opds_js_no_console_log(self, opds_js):
        # Strip comment lines before checking
        lines = [l for l in opds_js.split('\n') if not l.strip().startswith('//') and not l.strip().startswith('/*')]
        code = '\n'.join(lines)
        assert "console.log" not in code, "Remove console.log before release"

    def test_opds_proxy_cgi_shebang(self):
        content = (CGI_DIR / "opds_proxy.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_opds_download_cgi_shebang(self):
        content = (CGI_DIR / "opds_download.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_opds_sources_cgi_shebang(self):
        content = (CGI_DIR / "opds_sources.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_opds_uses_escape_html(self, opds_js):
        assert "escapeHtml(" in opds_js


COLLECTIONS_JS = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "www" / "collections.js"


@pytest.fixture
def collections_js():
    return COLLECTIONS_JS.read_text(encoding="utf-8")


class TestCollectionsTab:
    def test_collections_tab_in_registry(self, html):
        assert "id: 'collections'" in html
        assert "label: 'Collections'" in html

    def test_load_collections_function_exists(self, collections_js):
        assert "function loadCollections" in collections_js

    def test_collections_cgi_exists(self):
        assert (CGI_DIR / "collections.cgi").exists()

    def test_collection_create_cgi_exists(self):
        assert (CGI_DIR / "collection_create.cgi").exists()

    def test_collection_remove_cgi_exists(self):
        assert (CGI_DIR / "collection_remove.cgi").exists()

    def test_collection_books_cgi_exists(self):
        assert (CGI_DIR / "collection_books.cgi").exists()

    def test_collections_cgi_outputs_json(self):
        content = (CGI_DIR / "collections.cgi").read_text(encoding="utf-8")
        assert "application/json" in content

    def test_collection_create_cgi_uses_icu_workaround(self):
        content = (CGI_DIR / "collection_create.cgi").read_text(encoding="utf-8")
        assert "PRAGMA writable_schema" in content
        assert "stop com.lab126.ccat" in content

    def test_collection_remove_cgi_handles_book_param(self):
        content = (CGI_DIR / "collection_remove.cgi").read_text(encoding="utf-8")
        assert "book)" in content or "BOOK_KEY" in content

    def test_collections_js_has_render_function(self, collections_js):
        assert "function renderCollections" in collections_js

    def test_collections_js_has_create_function(self, collections_js):
        assert "function showCreateCollection" in collections_js

    def test_collections_js_has_delete_function(self, collections_js):
        assert "function deleteCollection" in collections_js

    def test_collections_js_has_save_function(self, collections_js):
        assert "function saveCollection" in collections_js

    def test_collections_js_uses_escape_html(self, collections_js):
        assert "escapeHtml" in collections_js

    def test_collections_js_no_console_log(self, collections_js):
        assert "console.log" not in collections_js

    def test_collections_cgi_uses_db_var(self):
        content = (CGI_DIR / "collections.cgi").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content

    def test_collection_create_cgi_uses_db_var(self):
        content = (CGI_DIR / "collection_create.cgi").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content


HC_DIR = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "hardcover"


class TestSyncServices:
    def test_hardcover_config_exists(self):
        assert (HC_DIR / "hc_config.json").exists()

    def test_hc_sync_script_exists(self):
        assert (HC_DIR / "hc_sync.sh").exists()

    def test_hc_search_script_exists(self):
        assert (HC_DIR / "hc_search.sh").exists()

    def test_hc_update_script_exists(self):
        assert (HC_DIR / "hc_update.sh").exists()

    def test_hc_build_mapping_script_exists(self):
        assert (HC_DIR / "hc_build_mapping.sh").exists()

    def test_hc_page_cgi_exists(self):
        assert (CGI_DIR / "hc_page.cgi").exists()

    def test_hc_status_cgi_exists(self):
        assert (CGI_DIR / "hc_status.cgi").exists()

    def test_hc_savetoken_cgi_exists(self):
        assert (CGI_DIR / "hc_savetoken.cgi").exists()

    def test_hc_domapping_cgi_exists(self):
        assert (CGI_DIR / "hc_domapping.cgi").exists()

    def test_sync_services_tab(self, html):
        assert "id: 'progress'" in html
        assert "'Sync Services'" in html
        assert "loadSyncServices" in html

    def test_hc_save_token_function(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function hcSaveToken(" in js

    def test_hc_build_mapping_function(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function hcBuildMapping(" in js

    def test_hc_refresh_status_function(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function hcRefreshStatus(" in js

    def test_load_sync_services_function(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "function loadSyncServices(" in js

    def test_load_sync_services_fetches_both(self, html):
        js = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
        assert "grpage.cgi" in js
        assert "hc_page.cgi" in js

    def test_no_load_progress_remaining(self, html):
        assert "loadProgress" not in html

    def test_hc_sync_uses_db_var(self):
        content = (HC_DIR / "hc_sync.sh").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content

    def test_hc_build_mapping_uses_db_var(self):
        content = (HC_DIR / "hc_build_mapping.sh").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content

    def test_hc_page_cgi_shebang(self):
        content = (CGI_DIR / "hc_page.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_hc_status_cgi_outputs_json(self):
        content = (CGI_DIR / "hc_status.cgi").read_text(encoding="utf-8")
        assert "application/json" in content

    def test_hc_sync_has_flag_file(self):
        content = (HC_DIR / "hc_sync.sh").read_text(encoding="utf-8")
        assert "ENABLE_HC_SYNC" in content

    def test_hc_sync_has_pid_file(self):
        content = (HC_DIR / "hc_sync.sh").read_text(encoding="utf-8")
        assert "hc_sync.pid" in content

    def test_hc_toggle_exists(self):
        assert (Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "bin" / "hc_toggle.sh").exists()

    def test_hc_upstart_exists(self):
        assert (Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "upstart" / "hc-sync.conf").exists()


STATS_DB_DIR = Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager"


class TestReadingStats:
    def test_stats_overview_cgi_exists(self):
        assert (CGI_DIR / "stats_overview.cgi").exists()

    def test_stats_history_cgi_exists(self):
        assert (CGI_DIR / "stats_history.cgi").exists()

    def test_stats_daemon_exists(self):
        assert (BIN_DIR / "ksm_stats_daemon.sh").exists()

    def test_stats_upstart_config_exists(self):
        assert (Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "upstart" / "ksm-stats.conf").exists()

    def test_stats_overview_cgi_shebang(self):
        content = (CGI_DIR / "stats_overview.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_stats_overview_cgi_outputs_json(self):
        content = (CGI_DIR / "stats_overview.cgi").read_text(encoding="utf-8")
        assert "application/json" in content

    def test_stats_overview_cgi_uses_db_var(self):
        content = (CGI_DIR / "stats_overview.cgi").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content

    def test_stats_history_cgi_shebang(self):
        content = (CGI_DIR / "stats_history.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_stats_history_cgi_outputs_json(self):
        content = (CGI_DIR / "stats_history.cgi").read_text(encoding="utf-8")
        assert "application/json" in content

    def test_stats_history_cgi_uses_stats_db_var(self):
        content = (CGI_DIR / "stats_history.cgi").read_text(encoding="utf-8")
        assert 'STATS_DB="${STATS_DB:-' in content

    def test_stats_daemon_has_pid_file(self):
        content = (BIN_DIR / "ksm_stats_daemon.sh").read_text(encoding="utf-8")
        assert "ksm_stats_daemon.pid" in content

    def test_stats_daemon_has_flag_file(self):
        content = (BIN_DIR / "ksm_stats_daemon.sh").read_text(encoding="utf-8")
        assert "ENABLE_KSM_STATS" in content

    def test_stats_upstart_checks_flag(self):
        content = (Path(__file__).parent.parent / "kual-extension" / "kindle-series-manager" / "upstart" / "ksm-stats.conf").read_text(encoding="utf-8")
        assert "ENABLE_KSM_STATS" in content


class TestFontsExtended:
    def test_font_enable_cgi_exists(self):
        assert (CGI_DIR / "font_enable.cgi").exists()

    def test_font_disable_cgi_exists(self):
        assert (CGI_DIR / "font_disable.cgi").exists()

    def test_font_delete_cgi_exists(self):
        assert (CGI_DIR / "font_delete.cgi").exists()

    def test_font_enable_cgi_shebang(self):
        content = (CGI_DIR / "font_enable.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_font_disable_cgi_shebang(self):
        content = (CGI_DIR / "font_disable.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_font_delete_cgi_shebang(self):
        content = (CGI_DIR / "font_delete.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_font_page_cgi_shebang(self):
        content = (CGI_DIR / "font_page.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_font_upload_cgi_shebang(self):
        content = (CGI_DIR / "font_upload.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_font_enable_path_traversal_check(self):
        content = (CGI_DIR / "font_enable.cgi").read_text(encoding="utf-8")
        assert "*/*" in content and "*..*" in content

    def test_font_disable_path_traversal_check(self):
        content = (CGI_DIR / "font_disable.cgi").read_text(encoding="utf-8")
        assert "*/*" in content and "*..*" in content

    def test_font_delete_path_traversal_check(self):
        content = (CGI_DIR / "font_delete.cgi").read_text(encoding="utf-8")
        assert "*/*" in content and "*..*" in content

    def test_font_upload_path_traversal_check(self):
        content = (CGI_DIR / "font_upload.cgi").read_text(encoding="utf-8")
        assert "*/*" in content and "*..*" in content

    def test_font_upload_extension_whitelist(self):
        content = (CGI_DIR / "font_upload.cgi").read_text(encoding="utf-8")
        assert "ttf|otf|ttc" in content or ("ttf" in content and "otf" in content and "ttc" in content)


class TestScreensaversExtended:
    def test_ss_delete_cgi_exists(self):
        assert (CGI_DIR / "ss_delete.cgi").exists()

    def test_ss_enable_cgi_exists(self):
        assert (CGI_DIR / "ss_enable.cgi").exists()

    def test_ss_disable_cgi_exists(self):
        assert (CGI_DIR / "ss_disable.cgi").exists()

    def test_ss_config_cgi_shebang(self):
        content = (CGI_DIR / "ss_config.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_ss_bookcovers_cgi_shebang(self):
        content = (CGI_DIR / "ss_bookcovers.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_ss_delete_filename_sanitization(self):
        content = (CGI_DIR / "ss_delete.cgi").read_text(encoding="utf-8")
        assert "[^a-zA-Z0-9._-]" in content

    def test_ss_enable_filename_sanitization(self):
        content = (CGI_DIR / "ss_enable.cgi").read_text(encoding="utf-8")
        assert "[^a-zA-Z0-9._-]" in content

    def test_ss_disable_filename_sanitization(self):
        content = (CGI_DIR / "ss_disable.cgi").read_text(encoding="utf-8")
        assert "[^a-zA-Z0-9._-]" in content

    def test_fbink_ss_enhanced_uses_db_var(self):
        content = (BIN_DIR / "fbink_ss_enhanced.sh").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content


class TestCollectionsExtended:
    def test_collection_books_cgi_shebang(self):
        content = (CGI_DIR / "collection_books.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_collection_books_cgi_uses_db_var(self):
        content = (CGI_DIR / "collection_books.cgi").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content

    def test_collection_remove_cgi_shebang(self):
        content = (CGI_DIR / "collection_remove.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_collection_remove_cgi_uses_db_var(self):
        content = (CGI_DIR / "collection_remove.cgi").read_text(encoding="utf-8")
        assert 'DB="${DB:-/var/local/cc.db}"' in content

    def test_collection_remove_cgi_uses_escape_sql(self):
        content = (CGI_DIR / "collection_remove.cgi").read_text(encoding="utf-8")
        assert "escape_sql" in content

    def test_collection_create_cgi_shebang(self):
        content = (CGI_DIR / "collection_create.cgi").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")
