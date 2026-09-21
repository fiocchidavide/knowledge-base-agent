# Spec: `zotero-import` skill

**Status: specification only — not implemented.** This file exists so a later session can
write `skills/zotero-import/SKILL.md` without re-deriving any of it. Everything below was
verified against the live library and the live MCP server on 2026-09-21; the numbers are
measurements, not estimates.

It condenses §1 (structure) and §2 (metadata) of `PLAN.md` into the rules a
*steady-state* import must follow — the ongoing "add this to Zotero" job, once the
migration is done and Calibre is gone.

---

## 1. What it replaces

`skills/knowledge-base-agent/SKILL.md` must be **retired or rewritten**, for two reasons:

1. **It routes books to Calibre**, which is being retired. Its central "book vs. paper"
   decision no longer has two destinations to choose between.
2. **It calls five tools that do not exist** on the current `zotero-mcp` server:
   `zotero_add_by_doi`, `zotero_add_from_file`, `zotero_manage_collections`,
   `zotero_find_duplicates`, `zotero_merge_duplicates`. Any run following it fails at the
   first Zotero write.

Recommended: keep the plugin, replace its single skill with `zotero-import`, drop the
`calibre` MCP server from `.mcp.json` once Calibre is actually deleted (not before — the
migration's fallback depends on it being readable).

The Calibre-specific capabilities worth *not* losing: `calibre_extract_isbn`'s job (find
an ISBN inside a PDF) has no Zotero equivalent and must be reimplemented locally with
`mutool` + a regex. See §4.

---

## 2. Correct tool inventory

Verified present on the server. Use only these.

| Job | Tool | Notes |
|---|---|---|
| Create item from DOI / URL / ISBN / BibTeX / CSL / **file** | `zotero_add_item` | One tool, `source_type='auto'`. Takes `collections`, `tags`, `if_exists`, `attach_mode`. |
| Attach a file to an existing item | `zotero_attach_file` | Idempotent on filename + MD5. Absolute paths only. |
| Edit metadata | `zotero_update_item` | ⚠ `tags=` **replaces**; use `add_tags`/`remove_tags`. Same trap on `collections`. |
| Many items at once | `zotero_batch_update` | Tags + `Key: value` lines in Extra. Selector by keys, query, or tag. |
| Move between collections | `zotero_set_item_collections` | Incremental `add_to` / `remove_from`. |
| Create / rename / delete collection | `zotero_create_collection`, `zotero_update_collection`, `zotero_delete_collection` | |
| Find things | `zotero_search_items`, `zotero_advanced_search`, `zotero_search_by_tag`, `zotero_search_by_citation_key`, `zotero_semantic_search` | |
| Inspect | `zotero_get_item_metadata`, `zotero_get_item_children`, `zotero_get_attachment_path` | |
| Read a PDF already in Zotero | `zotero_read_pdf_pages`, `zotero_get_pdf_outline`, `zotero_get_item_fulltext` | |
| Index new files | `zotero_update_search_database` | Must run after a batch of attachments. |
| Write gate | `zotero_write_capabilities`, `zotero_authorize_local_writes` | Call the first at preflight. |

**There is no duplicate-detection or merge tool.** Dedup is the skill's own job: search by
title/ISBN/DOI before creating, and hand genuine duplicates to the user to merge in the
Zotero UI (Duplicate Items pane). Never silently create a second copy.

**`zotero_add_item(source_type='isbn')` is documented as Open Library → Google Books.**
Measured on 95 real ISBNs: Open Library resolves 92% but returns thin, sentence-case
records with no edition and no series; the server's Google Books call is unauthenticated
and returns **HTTP 429 on every request**. So the built-in ISBN path is a *seed*, never
truth — §4 is the real pipeline, and it needs your own `GB_KEY`.

---

## 3. Structure rules the skill must enforce

Full rationale in `PLAN.md` §1. The operative rules:

- **New items go to `Inbox/` and nowhere else.** The skill never guesses a topic
  collection. Collections are context (`Courses/ETH/<course>`, `Projects/<name>`); only
  the user knows the context.
- **Classification is tags, not collections.** Every item gets:
  - 1–3 `topic:` tags from the controlled vocabulary (`PLAN.md` §1.2). A needed term that
    isn't in the list is a **vocabulary change to propose**, not a tag to invent silently.
  - exactly one `kind:` tag — `textbook · monograph · lecture-notes · reference · manual ·
    solutions · popular · paper`.
  - `needs-review` if any field failed the acceptance gate.
- **Item type follows the object, not the file.** `book` (has ISBN / formally published) ·
  `document` (author-hosted notes) · `manuscript` (pre-publication draft) ·
  `journalArticle` / `preprint` / `conferencePaper` for papers.
- **Field conventions** (`PLAN.md` §1.4) are not optional — they're what makes the
  bibliography output correct: edition as a bare number and never in the title,
  `shortTitle` set, `DOI:` in Extra for book-type items (no DOI field exists on `book`),
  full title including subtitle, creator order from the title page.
- **Extra always carries** `imported: <date>`, and `source: <where the file came from>`
  when it isn't obvious.

