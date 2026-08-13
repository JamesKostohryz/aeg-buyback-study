# NEXT SESSION PROMPT — buyback study: repair the generalized study code

Paste this whole file into a fresh chat in the AEG Valuation System 2 project. Written 2026-08-09 at
the second handoff, replacing the prompt of the same name. **Recommended model: Sonnet. The work is
mechanical and fully specified.**

**A note on the word "template," which is overloaded in this project.** This prompt is about
`buyback_study_TEMPLATE.py` — the generalized Python code that applies the buyback study to any
company. It has nothing to do with "Template A," the implied-expectations report template, which is
a separate piece of work in the `AEG Report Templates And Sample Reports` folder. Where this file
says "the template" it means the Python code.

## What was finished last session

The Apple study is done and verified. `Buyback-Study-AAPL.html` now runs to eleven sections and eight
exhibits: the capital-decomposition addendum is folded in, sections 7 and 8 are rewritten, and there
are two new sections on the Real Capital Base and on the return on retained earnings. Forty automated
checks in `code/verify.py` run against the generated document itself and fail the build if any
published figure drifts from its computed source. Every figure is computed; none is typed. The
generator now reads the engine anchor from `AAPL_summary.csv` at build time rather than carrying it
as a constant.

**Two corrections landed that change numbers you may remember.**

The vendor balance-sheet "Total Debt" line changes definition in fiscal 2024 — it starts folding
capitalized leases in and does not restate the earlier years. Fiscal 2025 is an endpoint, so the
series could not be differenced across the break. Gross borrowings now come from Securities and
Exchange Commission tags. Gross debt added is $98.7 billion not $112.4 billion; the increase in net
financial obligations is $87.5 billion not $101.2 billion; the return on incremental operating
capital is **164.9 percent not 125.0 percent**; the capital split is **95.5 / 5.0 not 94.0 / 6.5**.
The addendum and the findings document are reissued. The engine is *not* fixed — see
`claude/AEG-Engine-Defect-Vendor-Total-Debt-Break-2026-08-09.md`.

And version 1 called $62.12 the "dollar-weighted average price paid." It is not. $62.12 is total cash
over total shares retired, which is weighted by shares. The **dollar**-weighted average is
**$114.08**. Both are now reported, each labelled with its weighting. James caught this one.

## Read these first, in this order

1. `AEG Buyback Study/00-Buyback-Study-METHODOLOGY-2026-08-09.md` — **version 2**. Governing document.
   Section 2 now carries both rejected vendor lines; section 6 is rewritten against a real
   second-company run.
2. `AEG Buyback Study/Template-Exercise-FINDINGS-2026-08-09.md` — the nine template defects, with
   the code that found them. **This is the work order for section 1 below.**
3. `AEG Buyback Study/AAPL-Capital-Decomposition-ADDENDUM-2026-08-09.md` — version 2, reissued.
4. `AEG Buyback Study/AAPL-Buyback-FINDINGS-2026-08-09.md` — version 2, corrected.
5. `AEG Definition & Explanation Articles/00-HOUSE-CONVENTIONS-2026-08-08.md`.
6. Load the `rva-style-guide` skill before writing a word of copy.

Code is all in project knowledge under `AEG Buyback Study/code/`: `source_data.py`, `build.py`,
`gen_article.py`, `verify.py`, `run6_aeg_account.py`, `run7_capital_decomposition.py`, plus the two
template tests `template_test_HD.py` and `template_test_CRM_probe.py`. The template itself is
`buyback_study_TEMPLATE.py`. To reproduce: clone `JamesKostohryz/aeg-valuation`, copy
`AAPL_reported_is.csv`, `AAPL_reported_bs.csv`, `AAPL_reported_cf.csv`, `AAPL_dupont.csv`,
`coe_history_AAPL_annual.csv`, `AAPL_restated.csv` and `AAPL_summary.csv` from `outputs/` alongside
the code, then `python3 gen_article.py && python3 verify.py`. Verify must print ALL 40 CHECKS PASS.

## Task 1 — repair the generalized study code. This is the job.

Nine defects, in priority order, all specified in the findings document. Close the first five, then
re-run `template_test_HD.py` against the fixed template and regenerate the findings file. Do not
generate a company report from the template until that passes.

The first two are the ones that matter. `parse_concept()` scans only the `USD` and `shares` unit
buckets, and diluted earnings per share is filed under `USD/shares` — so the template returns an
**empty** earnings-per-share series for every company, silently disabling the attribution, the
multiple paid and the whole timing test. And when no year has an observable issuance rate the
fallback is silently set to zero, which collapses shares retired into the net share reduction and
reports a dilution offset of zero for exactly the companies where dilution is the story. On
Salesforce that produced an implied average price of $869.89 a share against a stock whose high that
year was $369.00.

The single rule behind six of the nine: **a missing input must never be silently treated as zero,
and an estimated input must always be announced.**

## Task 2 — the one property still unexercised

Home Depot's dilution offset is 7.5 percent, so the at-or-above-one-hundred-percent reporting path
has still never fired on real data. Salesforce could not supply it either, because it tags neither
retirement nor treasury acquisitions. Find a company that tags one of them *and* issues nearly as
fast as it buys — a mid-cap software or biotech name is the likely shape — and run it.

