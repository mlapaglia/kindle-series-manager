#!/bin/bash
set -e

echo "========================================"
echo "  Tier 1 & 3: Python Tests"
echo "========================================"
python -m pytest tests/test_kindle_series.py tests/test_html_js.py -v

echo ""
echo "========================================"
echo "  Tier 2: ShellCheck"
echo "========================================"
EXCLUDES="SC2086,SC2046,SC2181,SC2012,SC2018,SC2019"
shellcheck -s sh -e "$EXCLUDES" kual-extension/kindle-series-manager/bin/*.sh
echo "  Shell scripts OK"

find kual-extension/kindle-series-manager/www/cgi-bin -name '*.cgi' | while read -r f; do
    shellcheck -s sh -e "$EXCLUDES" "$f"
done
echo "  CGI scripts OK"

echo ""
echo "========================================"
echo "  Tier 4: CGI Integration Tests"
echo "========================================"
bash tests/cgi/run_cgi_tests.sh

echo ""
echo "========================================"
echo "  JSON Validation"
echo "========================================"
python3 -c "import json; json.load(open('kual-extension/kindle-series-manager/menu.json'))"
echo "  menu.json OK"

echo ""
echo "========================================"
echo "  Release Package Validation"
echo "========================================"
zip -r /tmp/test-package.zip . -x '.git/*' '.github/*' '.venv/*' '__pycache__/*' '*.pyc' > /dev/null
unzip -l /tmp/test-package.zip | grep -q "kual-extension/kindle-series-manager/config.xml"
unzip -l /tmp/test-package.zip | grep -q "kual-extension/kindle-series-manager/menu.json"
unzip -l /tmp/test-package.zip | grep -q "kual-extension/kindle-series-manager/bin/webapp.sh"
unzip -l /tmp/test-package.zip | grep -q "kual-extension/kindle-series-manager/www/index.html"
unzip -l /tmp/test-package.zip | grep -q "kual-extension/kindle-series-manager/www/cgi-bin/series/create.cgi"
unzip -l /tmp/test-package.zip | grep -q "kual-extension/kindle-series-manager/bin/fbink_ss_daemon.sh"
rm -f /tmp/test-package.zip
echo "  Package structure OK"

echo ""
echo "========================================"
echo "  All tests passed"
echo "========================================"
