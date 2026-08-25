#!/usr/bin/env bash
# Batch ULog -> Parquet conversion, delegated to ulog-convert from PX4/flight-review-rs.
#
# This project writes no ULog parser (docs/adr/0001). This wrapper exists only to pin
# and record the tool version alongside the output, so an AnalysisManifest can name it.
#
# The flag names here were ASSUMED until 2026-08-25 and one of them was wrong: the
# single-file form takes the output directory positionally and has no --output, which
# only exists on `batch`. Checked against `ulog-convert --help` at
# flight-review-rs#0fb44f74 and corrected. Two consequences worth keeping:
#
#   - `batch` is upstream's own parallel path and takes the directory directly, so the
#     shell loop this file used to run is gone. Less of our code between us and the tool
#     is the point of adr/0001.
#   - `--format json` emits one JSON object per file, which is what makes conversion
#     failures *data about the corpus* rather than lines on stderr. M2 counts them, and
#     ingest/inventory.py reads this file rather than re-deriving them.
set -euo pipefail

# PRUNE_RAW=1 deletes each .ulg once its conversion has produced output. See below.
IN_DIR="${1:?usage: convert.sh <input-dir> <output-dir>}"
OUT_DIR="${2:?usage: convert.sh <input-dir> <output-dir>}"
ULOG_CONVERT="${ULOG_CONVERT:-ulog-convert}"

if ! command -v "$ULOG_CONVERT" >/dev/null 2>&1; then
  echo "ulog-convert not found. Install it with:" >&2
  echo "  cargo install --git https://github.com/PX4/flight-review-rs flight-review" >&2
  echo "The crate is 'flight-review'; 'ulog-convert' is the binary it ships." >&2
  exit 127
fi

mkdir -p "$OUT_DIR"
VERSION="$("$ULOG_CONVERT" --version 2>&1 | head -1)"
echo "Using: $VERSION"

RESULTS="$OUT_DIR/conversion-results.jsonl"
# Not `set -e`-fatal: a batch where some files fail still produced the ones that did not,
# and which failed is the finding. The summary records the exit code rather than hiding it.
STATUS=0
"$ULOG_CONVERT" batch "$IN_DIR" --output "$OUT_DIR" --format json > "$RESULTS" || STATUS=$?

RESULT_LINES="$(wc -l < "$RESULTS" | tr -d ' ')"
INPUT_COUNT="$(find "$IN_DIR" -type f -name '*.ulg' | wc -l | tr -d ' ')"

cat > "$OUT_DIR/conversion-summary.json" <<JSON
{
  "tool": "ulog-convert",
  "tool_version": "$VERSION",
  "tool_source": "https://github.com/PX4/flight-review-rs",
  "input_dir": "$IN_DIR",
  "inputs": $INPUT_COUNT,
  "results": $RESULT_LINES,
  "exit_code": $STATUS,
  "results_file": "$RESULTS",
  "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

# Retention, as code rather than as a sentence. docs/09-dpia.md 1.4 says downloaded logs
# are deleted once the analysis they support no longer needs them, and 7.4 recorded that
# this was still policy and not a pipeline step. It is a step now.
#
# Deleting is safe here because the .ulg is not the evidence: logs.px4.io publishes it
# permanently, the manifest records the log_id, and anything removed is re-retrievable.
# What it buys is R5 -- the DPIA's largest residual risk is a geolocated corpus sitting on
# a personal machine, and this makes that corpus roughly a third of the size.
#
# A log is deleted only when its conversion produced **at least one .parquet file**, and
# that bar is deliberately higher than it looks. Neither weaker test works:
#
#   - `ulog-convert` reports `"converted": true` for a 10-byte file that is not a ULog.
#     Verified 2026-08-25 by feeding it one.
#   - It also creates an output directory for that file, containing manifest.json and
#     metadata.json and no data.
#
# So the tool's own success flag and the directory's existence both say "converted" for a
# file it could not read. Parquet on disk is the only claim that survives contact with a
# broken input, and this is a delete: the guard has to be the strong one.
if [ "${PRUNE_RAW:-0}" = "1" ]; then
  pruned=0
  kept=0
  while IFS= read -r -d '' log; do
    stem="$(basename "$log" .ulg)"
    if [ -n "$(find "$OUT_DIR/$stem" -maxdepth 1 -name '*.parquet' -print -quit 2>/dev/null)" ]; then
      rm -f "$log"
      pruned=$((pruned + 1))
    else
      kept=$((kept + 1))
    fi
  done < <(find "$IN_DIR" -type f -name '*.ulg' -print0)
  echo "Pruned $pruned converted .ulg files; kept $kept whose conversion produced nothing."
fi

echo "Inputs $INPUT_COUNT, results $RESULT_LINES, exit $STATUS."
echo "Per-file: $RESULTS"
echo "Summary:  $OUT_DIR/conversion-summary.json"
[ "$RESULT_LINES" -gt 0 ] || { echo "No results produced." >&2; exit 1; }
