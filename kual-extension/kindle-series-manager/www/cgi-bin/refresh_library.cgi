#!/bin/sh
echo "Content-Type: application/json"
echo ""

stop com.lab126.ccat 2>/dev/null
sleep 1
start com.lab126.ccat 2>/dev/null

printf '{"status":"ok"}'
