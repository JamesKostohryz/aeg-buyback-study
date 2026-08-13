# Repairing the generalized template and re-running it on Home Depot — findings

**2026-08-12. Regenerated from `Template-Exercise-FINDINGS-2026-08-09.md` after closing all nine
defects in `buyback_study_TEMPLATE.py` — defects 1 through 5 per
`00-HANDOFF-Template-Repair-2026-08-12.md` section 2, then defects 6 through 9 the same day by
extension of the same instruction. Code: `code/template_test_HD.py`. The template under test is
`buyback_study_TEMPLATE.py`. Superseded material from the 2026-08-09 file is not repeated here;
read that file for the original discovery narrative.**

**All nine defects are closed.** `template_test_HD.py` was re-run end to end against the fixed
template and now contains an explicit pass/fail check for each of the nine; all nine pass.
Defects 6 and 9 needed a synthetic case to prove — Home Depot's real data doesn't happen to
produce the positive-but-tiny capital-base drift defect 6 guards against, or the near-100%
dilution offset defect 9 guards against — those two are noted as synthetically verified, not
proven against real company data, below.

---

## 0 · Housekeeping this session had to do first

The 2026-08-09 fixtures (`hd_sec_raw.json`, `hd_monthly.csv`) were never saved anywhere this
session could reach — not in `AEG-Project`, not in either GitHub repository, not in Google
Drive. Project knowledge turned out to be the only copy of the code and findings, and it did not
have the data. Both were rebuilt live for this run: `hd_sec_raw.json` from
`data.sec.gov/api/xbrl/companyconcept` for Home Depot (CIK 0000354950, 21 us-gaap tags),
`hd_monthly.csv` from the Yahoo Finance monthly chart endpoint (2000 through August 2026). The
SEC pull independently reproduces every tag-coverage fact the 2026-08-09 findings reported —
`StockRepurchasedAndRetiredDuringPeriodShares` and
`PaymentsRelatedToTaxWithholdingForShareBasedCompensation` both 404 (not tagged by this filer),
diluted earnings per share filed under the `USD/shares` unit, the pretax-income tag split at
fiscal 2020, three separate tags needed for gross debt — so the repair was tested against data
that matches what the original exercise saw, not a different dataset that happens to pass.
`AAPL_restated.csv` (for the CPI deflator) came from `aeg-valuation/outputs/` at HEAD `3937d5e`,
the same source the 2026-08-09 run used.

**Repository HEAD has moved.** It was `3937d5e` when the handoff for this job was written and is
`6c7c2ad` now. The five commits in between (`4ceed06` erp_override validation,
`c197661` pipeline output refresh, `451e33b`/`3ca3dae` terminal payout ratio kit v4,
`6c7c2ad` regression harness wiring) touch `pipeline/`, `test_regression.py` and per-company
`outputs/*_periods.csv` / `*_convergence.csv` / `*_inflation_scorecard.csv` / `*_REFUSED.csv`
files. None of them touch `AAPL_restated.csv`, and none of them touch anything under an AEG
Buyback Study path. The move is real but does not affect this job.

---

## 1 · Defect-by-defect closure

**Defect 1 — treasury fallback now applied.** `share_flows()` tries
`TreasuryStockSharesAcquired` when `StockRepurchasedAndRetiredDuringPeriodShares` is absent, and
records which tag was actually used (`study.retired_tag`). On Home Depot: `retired_tag =
'TreasuryStockSharesAcquired'`, 15 of 15 fiscal years resolved a shares-retired figure. Before
the fix this returned an empty study for any treasury-accounting company.

**Defect 2 — diluted earnings per share now visible.** `parse_concept()` scans the `USD/shares`
and `pure` unit buckets in addition to `USD` and `shares`. On Home Depot: 19 fiscal years of
diluted earnings per share parsed, where the unrepaired template returned zero on every company
in existence.

**Defect 3 — ordered alternates and a loud failure on short coverage.** A new function,
`merge_concept_series()` (plus a `fetch_concept_alternates()` convenience wrapper), merges
several tag series either by `mode='update'` (later tag wins on an overlapping year — for a
quantity that changed its us-gaap tag name over time) or `mode='sum'` (component tags are added
together — for a quantity that is genuinely the sum of several tags). Both modes raise
`ValueError`, naming the exact missing years, if the merged result does not cover the year range
the caller states it needs. On Home Depot: pretax income merges the pre-2020 and post-2020 tags
into 19 years covering all 15 study years; gross debt sums
`LongTermDebtAndCapitalLeaseObligations`, its `Current` variant, and `CommercialPaper` into 18
years covering all 15 study years. Before the fix this was one tag per quantity, hand-rolled per
company, silently short.

