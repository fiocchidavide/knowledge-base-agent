# knowledge-base-agent

A Claude Code **user-level skill/plugin**, not a library. It lives at
`~/.claude/skills/knowledge-base-agent/` and wraps two general-purpose MCP
servers — [`calibre-mcp`](https://github.com/caelum29/calibre-mcp) (an npm
dependency, see `package.json`) and
[`zotero-mcp`](https://github.com/54yyyu/zotero-mcp) (launched via `uvx`, no
install step) — with an `.mcp.json` and a `skills/knowledge-base-agent/SKILL.md`
runbook. Because it's a **skills-directory plugin** (auto-discovered from
`~/.claude/skills/`, loads as `knowledge-base-agent@skills-dir`), it's available in
*every* Claude Code conversation, not just when this folder is open — saying *"I have
some PDFs in Downloads, import them"* anywhere just works: books go to Calibre, papers
go to Zotero, and lookups or reorganizing across both are handled conversationally, no
re-explaining the process each time.

## Toggling it on/off

Because the two MCP servers spawn for every Claude Code session once this plugin is
enabled (there's no way to make MCP activation lazy/per-skill today), you may want to
switch it off in sessions that have nothing to do with books or papers:

- `/plugin disable knowledge-base-agent@skills-dir` / `/plugin enable ...` — disables or
  enables the whole plugin (skill + both MCP servers together). Run `/reload-plugins`
  after toggling.
- `/skills` — interactive menu to toggle just the skill's own auto-invocation (Space to
  cycle states, Esc to save) without touching the MCP servers.
- `/mcp` — interactive panel to toggle the `calibre`/`zotero` MCP connections
  individually, independent of the skill.

## Setup

```sh
./setup.sh
```

That installs `calibre-mcp` (npm) and `zotero-mcp-server` (uv/pip), and prints the
one-time manual steps each app still needs ticked on its own side (below). `.mcp.json`
already points Claude Code at both — `calibre-mcp` with the write gate on, `zotero-mcp`
via `uvx` with `ZOTERO_LOCAL=true`.

**Calibre-side** only matters for runs that actually touch a Calibre book — a
Zotero-only session doesn't need any of this. When it does matter, one of these needs
to be true:

- Calibre GUI running, with **Preferences → Sharing over the net → Advanced → allow
  local connections to make changes** ticked, Content Server restarted; or
- a standalone server: `./start-server.sh` (wraps
  `calibre-server --enable-local-write --port 8080 "/path/to/Calibre Library"`)
  (GUI must be closed — it holds the library lock).

If neither is true when an import needs Calibre, Claude will offer to run
`~/.claude/skills/knowledge-base-agent/start-server.sh` itself (with your go-ahead) and
shut it back down once the import is verified — see
`skills/knowledge-base-agent/SKILL.md`.

**Zotero-side**, one of these needs to be true (do this once):

- Zotero desktop running, with **Settings → Advanced → "Allow other applications
  to communicate with Zotero"** ticked (local mode, `ZOTERO_LOCAL=true`, already
  set in `.mcp.json`); or
- `ZOTERO_API_KEY` / `ZOTERO_LIBRARY_ID` set in `.mcp.json`'s `env` block instead,
  to use the web API.

Write access needs one extra one-time step: the first time Claude calls
`zotero_authorize_local_writes`, Zotero will pop up a permission dialog — click
"Always Allow." No separate CLI command needed.

Once set up, just ask Claude (in any project, any conversation) to import, look up, or
organize your books and papers. See `skills/knowledge-base-agent/SKILL.md` for the full
runbook it follows.

## Usage

The skill's description frontmatter auto-triggers it — no need to name it or open this
folder. Four request shapes it handles, each described in full in
`skills/knowledge-base-agent/SKILL.md`:

- **Import** — *"I have some PDFs in Downloads, import them"* / "import these books" /
  "add these to my library." Defaults to `~/Downloads` (recurses into subfolders) unless
  you name a different folder; only `*.pdf *.epub *.mobi *.azw3` are picked up. Claude
  works through the files one at a time, reads each one's actual content (never trusts
  the filename) to decide book vs. paper, and verifies metadata before filing it —
  Calibre via Open Library/Google Books lookups (`calibre_recover_metadata`), Zotero via
  DOI or extracted metadata. Unverified books are pulled back out of Calibre rather than
  left half-identified; uncertain papers stay in Zotero tagged `needs-review`. Every run
  writes a row-per-file report to `~/Downloads/_import-report.md` (status vocabulary:
  `found` / `incomplete` / `metadata-not-found` / `unidentified` / `duplicate` /
  `ambiguous` / `error`) and ends with a totals summary plus a "needs manual attention"
  list.
- **Lookups** — *"what does my Zotero library have on X,"* "find this book," "what have
  I highlighted in Z." Answered conversationally straight from the read tools, no runbook
  or file changes involved.
- **Reorganizing** — retagging, moving items between Zotero collections, merging
  duplicates, tidying loose files: handled ad hoc with the relevant read/write tools.
  Deletes and merges always get a dry-run preview and explicit confirmation first.
- **Retroactive sweep** (opt-in only) — *"go through my Calibre library and find stuff
  that's actually papers."* Scans the existing library, proposes every item it would
  reclassify, and waits for your explicit go-ahead before moving anything — this is the
  one flow that always confirms before acting, since it touches an already-organized
  library rather than a fresh import.

## Why a separate repo

`calibre-mcp` and `zotero-mcp` are the general-purpose servers (published to npm
and PyPI respectively, feature-general). This repo is the personal workflow layer
on top: the specific defaults (`~/Downloads` as the usual import source), the
write-gate config for both, and the verification-first import/routing procedure —
kept out of the servers so they stay generic.

## Repo layout

```
.claude-plugin/plugin.json     — plugin manifest (name, description, version, author);
                                  what makes this a skills-directory plugin
.mcp.json                      — the calibre + zotero MCP server definitions (commands,
                                  args, env — including the write-gate/local-mode flags)
skills/knowledge-base-agent/SKILL.md — the runbook Claude follows (auto-triggered by its
                                        description frontmatter): trigger phrases,
                                        environment/preflight checks, the per-file import
                                        procedure, and the report format
setup.sh                       — one-time installer: `npm install` (calibre-mcp) +
                                  `uv tool install` / `pip install` (zotero-mcp-server),
                                  then prints the manual one-time steps below
start-server.sh                — on-demand standalone Calibre Content Server launcher
                                  (write-enabled), used when the Calibre GUI isn't running
package.json / package-lock.json — the calibre-mcp npm dependency pin
.claude/settings.json          — project settings: enables the `calibre`/`zotero` MCP
                                  servers from `.mcp.json` and allowlists a few setup/
                                  health-check commands (`npm install`, `npm ci`, a
                                  localhost:8080 curl health check)
.gitignore                     — node_modules/, .DS_Store, *.log
```

If this folder is ever opened directly as a Claude Code *project* (rather than used as a
plugin), its `.mcp.json` also works as an ordinary project-scoped MCP config — just note
both paths would then be configuring the same two servers, so there's no need to also
enable the plugin in that same session.
