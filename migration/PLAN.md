# Calibre → Zotero migration plan

**Decision:** Zotero becomes the single library. Calibre is retired.
**Drafted:** 2026-09-21 · **Status:** approved structure, not yet executed.

Your four choices, recorded so a later session doesn't re-litigate them:

| Question | Your answer |
|---|---|
| Library structure | **Purist — flat library, tags + saved searches do the classifying** |
| Attachments | **Stored copies** into `~/Zotero/storage` |
| Calibre's fate | **Leave untouched** until you say otherwise |
| Review gates | **Approve every book** before it lands |

---

## 0. What's actually there (measured, not assumed)

**Calibre** — `~/Calibre Library`, 1.6 GB
- **115 books, 100% PDF**, every one has a cover, 1 format each
- 96 have an ISBN · 3 have a DOI · **19 have no identifier at all**
- Only 15 have a language set (8 `eng`, 7 `ita`) — the other 100 are blank
- 34 tag assignments total across 29 distinct tags — **~85 books are untagged**
- 24 series recorded, 74 books have a `comments` value
- 0 annotations, 1 last-read position → **nothing to preserve but the files and the metadata**

**Zotero** — `~/Zotero`, 383 MB, 52 items
- 19 journalArticle · 9 preprint · 2 conferencePaper · 2 webpage · 1 document · 1 book
- 83 attachments, **all stored copies** (`linkMode` 0/1) — no linked files
- 13 collections, mixing two incompatible axes (topic: `Math`, `AI`, `Cryptography`; source: `Dispense/ETH/…`)
- 14 distinct tags, **almost all auto-imported arXiv subject strings** ("Computer Science - Machine Learning") — no deliberate vocabulary
- **No sync account configured.** Better BibTeX installed.

### Three problems the migration must actively fix

1. **Author order is scrambled on ~32 books.** Calibre alphabetises its `books_authors_link` table, so the display order is wrong. *Introduction to Algorithms* reads "Leiserson, Rivest, Stein, Cormen"; *Handbook of Applied Cryptography* leads with van Oorschot instead of Menezes. The `author_sort` column usually preserves the true order — but it is itself mangled on some rows (`"Stein;, Thomas H. Cormen;Charles E. Leiserson;…"`). **Order must be taken from the PDF title page**, with `author_sort` as a hint.

