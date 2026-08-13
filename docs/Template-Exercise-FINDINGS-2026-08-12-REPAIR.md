# Exercising the generalized template on a second company — findings, post-repair

**2026-08-12. Supersedes `Template-Exercise-FINDINGS-2026-08-09.md` for defects 1 through 5
only — that file's sections 3 and 4 (what worked, what the Home Depot run found in passing) and
its findings on defects 6 through 9 are unaffected and still current. This document records
that defects 1-5 were closed in `buyback_study_TEMPLATE.py` and re-verified, per
`00-HANDOFF-Template-Repair-2026-08-12.md` section 2.**

**Verification method.** The original hd_sec_raw.json fixture this exercise first ran against
could not be located this session (see the handoff). Rather than block on it, `template_test_HD.py`
was rewritten to fetch Home Depot's SEC filings live from `data.sec.gov` — the same interface the
template itself uses — so the re-verification below is against real, current filings, not a cached
snapshot. No price file (`hd_monthly.csv`) was available this session, so price-dependent checks
(validation against traded range, timing, internal rate of return) did not re-run; everything
defects 1 through 5 touch did.

---

## 1 · Defects 1 through 5 — closed and verified

**Defect 1 — the treasury fallback is documented but never applied. CLOSED.**
`StockRepurchasedAndRetiredDuringPeriodShares` confirmed empty for Home Depot on a live fetch, as
before. `share_flows()` now tries `TreasuryStockSharesAcquired` on its own — no manual
substitution in the test driver — and records which tag supplied the series on
`study.share_tag_used`. Verified: `share_tag_used == 'TreasuryStockSharesAcquired'`, 14 of 14
determinable years populated, none dropped.

**Defect 2 — the concept parser cannot see earnings per share, on any company. CLOSED.**
`parse_concept()` now scans `'USD/shares'` (and `'pure'`) alongside `'USD'` and `'shares'`.
Verified on a live fetch: `EarningsPerShareDiluted` returns 19 fiscal years for Home Depot
through the template's own `fetch_concept()`, with no patched copy in the test driver.

**Defect 3 — one tag name per quantity is not enough. CLOSED.**
`fetch_concept()` (and the underlying `TAGS` table) now accepts a single SEC tag name or an
ordered list of alternates, merged by fiscal year with the later-listed alternate winning on
overlap, plus an optional `min_years` that raises loudly on short coverage instead of returning a
silently incomplete series. Verified: pretax income merged from
`IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` and
the `...MinorityInterestAndIncomeLossFromEquityMethod...` variant, live, covering 19 fiscal years
against a `min_years=15` requirement; a synthetic short-coverage case confirmed the function raises
`ValueError` rather than returning quietly.

**Defect 4 — the zero-issuance default. CLOSED, per the 2026-08-12 handoff's updated fix (not
the original findings doc's).** Where NO year anywhere in the panel has an observable issuance
rate, the fallback rate is no longer silently set to zero. `share_flows()` leaves `retired`/`issued`
undetermined for every such year (recorded in `self.no_gross_price_years`) rather than deriving a
fictitious gross count, and `net_retirement_cost()` — cash divided by the NET share count
reduction, sign-guarded — is reported for those years instead, exactly as
`00-HANDOFF-Template-Repair-2026-08-12.md` section 2 specifies. Verified on a synthetic
Salesforce-shaped case (no retirement or treasury tag at all): `retired == {}`, all four years
land in `no_gross_price_years`, and each gets a positive, sane `net_retirement_cost` instead of the
$869.89-per-share fabrication the original defect produced. `report()` and `to_csv()` were also
corrected to stop silently mismatching cash and share totals across years with and without a
determinable gross count (a second-order instance of the same defect, found while fixing the
first).

**Defect 5 — the issuance-rate fallback averages the wrong years. CLOSED.** Where an issuance rate
IS observable somewhere in the panel, the fallback now uses the mean of the earliest three
observed years (all of them if fewer exist) rather than the full-panel mean, and always states
which years and what rate. Verified live: Home Depot's note now reads *"net issuance observable in
10 year(s) overall; the fallback rate is the mean of the EARLIEST 3 observed year(s)
(2016-2018)... not the full-panel mean, which would extrapolate a later, lower rate backward
across years it was never observed in."* This is the fix the original findings doc asked for by
name.

---

## 2 · Re-run headline numbers, live data, no price file

Cash spent $92,704mn, shares retired 680mn, dollar-weighted price paid $136.28, sign guard
suppressed exactly the FY2013-FY2019 window (ΔNOA −$533mn) and did not fire on the other three.
Against the original run's $92.7bn / 678mn / $136.80 and the same single suppressed window, this is
the same company telling the same story through a different, now-repaired code path and a fresh
data pull — not an exact match (different vintage, no split-adjustment differences expected since
Home Depot has none), but close enough to corroborate rather than contradict the original finding.

---

## 3 · Defects 6 through 9 — unchanged, still open

Out of scope for this repair per `00-HANDOFF-Template-Repair-2026-08-12.md` section 2. Restated
here only so this document is a complete picture of where the template stands, not to imply they
were touched:

- **Defect 6** — the return-on-incremental-capital sign guard is one-sided; it does not suppress a
  positive but trivially small ΔNOA, which would print a meaningless triple-digit-percent return
  with no warning.
- **Defect 7** — `comp_wedge()` silently substitutes zero for `PaymentsRelatedToTaxWithholdingForShareBasedCompensation`
  when a company does not tag it (Home Depot does not); confirmed still present on this run.
- **Defect 8** — `fy_end_price()` assumes a September-like fiscal year and returns nothing for a
  January year-end; not re-exercised this session (no price file).
- **Defect 9** — no reporting threshold exists for a dilution offset at or above 100%; Home Depot's
  is 7.5%, so this path remains unexercised — restated from the original findings doc, unchanged.

---

## 4 · What is still needed before a company report can be generated from this template

A real price file (`hd_monthly.csv`, EODHD monthly closes, split-adjusted) to re-exercise price
validation, timing and internal rate of return end to end, and a company that exercises the
untouched defects 6 through 9 and the still-unexercised near-100% dilution path (see the original
findings doc, section 3, "worth one search"). Per the handoff: **do not generate a company report
from the template until this is done**, and defects 1 through 5 being closed does not change that
— it closes exactly what it says it closes.
