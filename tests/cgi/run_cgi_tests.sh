#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CGI_DIR="$REPO_ROOT/kual-extension/kindle-series-manager/www/cgi-bin"
PASS=0
FAIL=0
TOTAL=0

setup_test_db() {
    TEST_DIR=$(mktemp -d)
    TEST_DB="$TEST_DIR/cc.db"
    sqlite3 "$TEST_DB" <<'SQL'
CREATE TABLE Entries (
    p_uuid PRIMARY KEY NOT NULL, p_type, p_location, p_lastAccess,
    p_modificationTime, p_isArchived, p_titles_0_nominal,
    p_titles_0_collation, p_titles_0_pronunciation,
    j_titles, p_titleCount,
    p_credits_0_name_collation, j_credits, p_creditCount,
    j_collections, p_collectionCount, j_members, p_memberCount,
    p_lastAccessedPosition, p_publicationDate, p_expirationDate,
    p_publisher, p_isDRMProtected, p_isVisibleInHome, p_isLatestItem,
    p_isDownloading, p_isUpdateAvailable, p_virtualCollectionCount,
    p_languages_0, j_languages, p_languageCount, p_mimeType,
    p_cover, p_thumbnail, p_diskUsage, p_cdeGroup, p_cdeKey, p_cdeType,
    p_version, p_guid, j_displayObjects, j_displayTags,
    j_excludedTransports, p_isMultimediaEnabled, p_watermark,
    p_contentSize, p_percentFinished, p_isTestData,
    p_contentIndexedState, p_metadataIndexedState, p_noteIndexedState,
    p_credits_0_name_pronunciation, p_metadataStemWords,
    p_metadataStemLanguage, p_ownershipType, p_shareType,
    p_contentState, p_metadataUnicodeWords, p_homeMemberCount,
    j_collectionsSyncAttributes, p_collectionSyncCounter,
    p_collectionDataSetName, p_originType, p_pvcId,
    p_companionCdeKey, p_seriesState, p_totalContentSize REAL,
    p_visibilityState, p_isProcessed, p_readState, p_subType
);
CREATE TABLE Series (
    d_seriesId, d_itemCdeKey, d_itemPosition, d_itemPositionLabel,
    d_itemType, d_seriesOrderType,
    UNIQUE (d_seriesId, d_itemCdeKey)
);
INSERT INTO Entries (p_uuid, p_type, p_cdeKey, p_cdeType, p_titles_0_nominal,
    p_titles_0_collation, p_location, p_isVisibleInHome, p_seriesState, p_originType)
VALUES ('uuid-1', 'Entry:Item', 'B08BKGYQXW', 'EBOK', 'Dungeon Crawler Carl: Book 1',
    'Dungeon Crawler Carl: Book 1', '/mnt/us/documents/DCC1.kfx', 1, 1, 0);
INSERT INTO Entries (p_uuid, p_type, p_cdeKey, p_cdeType, p_titles_0_nominal,
    p_titles_0_collation, p_location, p_isVisibleInHome, p_seriesState, p_originType)
VALUES ('uuid-2', 'Entry:Item', 'B08PBCD9Y7', 'EBOK', 'Carls Doomsday Scenario: Book 2',
    'Carls Doomsday Scenario: Book 2', '/mnt/us/documents/DCC2.kfx', 1, 1, 0);
INSERT INTO Entries (p_uuid, p_type, p_cdeKey, p_cdeType, p_titles_0_nominal,
    p_titles_0_collation, p_location, p_isVisibleInHome, p_seriesState, p_originType)
VALUES ('uuid-3', 'Entry:Item', 'B08V4QSV6W', 'EBOK', 'The Dungeon Anarchists Cookbook: Book 3',
    'The Dungeon Anarchists Cookbook: Book 3', '/mnt/us/documents/DCC3.kfx', 1, 1, 0);
SQL
    echo "$TEST_DIR"
}

