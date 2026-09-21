# Migration report — Calibre → Zotero

**Completed 2026-09-21.** All 115 books migrated and verified. Calibre untouched.

## Reconciliation

| Check | Result |
|---|---:|
| Calibre books | 115 |
| Distinct `calibre-id`s present in Zotero | **115** |
| Books not migrated | **none** |
| Calibre files with no byte-identical attachment in Zotero | **none** |
| Items with an empty title | 0 |
| Items with no creator | 4 — all deliberate (see below) |
| Tagged `migration:calibre-2026-09` | 125 |
| Tagged `needs-review` | 13 |

Every attachment was MD5-checked against its Calibre original. Zotero storage went from
383 MB to 1.7 GB; `~/Calibre Library` is unchanged at 1.6 GB.

**The four creator-less items are correct, not defects:** two pre-existing webpages with no
byline, plus *Geometry: Combinatorics and Algorithms* and *Lecture Notes on Concurrent
Computing*, whose PDFs genuinely name no author. Both are tagged `needs-review`.

## What was built

- **115 books → 113 new items.** Two deliberate mergers: the Rudin *Principles* pair
  (#225 + #236) became one item with two attachments, and #247 filled in a stub that
  pre-existed the migration rather than duplicating it.
- **22 orphan attachments → 11 parent items.** Bare PDFs sitting in collections with no
  metadata, uncitable. The 23rd was byte-identical to an existing attachment and needed
  no parent.
- **Collections restructured** to the purist model: `Courses/{ETH,MIT,EPFL}`, `Inbox`,
  `Archive`. Four topic collections dissolved into tags after every member was tagged.
- **Vocabulary in use:** 8 `kind:` terms, **45 `topic:` terms**. The seven added during
  the run (`discrete-mathematics`, `functional-analysis`, `computational-geometry`,
  `quantum-computing`, `concurrency`, `databases`, `signal-processing`) plus
  `electronics` were needed for lecture notes and hardware material the book-derived
  vocabulary hadn't anticipated.

## What the adjudication caught

The measured pipeline (PLAN.md §2) proposed; reading each PDF decided. Cases where the
file contradicted every external source:

**Three confident wrong-book matches.** #117 (ISBN belongs to the Athabasca UP print, the
file is Morin's free C++ beta), #140 (*Basic German*, where two independent sources agreed
on *An Introduction to Ethics for Health Professionals* — and Calibre's ISBN was itself
wrong; the copyright page prints `0-415-28404-X`), #168 (Crossref returns a DOI titled
*Elliptic Curves* for the *Fields and Galois Theory* ISBN; DOI omitted rather than
recorded wrong).

**Nine books whose Calibre author field held something that was not an author:**
`"David, Nieri"` (#127, not an author of that book), `"Author-names"` (#135),
`"Texas Instruments, Incorporated [SLYW038,C"` (#138, a literature number),
`"rumbaugh"` (#207), `"09:15:55, R. Rajagopal 4716 2000 Dec 22"` (#224, a PDF creation
timestamp), `"althea"` (#225, the retyper's handle), `"Jfly"` (#231, a scanner's handle),
`"Project, Open Logic"` (#232, the publisher as a person), plus #186's corrupt
`author_sort`.

**Where Calibre beat the sources.** #194's copyright page reads "© 2023, 2014, 2008" —
your 2023 was right, Google Books' 2022 wrong. #210's ISBN matched the printed copyright
page exactly. #129's Spanish double surname *González Vasco* was correct in Calibre and
mangled by the name-splitter. #149's own note had already flagged the filename
misattribution.

**People no external source listed:** five translators (Brookfield; Levy and Cargo twice),
the Italian edition's editors (#190), Ila Neustadt (#205), Herbert Bos (#194), Sébastien
Josse (#202), and Deligne's three co-authors on #170.

**Kind errors, not detail errors.** #230 is an *edited* volume — "edited by Copeland, Posy,
and Shagrir" on the title page — and #138's Kay and Green are editors, not authors.

**Two books needed rendering rather than extraction.** #210 (no text layer at all; title
page "Second Edition", copyright "© 1986", ISBN matching Calibre's — closing a question
your Calibre note had left open) and #188 (fully garbled text layer). #186 needed it for
a subtler reason: extraction returns text in *layout* order, which inverted the author
list on its cover.

## Still open

**13 items tagged `needs-review`**, each with the reason in its Extra field. The
substantive ones:

| Item | Question |
|---|---|
| #136 Handbook of Applied Cryptography | Chapter-only PDF, no front matter. Year 1996 (yours) vs 1997 (GB/OL) |
| #154 Stewart, *Calculus* | No copyright page; 2008 (yours/K10plus) vs 2007 (GB/OL) |
| #200 *Clean Code* | © 2009 but "First printing July, 2008" — recorded as 2009 |
| #139 Pont | PDF is the 2014 SafeTTy re-release of the 2001 book |
| #168 Milne, *Fields and Galois Theory* | Kea Books (PDF) vs World Scientific (your ISBN) |
| #175 *Tannakian Categories* | Title page credits Milne alone; the 1982 original is Deligne–Milne |
| #216 Eisenstein | PDF is the 2018 draft titled *Natural Language Processing* |
| #117, #118 | Edition/artifact questions noted in Extra |
| Geometry notes, Concurrent Computing | No author stated anywhere in the PDFs |

**One redundant attachment**: `SWAYP9PC` is byte-identical (MD5
`bd17ebfa3fa7edd2aea1e29705a47ca9`) to `YEHYCBY5`, already a child of *Information Theory
and Coding*. Left in place pending your word.

**Saved searches are still to be created by hand** — the MCP server cannot make them.
The 11 definitions are in PLAN.md §1.3, about ten minutes in the Zotero UI. Under the
purist model these *are* your folders, so this step matters.

**Semantic search indexing** is unavailable (`zotero-mcp-server[semantic]` not installed).
Zotero's own full-text index builds automatically in the app.

## Corrections made to this plan during the run

1. **Better BibTeX is not installed** — the `~/Zotero/better-bibtex` directory holds only a
   2-byte stub. Nothing regenerates citation keys; empty is the correct resting state.
2. **Every Zotero item type has a DOI field**, `book` included — DOIs do not belong in Extra.
3. **Calibre's DB path is not the filesystem path** (apostrophe → underscore). Cost 4 of
   115 books, each of which looked like an unreadable scan. Fixed in `lib/paths.py`.
4. **Zotero runs SQLite in WAL mode.** A snapshot without `-wal` reads stale. This produced
   a false "0/10 attachments" in wave 1 — and, earlier, made the *initial survey* undercount
   the pre-existing library as 34 regular items when it is **37**. The three invisible items
   (BashGuide, LaTeX Math for Undergrads, The Matrix Cookbook) were untouched by the
   migration and have since been tagged.
5. **Text-extraction order is not reading order** — see #186 above.
6. `document` has no `numPages` or `edition` field; version and page count go to Extra.

## Calibre

**Untouched throughout**, as agreed — no writes, no Content Server, no removals. It remains
a complete working fallback. The decommission checklist is PLAN.md §4, Phase 5.
