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
| Generalized template | `buyback_study_TEMPLATE.py`, `buyback_study.py` |
| Apple build chain | `code/gen_article.py`, `code/build.py`, `code/source_data.py` |
| Independent verification | `code/verify.py` — CI-gated, must print `ALL <n> CHECKS PASS.` |
| Home Depot regression test | `code/template_test_HD.py` — CI-gated, eleven checks |
| Costco study | `code/run_COST.py`, `code/full_study_COST.py` |
| Published Apple study | `Buyback-Study-AAPL.html` |
| Methodology | `docs/00-Buyback-Study-METHODOLOGY-2026-08-09.md` |
| Current work order | `docs/00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md` |
| Findings and handoffs | `docs/*FINDINGS*`, `docs/*HANDOFF*` |

## If you are starting a new session on this project

Clone or check the repository at HEAD rather than trusting project knowledge or the AEG-Project
working copy for anything code- or figure-related. Project knowledge is retained only as a
historical record and is not updated going forward.
