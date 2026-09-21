# Tested pipeline code

Working, validated code — not pseudocode. Each module was run against all 115
Calibre books and the 95 distinct ISBNs before being placed here.

| file | what it does | validation |
|---|---|---|
| `sources.py` | one adapter per metadata source (Google Books, Crossref, Open Library, K10plus SRU, LoC SRU), with an on-disk response cache | 475 live queries, 99% of ISBNs resolved by ≥1 source |
| `norm.py` | `edition()` — MARC 250 / free text → an edition *number*, rejecting printings | 43/43 on the real strings the corpus returned |
| `clean.py` | the eight cleanup rules (subtitle join, entity unescape, edition-tail strip, sentence-case guard, series junk list, MARC place artefacts, name splitting, multi-year copyright lines) | each rule traceable to an observed defect |
| `resolve.py` | per-field waterfall, majority-vote with priority tie-break | see PLAN.md §2.3 |
| `dossier.py` | runs the whole thing over the Calibre DB, writes `dossiers.json` | 115/115 books, 77 clean |
| `frontmatter.py` | front-matter text, page geometry, PNG rendering, and cover-distrust signals — the inputs to **adjudication** (PLAN.md §2.6) | found 54 image-only covers and 19 whose page geometry doesn't match the body |

Nothing here decides anything. `resolve.py` ranks evidence; the metadata that lands is
the model's call after reading the book's own front matter, with the PDF as final
authority. See PLAN.md §2.6.

## Running it

    export SCR=<a working dir>          # cache + outputs land here
    export GB_KEY=<google books api key>
    python3 dossier.py

**Do not commit the Google Books key.** Keep it in the environment, or in a
`.env` file next to this README (already gitignored).
