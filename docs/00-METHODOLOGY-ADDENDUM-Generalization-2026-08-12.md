# ADDENDUM — what the Apple study is missing as a template for other companies

**2026-08-12. Companion to `00-Buyback-Study-METHODOLOGY-2026-08-09.md`, which it extends and does
not replace. Commissioned by James after the net-retirement-cost section landed, on the observation
that the Apple report is meant to be the model for a series.**

The Apple study is sound on Apple. The question here is different: **which of its measures will
produce a confidently wrong answer when pointed at a company that is not Apple?** The items below are
ranked by that risk, not by how interesting they are. Two are built and in the report already; the
rest are specified for the sessions that will build them.

Apple is, for these purposes, an unrepresentative company in five separate ways at once. It has
smooth earnings, it began the period with no debt, it has never raised equity, it retires its shares
rather than holding them in treasury, and it tags the retirement count. Nearly every gap below is a
gap because Apple could not exercise the property.

---

## 1 · The entry effect is struck on reported earnings, and on a cyclical company that inverts the answer

**Risk: wrong sign. Status: NOT BUILT. Gated.**

`ENTRY[t] = retired_t x (real EPS_(t+1) - rho x real price paid_t)`. The earnings term is next year's
**reported** earnings per share.

For Apple this is defensible, because Apple's earnings do not swing far from their own path. For a
semiconductor maker, a homebuilder, an automaker, an energy producer, a shipper or a bank, it is not.
A repurchase made at the top of a cycle is struck against peak earnings and prints a large positive
entry effect; the identical decision made at the bottom is struck against depressed earnings and
prints a negative one. **The measure will systematically praise the worst-timed repurchases in the
market and condemn the best.**

It also sits awkwardly with this project's own doctrine, which is that value is Neutral Earnings Power
capitalized at the real rate, not whatever the year happened to print. The study capitalizes at the
real rate and then feeds it reported earnings.

**Two ways out, and they are not equivalent.** Substituting Neutral Earnings Power into the entry
effect changes what the measure means: it stops being *what the repurchase actually earned* and
becomes *what it could reasonably have been expected to earn*. Both are legitimate and they answer
different questions. The realized measure is the honest one for an ex-post disclosure study, which is
what this is. So the recommendation is **not** to substitute, but to **refuse**: compute the deviation
of reported earnings from the Neutral Path in each year, and where a tranche's earnings anchor sits
materially off that path, suppress the entry effect for that tranche and say why, exactly as the study
already suppresses a ratio with a bad denominator. A cyclical company then gets a study with holes in
it, which is the truthful output.

**Do not run this study on a cyclical company until this guard exists.** That is the single most
important sentence in this addendum.

---

## 2 · The capital charge is held at a constant rate across a period in which leverage changed

**Risk: wrong sign. Status: the TOLERANCE is built and published; the CORRECTION is built,
template-verified and scheduled, but has not been run on any company. Gated.**

**Revised 2026-08-12, second pass, after the engine session reported.** The first version of this
section said the re-levering treatment was deferred and that the project had not made the modelling
judgment it required. Both statements were true when written and both are now wrong. The section is
restated rather than patched, because the recommendation at the end of it has changed.

A company that borrows to retire its own stock raises the required return on the equity that remains.
A capitalization rate held flat across thirteen years of rising leverage therefore undercharges the
later years — which are exactly the years a repurchase study is most interested in.

**The tolerance, which is built and is the sharpest number in the report.** The entry effect is
linear in the capitalization rate, so it has exactly one root, and that root is the
retirement-weighted forward real earnings yield — a closed form, no search. For Apple:

| | Break-even real cost of equity |
|---|---|
| Whole program, fiscal 2013–24 tranches | **5.99%** |
| Fiscal 2013–19 tranches | 7.80% |
| Fiscal 2020–24 tranches | 4.44% |
| Rate the engine actually uses | 5.4881% |

**The headline conclusion that Apple's program added abnormal earnings growth on entry survives on
fifty basis points of capitalization rate and nothing else.** Apple's net financial obligations rose
by roughly half a turn of equity over the period. Fifty basis points is well inside what that change
could plausibly justify.

**What the engine's live path does, as read at commit `3937d5e` and still true at `9daa6e8`.** The
cost of equity is composed exactly as `real_rf + market_erp + idiosyncratic`. There is no beta term
and no re-levering step in it; `market_erp` is a market-wide series and cannot respond to one
company's capital structure; and the re-lever layer that exists in the workbook is dormant, the
published valuation not consuming it. What the engine enforces instead is the value-neutrality of
leverage by accounting identity — the four-method tie and the canonical closure, financing absorbing,
the equity and enterprise readings agreeing at exactly zero. That makes leverage neutral to *value*.
It does not make the *cost of equity* respond to leverage. **No company valuation has yet been struck
on a re-levered rate.**

