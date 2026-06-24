#!/usr/bin/env bash
set -e
PROJECT_PATH="${1:-../..}"
PATCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS=$(date +%Y%m%d_%H%M%S)

echo "=== Job-Hunter Pro Docs Bundle v2 ULTIMATE ==="
echo "Target: $PROJECT_PATH"

if [ -d "$PROJECT_PATH/docs" ]; then
    BACKUP="$PROJECT_PATH/docs.bak_v2_$TS"
    echo "Backing up to $BACKUP"
    mv "$PROJECT_PATH/docs" "$BACKUP"
fi

mkdir -p "$PROJECT_PATH/docs/PRDs"
cp -r "$PATCH_ROOT/docs/"* "$PROJECT_PATH/docs/"

echo "Done. Read docs/00_MASTER_CONTINUITY.md"
