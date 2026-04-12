#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/workspace/repo"
ZIP_URL="https://raw.githubusercontent.com/joachimvandekerckhove/cogs205b-s26/main/modules/02-version-control/files/data.zip"
DATE_STR="$(date +%F)"
DEST_DIR="$REPO_ROOT/data/$DATE_STR"
TMP_DIR="$(mktemp -d)"
ZIP_FILE="$TMP_DIR/data.zip"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$DEST_DIR"

wget -q -O "$ZIP_FILE" "$ZIP_URL"
unzip -q "$ZIP_FILE" -d "$TMP_DIR/unpacked"

find "$TMP_DIR/unpacked" -maxdepth 1 -type f -name "*.csv" -exec cp {} "$DEST_DIR/" \;

cd "$REPO_ROOT"
git add scripts/fetch-csvs.sh "data/$DATE_STR"/*.csv
git diff --cached --quiet || git commit -m "Add CSV files for $DATE_STR"
git branch -M main
git push -u origin main
