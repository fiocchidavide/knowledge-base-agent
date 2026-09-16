# calibre-agent

A Claude Code workflow, not a library. This repo wraps
[`calibre-mcp`](https://github.com/caelum29/calibre-mcp) (a dependency, see
`package.json`) with a project-scoped MCP config and a `CLAUDE.md` runbook, so opening
Claude Code here and saying *"I have some PDFs in Downloads, import them"* just works —
no re-explaining the process each time.

## Setup

```sh
npm install
```

That pulls in `calibre-mcp`; `.mcp.json` points Claude Code at it and turns on the
write gate. Calibre-side, one of these needs to be true (do this once):

- Calibre GUI running, with **Preferences → Sharing over the net → Advanced → allow
  local connections to make changes** ticked, Content Server restarted; or
- a standalone server: `calibre-server --enable-local-write --port 8080 "/path/to/Calibre Library"`
  (GUI must be closed — it holds the library lock).

Then open Claude Code in this folder and just ask it to import your books. See
`CLAUDE.md` for the full runbook it follows.

## Why a separate repo

`calibre-mcp` is the general-purpose server (published to npm, feature-general). This
repo is the personal workflow layer on top: the specific defaults (`~/Downloads` as the
usual source), the write-gate config, and the verification-first import procedure — kept
out of the server so the server stays generic.
