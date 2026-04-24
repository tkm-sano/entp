#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT="${1:-4020}"
BUILD_DIR="/tmp/talent-site/_site"

export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

"$REPO_ROOT/bin/jekyll" build

echo "Serving local preview at http://127.0.0.1:${PORT}/"
python3 -m http.server "$PORT" -d "$BUILD_DIR"
