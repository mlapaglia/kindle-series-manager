#!/bin/sh
echo "Content-Type: text/plain"
echo ""

GR_DIR="/mnt/us/extensions/kindle-series-manager/goodreads"
CREDS_FILE="$GR_DIR/gr_creds.json"

urldecode() {
    echo "$1" | sed 's/+/ /g;s/%20/ /g;s/%3A/:/g;s/%2C/,/g;s/%2F/\//g;s/%27/'"'"'/g;s/%28/(/g;s/%29/)/g;s/%26/\&/g;s/%3D/=/g;s/%40/@/g;s/%25/%/g;s/%2B/+/g;s/%21/!/g;s/%23/#/g;s/%24/$/g'
}

read -r POST_BODY

EMAIL=""
PASSWORD=""
USER_ID=""

OLDIFS="$IFS"
IFS='&'
for PARAM in $POST_BODY; do
    PKEY=$(echo "$PARAM" | cut -d'=' -f1)
    PVAL=$(echo "$PARAM" | cut -d'=' -f2-)
    case "$PKEY" in
        email)    EMAIL=$(urldecode "$PVAL") ;;
        password) PASSWORD=$(urldecode "$PVAL") ;;
        user_id)  USER_ID=$(urldecode "$PVAL") ;;
    esac
done
IFS="$OLDIFS"

if [ -z "$EMAIL" ]; then
    echo "Error: email is required"
    exit 0
fi

if [ -z "$PASSWORD" ]; then
    echo "Error: password is required"
    exit 0
fi

if [ -z "$USER_ID" ]; then
    echo "Error: Goodreads user ID is required"
    exit 0
fi

mkdir -p "$GR_DIR"

SAFE_EMAIL=$(echo "$EMAIL" | sed 's/\\/\\\\/g;s/"/\\"/g')
SAFE_PASSWORD=$(echo "$PASSWORD" | sed 's/\\/\\\\/g;s/"/\\"/g')
SAFE_USER_ID=$(echo "$USER_ID" | sed 's/\\/\\\\/g;s/"/\\"/g')

(
    umask 077
    cat > "$CREDS_FILE" << EOF
{
  "email": "$SAFE_EMAIL",
  "password": "$SAFE_PASSWORD",
  "goodreads_user_id": "$SAFE_USER_ID"
}
EOF
)
chmod 600 "$CREDS_FILE"

echo "Credentials saved."
