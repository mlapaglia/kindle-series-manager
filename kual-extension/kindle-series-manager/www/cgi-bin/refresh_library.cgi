#!/bin/sh

json_error() {
    echo "Status: 500 Internal Server Error"
    echo "Content-Type: application/json"
    echo ""
    printf '{"status":"error","message":"%s"}' "$1"
    exit 1
}

echo "Content-Type: application/json"

stop com.lab126.ccat 2>/dev/null
if [ $? -ne 0 ]; then
    json_error "Failed to stop com.lab126.ccat"
fi

sleep 1

start com.lab126.ccat 2>/dev/null
if [ $? -ne 0 ]; then
    json_error "Failed to start com.lab126.ccat"
fi

echo ""
printf '{"status":"ok"}'
