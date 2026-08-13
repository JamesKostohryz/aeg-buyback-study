# Where the buyback study actually lives — read this first

**As of 2026-08-12, the source of truth is this repository:
`github.com/JamesKostohryz/aeg-buyback-study`.**

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
| Generalized template | `buyback_study_TEMPLATE.py` — the ONLY copy. `buyback_study.py` is a re-export shim with no code in it (changed 2026-08-13; it used to be a hand-synced byte-identical copy) |
| Apple build chain | `code/gen_article.py`, `code/build.py`, `code/source_data.py` |
| Independent verification | `code/verify.py` — CI-gated, must print `ALL <n> CHECKS PASS.` |
| Home Depot regression test | `code/template_test_HD.py` — CI-gated, eleven checks |
| Round-trip proving fixture | `code/roundtrip_test_AAL.py` — CI-gated, twenty-seven checks. American Airlines, and NOT a study of it |
| Round-trip fixtures | `code/aal_sec_raw.json`, `code/aal_monthly.csv`, `code/aal_traded_range.csv` |
| Costco study | `code/run_COST.py`, `code/full_study_COST.py` |
| Published Apple study | `Buyback-Study-AAPL.html` |
| Methodology | `docs/00-Buyback-Study-METHODOLOGY-2026-08-09.md` |
| Current work order | `docs/00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md` |
| Entry-effect decomposition | `docs/METHODOLOGY-ADDENDUM-Earnings-Timing-Decomposition-2026-08-13.md` (item 1) |
| The round trip | `docs/METHODOLOGY-ADDENDUM-Round-Trip-2026-08-13.md` (item 3) |
| Treasury permanence | `docs/METHODOLOGY-ADDENDUM-Treasury-Permanence-2026-08-13.md` (item 4) |
| Findings and handoffs | `docs/*FINDINGS*`, `docs/*HANDOFF*` |

## If you are starting a new session on this project

Clone or check the repository at HEAD rather than trusting project knowledge or the AEG-Project
working copy for anything code- or figure-related. Project knowledge is retained only as a
historical record and is not updated going forward.
