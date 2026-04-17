#!/bin/sh
#
# Goodreads login via Amazon's auth portal.
# Reads credentials from gr_creds.json in the same directory.
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CREDS_FILE="$SCRIPT_DIR/gr_creds.json"
COOKIE_JAR="$SCRIPT_DIR/gr_cookies.txt"
SESSION_FILE="$SCRIPT_DIR/gr_session.txt"
DEBUG_DIR="$SCRIPT_DIR/debug"

mkdir -p "$DEBUG_DIR"
rm -f "$COOKIE_JAR"

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"

EMAIL=$(grep '"email"' "$CREDS_FILE" | sed 's/.*"email".*"\([^"]*\)".*/\1/')
PASSWORD=$(grep '"password"' "$CREDS_FILE" | sed 's/.*"password".*"\([^"]*\)".*/\1/')

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
    echo "ERROR: Could not parse email/password from $CREDS_FILE"
    exit 1
fi

echo "=== Step 1: Fetch Goodreads sign-in page ==="
GR_SIGNIN=$(curl -s -L -c "$COOKIE_JAR" \
    -H "User-Agent: $UA" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.9" \
    "https://www.goodreads.com/user/sign_in")
echo "$GR_SIGNIN" > "$DEBUG_DIR/01_gr_signin.html"

AP_URL=$(echo "$GR_SIGNIN" | grep -o 'href="https://www.goodreads.com/ap/signin[^"]*amzn_goodreads_web_na[^"]*"' | head -1 | sed 's/href="//;s/"$//' | sed 's/&amp;/\&/g')

if [ -z "$AP_URL" ]; then
    echo "ERROR: Could not find Amazon auth portal URL"
    exit 1
fi

echo "Found auth portal URL"

echo ""
echo "=== Step 2: Fetch Amazon login form ==="
AP_HTML=$(curl -s -L -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -H "User-Agent: $UA" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.9" \
    -H "Referer: https://www.goodreads.com/user/sign_in" \
    "$AP_URL")
echo "$AP_HTML" > "$DEBUG_DIR/02_ap_signin.html"

AP_ACTION=$(echo "$AP_HTML" | grep -o 'name="signIn"[^>]*action="[^"]*"\|action="[^"]*"[^>]*name="signIn"' | grep -o 'action="[^"]*"' | sed 's/action="//;s/"//')

if [ -z "$AP_ACTION" ]; then
    AP_ACTION=$(echo "$AP_HTML" | tr '\n' ' ' | grep -o '<form[^>]*id="ap_signin_form"[^>]*>' | grep -o 'action="[^"]*"' | sed 's/action="//;s/"//')
fi

if [ -z "$AP_ACTION" ]; then
    AP_ACTION=$(echo "$AP_HTML" | grep 'action=' | grep -i 'signin\|sign_in\|auth' | grep -o 'action="[^"]*"' | head -1 | sed 's/action="//;s/"//')
fi

if [ -z "$AP_ACTION" ]; then
    echo "ERROR: Could not find form action URL"
    exit 1
fi

echo "Form action: $AP_ACTION"

extract_hidden() {
    echo "$AP_HTML" | grep -o "name=\"$1\"[^>]*value=\"[^\"]*\"" | head -1 | sed 's/.*value="//;s/"//'
}

AP_APPID=$(extract_hidden "appActionToken")
AP_APPACTION=$(extract_hidden "appAction")
AP_PREVRID=$(extract_hidden "prevRID")
AP_WORKFLOWSTATE=$(extract_hidden "workflowState")
AP_OPENID_RETURN=$(extract_hidden "openid.return_to")
AP_OPENID_HANDLE=$(extract_hidden "openid.assoc_handle")
AP_OPENID_MODE=$(extract_hidden "openid.mode")
AP_OPENID_NS=$(extract_hidden "openid.ns")
AP_OPENID_IDENTITY=$(extract_hidden "openid.identity")
AP_OPENID_CLAIMED=$(extract_hidden "openid.claimed_id")
AP_OPENID_PAPE=$(extract_hidden "openid.pape.max_auth_age")
AP_SITESTATE=$(extract_hidden "siteState")
AP_PAGEID=$(extract_hidden "pageId")

echo "Extracted hidden fields (appActionToken: ${AP_APPID:0:20}...)"

echo ""
echo "=== Step 3: Submit login ==="
LOGIN_RESPONSE=$(curl -s -L \
    -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -H "User-Agent: $UA" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.9" \
    -H "Referer: $AP_URL" \
    --data-urlencode "appActionToken=$AP_APPID" \
    --data-urlencode "appAction=$AP_APPACTION" \
    --data-urlencode "prevRID=$AP_PREVRID" \
    --data-urlencode "workflowState=$AP_WORKFLOWSTATE" \
    --data-urlencode "openid.return_to=$AP_OPENID_RETURN" \
    --data-urlencode "openid.assoc_handle=$AP_OPENID_HANDLE" \
    --data-urlencode "openid.mode=$AP_OPENID_MODE" \
    --data-urlencode "openid.ns=$AP_OPENID_NS" \
    --data-urlencode "openid.identity=$AP_OPENID_IDENTITY" \
    --data-urlencode "openid.claimed_id=$AP_OPENID_CLAIMED" \
    --data-urlencode "openid.pape.max_auth_age=$AP_OPENID_PAPE" \
    --data-urlencode "siteState=$AP_SITESTATE" \
    --data-urlencode "pageId=$AP_PAGEID" \
    --data-urlencode "email=$EMAIL" \
    --data-urlencode "password=$PASSWORD" \
    --data-urlencode "create=0" \
    "$AP_ACTION")
echo "$LOGIN_RESPONSE" > "$DEBUG_DIR/03_login_response.html"

CSRF_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o 'csrf-token" content="[^"]*"' | head -1 | sed 's/csrf-token" content="//;s/"//')

if [ -z "$CSRF_TOKEN" ]; then
    AUTH_ERROR=$(echo "$LOGIN_RESPONSE" | grep -o 'auth-error-message-box\|important-message-box\|a]ert-heading\|error-slot' | head -1)
    if [ -n "$AUTH_ERROR" ]; then
        echo "ERROR: Login failed - Amazon returned an error. Check credentials."
        ERROR_MSG=$(echo "$LOGIN_RESPONSE" | grep -o 'class="a-list-item">[^<]*<' | head -1 | sed 's/.*>//;s/<$//')
        if [ -n "$ERROR_MSG" ]; then
            echo "  Message: $ERROR_MSG"
        fi
    else
        AP_STILL=$(echo "$LOGIN_RESPONSE" | grep -c "ap/signin\|ap_email\|signIn_submit")
        if [ "$AP_STILL" -gt 0 ]; then
            echo "ERROR: Still on Amazon login page. Possible CAPTCHA or MFA required."
        else
            echo "ERROR: Could not extract CSRF token from final page."
            echo "Response may have landed on an unexpected page."
        fi
    fi
    echo "Debug files saved to $DEBUG_DIR/"
    exit 1
fi

echo "$CSRF_TOKEN" > "$SESSION_FILE"

echo ""
echo "Login successful!"
echo "CSRF token: ${CSRF_TOKEN:0:30}..."
echo "Cookies saved to: $COOKIE_JAR"
echo "Session saved to: $SESSION_FILE"
echo "Debug files saved to: $DEBUG_DIR/"
