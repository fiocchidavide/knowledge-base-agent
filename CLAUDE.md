# CLAUDE.md — calibre-agent

This repo exists for one recurring job: **when Davide has ebook files sitting somewhere
and says "import these to Calibre," run the import runbook below without needing to be
told the steps.** The `calibre` MCP server (the `calibre-mcp` npm dependency of this
repo, configured in `.mcp.json`) is already wired up with writes enabled — see
[Environment](#environment) if a tool call fails.

## Trigger

Any message like *"I have some PDFs in Downloads, import them"*, *"import these books,"*
or *"add these to my library"* means: run the [Import runbook](#import-runbook) below.
Default `SOURCE_DIR` is `~/Downloads` unless the user names a different folder or file
list — if they do, use that instead (it must resolve under an allowed import root, see
[Environment](#environment)). No need to re-confirm the plan each time; just start,
reporting progress as you go per the [Ground rules](#ground-rules).

## Environment

- Calibre **GUI is normally running** with its Content Server on `http://localhost:8080`.
  Writes only work if that server allows local writes (Preferences → Sharing over the net
  → Advanced → *allow local connections to make changes*, or a standalone
  `calibre-server --enable-local-write`) — **Calibre-side setup is Davide's job, not
  yours**; if `calibre_ping` or a write call reports the server refusing writes or
  unreachable, stop and tell him what to fix, don't try to start Calibre yourself.
- The MCP-side write gate is already on (`CALIBRE_MCP_ENABLE_WRITE=1` in `.mcp.json`), so
  all tools below should be visible. If they aren't, the project's `.mcp.json` server
  wasn't trusted — check `/mcp` or `.claude/settings.json`'s `enabledMcpjsonServers`.
- Library name/id is **not hardcoded** — call `calibre_list_libraries` once at the start
  of a run to discover it and confirm connectivity; pass `library` explicitly to other
  tools only if more than one library is configured (leave it unset to use the default).
- `calibre_add_book` only imports from folders listed in `CALIBRE_MCP_ADD_ROOTS`. The
  server's default (unset env) covers `~/Documents` and `~/Downloads` — that's why the
  default `SOURCE_DIR` above is Downloads. If the user points you at a folder outside
  those roots (e.g. `~/Desktop`), tell them to add it via `CALIBRE_MCP_ADD_ROOTS` in
  `.mcp.json`'s `env` block (colon-separated paths) — you can edit that file yourself,
  but the server needs a restart to pick it up.

## Inputs (defaults — override per request)

- `SOURCE_DIR` — folder of books to import. Default `~/Downloads`. If it has subfolders,
  recurse into them.
- `REVIEW_DIR` — where copies of unidentified/unverified books go for manual review.
  Default `~/Downloads/_needs-review` (create it; never import *from* here).
- `REPORT` — the run report. Default `~/Downloads/_import-report.md`.
- Formats to import: `*.pdf *.epub *.mobi *.azw3`. Skip everything else (including
  `.md`/`.txt` — `calibre_add_book` isn't the right tool for those).

## Ground rules

- **Execute directly, one book at a time**, verifying each before moving to the next —
  don't batch a dry run first unless asked.
- **Uncertain → don't keep it in the library.** If you can't confidently identify a book
  from its own text, or the fetched metadata is missing/mismatched, remove it (see step
  7) and copy the original into `REVIEW_DIR` (keep the source subfolder name in the
  copied filename so it's traceable) instead of leaving it half-imported. Leave the
  original file in `SOURCE_DIR` untouched.
- **Metadata source of truth:** `calibre_recover_metadata` queries Open Library then
  Google Books (Goodreads has no public API since 2020 and isn't a source). Cross-check
  against what step 3 actually read from the book's own pages — never trust the filename.
- **Stop conditions.** If `calibre_add_book` starts failing repeatedly, or the Content
  Server stops responding, halt and report what you've done so far — don't keep looping.
- Report progress in short updates as you go (a line or two per book is enough); don't
  go silent for the whole run.

## Import runbook

### 0. Preflight (once per run)

1. `calibre_ping` — confirms the Content Server is reachable and reports write status.
2. `calibre_list_libraries` — confirms the library name/id and default.

If either fails, stop and tell the user what's wrong (see [Environment](#environment)) —
don't retry in a loop.

### Per-book procedure

For each matching file under `SOURCE_DIR`, in a stable order (sorted by path):

1. **Duplicate check.** Derive a rough title/author from the filename and run
   `calibre_search` (`mode: meta`). A clear existing match → status `duplicate`, skip.

2. **Add the file.** `calibre_add_book` with the absolute path. Capture the returned book
   id — you need it to read the book back and to remove it later if it doesn't pan out.

3. **Identify from the content, not the filename.** `calibre_get_content` on the new id —
   read the opening pages (and, for PDFs, skim for a copyright page); use `structure:
   true` first if you want the chapter map. Extract candidate title, author(s), edition,
   publisher, year. Many files have junk names (`795731065.pdf`, `top.dvi`) — the text is
   ground truth, the filename isn't.

4. **Find the ISBN.** `calibre_extract_isbn` (`apply: false` first to preview). If it
   finds a valid one, re-run with `apply: true` — it's the strongest lookup key.

5. **Fetch external metadata.** `calibre_recover_metadata` by id — a preview-only
   proposal from Open Library / Google Books, never writes.

6. **Double-check.** Compare the proposal against what you read in step 3:
   - Title + primary author match the title page → accept.
   - Mismatch, empty title/author, or a low-confidence result → **not verified**.

7. **Decide and act:**
   - **Verified & complete** (title, authors, and at least one of
     publisher/pubdate/isbn): `calibre_update_book` with the changes, then
     `calibre_get_book` to confirm what landed. Status `found`.
   - **Verified but thin** (title+author right, rest missing): apply what you have via
     `calibre_update_book`. Status `incomplete`.
   - **Not verified / not identified / mismatch:** `calibre_remove_book` with
     `ids: [id]` and `confirm: true` (it goes to Calibre's trash, recoverable), copy the
     original into `REVIEW_DIR`, status `unidentified` or `metadata-not-found`. Never
     leave an unverified book in the library.

8. **Log immediately** to `REPORT` (append one row per book, so a crash loses at most one
   entry).

## Report format (`REPORT`)

```
| # | File (rel path) | Book id | Status | Title (verified) | Author | ISBN | Source | Notes |
|---|-----------------|---------|--------|-------------------|--------|------|--------|-------|
| 1 | Algorithms/clrs.pdf | 3 | found | Introduction to Algorithms, 3rd ed | Cormen et al. | 978-0262033848 | OpenLibrary | title page matched |
| 2 | AI/795731065.pdf | — | metadata-not-found | — | — | — | — | copied to _needs-review; no ISBN, OL/Google empty |
```

**Status vocabulary:** `found` · `incomplete` · `metadata-not-found` · `unidentified` ·
`duplicate` · `error`.

End the report with a **summary block**: totals per status, and an explicit **"Needs
manual attention"** list (every `metadata-not-found` / `unidentified` / `error` row) with
its `REVIEW_DIR` copy path.

## When done

Print the summary (totals per status) and the path to the full report. Don't leave the
user to go dig for it.
