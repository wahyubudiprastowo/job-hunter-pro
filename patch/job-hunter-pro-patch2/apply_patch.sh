#!/usr/bin/env bash
set -e
PROJECT_PATH="${1:-../job-hunter-pro}"
PATCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS=$(date +%Y%m%d_%H%M%S)
echo "=== Job-Hunter Pro PATCH 2 ==="
if [ ! -d "$PROJECT_PATH" ]; then echo "❌ Not found: $PROJECT_PATH"; exit 1; fi
FILES=("packages/extractors/linkedin.py" "data/answers.json")
BACKUP_DIR="$PROJECT_PATH/.backup_p2_$TS"
mkdir -p "$BACKUP_DIR"
for f in "${FILES[@]}"; do
    [ -f "$PROJECT_PATH/$f" ] && mkdir -p "$BACKUP_DIR/$(dirname "$f")" && cp "$PROJECT_PATH/$f" "$BACKUP_DIR/$f" && echo "  ✓ Backup: $f"
done
for f in "${FILES[@]}"; do
    [ -f "$PATCH_ROOT/$f" ] && mkdir -p "$(dirname "$PROJECT_PATH/$f")" && cp "$PATCH_ROOT/$f" "$PROJECT_PATH/$f" && echo "  ✓ Patch: $f"
done
echo "🎉 Done."