run_cgi() {
    local cgi_script="$1"
    local query_string="${2:-}"
    local post_body="${3:-}"
    local content_length=${#post_body}

    DB="$TEST_DB" \
    QUERY_STRING="$query_string" \
    CONTENT_LENGTH="$content_length" \
    REQUEST_METHOD="${post_body:+POST}" \
    sh -c "echo '$post_body' | $CGI_DIR/$cgi_script" 2>/dev/null
}

assert_contains() {
    local output="$1"
    local expected="$2"
    local test_name="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$output" | grep -q "$expected"; then
        PASS=$((PASS + 1))
        echo "  PASS: $test_name"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: $test_name"
        echo "    Expected to contain: $expected"
        echo "    Got: $(echo "$output" | head -5)"
    fi
}

assert_not_contains() {
    local output="$1"
    local unexpected="$2"
    local test_name="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$output" | grep -q "$unexpected"; then
        FAIL=$((FAIL + 1))
        echo "  FAIL: $test_name"
        echo "    Did not expect: $unexpected"
    else
        PASS=$((PASS + 1))
        echo "  PASS: $test_name"
    fi
}

echo "=== CGI Integration Tests ==="
echo ""

TEST_DIR=$(setup_test_db)
TEST_DB="$TEST_DIR/cc.db"

stub_commands() {
    mkdir -p "$TEST_DIR/bin"
    echo '#!/bin/sh' > "$TEST_DIR/bin/mntroot"
    echo '#!/bin/sh' > "$TEST_DIR/bin/stop"
    echo '#!/bin/sh' > "$TEST_DIR/bin/start"
    echo '#!/bin/sh' > "$TEST_DIR/bin/sqlite3"
    cat > "$TEST_DIR/bin/sqlite3" <<'STUBSQL'
#!/bin/sh
command sqlite3 "$@"
STUBSQL
    chmod +x "$TEST_DIR/bin/"*
}

echo "--- series.cgi ---"
OUTPUT=$(DB="$TEST_DB" sh "$CGI_DIR/series.cgi" 2>/dev/null)
assert_contains "$OUTPUT" "Content-Type" "returns HTTP header"
assert_contains "$OUTPUT" "text/html" "returns HTML content type"

echo ""
echo "--- books.cgi ---"
OUTPUT=$(DB="$TEST_DB" sh "$CGI_DIR/books.cgi" 2>/dev/null)
assert_contains "$OUTPUT" "Dungeon Crawler Carl" "lists books from database"
assert_contains "$OUTPUT" "B08BKGYQXW" "includes cdeKey in output"

echo ""
echo "--- seriesdata.cgi ---"
# First create a series so we can query it
sqlite3 "$TEST_DB" "INSERT INTO Series (d_seriesId, d_itemCdeKey, d_itemPosition, d_itemPositionLabel, d_itemType, d_seriesOrderType) VALUES ('urn:collection:1:asin-SL-DCC', 'B08BKGYQXW', 0.0, '1', 'Entry:Item', 'ordered');"
sqlite3 "$TEST_DB" "INSERT INTO Series (d_seriesId, d_itemCdeKey, d_itemPosition, d_itemPositionLabel, d_itemType, d_seriesOrderType) VALUES ('urn:collection:1:asin-SL-DCC', 'B08PBCD9Y7', 1.0, '2', 'Entry:Item', 'ordered');"
sqlite3 "$TEST_DB" "INSERT INTO Entries (p_uuid, p_type, p_cdeKey, p_cdeType, p_titles_0_nominal, p_memberCount) VALUES ('uuid-series', 'Entry:Item:Series', 'SL-DCC', 'series', 'DCC', 2);"

OUTPUT=$(DB="$TEST_DB" QUERY_STRING="id=urn%3Acollection%3A1%3Aasin-SL-DCC" sh "$CGI_DIR/seriesdata.cgi" 2>/dev/null)
assert_contains "$OUTPUT" "application/json" "returns JSON content type"
assert_contains "$OUTPUT" "DCC" "returns series name"
assert_contains "$OUTPUT" "B08BKGYQXW" "includes member books"

echo ""
echo "--- books_browse.cgi ---"
OUTPUT=$(sh "$CGI_DIR/books_browse.cgi" 2>/dev/null)
assert_contains "$OUTPUT" "application/json" "returns JSON content type"
assert_contains "$OUTPUT" "\[" "returns JSON array"

echo ""
echo "--- JSON validation: menu.json ---"
TOTAL=$((TOTAL + 1))
if python3 -c "import json; json.load(open('$REPO_ROOT/kual-extension/kindle-series-manager/menu.json'))" 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "  PASS: menu.json is valid JSON"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL: menu.json is not valid JSON"
fi

rm -rf "$TEST_DIR"

echo ""
echo "=== Results: $PASS passed, $FAIL failed, $TOTAL total ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