---

## 4. The metadata pipeline (the core of the skill)

**Do not reimplement this — it exists and is tested.** `migration/lib/` holds working
modules validated against 115 books and 475 live API queries. The skill should call them.
Full measurements in `PLAN.md` §2.

```
lib/sources.py   five source adapters + on-disk response cache
lib/norm.py      edition() — MARC 250 / free text -> edition NUMBER (43/43 on real data)
lib/clean.py     the eight cleanup rules
lib/resolve.py   per-field waterfall, majority-vote with priority tie-break
```

### 4.1 Which source for which field (measured, not assumed)

No single source suffices. The split is clean and non-obvious:

| field | use | never use |
|---|---|---|
| title, authors, pages, language, **abstract** | **Google Books** (94% hit, 86% abstracts) | catalogues — they are sentence-case |
| **edition, series, place** | **K10plus** — the *only* real source (58% / 46% / 89%) | Google Books — it has **none** of these, ever |
| DOI, structured author names | **Crossref** (34% hit, but authoritative) | |
| year | Crossref → Google Books → Open Library | ⚠ **K10plus — 37% wrong** |
| pages | `mutool info` on the actual file | any external source |

**Google Books needs an API key.** Unauthenticated it returns HTTP 429 on every request
(0% coverage); with a key it is the best single source (94%). Read it from `GB_KEY` in
the environment — **never hardcode it in the skill or any committed file.**

**Library of Congress is dominated** (21% coverage, nothing unique) — don't wire it in.

### 4.2 Three traps the skill must encode

