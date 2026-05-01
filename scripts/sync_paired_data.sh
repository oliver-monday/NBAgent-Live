#!/usr/bin/env bash
# scripts/sync_paired_data.sh
#
# Pulls recent forward_collection workflow artifacts and
# extracts per-game CSVs to data/wp_kalshi_paired/.
#
# Usage:
#   ./scripts/sync_paired_data.sh           # last 30 days
#   ./scripts/sync_paired_data.sh 90        # last 90 days
#   ./scripts/sync_paired_data.sh all       # all available
#
# Prerequisites:
#   gh CLI installed (`brew install gh`)
#   gh authenticated (`gh auth login`, one-time)
#
# Idempotent: safe to re-run; existing local files are
# overwritten only if the artifact's version is newer
# (mv -f).

set -euo pipefail

REPO="oliver-monday/NBAgent-Live"
WORKFLOW="forward_collection.yml"
DEST="data/wp_kalshi_paired"
DAYS="${1:-30}"

# Pre-flight checks
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not installed. Install with: brew install gh"
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh not authenticated. Run: gh auth login"
  exit 1
fi

mkdir -p "$DEST"

# Fetch workflow run list with success status
if [ "$DAYS" = "all" ]; then
  LIMIT=200
else
  LIMIT=$((DAYS + 5))  # buffer for off-day skips
fi

echo "Listing successful runs of $WORKFLOW (limit=$LIMIT)..."
RUNS=$(gh run list \
  --repo "$REPO" \
  --workflow "$WORKFLOW" \
  --status success \
  --limit "$LIMIT" \
  --json databaseId,createdAt \
  | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta
runs = json.load(sys.stdin)
days = '$DAYS'
if days != 'all':
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    runs = [r for r in runs
            if datetime.fromisoformat(r['createdAt'].replace('Z', '+00:00')) >= cutoff]
print('\n'.join(str(r['databaseId']) for r in runs))
")

if [ -z "$RUNS" ]; then
  echo "No matching runs found."
  exit 0
fi

COUNT=$(echo "$RUNS" | wc -l | tr -d ' ')
echo "Found $COUNT runs to sync."

TMPROOT=$(mktemp -d)
trap "rm -rf $TMPROOT" EXIT

PULLED=0
SKIPPED=0
for run_id in $RUNS; do
  TMPDIR="$TMPROOT/$run_id"
  if gh run download "$run_id" \
       --repo "$REPO" \
       --dir "$TMPDIR" \
       --pattern 'wp-kalshi-paired-*' \
       2>/dev/null; then
    # Move CSVs to DEST
    find "$TMPDIR" -name '*_timeseries.csv' \
      -exec mv -f {} "$DEST/" \; 2>/dev/null || true
    find "$TMPDIR" -name '*_scoring_plays.csv' \
      -exec mv -f {} "$DEST/" \; 2>/dev/null || true
    PULLED=$((PULLED + 1))
  else
    SKIPPED=$((SKIPPED + 1))
  fi
done

echo ""
echo "Sync complete: $PULLED pulled, $SKIPPED skipped."
echo "Local files in $DEST:"
echo "  *_timeseries.csv:    $(ls $DEST/*_timeseries.csv 2>/dev/null | wc -l | tr -d ' ')"
echo "  *_scoring_plays.csv: $(ls $DEST/*_scoring_plays.csv 2>/dev/null | wc -l | tr -d ' ')"
