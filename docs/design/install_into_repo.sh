#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /absolute/path/to/crm-repository" >&2
  exit 64
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$1" && pwd)"
DEST="$REPO_ROOT/docs/design"

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "Repository root does not exist: $REPO_ROOT" >&2
  exit 66
fi

mkdir -p "$DEST"

for file in \
  README.md REFERENCE_CONTACT_SHEET.png design-tokens.json design-tokens.css \
  screen-reference-map.csv asset-source-manifest.csv selected-icon-map.csv \
  LICENSE_NOTICES.md SHA256SUMS.txt INSTALL_IN_REPOSITORY.md; do
  cp -f "$SOURCE_DIR/$file" "$DEST/$file"
done

for directory in assets brand mock-data prototype references; do
  rm -rf "$DEST/$directory"
  cp -R "$SOURCE_DIR/$directory" "$DEST/$directory"
done

cp -f "$SOURCE_DIR"/docs/*.md "$DEST/"

echo "Installed frontend reference materials into: $DEST"
echo "Review and append $DEST/AGENTS_FRONTEND_PATCH.md to $REPO_ROOT/AGENTS.md"
echo "No application source, dependencies, secrets, or deployment files were changed."
