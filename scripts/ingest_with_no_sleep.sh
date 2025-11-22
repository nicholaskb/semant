#!/bin/bash
#
# Run ingestion with sleep prevention (macOS)
# 
# This prevents your Mac from sleeping during ingestion
#
# Usage:
#   ./scripts/ingest_with_no_sleep.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚫 Preventing sleep during ingestion..."
echo "   (Press Ctrl+C to stop and allow sleep)"

# Prevent sleep and run the parallel ingestion
# -d: prevent display sleep
# -i: prevent idle sleep
# -m: prevent disk sleep
caffeinate -d -i -m bash "$PROJECT_ROOT/scripts/ingest_uploads_parallel_screens.sh" "$@"