## Task 3 — rulings that are settled. Do not reopen these.

**The AEG pivot is Neutral Value, not Intrinsic Value.** Settled by James, 2026-08-09. A repurchase's
contribution to measured abnormal earnings growth is the earnings acquired less the real cost of
equity applied to the price paid, so it is positive precisely when the earnings yield at the price
paid exceeds the real cost of equity — that is, when the price paid sits below Neutral Value. No
estimate of Intrinsic Value enters it, and none may be substituted. Whether a purchase made at a low
earnings yield is later justified by abnormal growth is a question of which year the abnormal
earnings growth is recognized in, not of where the pivot sits. Methodology section 4.3 records this.
A previous session got it wrong and it had to be corrected twice; do not let it drift back.

**Scope is ex-post disclosure only.** The ex-ante normal-earnings benchmark that charges every capital
source is gated work — it rewrites the heart of the AEG form and must be re-threaded through all four
legs of the value tie, and it needs the share count un-frozen in Equity mode first. See
`claude/AEG-Capital-Attribution-SPEC-2026-08-08.md`. Nothing in this study moves a valuation number
and it must stay that way.

**The study states no estimate of Apple's Intrinsic Value.** It reports Neutral Value from the engine,
the price, the break-even, and what the price paid implies. The reader judges.

## Task 4 — the implied-expectations companion piece already exists. Do not build a new one.

`AEG Report Templates And Sample Reports/Sample Reports/AAPL-Implied-Expectations-Report.html`
exists, along with `claude/AAPL_Implied_Report_TemplateA_v2.html` and the build spec and working
draft in the same folder. **Revising that is a separate job from this one and belongs in its own
chat**, because it is Template A work rather than buyback-study work and it carries a known
published error of its own: the line reading "Inflation adjustments, net +$2.64 (debt capital gain
+$2.87, depreciation penalty −$0.23)," in which all three parts are wrong — the debt mark is not an
inflation adjustment, the depreciation figure sits on a retired basis, and the anchor-level line has
changed sign.

What this session owes that job is one thing only, and it should be handed over rather than acted
on: the premium in Apple's current price over Neutral Value is about $3,113 billion, which
capitalized in the Ohlson–Juettner form requires a perpetual real abnormal earnings growth flow of
roughly $9.4 billion a year forever — about 2.0 times what Apple actually delivered on average over
the thirteen years studied, from a business whose abnormal earnings growth was negative in six of
them. **Those three figures were carried forward from a prior session and have NOT been re-verified
against the corrected debt series. Re-derive all three from HEAD before anyone quotes them.**

## Traps that have already bitten this work

The vendor cash-flow feed cannot be used for repurchases or issuance: "Repurchase of Capital Stock"
is, for early years, the negative absolute value of "Net Common Stock Issuance" above it. The vendor
balance-sheet total-debt line cannot be used either — see above. Use the Securities and Exchange
Commission XBRL company-concept interface; tags are in methodology section 2.

`Ordinary Shares Number` in the repo balance sheet is the weighted average diluted count, not
period-end shares. Period-end comes from SEC `CommonStockSharesOutstanding`.

As-filed share counts sit on the split basis in force at the filing date. Apple needs ×28 before June
2014, ×4 between June 2014 and August 2020, ×1 after. Derive this per company; Home Depot's is 1.0
throughout and the machinery got that right.

Validate implied prices against intra-period highs and lows, never period-end closes. Fiscal 2015's
implied $26.59 sits below the lowest month-end close of $27.00 but comfortably inside the true traded
low of $23.00. **This validator is the most valuable guard in the study — it caught two separate
silent estimation failures on two different companies in the template exercise. Never make it
optional.**

Suppress, don't print, a ratio with a small or negative denominator — and the guard must be
two-sided, not sign-only. Apple's net operating assets were negative in nine of thirteen years.

Do not compute a per-share clean-surplus AEG series across a changing share count. The entity-level
cum-dividend series is share-count invariant; the per-share terms allocate an entity-level quantity.

Two averages exist for the price paid and they are nearly a factor of two apart. Say which weighting
you are on, every time.

## Standards

American spelling. Prose over bullet lists in published copy. Acronyms written out on first use. Real
terms unless a sentence says otherwise. Neutral Value, Intrinsic Value and Price are three distinct
quantities and are never used as synonyms; "fair value" is retired. Any engine figure published must
be read from the repository at HEAD by the session that publishes it — `gen_article.py` now does this
automatically from `AAPL_summary.csv`; keep it that way.

Every central measure is computed two independent ways and must reconcile before a sentence is
written about what it means. This is house convention section 6 and it is not a formality — it caught
the return-on-retained-earnings figure, it proved the derived share counts, and it is the only reason
the vendor total-debt break was found at all.

James is not a programmer. Explain in plain language, hand him one complete file to paste rather than
diffs, and walk him click by click through anything he must do himself. He wants precise pushback,
not agreement. Two things in this study came directly from him overruling or challenging a session,
one calculation he requested had to be declined as double counting and delivered a different way
instead, and his challenge to the $62 figure caught a labelling error that would have gone out.