2. **Edition lives in free text.** The `comments` field is not an abstract — it's a 76-character-average note, mostly edition statements ("Fourth Edition (2015).", "Quarta edizione.", "Fifth printing (with corrections).") mixed with real provenance you'd lose if it were discarded: *"Penultimate version (Feb 2025). Free notes, jmilne.org/math/"*, *"Community-retyped edition of the 3rd edition; not an official publisher release"*, and a whole paragraph on Billingsley warning the ISBN may be the wrong edition. Exactly one entry (Copeland, #230) is a genuine publisher abstract. So `comments` maps to **`edition` + `extra` + occasionally `abstractNote`** — never blindly to one field.

3. **The one "duplicate" is not a duplicate.** #225 and #236 are both *Principles of Mathematical Analysis*, 3rd ed., same ISBN — but #225 is a 388-page community retypeset (TeX, 1.6 MB) and #236 is the 594-page McGraw-Hill scan (30 MB). → **one Zotero item, two attachments**, the retype as primary.

---

## 1. The new Zotero structure

### The model in one sentence

Collections answer *"what was I doing when I needed this"*; tags answer *"what is this about"*; saved searches turn tag queries into the folders you actually click.

### 1.1 Collections — context only

```
Inbox/                      everything new lands here; should trend to empty
Courses/
  ETH/<course name>         ← replaces "Dispense/ETH"
  EPFL/<course name>
  MIT/<course name>
  UniTO/<course name>
Projects/<project name>     thesis, a paper being written, a reading group
Archive/                    superseded editions, things you're done with
```

That is the whole tree. **The 115 books go to the library root with no collection.** A book joins a collection only when a course or project actually uses it — and it can join several, because collections are membership, not location.

**Migrating the existing 13 collections:**

| Today | Becomes |
|---|---|
| `Dispense/ETH/*` | `Courses/ETH/*` (rename the parent, keep children) |
| `Dispense/MIT`, `Dispense/EPFL` | `Courses/MIT`, `Courses/EPFL` |
| `Math`, `AI`, `AI/LLMs · NLP`, `Cryptography` | **dissolved** → items get `topic:` tags, collections deleted |
| `Inbox` | kept as-is |
| `Manuals and reference` | dissolved → `kind:reference` |

`Dispense/ETH/{Large Language Models, Mathematics of Information, Geometry}` are course names, so they survive verbatim under `Courses/ETH/`.

### 1.2 Tags — the real search surface

Three namespaces, colon-prefixed so the tag selector groups them alphabetically.

**`topic:` — what it's about.** Controlled vocabulary, derived from your actual 167 items. A book gets 1–3; more than 3 means the vocabulary needs a new term, not a longer list.

```
Mathematics
  topic:real-analysis        topic:complex-analysis     topic:measure-theory
  topic:probability          topic:stochastic-processes topic:statistics
  topic:causal-inference     topic:linear-algebra       topic:abstract-algebra
  topic:number-theory        topic:algebraic-geometry   topic:calculus
  topic:numerical-analysis   topic:optimization         topic:logic
  topic:information-theory

Computer science
  topic:algorithms           topic:complexity           topic:computability
  topic:automata             topic:cryptography         topic:security
  topic:privacy              topic:networking           topic:operating-systems
  topic:computer-architecture topic:embedded            topic:machine-learning
  topic:nlp                  topic:ai                   topic:data-science
  topic:software-engineering topic:programming          topic:systems-administration

Other
  topic:history-of-computing topic:cognitive-science    topic:languages
```

**`kind:` — what sort of object it is.** Exactly one per item.

```
kind:textbook      a course-shaped book with exercises
kind:monograph     a research-level treatment
kind:lecture-notes Milne, Boneh–Shoup, course handouts
kind:reference     handbooks, pocket references, HAC
kind:manual        tool documentation (Pro Git, PowerShell)
kind:solutions     instructor's manuals, solution sets
kind:popular       GEB, The Annotated Turing
kind:paper         journal articles, preprints, conference papers
```

**Status — coloured, so they get keyboard shortcuts 1–3 and show as dots in the item list.**

```
★ reading        colour 1   what's open right now
to-read          colour 2   the actual queue
needs-review     colour 3   metadata you don't trust yet
```

**Housekeeping tags** (uncoloured, removable later):
`migration:calibre-2026-09` on every item this migration creates — a single click selects the whole run for inspection or rollback.

**One rule that keeps the vocabulary from rotting:** the arXiv-imported tags ("Computer Science - Machine Learning") are noise from a different namespace. Strip them on the 52 existing items, or leave them but never add more. Recommended: strip — `zotero_batch_update` does it in one call per tag.

### 1.3 Saved searches — the folders you click

⚠️ **The MCP server cannot create saved searches** — there is no such tool, and writing them into `zotero.sqlite` behind the running app would risk corrupting it. These are a **manual, 10-minute one-time job** in the Zotero UI (File → New Saved Search). Definitions to type in:

| Name | Condition |
|---|---|
| **Analysis** | Tag is `topic:real-analysis` **or** `topic:complex-analysis` **or** `topic:measure-theory` |
| **Algebra & Number Theory** | Tag is `topic:abstract-algebra` or `topic:linear-algebra` or `topic:number-theory` or `topic:algebraic-geometry` |
| **Probability & Statistics** | Tag is `topic:probability` or `topic:statistics` or `topic:stochastic-processes` or `topic:causal-inference` |
| **Theory of Computation** | Tag is `topic:complexity` or `topic:computability` or `topic:automata` or `topic:algorithms` |
| **Security & Crypto** | Tag is `topic:cryptography` or `topic:security` or `topic:privacy` |
| **Systems** | Tag is `topic:networking` or `topic:operating-systems` or `topic:computer-architecture` or `topic:embedded` |
| **AI/ML** | Tag is `topic:machine-learning` or `topic:nlp` or `topic:ai` |
| **Needs attention** | Tag is `needs-review` **or** Attachment File Type `does not contain` PDF |
| **Reading queue** | Tag is `to-read` or `★ reading` |
| **Italian** | Language contains `it` |
| **Added this month** | Date Added is in the last 30 days |

Everything else is `Ctrl/Cmd-F` in the tag selector, which is what the purist model is for.

### 1.4 Item types and field conventions

| Situation | Zotero item type |
|---|---|
| Published book with ISBN | `book` |
| Self-published / author-hosted notes (Milne ×14, Boneh–Shoup, Zach, Judson) | `document` |
| Pre-publication draft (Vershynin 2nd ed., Hernán & Robins) | `manuscript` |
| Everything already in Zotero | unchanged |

Field conventions, applied uniformly:

- **`title`** — full title including subtitle after a colon, exactly as on the title page. Edition does **not** go in the title (fix `Modern Operating Systems (4th Edition)` → title + `edition: 4`).
- **`shortTitle`** — main title before the colon. Makes `\cite` output readable.
- **`creators`** — order from the title page. `van Oorschot`, `Le Gall`, `González Vasco` keep their particles in `lastName`.
- **`edition`** — a bare number (`4`), Zotero's convention.
- **`series` / `seriesNumber`** — from Calibre or Crossref (`Texts and Readings in Mathematics` / `37`).
- **`numPages`** — real page count from `mutool info`, not the publisher's claim.
- **`language`** — `en` / `it`, inferred from content. Currently blank on 100 books.
- **`abstractNote`** — only a genuine abstract. Empty is better than an edition note.
- **`rights`** — `CC BY 4.0`, `Open access` where the source says so.
- **`url`** — for anything author-hosted or open access (jmilne.org, openlogicproject.org, miguelhernan.org).
- **`extra`** — the machine-readable tail, one `Key: value` per line:
  ```
  DOI: 10.1007/978-3-030-33143-6
  calibre-id: 181
  migrated: 2026-09-21
  ```
  `book` has no DOI field in Zotero, so `DOI:` in Extra is the standard place — Better BibTeX and CSL both read it. **`calibre-id:` is the durable join key** (see §3).
  Provenance prose from `comments` that isn't an edition goes here too, as a plain line.

---

## 2. Getting high-quality metadata

Everything in this section is **measured on your actual library** — 95 distinct ISBNs
× 5 sources = 475 live queries, then the full resolver run over all 115 books. The code
is in `lib/` and it runs.

### 2.1 Source coverage, per field

Five sources probed: Google Books (authenticated), Crossref, Open Library, **K10plus**
(the German union catalogue's SRU endpoint, MARCXML — free, no key) and the **Library of
Congress** SRU (MODS).

| field | crossref | k10plus | loc | **google** | openlib | any |
|---|---:|---:|---:|---:|---:|---:|
| **record found** | 34% | 89% | 21% | **94%** | 92% | **99%** |
| title | 34% | 89% | 21% | **94%** | 92% | 99% |
| authors | 29% | 89% | 21% | **94%** | 80% | 97% |
| publisher | 34% | **89%** | 0% | 77% | 92% | 96% |
| year | 34% | 88%⚠ | 21% | **92%** | 91% | 99% |
| **edition** | 8% | **58%** | 13% | **0%** | 25% | 63% |
| **series** | 18% | **46%** | 6% | **0%** | 9% | 49% |
| **place** | 0% | **89%** | 15% | **0%** | 31% | 89% |
| pages | 0% | 22% | 16% | **74%** | 72% | 93% |
| abstract | 2% | 44% | 5% | **86%** | 16% | 91% |

**Your key changes the picture completely.** Unauthenticated, Google Books returned
HTTP 429 on every request. With the key it is the single best source — 94% coverage,
the best author data, and **86% real publisher abstracts**, which nothing else supplies.

**But no single source is sufficient**, and the split is clean:
- **Google Books** owns title, authors, pages, language, abstract. It has **no edition,
  no series, no place** — ever.
- **K10plus** is the only real source for **edition (58%), series (46%) and place (89%)**.
- **Crossref** covers only 34%, but when it hits it gives a DOI and structured
  `given`/`family` names that sidestep all name-splitting guesswork.
- **Library of Congress is dominated** — 21% coverage, nothing unique. **Drop it.**
  (My MODS parser also misses `publisher`; not worth fixing for a source we don't need.)

Only **one** ISBN in 95 resolved nowhere: `9788891902542`, the Italian Kurose & Ross.

### 2.2 ⚠ Three traps that would have silently corrupted the library

**1. K10plus dates the printing, not the edition — wrong in 24 of 65 comparable records (37%),** by up to 26 years:

| book | k10plus | truth | MARC 250 field |
|---|---:|---:|---|
| Hodge Cycles, Motives, and Shimura Varieties | 2008 | 1982 | `[Nachdr.]` |
| Rudin, *Real and Complex Analysis* | 2013 | 1987 | `3. ed., internat. ed., [Nachdr.]` |
| Boyd & Vandenberghe, *Convex Optimization* | 2023 | 2004 | `Version 29` |
| Arora & Barak, *Computational Complexity* | 2016 | 2009 | `4th printing 2016` |

→ **Never take `year` from a library catalogue.** Encoded as a hard `NEVER` rule in
`lib/resolve.py`.

**2. An ISBN can resolve to a completely different book.** Calibre #140 is *Basic German:
A Grammar and Workbook*. Its ISBN `9780415283090` returns, from **two independent
sources that agree with each other**, *An Introduction to Ethics for Health Professionals*.
A pipeline that trusted agreement would have overwritten the record. Only cross-checking
the external title against **Calibre's own title and the PDF** catches it.
→ **Title agreement with the local record is a hard gate, not a nice-to-have.**

**3. A printing is not an edition.** MARC 250 returns `3. print`, `32. printing`,
`Ninth printing`, `[Nachdr.]`, `[Repr.]`, `Corr. 2. print., [repr.]`. Copying these as
editions would have been wrong 13 times. `lib/norm.py::edition()` drops printing-only
clauses and parses mixed ones (`4. ed., 4. print` → 4). It scores **43/43** on every
edition string the corpus actually produced, including `4a edizione` → 4 and
`20th-anniversary ed.` → *no number* (an anniversary edition isn't the 20th edition).

### 2.3 The resolver

Per-**field** waterfalls, ordered by measured accuracy, with **majority vote first and
source priority only as the tie-break** — because three sources agreeing beat one
high-priority source. (Measured: Crossref alone said Cover & Thomas was 2005; Google
Books, LoC and the PDF copyright page all said 2006. Priority-only picked 2005.)

| field | order | notes |
|---|---|---|
| title | pdf → gb → crossref → openlib → k10plus | catalogue titles are **sentence-case** (k10plus 17% title-case, LoC 0%) — rejected outright |
| authors | pdf → **crossref** → gb → k10plus | Crossref's structured names need no splitting |
| year | crossref → gb → openlib → pdf | **k10plus banned** |
| edition | pdf → **calibre comments** → k10plus → openlib | your own notes won 45 of 59 |
| series | crossref → k10plus → calibre | gb has none |
| place | k10plus → openlib | crossref/gb have none |
| pages | **mutool only** | the file is the only truth about the file |
| abstract | gb → k10plus → crossref | |
| DOI | crossref only | |

**Sources agree with each other on author order 91–100%** of the time, and **Calibre's
`author_sort` matched the external consensus 20 times out of 20** — so `author_sort` is
trustworthy for ordering even though the displayed author list is alphabetised garbage.

### 2.4 Eight cleanup rules, each from an observed defect

Built and tested in `lib/clean.py`:

1. **Google Books splits the subtitle off** → `Computational Complexity` + `A Modern Approach` rejoined.
2. **Crossref returns XML-escaped text** → `Measure, Integration &amp; Real Analysis` unescaped.
3. **Catalogues are sentence-case** → `Principles of mathematical analysis` rejected in favour of the printed casing.
4. **Copyright lines list every edition** → `© 1996, 2005, 2024` takes the *latest*, not the first. (This one bug was dating 11 books wrong, including most of Milne's notes.)
5. **Google Books appends the edition to the title** → `Introduction to Algorithms, fourth edition` → title + `edition: 4`.
6. **K10plus puts platforms in the series field** → `SpringerLink`, `Springer eBook Collection` blocklisted.
7. **MARC place artefacts** → `New York [u.a.]` → `New York`.
8. **Names arrive in three shapes** → `Oorschot, Paul C. van` and `Paul C. van Oorschot` both → `{firstName: "Paul C.", lastName: "van Oorschot"}`, particles handled in both directions.

### 2.5 What the pipeline actually produces

Run over all 115 books:

| field | filled |
|---|---:|
| title, creators, year | **100%** |
| publisher | 99% |
| pages (from `mutool`) | 97% |
| abstract available | 73% |
| place | 71% |
| edition | 51% |
| series | 42% |

**77 of 115 books (67%) come out clean with no flag.** Another **19 are flagged only
`no-external-source`** — Milne's notes, the open textbooks, the Italian university PDFs —
which is expected, not a defect: they're self-published and the PDF plus your Calibre
record *is* the authority.

**That leaves 19 books that genuinely need your eyes:**

| flag | n | what it means |
|---|---:|---|
| `title-conflict` | 14 | external title diverges from yours — includes the #140 wrong-book catch |
| `name-split` | 3 | e.g. `María Isabel González Vasco` — Spanish double surname, unresolvable by rule |
| `edition-conflict` | 2 | Tao *Analysis I*/*II* — sources disagree |

Everything else lands with the acceptance gate below and no human time spent.

### 2.6 Acceptance gate

- **Confirmed** — the winning value has ≥2 sources, or is confirmed by the PDF → write it.
- **Single-source** — only one source has it, nothing contradicts → write it.
- **Conflict** → flag, surface both values in the approval card, **never pick silently**.
- **Absent** → leave empty. An empty field is honest; a guessed one poisons a bibliography.

Any unresolved flag also gets the `needs-review` tag in Zotero, so it stays findable
after the migration ends.

### 2.7 Operational notes

- Send `?mailto=` to Crossref (polite pool). Keep the Google Books key in the
  environment as `GB_KEY` — `lib/.gitignore` already excludes `.env`; **it is not written
  into any file here.**
- **Follow redirects on Open Library**: `/isbn/X.json` 302s to `/books/OL…M.json`, and a
  non-following client reports a false miss. This produced a bogus "0% coverage" reading
  on the first pass.
- All responses are cached to disk by `lib/sources.py`, so Phase 2 is re-runnable and
  interruptible at zero API cost.

## 3. Making it interruptible

### 3.1 Two layers of bookkeeping, because one can be lost

**Layer 1 — the ledger.** `migration/ledger.jsonl`, append-only JSONL, one line per state transition. Append-only means a crash mid-write costs at most the last line, and `tail` always tells you where you stopped.

```jsonl
{"ts":"2026-09-21T14:02:11Z","calibre_id":181,"event":"intent","title":"Measure, Integration & Real Analysis"}
{"ts":"2026-09-21T14:02:19Z","calibre_id":181,"event":"created","zotero_key":"A1B2C3D4"}
{"ts":"2026-09-21T14:02:31Z","calibre_id":181,"event":"attached","attachment_key":"E5F6G7H8","sha256":"9f2c…","bytes":4182931}
{"ts":"2026-09-21T14:02:33Z","calibre_id":181,"event":"tagged","tags":["topic:measure-theory","kind:textbook"]}
{"ts":"2026-09-21T14:02:40Z","calibre_id":181,"event":"verified","status":"done"}
```

Per-book state machine:
```
pending → proposed → approved → created → attached → tagged → verified → done
                  ↘ skipped   ↘ deferred   ↘ failed
```

**Layer 2 — the library describes itself.** Every created item carries `calibre-id: <n>` in Extra and the tag `migration:calibre-2026-09`. **Even if the ledger is deleted entirely, the migration can be fully reconstructed** by listing items with that tag and reading their `calibre-id`. This is the property that makes the run genuinely safe to abandon.

### 3.2 Resume protocol

Any session that picks this up runs, before anything else:

1. Read `ledger.jsonl`; build the last-known state per `calibre_id`.
2. **Reconcile orphaned intents** — any `intent` without a terminal event: search Zotero for `calibre-id: <n>`.
   - Item found → the write succeeded and the ledger lost the line; append the missing events and continue from the real state.
   - No item → the write never landed; reset to `pending`.
3. Cross-check the whole run: `zotero_search_by_tag("migration:calibre-2026-09")` vs. ledger `done` count. Any drift is reported, never auto-corrected.
4. Print `N/115 done · M deferred · next: #X "<title>"` and stop for your go-ahead.

A single idempotency rule makes every step safe to repeat: **never create an item without first searching for its `calibre-id`.** `zotero_add_item`'s own `if_exists` only dedupes on DOI/ISBN/URL, which 19 of your books don't have — so this check is ours to do, not the server's.

`zotero_attach_file` is already idempotent on filename + MD5, so re-attaching costs nothing.

### 3.3 Safety net before the first write

- `cp ~/Zotero/zotero.sqlite migration/backup/zotero.sqlite.<date>` — and note that Zotero keeps its own `.bak`.
- `sqlite3 ~/Calibre\ Library/metadata.db .dump | shasum -a 256` recorded, so any accidental Calibre change is detectable.
- Calibre is **not** written to at all. No Content Server, no `calibre_*` write tool, no `calibre_remove_book`. It stays a complete working fallback until you say otherwise.
- Rollback at any point: select tag `migration:calibre-2026-09` in Zotero, delete to trash, restore the sqlite backup if it went badly wrong.

### 3.4 Where the state lives

```
~/.claude/skills/knowledge-base-agent/migration/
  PLAN.md                        this file
  zotero-import.SKILL-SPEC.md    spec for the future skill (§4)
  ledger.jsonl                   append-only state  ← created at run start
  dossiers/<calibre-id>.json     cached research per book (see §4.2)
  backup/zotero.sqlite.<date>    pre-run snapshot
  report.md                      human-readable running summary
```

It's inside a git repo, so `git log` on the ledger is a second free audit trail.

---

## 4. Execution phases

### Phase 0 — Preflight (one session, ~10 min, no writes to books)
`zotero_write_capabilities` → authorize if needed · take the backups · create `ledger.jsonl` · confirm `mutool` and network reach to Crossref/Open Library.

### Phase 1 — Restructure the existing 52 items (one session, reviewed as a block)
Rename `Dispense` → `Courses`; delete the four topic collections after tagging their members; strip arXiv noise tags; apply `kind:paper` + `topic:` to the 52 existing items; create the coloured status tags.
**Why first:** the vocabulary has to exist before 115 books are tagged against it, and doing it on 52 items surfaces vocabulary gaps cheaply.

### Phase 2 — Research all 115 offline (no Zotero writes)
Run the §2.2 waterfall over every book, cache each result to `dossiers/<id>.json`. Pure reads: sqlite, mutool, two HTTP APIs. **Interruptible at zero cost** — a cached dossier is never re-fetched.
Output: `report.md` listing every book with its proposed item, its evidence, and any conflict.

### Phase 3 — Approve and write, in waves of ~10
You chose to approve every book. To make 115 approvals tolerable, they're batched for *presentation*, not for writing:

> I show 10 compact cards (title · type · authors in final order · edition · series · publisher/year · ISBN/DOI · proposed tags · conflicts flagged ⚠).
> You reply in one line — `all ok`, or `3: author order wrong, 7: skip, rest ok`.
> I then write them one at a time, ledger line per step, and report the 10 results.

Nothing is written before your word on that specific book. Deferred books get `deferred` in the ledger and are re-offered at the end. 12 waves, and **any wave boundary is a clean stopping point**.

### Phase 4 — Reconcile (one session)
Count check (115 vs. ledger vs. tag) · every item has exactly one PDF child with matching size · no item left with an empty title or zero creators · `zotero_update_search_database` so full-text and semantic search index the new PDFs · Better BibTeX citation keys generated and free of collisions.

### Phase 5 — Settle in (yours, unscheduled)
Create the 11 saved searches by hand (§1.3) · live in Zotero for a few weeks · then decide Calibre's fate. When you do: archive `~/Calibre Library` to a dated zip first, verify the 115 PDFs are all in `~/Zotero/storage`, *then* delete.

### Time estimate
Phase 0: 10 min · Phase 1: 30 min · Phase 2: ~45 min unattended · Phase 3: 12 waves × ~5 min of your attention · Phase 4: 20 min. Spread over as many sessions as you like.

---

## 5. Two things to know before starting

**Sync.** You have no Zotero account configured. If you ever enable sync, 1.6 GB of books + 383 MB of existing attachments is far past the 300 MB free tier — you'd need a paid plan or a WebDAV target. Nothing to do now; just don't be surprised. (Linked-file attachments would have avoided this, which is the trade-off you declined — reversible later via Zotero's "Manage Attachments".)

**The existing skill is stale and will fail.** `skills/knowledge-base-agent/SKILL.md` calls five tools that don't exist on the current server: `zotero_add_by_doi`, `zotero_add_from_file`, `zotero_manage_collections`, `zotero_find_duplicates`, `zotero_merge_duplicates`. The real ones are `zotero_add_item` (one tool for DOI/URL/ISBN/BibTeX/file), `zotero_set_item_collections`, and there is **no duplicate-detection or merge tool at all** — deduplication is manual in the Zotero UI. That skill also routes books to Calibre, which is exactly what you're retiring. See the spec in `zotero-import.SKILL-SPEC.md`; retiring or rewriting the old skill is part of that work.
