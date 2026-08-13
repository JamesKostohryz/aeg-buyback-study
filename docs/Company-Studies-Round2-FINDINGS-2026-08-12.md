# Third company round — template extension, McDonald's (abandoned), Costco (clean) — findings

**2026-08-12, same day as `Template-Exercise-FINDINGS-2026-08-12.md`, which covers the nine
numbered defects and the Home Depot re-run. This file picks up from there: after Apple and Home
Depot, James asked to try a company from the AEG valuation pipeline. This covers what that
turned up on McDonald's, the template change it forced, and the clean result on Costco that
followed.**

---

## 0 · What changed in the template

`buyback_study_TEMPLATE.py` gained a third fallback tier, added while investigating McDonald's
(section 1 below) and used again, differently, for Costco (section 2). Two new tags:
`shares_issued` (`CommonStockSharesIssued`) and `treasury_shares_balance`
(`TreasuryStockShares`, with a `TreasuryStockCommonShares` alternate merged in for companies that
renamed the tag mid-history, McDonald's among them).

`shares_outstanding()` now falls back to `issued - treasury_shares_balance` when no direct
`CommonStockSharesOutstanding` tag exists. `share_flows()` now falls back, as a last resort, to
the year-over-year **increase** in the treasury balance as an estimate of shares retired — labeled
explicitly as a **net**, not gross, figure, and any year where the balance **falls** (net
reissuance) is left unresolved rather than reported as a negative or zero retirement. Both
fallbacks announce themselves once via `study.notes`, never silently.

This tier turned out to have two very different reliability outcomes depending on the company, which
is the actual finding of this round.

---

## 1 · McDonald's — the fallback fires, and it is unreliable. Not landed.

McDonald's tags neither a direct retirement flow nor `TreasuryStockSharesAcquired`. Its
`CommonStockSharesIssued` has been flat for seventeen straight years — no complications from new
issued shares — so it looked like the cleanest possible test of the new fallback.

It was not. The price validator failed on 13 of 14 study years, in some years by five to six times
the actual trading range for the implied price paid per share. Root cause, confirmed by direct
investigation rather than assumed: McDonald's treasury balance nets together real repurchases
against stock-option-exercise reissuances (a real, separately tagged flow,
`StockIssuedDuringPeriodSharesStockOptionsExercised`) **and**, almost certainly, untagged RSU/PSU
vesting reissuances that have no XBRL tag to add back at all. Adding back the option-exercise
shares did not fix the problem — results stayed badly wrong, worse in some years — which is the
evidence that a second, untagged reissuance channel is doing the damage.

**Conclusion: the issued-minus-treasury-balance fallback is fundamentally unreliable for automated
reconstruction wherever a company also reissues treasury shares for compensation in the same
years it is buying them back**, which is most large, mature filers. A batch check of the same
pattern found PepsiCo, Procter & Gamble and Nike tagged identically to McDonald's — same risk,
not separately tested.

**Nothing from this run is landed.** `run_MCD.py`, `mcd_sec_raw.json`, `mcd_monthly.csv` and any
output stayed in scratch and were not copied into this folder. Per James, a real McDonald's study
is a legitimate future project but requires manual 10-K footnote research to get true gross
repurchase counts — not automated XBRL reconstruction. Not started.

---

## 2 · Costco — direct-tag pattern, clean, landed

Switched to Costco on James's confirmation. Costco tags
`StockRepurchasedAndRetiredDuringPeriodShares` directly — the same pattern Apple's own
hand-curated study uses, and the most reliable of the three patterns this project has now seen.
The third-pass fallback was not needed for the retirement count; it was checked and confirmed
absent (Costco does not tag `TreasuryStockSharesAcquired` at all).

**Window: FY2015–FY2025, not FY2017–FY2025.** The first pass through this study, landed earlier
the same day, claimed the window had to start in FY2017 because "Costco tags nothing usable
before FY2017." **That claim was wrong** — checked again after James asked why the report was so
much thinner than Apple's, `StockRepurchasedAndRetiredDuringPeriodShares` actually covers FY2015
onward directly: filed, zero derived years, zero price-validator failures across all eleven years.
Fiscal 2012–2014 genuinely has no usable share-count tag (real repurchase cash exists — $632m,
$36m, $334m — but no retirement or treasury-acquired flow to pair it with) and correctly remain
outside the window. The corrected window is eleven years, not nine; every number below is on the
corrected basis and supersedes the first pass.

**Headline finding: Costco's buyback is not, in substance, a repurchase program.**

| | |
|---|---|
| Cash spent, FY15–25 | $5,421m |
| Shares retired | 18.6mn |
| Dollar-weighted price paid | $290.78 (35.89x P/E paid) |
| **Dilution offset** | **129.8%** |

The dilution offset — shares issued (via employee compensation programs) as a share of shares
retired — is 129.8%, over the template's 100% threshold for "NOT A REPURCHASE PROGRAM." Costco
issued more shares over this period than it retired; shares outstanding actually **rose**,
by 1.27%, across the window. The buyback is functioning as dilution absorption against a
heavy stock-compensation program, not a net return of capital to shareholders — a materially
different story from Apple (return of capital) or Home Depot (7.8% dilution offset, genuine
capital return).

One same-pattern-as-Home-Depot gap carries over: Costco does not tag
`ProceedsFromIssuanceOfCommonStock`, so the compensation wedge in the report is understated by an
unknown amount and is flagged as such.

Cost of equity used is a placeholder (5.5% real, not sourced from the AEG engine's own curve for
COST) — flagged in the report's notes; do not quote the earnings-yield or break-even figures from
this run without replacing it.

**A much deeper report was built the same day, after James pointed out the first pass was far
thinner than the Apple study it was meant to use as a template.** The template itself
(`buyback_study_TEMPLATE.py`) only ever generalized a SUBSET of what Apple's hand-built report
does — it has no method for the abnormal-earnings-growth account (entry effect / continuing
effect), the net retirement cost variants, funding-source attribution, the Real Capital Base, or
return on retained earnings; those were built by hand for Apple in `gen_article.py` and its
companions and never folded back into the reusable template. `code/full_study_COST.py` computes
all of them for Costco from real filed data, following the exact formulas in
`00-Buyback-Study-METHODOLOGY-2026-08-09.md` sections 4.1–4.9, and
`docs/Costco-Buyback-Study-2026-08-12.docx` is the resulting twelve-section narrative report,
built to the same structure as the Apple study. Two things it genuinely cannot do, disclosed
throughout rather than faked: there is no AEG-engine cost-of-equity history or Neutral Value for
Costco, so a single placeholder rate (5.5% real) stands in for the entry-effect and
return-on-retained-earnings sections, and the "at Neutral Value" IRR column and the final
Neutral-Value pivot section are stated as unavailable. On the placeholder rate, the striking new
finding is that Costco's entry effect is negative in every tranche of the program — the
retirement-weighted break-even real cost of equity is 3.62%, below the placeholder itself — and
the EPS-growth channel attribution shows the buyback contributed nothing to per-share earnings
growth over the window (in fact slightly subtracted from it), unlike Apple where the buyback
funded close to 30% of EPS growth.

---

## 3 · What this round adds to the tagging-pattern survey

Three confirmed patterns now, ranked by reliability:

1. **DIRECT** (Apple, Costco) — retirement tagged directly. Most reliable.
2. **TREASURY-ACQUIRED-FLOW** (Home Depot, and — per a batch tag check, not independently
   re-run per company — JNJ, KO, T, WMT, POOL, MRK) — no direct retirement tag, but
   `TreasuryStockSharesAcquired` is a genuine flow. Reliable.
3. **BALANCE-ONLY** (McDonald's, confirmed; PepsiCo, Procter & Gamble, Nike, same tag pattern by
   batch check) — no flow tag at all, only a period-end balance. **Confirmed unreliable** for
   automated reconstruction whenever compensation-driven reissuance overlaps repurchase years,
   which is the normal case, not the exception.

This is a concrete, evidence-based answer to "which pipeline companies are safe to study next":
anything confirmed pattern 1 or 2 is safe to run the same way COST was; pattern 3 needs manual
10-K work, not the template as it stands.

---

## 4 · Where things landed

- `buyback_study_TEMPLATE.py` and `buyback_study.py` (plain-name alias import target) — both
  updated to the third-pass version, both in this folder's root, verified byte-identical to each
  other.
- `code/run_COST.py`, `code/cost_sec_raw.json`, `code/cost_monthly.csv`,
  `code/COST_buyback_dataset.csv` — the Costco study, re-run from this exact location and
  reconfirmed clean before landing.
- `code/template_test_HD.py` re-run from this exact location after the template update — all 11
  checks still PASS.
- Nothing from the McDonald's attempt is landed, per section 1.