1. **A library catalogue dates the printing, not the edition.** K10plus said Boyd &
   Vandenberghe was 2023 (it's 2004) and Rudin's *Real and Complex Analysis* 2013 (it's
   1987). Wrong in 24 of 65 comparable records. `resolve.py` carries this as a hard
   `NEVER` rule; keep it.

2. **An ISBN can resolve to a different book entirely.** ISBN `9780415283090` is
   *Basic German: A Grammar and Workbook* locally, but two independent sources **that
   agree with each other** return *An Introduction to Ethics for Health Professionals*.
   Agreement is not truth. **Cross-checking the external title against the local record /
   the PDF is a hard gate**, and it is the only thing that catches this class of error.

3. **A printing is not an edition.** MARC 250 yields `32. printing`, `[Nachdr.]`,
   `Corr. 2. print., [repr.]`. `norm.edition()` drops printing-only clauses, parses mixed
   ones (`4. ed., 4. print` → 4), handles `4a edizione` → 4, and correctly refuses to
   turn `20th-anniversary ed.` into edition 20.

### 4.3 Resolution rule

**Majority vote first; source priority only as the tie-break.** Three sources agreeing
beat one high-priority source — measured: Crossref alone dated Cover & Thomas 2005 while
Google Books, LoC and the PDF copyright page all said 2006.

### 4.4 The eight cleanup rules (`lib/clean.py`)

Each one traceable to a defect observed on real data:

1. Google Books splits the subtitle into its own field → rejoin.
2. Crossref returns XML-escaped text (`&amp;`) → unescape.
3. Catalogue titles are sentence-case → reject in favour of printed casing.
4. Copyright lines list every edition (`© 1996, 2005, 2024`) → take the **latest**.
5. Google Books appends the edition to the title → strip it into `edition`.
6. K10plus puts platform names (`SpringerLink`) in the series field → blocklist.
7. MARC place artefacts (`New York [u.a.]`) → strip.
8. Names arrive in three shapes → `{firstName, lastName}`, particles handled both ways
   (`Oorschot, Paul C. van` → `van Oorschot`). Spanish double surnames stay ambiguous by
   rule — **flag, don't guess**.

### 4.5 Adjudication — the model decides, the PDF rules

**The pipeline proposes; it never writes.** Its output is a dossier of candidate values
with provenance. The skill must then **read the file's own front matter and settle every
field against it**, for every item, regardless of how clean the candidates look. Five
agreeing catalogues agree about a *catalogue record*, not about the file on disk — see
§4.2 trap 2, where two independent sources agreed with each other and were both wrong.

Order of authority:

```
1. the PDF's typeset title page and verso (copyright page)   <- decisive
2. rest of the front matter: series page, preface, TOC
3. external sources — for what the PDF omits, and to corroborate
4. the local/prior record — a prior judgement, not final
5. page 1 / the cover image                                  <- lowest
```

**⚠ Page 1 is the least trustworthy page.** 47% of the migrated corpus had an image-only
first page. Covers in scraped PDFs are fetched separately from retailer or catalogue
pages and can show the wrong edition, printing, or book. Distrust a cover that: is an
image while the body has a text layer; differs in page size or resolution from what
follows; carries site branding or a watermark; or states an edition the title page does
not. **The internal title page outranks the cover, always.**

**Reading image-only pages needs no OCR toolchain** (`tesseract`/`ocrmypdf` are not
installed). Render and look:

```
mutool draw -F txt -o - <pdf> 1-10                  text layer, if any
mutool draw -F png -r 150 -o p%d.png <pdf> 1-10     render; the model reads the images
```

Rendering is effectively free — page 3 of a 206 MB scan took 0.03 s. That same trick
resolved a book the previous pipeline had marked permanently unverifiable for exceeding
its text-extraction size limit.

Judgements that stay with the model, because no rule suffices: where the subtitle
boundary falls · edition vs. printing vs. impression · which of the copyright,
first-publication, this-printing and online-first years dates *this* artifact · author
order and ambiguous name splits · `book` vs `document` vs `manuscript` · whether a draft
is the edition it claims · whether a supplied abstract is a real abstract or marketing
copy · whether a duplicate is one work in two artifacts.

Resolution, after reading:
**PDF states it → PDF wins, whatever the sources say**, with the discrepancy recorded in
`extra` so the decision stays auditable. PDF silent → sources, by §4.1/§4.3. Sources
conflict and PDF silent → leave empty and tag `needs-review`. An empty field is honest;
a guessed one poisons a bibliography.

### 4.6 Per-file procedure

```
1. IDENTIFY — content is truth; the filename is a hint and the cover is an unsourced claim.
   mutool info <pdf>                        -> page count (the only page-count source)
   mutool draw -F txt -o - <pdf> 1-10       -> front matter text layer, if any
   mutool draw -F png -r 150 ... <pdf> 1-10 -> render and READ when there is no text
                                               layer, or the cover is image-only (47%)

   Book signals: ISBN on the copyright page, a table of contents, "Nth edition",
                 a dedication or preface, >150 pages.
   Paper signals: DOI, abstract, references section, journal/conference name, <60 pages.
   Ambiguous (thesis, book chapter, tech report): import with `needs-review` and say so.

2. EXTRACT IDENTIFIERS from that text:
   ISBN   /\b97[89][\d -]{10,}\b|\b\d{9}[\dXx]\b/  -> validate the checksum
   DOI    /\b10\.\d{4,9}\/[-._;()\/:a-z0-9]+\b/i
   arXiv  /arXiv:\s*\d{4}\.\d{4,5}/

3. RESOLVE
   DOI or arXiv  -> zotero_add_item(source=<doi|url>)   authoritative, prefer always
   ISBN          -> lib/sources.py fan-out, then lib/resolve.py
   nothing       -> the author's own page is authoritative for self-hosted notes.
                    Never invent a publisher; ask instead.

4. ADJUDICATE  (§4.5; PLAN.md §2.6) — NOT a gate the pipeline applies on its own
   read the front matter, settle every field against the PDF
   PDF states it        -> PDF wins; note any override in `extra`
   PDF silent, agreed   -> write
   PDF silent, conflict -> leave empty and tag needs-review
   never pick silently between conflicting values

5. WRITE
   zotero_add_item(source=<absolute path>, collections=['Inbox'], tags=[...],
                   if_exists='file')
   -> zotero_update_item(...) to correct what extraction got wrong
   -> zotero_update_search_database() once per batch
```

**Operational:** send `?mailto=` to Crossref (polite pool); **follow redirects on Open
Library** — `/isbn/X.json` 302s to `/books/OL…M.json` and a non-following client reports a
false miss; cache every response (`lib/sources.py` already does), which makes any batch
re-runnable at zero API cost.

## 5. Behaviour

- **Execute directly**, one file at a time, verifying before moving on. No dry run unless
  asked.
- **Report as you go** — a line per file.
- **Never delete or merge without confirming.** There is no merge tool anyway; propose and
  let the user do it in the UI.
- **Stop after repeated write failures** rather than looping.
- **Default source folder** `~/Downloads`, recursing. Formats: `.pdf .epub .djvu .docx`.
- **Ledger** — reuse the append-only JSONL pattern from `PLAN.md` §3.1 for any run over ~10
  files, with `imported:` in Extra as the self-describing fallback. Small runs don't need it.

---

## 6. To decide when implementing

1. **Fold in or replace?** A single `zotero-import` skill, or keep `knowledge-base-agent`
   as the name and rewrite its body? The name is referenced in the plugin manifest and the
   MCP server names; a rewrite in place is less churn.
2. **When to drop the `calibre` MCP server** from `.mcp.json` — only after `~/Calibre
   Library` is actually deleted, since the migration fallback reads it.
3. **Topic vocabulary drift.** The list in `PLAN.md` §1.2 covers today's 167 items. Decide
   where it lives once the skill exists — a `references/topics.md` the skill reads, so it
   can be extended without editing the skill body. Recommended.
4. **Auto-tagging confidence.** Should the skill propose `topic:` tags from content and
   apply them, or always ask? Suggested: apply when the topic is unambiguous from the
   title/abstract, ask when it would need a new vocabulary term.
5. **Reimplement `calibre_extract_isbn`** as a local helper script (`mutool` + checksum
   validation) — §4 step 1 depends on it and there is no Zotero-side equivalent.
6. **Better BibTeX.** Citation keys auto-pin on creation; BBT 9.x offers no programmatic
   refresh. If a key is malformed, the only fix is writing `citation_key` directly via
   `zotero_update_item`. Decide whether the skill checks keys at all.