**What changed on 2026-08-12, and it is more than a status field.** The V2 re-levering was approved,
built and proven in the same session, and the method is now specified rather than open: **pure
Modigliani–Miller Proposition II with no tax adjustment; the unlevered rate solved once at the
anchor; leverage taken as the anchor market-to-book multiple applied to the model's own driven book
equity.** It was verified by a real recalculation of the template's own base-company fixture, leaving
the four-method tie unchanged with the hook off and on while equity value moves. It is **scheduled as
the next gated item**, not deferred, and `disclose.py`'s docstring now says so (commit `196b69d`).
The working hook is `patches/relever_v2.py`.

**One caution about where that hook lives.** It is in the `C:\Users\james\AEG-Project` working folder
and NOT in the repository. It is a gated engine change, proven by a recalculation that cannot be
reproduced in a cloud session, and its only copy sits on a machine that several recent sessions could
not reach at all. It should be committed.

**And a provenance finding that changes the recommendation.** The engine session traced both rates
this study publishes. The flat long-run rate is read from the engine's own per-tenor curve, no
averaging, and is clean. But the year-by-year company history — `coe_history_<TICKER>_annual.csv` —
is **not computed by this system at all.** It derives from a monthly effective cost-of-equity
decomposition covering 1877 to 2026 that was ingested whole from an external source on 2026-07-21 and
has never been recomputed by anything in either repository. Separately confirmed: the ERP collapse
function retired on 2026-08-12 never fed either figure, so neither moves and no regeneration is
needed. But the historical curve is a **data input, not a model output, and it is not reproducible
from this system.**

That matters because the alternative entry effect of minus $13.5 billion — the one that reverses the
study's headline sign — is struck on that curve. The disagreement between it and the plus $4.6
billion figure is not a defect. It is a flat thirty-year rate against a time-varying historical mean,
two different things, and the study reports both and declines to choose. The provenance is now
disclosed in the method footer.

**The recommendation, and it is the reverse of this section's first version.** Previously: use the
historical curve now, because it is available and carries the leverage signal empirically through
option-implied volatility. **That is no longer the better path.** The historical curve is an
unreproducible external ingest, it mixes leverage with changing business risk and single-name option
flow so it cannot be described as a leverage decomposition, and its idiosyncratic component is zeroed
in the engine's own headline — so promoting it to a published capital charge would put the study on a
basis the engine itself does not use, sourced from a file neither repository can rebuild.

**So: do not promote the historical curve. Keep it exactly where it is — a disclosed alternative,
with its provenance stated, neither suppressed nor preferred. Hold the break-even tolerance as the
interim answer to the leverage question, because it is exact, reproducible and requires no rate at
all. Then inherit the V2 re-levered rate from the engine when it lands, and compare it against the
fifty basis points.** Do not build a bespoke re-levering rule inside the buyback study; that is how
one quantity ends up with two definitions in one system.

---

## 3 · There is no measure of the round trip, which is the pattern that most damages shareholders

**Risk: a missing finding, not a wrong one. Status: NOT BUILT. Safe.**

Buy heavily near a peak, then issue equity near a trough. Airlines, cruise operators, banks in 2008,
Boeing in 2020. It is the case that animates the entire public argument against repurchases, and the
Apple study has no measure that can see it — because Apple has never raised equity, so nothing was
built.

A template that cannot detect a company retiring stock at $60 and issuing it back at $15 four years
later is missing the finding a reader will most want. It is cheap: repurchase cash per year against
equity raised per year, at the prices at each end, and a cumulative round-trip loss where both
occurred inside the window. The tags are `PaymentsForRepurchaseOfCommonStock` against
`ProceedsFromIssuanceOfCommonStock` and `ProceedsFromIssuanceOfCommonStockAndWarrants` and their
at-the-market variants, with the ordinary employee-plan flow netted out so it does not masquerade as
a distress raise.

**Build this second, after the cyclicality guard.** It is the item most likely to make the series
worth reading.

---

## 4 · The net retirement cost assumes permanence, and for a treasury-stock company it is not permanent

**Risk: overstatement. Status: NOT BUILT. Safe, and cheap.**

Section 7's measure divides cash by the reduction in shares outstanding and calls it the cost of
removing a share permanently. For a company that retires its shares, as Apple does, that is right.
For a company that holds them in treasury — Home Depot, and a large fraction of the market — the
shares can be reissued, and the reduction is a decision rather than a fact.

