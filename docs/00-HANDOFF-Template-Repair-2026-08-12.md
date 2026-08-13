# HANDOFF — repair the generalized buyback-study template

**Written 2026-08-12. Paste this whole file into a fresh chat in the AEG Valuation System 2 project.
Recommended model: Sonnet. This is mechanical code repair against a specification that already
exists; the judgment was spent when the defects were found.**

**Supersedes section 3 of `AEG Buyback Study/00-HANDOFF-Buyback-Study-2026-08-12.md`.** Sections 1
and 2 of that file are DONE — do not redo them. What was done is recorded in section 1 below.

**First action.** Ask James to grant the folder `C:\Users\james\AEG-Project` and read
`00-START-HERE.md` in it. The session that wrote this handoff could not reach it: the desktop bridge
was not connected, and no `remote-devices` tools were present at all. Anything in that folder
overrides this file.

---

## 1 · What is already done, so it is not repeated

**The study rebuilds and verifies at HEAD `3937d5e`.** `python3 gen_article.py && python3 verify.py`
prints **ALL 76 CHECKS PASS**, up from forty. The rebuilt document is in project knowledge at
`AEG Buyback Study/Buyback-Study-AAPL.html` and the four code files at
`AEG Buyback Study/code/` are current.

**The engine anchor is read from the quarantined run, with disclosure.** `gen_article.py` and
`verify.py` both read `AAPL_summary.STALE.csv` by name — deliberately not renamed to
`AAPL_summary.csv`, so a stale anchor cannot slip through unnoticed. The method footer carries a
paragraph headed *Currency of the valuation anchor*, and the build note carries the full statement.
James approved this on 2026-08-12.

**The vendor debt break was found to be half repaired, and every description of it was restated.**
The engine's lease ruling landed on 2026-08-09 and now feeds Apple's fiscal 2024 and 2025 debt rows
from primary source; fiscal 2022 and 2023 still carry noncurrent finance leases. The study's build
note, one sentence in section 8 and two of the forty original checks all asserted a four-year break
that no longer exists. All are corrected, and a third check was added asserting that fiscal 2024 and
2025 now agree to the dollar. The engine-side finding is filed at
`claude/AEG-Defect-Apple-Lease-Basis-Gap-FY2022-23-2026-08-12.md`. **Read that file before touching
anything that reads the vendor debt row.**

**Section 7, the net retirement cost, is built and published.** New section, everything after it
renumbered: sections 7–11 became 8–12, Exhibits 6–8 became 7–9. It carries the annual gross-against-
net table, the four measures, the methodological ruling as a signal box, and the Salesforce contrast.
Sixteen new checks cover it, including the identity `gross − issued = net` per year and cumulatively.
Nothing in section 3 moved: every figure there is still struck on the gross price of $62.12.

**Two items were left for James and are not yours.** The name *net retirement cost* is a new coinage
that does not extend the *neutral* root, and is flagged in the build note for a ruling under section 4
of the style guide. And the Salesforce fiscal 2024 and fiscal 2026 rows have not been re-derived from
filings — fiscal 2025 is independently corroborated, the other two are not — which is stated in the
build note and should be closed before that section is published outside the project.

---

## 2 · Your job: defects 1 through 5 in `buyback_study_TEMPLATE.py`

All nine defects are specified in full, with the code that found them, in
`AEG Buyback Study/Template-Exercise-FINDINGS-2026-08-09.md`. **That document is unaffected by
anything above and is still accurate.** Read it; do not work from this summary.

Close defects 1 through 5, re-run `template_test_HD.py` against the fixed code, and regenerate the
findings file. **Do not generate a company report from the template until that passes.**

The first two matter most, and both fail silently rather than loudly:

**Defect 2 — `parse_concept()` cannot see earnings per share, on any company.** It scans only the
`USD` and `shares` unit buckets. Diluted earnings per share is filed under `USD/shares`, so the
function returns an empty series for every registrant, silently disabling the attribution, the
multiple paid, the market multiple and the whole timing test.

**Defect 4 — the zero-issuance default.** Where no year has an observable issuance rate the fallback
is set to zero and the note announcing an estimate is appended only when observations exist. Shares
retired then collapses into the net share reduction and the dilution offset is reported as zero for
exactly the companies where dilution is the story.

**A connection that is new since the findings file was written, and it makes defect 4's fix cleaner.**
The net measure now has a name and a definition of its own in the Apple study. So the correct
behavior when no retirement count is available is not to derive a fictitious gross price. It is to
report the net retirement cost honestly and **decline to report a gross price at all**. Salesforce is
the case in point: it tags neither `StockRepurchasedAndRetiredDuringPeriodShares` nor
`TreasuryStockSharesAcquired`, so no gross price exists for it, and the template should say so rather
than invent one. Methodology section 3 already says this in words; the code should now say it too.

The rule behind six of the nine defects: **a missing input must never be silently treated as zero,
and an estimated input must always be announced.**

---

## 3 · Still unexercised, and worth one search

The dilution offset at or above one hundred percent has never fired on real data. Home Depot's is 7.5
percent; Salesforce tags nothing to compute a gross figure from. Find a company that tags a
retirement or treasury count **and** issues nearly as fast as it buys, and run the template against
it. Until then that reporting path is untested.

---

## 4 · Environment notes that will save you an hour

The repository clones fine in the sandbox and HEAD was `3937d5e` on 2026-08-12 — **check whether it
has moved before trusting anything here.** It moved twice in the three days before the previous
handoff was written, and the lease ruling that invalidated three claims landed in exactly that gap.

To reproduce the Apple study: clone `JamesKostohryz/aeg-valuation`, copy `AAPL_reported_is.csv`,
`AAPL_reported_bs.csv`, `AAPL_reported_cf.csv`, `AAPL_dupont.csv`, `coe_history_AAPL_annual.csv`,
`AAPL_restated.csv` and `AAPL_summary.STALE.csv` from `outputs/` alongside the four code files from
`AEG Buyback Study/code/`, then run `gen_article.py` and `verify.py`. A cloud session cannot build or
recalculate the sealed workbook — the raw statement feeds are not in the repository — but nothing in
this job needs it.

---

## 5 · Settled. Do not reopen.

The pivot for a repurchase's contribution to abnormal earnings growth is **Neutral Value, not
Intrinsic Value**, settled by James on 2026-08-09. The scope of this study is **ex-post disclosure
only** and nothing in it moves a valuation number. The study **states no estimate of Apple's Intrinsic
Value**. The net retirement cost **is not a price, does not enter the abnormal earnings growth
account, and is not an expense** — that ruling is written into the code as a comment and into the
document as a signal box, and it was argued through on 2026-08-12.

---

## 6 · Traps carried forward unchanged

The vendor cash-flow feed cannot be used for repurchases or issuance. `Ordinary Shares Number` in the
repository balance sheet is the weighted average diluted count, not period-end shares; period-end
comes from `CommonStockSharesOutstanding`. As-filed share counts sit on the split basis in force at
the filing date — Apple needs ×28, ×4 and ×1, Home Depot 1.0 throughout. Validate implied prices
against intra-period highs and lows, never period-end closes; **this validator is the most valuable
guard in the study and caught two separate silent estimation failures on two different companies.
Never make it optional.** Suppress rather than print a ratio on a small or negative denominator, and
make the guard two-sided rather than sign-only.

**And there are now four averages in circulation, not two.** The share-weighted price paid is $62.12
and the dollar-weighted price paid is $114.08 — nearly a factor of two apart. Section 7 adds the net
retirement cost at $70.83 and the full cash cost at $74.26, which are neither. Say which one you are
on, every single time.
