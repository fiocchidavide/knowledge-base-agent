# knowledge-base-agent

Claude Code plugin that routes PDFs/EPUBs into the right personal library — books to
[Calibre](https://github.com/caelum29/calibre-mcp), papers to
[Zotero](https://github.com/54yyyu/zotero-mcp) — with verified metadata. Also handles
ad hoc lookups and reorganizing items in either library. Runbook:
`skills/knowledge-base-agent/SKILL.md`.

## Install

```sh
git clone https://github.com/fiocchidavide/knowledge-base-agent.git ~/.claude/skills/knowledge-base-agent
```

Restart Claude Code (or `/reload-plugins`). It auto-loads as
`knowledge-base-agent@skills-dir` from any project.

## Setup

```sh
./setup.sh
```

Installs `calibre-mcp` (npm) and `zotero-mcp-server` (uv/pip). Then, one-time:

- **Calibre** — GUI running with *Preferences → Sharing over the net → Advanced →
  allow local connections to make changes*, Content Server restarted; or run
  `./start-server.sh` for a standalone write-enabled server (GUI must be closed).
- **Zotero** — desktop app running with *Settings → Advanced → Allow other
  applications to communicate with Zotero* ticked. First write triggers a permission
  dialog — click "Always Allow."

## Examples

```
import the PDFs in ~/Downloads
what does my Zotero library have on transformers?
find my book on distributed systems
go through my Calibre library and find stuff that's actually papers
move that paper into my "NLP" collection
```

## Repo layout

- `.claude-plugin/plugin.json` — plugin manifest
- `.mcp.json` — calibre + zotero MCP server config
- `skills/knowledge-base-agent/SKILL.md` — the runbook
- `setup.sh`, `start-server.sh` — install / standalone Calibre server helpers
