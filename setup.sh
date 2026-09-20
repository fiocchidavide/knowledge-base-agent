#!/usr/bin/env bash
# One-time setup for both MCP servers this repo wires together:
#   - calibre-mcp: installed as an npm dependency (already documented in README.md)
#   - zotero-mcp-server: installed as a uv/pip tool (mirrors the calibre-mcp step)
# Neither app's own local-API settings can be flipped from here — those are printed
# as manual steps at the end.
set -euo pipefail

cd "$(dirname "$0")"

echo "== Calibre: installing calibre-mcp (npm) =="
npm install

echo
echo "== Zotero: installing zotero-mcp-server =="
if command -v uv >/dev/null 2>&1; then
  uv tool install zotero-mcp-server
elif command -v pip >/dev/null 2>&1; then
  pip install zotero-mcp-server
else
  echo "Neither uv nor pip found on PATH. Install one, then run:" >&2
  echo "  uv tool install zotero-mcp-server   # or: pip install zotero-mcp-server" >&2
  echo "(New to the command line? See the community Zotero MCP Setup GUI installer.)" >&2
fi

cat <<'EOF'

== Manual steps (one-time, per app) ==

Calibre:
  - GUI running, with Preferences -> Sharing over the net -> Advanced ->
    "allow local connections to make changes" ticked, Content Server restarted;
    or use ./start-server.sh for a standalone write-enabled server (GUI closed).

Zotero:
  - Zotero 7+: Settings -> Advanced -> tick "Allow other applications on this
    computer to communicate with Zotero".
  - .mcp.json already points Claude Code at zotero-mcp with ZOTERO_LOCAL=true,
    so no separate "zotero-mcp setup" / Claude Desktop config step is needed here.
  - Writes (Zotero 10+ only): the first time Claude calls
    zotero_authorize_local_writes it pops a permission dialog in Zotero --
    click "Always Allow". You can also run `zotero-mcp authorize-local` yourself
    once zotero-mcp-server is installed, if you'd rather do it ahead of time.

See README.md and skills/knowledge-base-agent/SKILL.md for the full picture.
EOF