The template needs to detect the treasury case (it already must, for the retirement count, per defect
1 of the template findings) and change the language accordingly: **cost per share withdrawn from the
float**, with the treasury balance disclosed as the reissuable overhang. Same arithmetic, honest
label.

---

## 5 · The tax treatment is missing in both directions

**Risk: understatement of cost, and a one-sided argument. Status: NOT BUILT. Safe.**

*The excise tax is missing from the funding account.* The one percent United States excise on net
repurchases has been in force since 2023. It is generally accrued and settled separately, so it does
not sit inside `PaymentsForRepurchaseOfCommonStock`, which is the line the study uses. It is a real
cash cost of the program and belongs in the sources-and-uses table. **No figure is quoted here
because none has been traced to a filing in this session** — it should be pulled per company from
`ExciseTaxPayable` or the equivalent disclosure, and the template should fail loudly if it cannot
find it for a post-2023 year rather than treat it as zero.

*And the strongest honest argument for repurchases is nowhere in the report.* A taxable shareholder
receiving a dividend pays tax now; a shareholder whose company repurchases instead defers the tax
into a capital gain and may never pay it at all. That is a genuine economic advantage and it is
absent. A report that is scrupulously even-handed about valuation and silent on this reads as
one-sided to anyone who disagrees with it, and the series' credibility depends on not being that.
It belongs in the closing section, stated plainly, without being quantified — the size depends on the
holder, which the company does not know.

---

## 6 · Every ratio is absolute, with no base rate

**Risk: uninterpretable output. Status: blocked until the series exists. Safe.**

The report states a 12.3 percent dilution offset, a 96 percent capital share, a 1.04 times ratio of
net cost to fiscal-year high. It never says whether any of those is high or low, and section 6
explicitly declines the peer comparison.

Once the template has run on a dozen companies the distribution is free, and "this is the ninetieth
percentile" is worth more than any individual ratio. **This is an argument for running the template
broadly and cheaply before polishing any single report**, which is close to the opposite of the
current sequencing.

---

## 7 · The dilution measure counts shares delivered, not the overhang already granted

**Risk: understatement. Status: NOT BUILT. Safe.**

The study counts shares actually issued in the year. It does not count unvested restricted stock
units and unexercised options, which are claims already incurred against future shareholders. For a
company whose share-based compensation runs at several percent of market capitalization, the overhang
is a material part of the honest dilution figure and it is disclosed in the filings.

---

## 8 · Two smaller items

**A dividend counterfactual.** Section 9 compares the repurchase against reinvestment in the business.
It never compares it against the obvious alternative, a dividend — which carries no price risk and
therefore cannot be mistimed. For a company whose repurchase was in substance a variable dividend,
that framing changes the reading.

**Governance and incentives.** Whether the repurchase plausibly served an earnings-per-share-linked
compensation target is checkable from the proxy statement and is entirely absent. It is the question
a sceptical reader asks first. It is also the one most likely to be read as an accusation, so if it
enters the template it should enter as a disclosed fact — whether such a target exists, and what it
is — and never as an inference about motive.

---

## 9 · What must NOT be added, so nobody re-opens it

The study states **no estimate of Intrinsic Value** and the pivot for the entry effect is **Neutral
Value**, settled by James on 2026-08-09. Scope is **ex-post disclosure only**; nothing here moves a
valuation number. The net retirement cost **is not a price, does not enter the abnormal earnings
growth account, and is not an expense**. The ex-ante benchmark that charges every capital source is
separate gated work at `claude/AEG-Capital-Attribution-SPEC-2026-08-08.md`. Attribution of a
company's own multiple expansion to float shrinkage is **not identifiable** from this data and is
stated as a limitation rather than estimated.

---

## 10 · Build order

1. **The cyclicality guard** (item 1). Stops the template producing a confidently wrong answer.
   Nothing else should be published on a cyclical company first.
2. **The round trip** (item 3). The finding that makes the series worth reading.
3. **Treasury permanence** (item 4) and **the excise tax** (item 5). Both cheap, both correct a
   quantity that is currently wrong rather than missing.
4. **Run broadly, then build base rates** (item 6).
5. **Inherit the re-levered cost of equity** (item 2) from the engine once the V2 hook lands on a real
   company. Do not build one in the study. The interim answer is already published: the fifty-basis-
   point break-even, which is exact and needs no rate. Gated on the engine, not on this study.

Items 7 and 8 are worth having and are not urgent.
