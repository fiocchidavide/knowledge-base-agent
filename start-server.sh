#!/usr/bin/env bash
# Starts a standalone Calibre Content Server with local writes enabled —
# what knowledge-base-agent/calibre-mcp needs for the write path to work.
# The Calibre GUI must be closed first (it holds an exclusive library lock).
set -euo pipefail

LIBRARY="${1:-$HOME/Calibre Library}"
PORT="${CALIBRE_SERVER_PORT:-8080}"

if pgrep -f "Contents/MacOS/calibre$" >/dev/null 2>&1; then
  echo "Calibre GUI appears to be running — it holds the library lock." >&2
  echo "Quit Calibre first, then re-run this script." >&2
  exit 1
fi

if ! command -v calibre-server >/dev/null 2>&1; then
  echo "calibre-server not found on PATH (expected from the Calibre install)." >&2
  exit 1
fi

echo "Starting Calibre Content Server (writes enabled) on port $PORT:"
echo "  library: $LIBRARY"
exec calibre-server --enable-local-write --port "$PORT" "$LIBRARY"
