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

if [[ ! -f ".env" ]]; then
    echo "ERROR: .env not found."
    echo "Create it first:"
    echo "  cp .env.example .env"
    exit 1
fi

docker compose up -d

echo
docker compose ps
