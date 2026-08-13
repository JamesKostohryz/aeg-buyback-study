# Where the buyback study actually lives — read this first

**As of 2026-08-12, the source of truth is this repository:
`github.com/JamesKostohryz/aeg-buyback-study`.**

**THE TEMPLATE IS CLOSED AS OF 2026-08-13.** Read
`docs/00-CLOSE-OUT-Template-2026-08-13.md` first. The revision cycle stopped there on
James's ruling; what follows are applications of the template, not further work on it.
There is now ONE generic driver, `code/run_study.py`, which takes a ticker plus a small
per-company configuration block. Do not write a new per-company driver.

Before this date the study existed only in project knowledge (unversioned) and, from later on
2026-08-12, in a working copy at `C:\Users\james\AEG-Project\AEG-Buyback-Study` on James's
machine. Both locations had drifted from each other on specific files before this migration —
see the addendum's working notes and `AEG-Project`'s own `00-START-HERE.md` for the reconciliation
record. The repository is now the single copy that matters. `AEG-Project\AEG-Buyback-Study` is a
working copy for click-and-edit convenience on James's machine, kept in sync with the repository,
not an independent source.

## Paths

| What | Repository path |
|---|---|
| Generic driver, ANY ticker | `code/run_study.py` — takes a ticker plus a small configuration block; no company-specific code. This is how a new company is run (2026-08-13) |
| Earnings-timing decomposition module | `timing_decomposition.py` — moved to the repository ROOT on 2026-08-13 so the template itself can import it. It used to sit in `code/` |
| Numeric-token differ | `code/numeric_token_diff.py` — proves a regenerated document moved no figure. The proof standard for pulling a measure into the template |
| Close-out note | `docs/00-CLOSE-OUT-Template-2026-08-13.md` — **read first** |
| The cold run | `docs/COLD-RUN-Oracle-2026-08-13.md` and its machine transcript beside it. Oracle fixtures: `code/orcl_sec_raw.json`, `code/orcl_monthly.csv`, `code/orcl_traded_range.csv` |
| Generalized template | `buyback_study_TEMPLATE.py` — the ONLY copy. `buyback_study.py` is a re-export shim with no code in it (changed 2026-08-13; it used to be a hand-synced byte-identical copy) |
| Apple build chain | `code/gen_article.py`, `code/build.py`, `code/source_data.py` |
| Independent verification | `code/verify.py` — CI-gated, must print `ALL <n> CHECKS PASS.` 333 checks as of 2026-08-13 |
| Template regression test | `code/template_test_HD.py` — CI-gated. Home Depot's eleven defect checks, seven item-4 checks, and (2026-08-13) defect 13, the entry effect's own guards, and the Oracle cold run reproduced offline |
| Round-trip proving fixture | `code/roundtrip_test_AAL.py` — CI-gated, twenty-seven checks. American Airlines, and NOT a study of it |
| Round-trip fixtures | `code/aal_sec_raw.json`, `code/aal_monthly.csv`, `code/aal_traded_range.csv` |
| Excise-tax proving fixture | `code/excise_test_ORLY.py` — CI-gated, thirty-seven checks. O'Reilly Automotive, and NOT a study of it |
| Excise-tax fixtures | `code/orly_sec_raw.json`, `code/orly_monthly.csv` |
| Costco study | `code/run_COST.py`, `code/full_study_COST.py`. NOTE 2026-08-13: `full_study_COST.py` was dividing by the deflator instead of multiplying, and lagging it a year. Corrected. Every real figure it prints has moved; the hand-written `.docx` has not and must be regenerated against the new figures, not the old ones |
| Published Apple study | `Buyback-Study-AAPL.html` |
| Methodology | `docs/00-Buyback-Study-METHODOLOGY-2026-08-09.md` |
| Current work order | `docs/00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md` |
| Entry-effect decomposition | `docs/METHODOLOGY-ADDENDUM-Earnings-Timing-Decomposition-2026-08-13.md` (item 1) |
| The round trip | `docs/METHODOLOGY-ADDENDUM-Round-Trip-2026-08-13.md` (item 3) |
| Treasury permanence | `docs/METHODOLOGY-ADDENDUM-Treasury-Permanence-2026-08-13.md` (item 4) |
| The excise tax, and the argument for repurchases | `docs/METHODOLOGY-ADDENDUM-Excise-Tax-2026-08-13.md` (item 5) |
| Findings and handoffs | `docs/*FINDINGS*`, `docs/*HANDOFF*` |
| Paste-in card for a fresh chat | `docs/00-PASTE-THIS-Close-Out-Session.md` — short; points at the prompt below |
| Full session briefing | `docs/00-NEXT-SESSION-PROMPT-Buyback-Study-2026-08-13b.md` — most recent wins |

## If you are starting a new session on this project

Clone or check the repository at HEAD rather than trusting project knowledge or the AEG-Project
working copy for anything code- or figure-related. Project knowledge is retained only as a
historical record and is not updated going forward.
