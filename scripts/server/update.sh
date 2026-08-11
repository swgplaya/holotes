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

if [[ $# -ne 1 ]]; then
    echo "Usage:"
    echo "  ./scripts/server/update.sh v0.2.1"
    exit 1
fi

TARGET_TAG="$1"

if ! git diff --quiet ||
   ! git diff --cached --quiet; then
    echo "ERROR: tracked working tree changes detected."
    echo "Commit or discard them before updating."
    exit 1
fi

echo "Fetching release tags..."
git fetch origin --tags --prune

if ! git rev-parse \
    --verify \
    --quiet \
    "refs/tags/$TARGET_TAG" \
    >/dev/null; then
    echo "ERROR: tag '$TARGET_TAG' does not exist."
    exit 1
fi

echo
echo "WARNING:"
echo "Create and download a Holotes database backup"
echo "before continuing with a production upgrade."
echo

read -r -p "Continue with $TARGET_TAG? [y/N] " ANSWER

case "$ANSWER" in
    y|Y|yes|YES)
        ;;
    *)
        echo "Update cancelled."
        exit 0
        ;;
esac

echo
echo "Switching to release $TARGET_TAG..."

git checkout \
    --detach \
    "$TARGET_TAG"

echo
echo "Building and recreating Holotes..."

docker compose up \
    -d \
    --build

echo
echo "Current status:"
docker compose ps
