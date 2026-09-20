---
name: knowledge-base-agent
description: Classify and import PDFs/EPUBs/MOBI/AZW3 into the right personal library — books go to Calibre, papers/articles go to Zotero — with verified metadata. Also handles ad hoc lookups in either library ("what does my Zotero library have on X", "find this book"), and reorganizing/moving/tagging items within or between them. Use whenever the user wants to import ebooks or papers, search or ask about their Calibre or Zotero library, or organize/move/tag items in either.
---

# knowledge-base-agent

This skill exists for one recurring job: **when the user has PDFs/EPUBs sitting somewhere
and says "import these," figure out which belong in Calibre (books) and which belong in
Zotero (papers/articles), and file each one correctly with verified metadata — without
needing to be told the steps.** It also handles ad hoc lookups ("what does my Zotero
library have on X") and reorganizing things between the two once they exist.

Two MCP servers back this, bundled with this plugin (`.mcp.json` at the plugin root,
writes enabled):
- **`calibre`** (the `calibre-mcp` npm package, run via `npx`) — the book library.
- **`zotero`** (the `zotero-mcp` package, run via `uvx`) — the paper/article library,
  talking to the local Zotero desktop app (`ZOTERO_LOCAL=true`).

See [Environment](#environment) if a tool call fails on either. This plugin lives at
`~/.claude/skills/knowledge-base-agent/` — that's the repo to edit if these
instructions, the MCP config, or the helper scripts need changing.

## Trigger

- *"I have some PDFs in Downloads, import them,"* *"import these books,"* *"add these to
  my library"* → run the [Import runbook](#import-runbook). Default `SOURCE_DIR` is
  `~/Downloads` unless the user names a different folder or file list — if they do, use
  that instead (it must resolve under an allowed Calibre import root, see
  [Environment](#environment)).
- *"What does my Zotero library have on X,"* *"find my notes on Y,"* *"what have I
  highlighted in Z"* → no runbook needed, see [Zotero lookups](#zotero-lookups-ad-hoc).
- *"Go through my Calibre library and find stuff that's actually papers"* (or similar,
  explicitly about existing/already-organized items) → see
  [Retroactive sweep](#retroactive-sweep-opt-in).
- Anything else about moving/tagging/organizing existing items → see
  [General organize/move requests](#general-organizemove-requests).

No need to re-confirm the plan before starting an import or a lookup; just start,
reporting progress as you go per the [Ground rules](#ground-rules). The retroactive sweep
is the one flow that always proposes before acting (see its section). This skill can
trigger from any project directory — it isn't tied to being opened in a specific folder.

## Environment

**Calibre:**
- **The Content Server only needs to be running when this run is actually going to
  add/update/remove a Calibre book.** Pure Zotero work — ad hoc lookups, an
  organize/move request that never touches Calibre, or an import run where every file
  turns out to be a paper or ambiguous — never needs Calibre up. Don't `calibre_ping` or
  otherwise block on Calibre in those cases; see the lazy check in the
  [Preflight](#0-preflight-once-per-run) and [per-file procedure](#per-file-procedure).
- **If it does turn out to be needed** (the first file in a run classifies as a book) and
  `calibre_ping` / `calibre_list_libraries` / a write call reports the server unreachable
  or refusing writes:
  - Check whether the Calibre GUI process is running (e.g.
    `pgrep -f "Contents/MacOS/calibre$"`). If so, it's holding the library lock a
    standalone server would need — ask the user to either turn on "allow local
    connections to make changes" in the running GUI's Preferences and restart its
    Content Server, or quit the GUI themselves so a standalone server can bind the
    library. Don't quit their GUI for them — it may hold unsaved state.
  - If the GUI isn't running, **propose to the user that you start the standalone
    server yourself**: `~/.claude/skills/knowledge-base-agent/start-server.sh` (takes an
    optional library-path argument). Get their go-ahead, launch it in the background,
    capture its PID, then re-`calibre_ping` to confirm it's up before continuing that
    file.
  - Once you've verified (`calibre_get_book`) that every book needing the server this run
    is done — or the run ends — **kill the process at that PID yourself**, so the user
    isn't left with a write-enabled Content Server they didn't start. Only kill a server
    you started this way; never touch one that was already running. Note in the run
    report that you started/stopped it.
  - If the user declines, or the GUI-lock case applies and there's no way forward
    without them acting, stop and tell them what to fix — don't keep retrying or try to
    force it.
- The MCP-side write gate is already on (`CALIBRE_MCP_ENABLE_WRITE=1` in this plugin's
  `.mcp.json`).
- Library name/id is **not hardcoded** — call `calibre_list_libraries` the first time
  it's actually needed in a run to discover it and confirm connectivity; pass `library`
  explicitly to other tools only if more than one library is configured.
- `calibre_add_book` only imports from folders listed in `CALIBRE_MCP_ADD_ROOTS`
  (default `~/Documents` and `~/Downloads`). If the user points you at a folder outside
  those roots, tell them to add it via `CALIBRE_MCP_ADD_ROOTS` in
  `~/.claude/skills/knowledge-base-agent/.mcp.json`'s `env` block (colon-separated
  paths) — you can edit that file yourself, but the server needs a reconnect (`/mcp`, or
  `/reload-plugins`) to pick it up.

**Zotero:**
- Zotero desktop is normally running locally; the server reads `~/Zotero/zotero.sqlite`
  directly (`ZOTERO_LOCAL=true`). Reads should work as soon as Zotero's Settings →
  Advanced → "Allow other applications to communicate with Zotero" is ticked —
  **Zotero-side setup is the user's job, not yours.**
- Writes need a one-time in-app authorization. Call `zotero_write_capabilities` at the
  start of a run; if it reports writes aren't authorized, call
  `zotero_authorize_local_writes` — this pops a permission dialog in the Zotero desktop
  app for the user to click "Always Allow." Don't attempt writes before this succeeds.
- Unlike Calibre, there's no hardcoded write gate env var beyond `ZOTERO_LOCAL` — write
  access is purely the in-app authorization above.

**Neither server showing up?** This is a user-level plugin, so check `/plugin` (is
`knowledge-base-agent@skills-dir` enabled?) and `/mcp` (are `calibre`/`zotero` connected
within it?) rather than a project's `.mcp.json` trust settings.

## Inputs (defaults — override per request)

- `SOURCE_DIR` — folder of files to import. Default `~/Downloads`. If it has subfolders,
  recurse into them.
- `REVIEW_DIR` — where copies of unidentified/unverified/ambiguous files go for manual
  review. Default `~/Downloads/_needs-review` (create it; never import *from* here).
- `REPORT` — the run report. Default `~/Downloads/_import-report.md`.
- `ZOTERO_INBOX` — the Zotero collection new papers land in until the user sorts them.
  Default `Inbox` (create it if it doesn't exist).
- Formats to import: `*.pdf *.epub *.mobi *.azw3`. Skip everything else (including
  `.md`/`.txt`).

## Ground rules

- **Execute directly, one file at a time**, verifying each before moving to the next —
  don't batch a dry run first unless asked.
- **Content is truth, never the filename.** Many files have junk names
  (`795731065.pdf`, `top.dvi`); always identify from what's actually on the page.
- **Book vs. paper is a content judgment, not a rule of thumb.** Look for book signals
  (ISBN, a table of contents/chapters, a copyright/dedication page, "Nth edition") vs.
  paper signals (a DOI, an abstract, a references/bibliography section, a journal or
  conference name, article-length page count). If it's genuinely ambiguous (a book
  chapter, a thesis, a technical report), don't force a guess — treat it like an
  unidentified item (see below).
- **Calibre is verify-or-remove; Zotero is add-then-flag.** Calibre has no good "review
  bin" concept for a half-imported book, so an unverified book gets pulled back out (see
  step 10 of the import runbook) and the source copied to `REVIEW_DIR`. Zotero has a
  proper Inbox + tagging model, so an uncertain paper still gets added (tagged
  `needs-review`, left in `ZOTERO_INBOX`) rather than deleted — don't apply Calibre's
  removal rule to Zotero items.
- **Never delete or merge without confirming first**, on either side:
  `calibre_remove_book`/`calibre_merge_books` and `zotero_merge_duplicates` all need a
  human-legible reason and, for merges, a dry-run preview before the real call.
- **Metadata source of truth:** for books, `calibre_recover_metadata` queries Open
  Library then Google Books. For papers, `zotero_add_by_doi` (when a DOI was found) is
  authoritative; otherwise cross-check whatever `zotero_add_from_file` extracted against
  what you actually read on the page.
- **Stop conditions.** If writes start failing repeatedly on either server, or a Content
  Server / Zotero connection stops responding, halt and report what you've done so far —
  don't keep looping.
- Report progress in short updates as you go (a line or two per file is enough); don't go
  silent for the whole run.

## Import runbook

### 0. Preflight (once per run)

1. `zotero_write_capabilities` — confirms Zotero connectivity and write status; if writes
   aren't authorized yet, call `zotero_authorize_local_writes` and wait for the user to
   approve the dialog before continuing to any Zotero write.

Calibre is **not** checked here — only lazily, the first time a file in this run actually
classifies as a book (step 3 of the per-file procedure). If nothing under `SOURCE_DIR`
turns out to be a book, `calibre_ping`/`calibre_list_libraries` are never called and the
Content Server never needs to be running.

If the Zotero check fails, stop and tell the user what's wrong (see
[Environment](#environment)) — don't retry in a loop.

### Per-file procedure

For each matching file under `SOURCE_DIR`, in a stable order (sorted by path):

1. **Read the file's own content** to get real signal before deciding anything: opening
   pages, any copyright/title page, and skim for an abstract/DOI/references section.

2. **Classify: book or paper?** Using the signals in [Ground rules](#ground-rules):
   - **Book →** continue with the Calibre path below.
   - **Paper →** continue with the Zotero path below.
   - **Ambiguous →** don't add to either library. Copy the original into `REVIEW_DIR`
     (keep the source subfolder name in the copied filename so it's traceable), status
     `ambiguous`, leave the original in `SOURCE_DIR` untouched, log and move on.

#### Book path (Calibre)

3. **Bring Calibre up, if this is the first book this run.** The first time a file in
   this run classifies as a book, call `calibre_ping` and `calibre_list_libraries`.
   - Reachable and writable → continue, remembering the library id/name for the rest of
     the run (don't re-check on every subsequent book).
   - Unreachable or refusing writes → follow the propose-start / shut-down-after flow
     under [Environment → Calibre](#environment) before continuing this file.
4. **Duplicate check.** Derive a rough title/author from the filename (informed by the
   real content you read in step 1) and run `calibre_search` (`mode: meta`). A clear
   existing match → status `duplicate`, skip the rest of this path.
5. **Add the file.** `calibre_add_book` with the absolute path. Capture the returned book
   id.
6. **Identify from the content, not the filename** (you've already read the opening
   pages in step 1 — use `calibre_get_content` with `structure: true` if you need the
   chapter map too). Extract candidate title, author(s), edition, publisher, year.
7. **Find the ISBN.** `calibre_extract_isbn` (`apply: false` first to preview). If it
   finds a valid one, re-run with `apply: true` — it's the strongest lookup key.
8. **Fetch external metadata.** `calibre_recover_metadata` by id — a preview-only
   proposal from Open Library / Google Books, never writes.
9. **Double-check.** Compare the proposal against what you read: title + primary author
   match the title page → accept; mismatch, empty title/author, or low confidence →
   **not verified**.
10. **Decide and act:**
    - **Verified & complete** (title, authors, and at least one of
      publisher/pubdate/isbn): `calibre_update_book` with the changes, then
      `calibre_get_book` to confirm. Status `found`.
    - **Verified but thin** (title+author right, rest missing): apply what you have.
      Status `incomplete`.
    - **Not verified / not identified / mismatch:** `calibre_remove_book` with
      `ids: [id]` and `confirm: true` (goes to Calibre's trash, recoverable), copy the
      original into `REVIEW_DIR`, status `unidentified` or `metadata-not-found`. Never
      leave an unverified book in the library.
11. **Log immediately** to `REPORT` (append one row per file).

If you started the Calibre server yourself for this run, shut it down (see
[Environment → Calibre](#environment)) once the last book needing it is verified, or the
run ends — don't leave it running for the user.

#### Paper path (Zotero)

3. **Duplicate check.** `zotero_search_items` / `zotero_advanced_search` by title/author,
   and `zotero_find_duplicates`. A clear existing match → status `duplicate`, skip.
4. **Add the item.**
   - If a DOI was found while reading the content: `zotero_add_by_doi` first (pulls
     authoritative metadata), then `zotero_attach_file` to attach the actual local PDF
     to the created item.
   - Otherwise: `zotero_add_from_file` directly, then patch anything wrong or missing
     via `zotero_update_item` using what you read on the page in step 1.
5. **File into the Inbox.** Check for `ZOTERO_INBOX` via `zotero_get_collections` /
   `zotero_search_collections`; create it once with `zotero_create_collection` if
   missing; add the item via `zotero_manage_collections`. New papers always land here —
   don't guess a topic collection, the user sorts those themselves.
6. **Verify.** `zotero_get_item_metadata` to confirm what landed.
7. **Decide status:**
   - Title/author/DOI check out → status `found`.
   - Extracted metadata is thin but plausible → status `incomplete`, still kept in Inbox.
   - Genuinely uncertain (extraction failed, no matching metadata anywhere) → still keep
     the item (don't delete), tag it `needs-review` via `zotero_update_item`, status
     `unidentified`.
8. **Log immediately** to `REPORT` (append one row per file).

## Zotero lookups (ad hoc)

For "what does my library have on X" / "find my notes on Y" / "what have I highlighted
in Z" style requests: no runbook, just use the read tools directly and answer
conversationally — `zotero_search_items`, `zotero_advanced_search`,
`zotero_get_item_fulltext`, `zotero_get_annotations`, `zotero_get_notes`,
`zotero_get_collections` / `zotero_get_collection_items`, `zotero_get_tags` /
`zotero_search_by_tag`, `zotero_semantic_search` if a plain keyword search comes up
empty. Same rule as everywhere else: quote what the source actually says, don't
paraphrase from memory of the title alone.

## Retroactive sweep (opt-in)

Only runs when explicitly asked (e.g. "go through my Calibre library and find stuff
that's actually papers"). This is stricter than a fresh import because it touches an
already-organized library — a misclassification here is more costly than for a new file.

1. Enumerate the Calibre library: `calibre_search`, unfiltered or per whatever criteria
   the user gave.
2. Classify each item with the same content-based rule as the import runbook, reading
   content via `calibre_get_content`.
3. **Always propose before moving anything.** List every flagged item (title, author,
   why it was flagged) and wait for the user's explicit confirmation — never move or
   remove a Calibre item on your own judgment in this flow.
4. On confirmation, per approved item:
   - Get the underlying file. `calibre_get_book` only returns format names, not a
     filesystem path — build the download URL yourself from the `serverUrl` /
     `libraryId` it returns plus the format, i.e.
     `{serverUrl}/get/{fmt}/{id}/{libraryId}`, and save the response to a temp file.
     (This endpoint isn't wrapped by a dedicated calibre-mcp tool — if it doesn't behave
     as expected, stop and tell the user rather than guessing further.)
   - Run that file through the Paper path above (steps 4–9) to get it into Zotero.
   - Once the Zotero copy is verified, `calibre_remove_book` (`confirm: true`) to remove
     it from Calibre.
5. Log to `REPORT` the same way, noting `swept-from-calibre` in the notes column.

## General organize/move requests

For anything else ad hoc — retagging a paper, moving an item between Zotero collections,
merging duplicates, tidying loose files in a folder — there's no fixed script: use the
relevant read/write tools directly. Keep the two standing rules: content is truth over
filenames, and never delete or merge without confirming first (`zotero_merge_duplicates`
and `calibre_merge_books` always get a dry-run preview before the real call).

## Report format (`REPORT`)

```
| # | File (rel path) | Destination | Item id | Status | Title (verified) | Author | ISBN/DOI | Source | Notes |
|---|-----------------|-------------|---------|--------|-------------------|--------|----------|--------|-------|
| 1 | Algorithms/clrs.pdf | Calibre | 3 | found | Introduction to Algorithms, 3rd ed | Cormen et al. | 978-0262033848 | OpenLibrary | title page matched |
| 2 | Papers/attn.pdf | Zotero | ABCD1234 | found | Attention Is All You Need | Vaswani et al. | 10.48550/arXiv.1706.03762 | DOI lookup | added to Inbox |
| 3 | AI/795731065.pdf | none | — | metadata-not-found | — | — | — | — | copied to _needs-review; no ISBN, OL/Google empty |
```

**Status vocabulary:** `found` · `incomplete` · `metadata-not-found` · `unidentified` ·
`duplicate` · `ambiguous` · `error`.

End the report with a **summary block**: totals per status (and per destination), and an
explicit **"Needs manual attention"** list (every `metadata-not-found` / `unidentified` /
`ambiguous` / `error` row) with its `REVIEW_DIR` copy path where applicable.

## When done

Print the summary (totals per status/destination) and the path to the full report. Don't
leave the user to go dig for it.