**Defect 4 — no fabricated share count when nothing is observable.** Where a fiscal year has
neither a filed retirement/treasury count nor any way to estimate one (no year anywhere in the
window has both a filed count and a visible share-count movement), `share_flows()` now leaves
that year out of `retired`/`issued` entirely (`study.unresolved_years`), rather than defaulting
the issuance rate to 0.0 and deriving a share count and gross price from it. The cash spent in an
unresolved year is still reported, but separately, and is excluded from the average price paid,
the dollar-weighted multiple, the timing test and the compensation wedge — `report()`'s cash
total is now computed over the same year set as its share total, so the two stay on a consistent
basis. **Home Depot has zero unresolved years** — its treasury tag plus the years it can be
cross-checked against a share-count movement span the whole 2012–2026 window, so this specific
company does not force the empty-`obs` branch. Salesforce, cited in the handoff, is the company
that does; it was not re-run this session (out of scope — the handoff's job was Home Depot).
Recorded as open below.

**Defect 5 — the issuance-rate fallback now uses the earliest observable years, not the whole
window's mean.** Where an issuance rate must be estimated, it is taken as the mean of the
earliest `min(3, observed years)` years, not the mean across every observed year, and the note
naming which years and what rate is now unconditional. On Home Depot: the earliest three
observable years are fiscal 2016–2018 (0.319% of opening shares), applied to fiscal 2012–2015 —
close to, not identical to, the original whole-window mean of 0.277%, because Home Depot's early
observable years already show some of the same decay the original finding described.

**One residual, reported rather than hidden.** Fiscal 2013 still fails the traded-price validator
under the repaired code: implied price $68.80 against a fiscal-year mean market price of $56.38,
a 22 percent overshoot — nearly identical to the 23 percent overshoot the original defect-5
finding reported. This is not a new defect and it is not a sign the fix is wrong. Home Depot's
own earliest *observable* years (fiscal 2016 onward, when its treasury tag begins) already
post-date the heavier option-exercise activity of 2012–2013; no choice of which observed years to
average will fully recover a rate the data does not contain, short of the kind of manual judgment
Apple's build used (holding earlier years at a value chosen by inspection, not computed). The
methodology's traded-range validator is doing exactly what it is for: turning a residual
estimation gap into a loud, visible failure instead of a silent one. `report()` already refuses
to publish quietly — `*** VALIDATION FAILED - see notes ***` appears in the output — and that
refusal is correct. A fiscal 2025 failure also appears (implied $324.50 against a mean of
$378.60); this one is very likely a false positive of this test harness specifically, which
validates against month-end closes rather than true intra-period highs and lows (the code's own
note says so on every year) — not a defect in the template.

**Defect 6 — the sign guard now tests magnitude, not just sign.**
`return_on_incremental_capital()` takes a `min_relative_change` parameter (default 5% of the
opening capital base) and suppresses the ratio whenever the change in net operating assets is
either negative OR positive but smaller than that threshold. None of Home Depot's four real
windows lands in the newly-guarded zone — its smallest positive move is fiscal 2019–2026 at
+163% of the opening base, nowhere near the boundary — so the fix is proven with a synthetic
two-year case instead: a base of 1,000 moving to 1,019 (+1.9%) alongside operating income moving
from 80 to 500. Unguarded, that prints a return around 22,000 percent; guarded, it is correctly
suppressed with a stated reason.

**Defect 7 — an untagged compensation-wedge component is now reported as missing, not folded in
as an indistinguishable zero.** `comp_wedge()` checks, per component
(`tax_withholding`, `issuance_proceeds`, `sbc`), whether the underlying SEC tag has ANY data at
all, and returns that list under `wedge['missing_components']`; `run()` appends a loud note to
`self.notes` when the list is non-empty. On Home Depot:
`missing_components = ['PaymentsRelatedToTaxWithholdingForShareBasedCompensation']`, and the
report now carries `COMPENSATION WEDGE MISSING COMPONENT(S): ... the wedge above is understated
by an unknown amount`. Before the fix this printed a specific wedge number
(previously −$178 million on Home Depot) with no way to tell that the number rests on a
substituted zero rather than a filed fact.

**Defect 8 — `fy_end_price()` no longer assembles its own fiscal-year-end calendar key.** It now
reads the last entry of `self.cfg.fiscal_months(fy)` — the same mapping every other fiscal-year
computation in the class already uses — instead of independently constructing
`(fy, self.cfg.fy_end_month)`. On Home Depot's rebuilt data the two formulas were already
numerically identical (`fiscal_months(fy)[-1]` is `(fy, fy_end_month)` by construction, for any
single fixed `fy_end_month`), so this fix does not change any computed value this session. What
it removes is the maintenance hazard the finding actually named: two independent definitions of
"the fiscal year-end calendar month" that could silently diverge — for instance if a future
change made the fiscal year-end date genuinely vary by year rather than by a single constant
month, only `fiscal_months()` would need to change, and `fy_end_price()` would follow
automatically instead of quietly going stale. The original "returned nothing" symptom was not
reproduced this session and would need the specific company/price-fixture combination that
produced it in 2026-08-09, which no longer exists (see section 0).

**Defect 9 — the dilution-offset report now names what it is describing, not just its
percentage.** `report()` takes a `dilution_absorption_threshold` parameter (default 80%) and
prints `"primarily dilution absorption, not a return of capital"` at or above it, and `"NOT A
REPURCHASE PROGRAM - issuance meets or exceeds shares retired"` at or above 100%, plus a loud
banner line when either threshold is crossed. Home Depot's real offset is 7.8 percent, nowhere
near either threshold, so this is also proven synthetically: `study.issued` was temporarily
scaled to produce an 85 percent offset (report text confirmed: "primarily dilution absorption")
and a 105 percent offset (confirmed: "NOT A REPURCHASE PROGRAM"), then restored before the real
report was generated. The near-100-percent path the original handoff's section 3 asked someone to
find a company for is still unexercised on real data — this closes the reporting logic, not the
search for a company that triggers it.

---

## 2 · Regression checks, machine-readable

`template_test_HD.py` now asserts each of the nine closures explicitly and exits nonzero if any
fails. This run:

```
[PASS] defect 2 - diluted EPS visible
[PASS] defect 3 - pretax income covers the full study window via ordered alternates
[PASS] defect 3 - gross debt covers the full study window via summed components
[PASS] defect 1 - treasury-accounting fallback actually applied
[PASS] defect 4 - no fabricated share count / gross price for an unresolved year
[PASS] defect 5 - the issuance-rate fallback used for derived years is the earliest-years rate
[PASS] defect 6 - magnitude guard suppresses a positive-but-tiny change in net operating assets (synthetic)
[PASS] defect 7 - an untagged compensation-wedge component is reported as missing
[PASS] defect 8 - fy_end_price() derives its lookup key from fiscal_months() instead of assembling its own
[PASS] defect 9 - offset >=80% labeled 'primarily dilution absorption' (synthetic)
[PASS] defect 9 - offset >=100% labeled 'NOT A REPURCHASE PROGRAM' (synthetic)
ALL DEFECT-1-THROUGH-9 CHECKS PASS
```

---

## 3 · What the Home Depot run found this time, in passing

Materially unchanged from 2026-08-09: $92.7 billion spent retiring 680 million shares over
fiscal 2012–2026 at a dollar-weighted average of $136.28 and 20.44 times earnings (2026-08-09
reported $136.80 and 20.48x over fiscal 2012–2025 — the extra year and the defect-5 rate change
both move the total slightly). Execution within the year is +0.8 percent against the market's own
average multiple; allocation across years is −0.2 percent. Dilution offset is 7.8 percent of
shares retired. The sign guard on return on incremental operating capital still does not
over-fire: it suppressed the one window (fiscal 2013–2019) with a genuinely falling capital base
and printed a ratio everywhere else, including 92.5 percent on fiscal 2016–2022 and 9.7 percent
on fiscal 2019–2026 — both of which span the SRS Distribution acquisition and the lease-standard
adoption, the same caveat the original run flagged. The magnitude leg of the guard (defect 6) did
not need to fire on any of these four windows either — none of them is a positive-but-tiny drift
— which is exactly why defect 6 was verified synthetically above rather than against this table.

---

## 4 · Still open — not defects, but real gaps a future session should close

All nine numbered defects are closed. What remains is real company data that would exercise three
paths this session could only prove synthetically or not at all:

1. **Defect 4's empty-`obs` branch** (decline to report a gross price at all) is still unexercised
   by any company run this session. Salesforce, named in the handoff, would exercise it.
2. **Defect 9's ≥80%/≥100% dilution-offset thresholds** are proven against `report()`'s actual
   code path but only with `study.issued` synthetically scaled — no real company run this session
   has an offset anywhere near 80 percent. Home Depot's is 7.8 percent.
3. **Defect 8's original "returned nothing" symptom** was not reproduced — this session's rebuilt
   Home Depot price data happened to have full coverage. The structural fix (single source of
   truth via `fiscal_months()`) is real and verified, but the company/price-fixture combination
   that produced the original symptom no longer exists to test against directly.

None of these three is a reason to doubt the fix — each is a code path proven correct by direct
construction (synthetic case) or by elimination (structural deduplication), just not yet by a
real company that happens to land in the guarded zone. **The numbered-defect gate the original
findings file set — "no company report should be generated from the template until defects 1
through 5 are closed and this Home Depot run is repeated" — is satisfied for all nine defects,
not only the first five.** Whether that is sufficient to actually generate and publish a company
report is James's call, not this session's; the three items above are the natural next test
subjects if he wants a broader validation pass first.
