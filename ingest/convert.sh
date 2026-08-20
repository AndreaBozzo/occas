#!/usr/bin/env bash
# Batch ULog -> Parquet conversion, delegated to ulog-convert from PX4/flight-review-rs.
#
# This project writes no ULog parser (docs/adr/0001). This wrapper exists only to pin
# and record the tool version alongside the output, so an AnalysisManifest can name it.
#
# M3: the upstream flag names below are ASSUMED and must be checked against
# `ulog-convert --help` before this script is used for anything real. If they differ,
# fix them here and note it in docs/adr/ rather than working around it.
set -euo pipefail

IN_DIR="${1:?usage: convert.sh <input-dir> <output-dir>}"
OUT_DIR="${2:?usage: convert.sh <input-dir> <output-dir>}"
ULOG_CONVERT="${ULOG_CONVERT:-ulog-convert}"

if ! command -v "$ULOG_CONVERT" >/dev/null 2>&1; then
  echo "ulog-convert not found. Install it from PX4/flight-review-rs, or set ULOG_CONVERT." >&2
  exit 127
fi

mkdir -p "$OUT_DIR"
VERSION="$("$ULOG_CONVERT" --version 2>&1 | head -1)"
echo "Using: $VERSION"

converted=0
failed=0
while IFS= read -r -d '' log; do
  if "$ULOG_CONVERT" "$log" --output "$OUT_DIR"; then
    converted=$((converted + 1))
  else
    # A conversion failure is data about the corpus, not just an error. M2 counts these.
    echo "FAILED: $log" >&2
    failed=$((failed + 1))
  fi
done < <(find "$IN_DIR" -type f -name '*.ulg' -print0)

cat > "$OUT_DIR/conversion-summary.json" <<JSON
{
  "tool": "ulog-convert",
  "tool_version": "$VERSION",
  "input_dir": "$IN_DIR",
  "converted": $converted,
  "failed": $failed,
  "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

echo "Converted $converted, failed $failed. Summary: $OUT_DIR/conversion-summary.json"
[ "$converted" -gt 0 ] || { echo "No logs converted." >&2; exit 1; }
