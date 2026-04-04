#!/usr/bin/env bash

set -euo pipefail

PORT="${1:-4020}"
BUILD_DIR="/tmp/talent-site/_site"
PREVIEW_ROOT="/tmp/talent-site/http-preview-root"
BASEURL_DIR="$PREVIEW_ROOT/entp"

bundle exec jekyll build

rm -rf "$PREVIEW_ROOT"
mkdir -p "$BASEURL_DIR"
cp -R "$BUILD_DIR"/. "$BASEURL_DIR"/

echo "Serving local preview at http://127.0.0.1:${PORT}/entp/"
python3 -m http.server "$PORT" -d "$PREVIEW_ROOT"
