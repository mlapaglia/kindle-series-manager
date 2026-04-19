#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/../../kual-extension/kindle-series-manager/bin"

echo "Building ss_shield for Kindle ARM..."
docker build -f "$SCRIPT_DIR/Dockerfile.build" -t ss_shield-build "$SCRIPT_DIR"

CONTAINER_ID=$(docker create ss_shield-build)
docker cp "$CONTAINER_ID:/build/ss_shield" "$OUTPUT_DIR/ss_shield"
docker rm "$CONTAINER_ID"

echo "Built: $OUTPUT_DIR/ss_shield"
ls -la "$OUTPUT_DIR/ss_shield"
