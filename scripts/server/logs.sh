#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(
    CDPATH= cd -- "$(dirname -- "$0")" &&
    pwd
)"

PROJECT_ROOT="$(
    CDPATH= cd -- "$SCRIPT_DIR/../.." &&
    pwd
)"

cd "$PROJECT_ROOT"

LINES="${1:-100}"

docker compose logs \
    --tail="$LINES" \
    -f \
    holotes
