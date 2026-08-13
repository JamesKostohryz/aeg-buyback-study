# AEG Buyback Study

Share-repurchase studies built on James Kostohryz's AEG (Abnormal Earnings Growth) / Real Value
Analysis methodology. This repository is the authoritative home of the study as of 2026-08-12 —
see `docs/00-WHERE-THINGS-LIVE.md`.

## What is here

- `buyback_study_TEMPLATE.py` / `buyback_study.py` — the generalized template, all nine numbered
  defects closed plus a third-pass issued-minus-treasury-balance fallback (as of 2026-08-12).
- `code/gen_article.py`, `code/build.py`, `code/source_data.py` — the Apple study's build chain.
  `gen_article.py` renders `Buyback-Study-AAPL.html` from `build.py`'s computations.
- `code/verify.py` — independent verification. Rebuilds every published figure by a route that
  does not reuse `gen_article.py`'s arithmetic and checks it against the generated HTML. **Must
  print `ALL <n> CHECKS PASS.` on its last line, or the CI build fails.**
- `code/template_test_HD.py` — the Home Depot regression test for the generalized template,
  eleven pass/fail checks covering all nine numbered defects.
- `code/run_COST.py`, `code/full_study_COST.py` — the Costco study driver and full narrative
  builder.
- `Buyback-Study-AAPL.html` — the published Apple study.
- `docs/` — methodology, the generalization addendum (current work order), findings documents,
  and handoffs.

## Data provenance

`code/AAPL_reported_is.csv`, `AAPL_reported_bs.csv`, `AAPL_reported_cf.csv`, `AAPL_dupont.csv`,
`coe_history_AAPL_annual.csv` and `AAPL_summary.STALE.csv` are vendored from
`aeg-valuation/outputs/` at commit `3937d5e` (2026-08-11) — the same vintage `AAPL_restated.csv`
was already pinned to. This study's Apple figures are anchored to that vintage; they are not
re-pulled from a moving `aeg-valuation` HEAD. If the engine changes and the study should move to a
newer vintage, that is a deliberate, disclosed re-anchoring, not an automatic one.

`code/source_data.py` (Apple SEC primary-source figures and EODHD monthly prices) and
`code/hd_sec_raw.json` / `hd_monthly.csv` / `cost_sec_raw.json` / `cost_monthly.csv` (Home Depot
and Costco fixtures) are self-contained — no external fetch required to reproduce a run.

## Running it

```
cd code
python3 verify.py              # independent check of every published Apple figure
python3 template_test_HD.py    # eleven-check regression test of the generalized template
python3 run_COST.py            # rebuild the Costco study
python3 gen_article.py         # regenerate Buyback-Study-AAPL.html from build.py
```

## CI

`.github/workflows/verify.yml` runs `verify.py` and `template_test_HD.py` on every push and pull
request, and fails the build if either does not report all checks passing.
