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

docker compose exec -T holotes \
    python -c \
    "import urllib.request; response = urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5); print('HTTP', response.status, response.read().decode())"
