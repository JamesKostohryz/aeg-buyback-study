# Exercising the generalized template on a second and third company — findings

**2026-08-09. Companion to `00-Buyback-Study-METHODOLOGY-2026-08-09.md` section 6. Code:
`code/template_test_HD.py` and `code/template_test_CRM_probe.py`. The template under test is
`buyback_study_TEMPLATE.py`.**

The template had never been run end to end against a company other than Apple. It has now been run
against The Home Depot in full, and probed against Salesforce for the one property Home Depot could
not exercise. Nine defects were found. Two of them would have produced a published study that was
quietly wrong rather than one that failed loudly, which is the failure mode the methodology document
was written to prevent.

---

## 1 · Why these two companies

Home Depot was chosen because it fails Apple's shape in four separate ways at once. It holds
repurchased shares in treasury rather than retiring them, so the tag Apple's study depends on does
not exist for it at all. Its net operating assets are large, positive and generally rising, so the
sign guard that suppressed almost every Apple window must *not* fire — and over-firing would have
been invisible on Apple, where firing was the normal case. Its fiscal year ends in late January or
early February, which is a far harder test of the calendar-to-fiscal mapping than Apple's September.
And it has not split since 1999, so every split factor must evaluate to exactly one and must not
inherit Apple's twenty-eight, four and one.

Salesforce was added afterward because Home Depot's dilution offset came out at 7.5 percent, which
leaves the near-or-above-one-hundred-percent reporting path unexercised. Salesforce turned out to
expose something worse than a missing report line.

---

## 2 · What broke

**Defect 1 — the treasury fallback is documented but never applied.** The template's tag table lists
`TreasuryStockSharesAcquired` and `TreasuryStockValueAcquiredCostMethod` with the comment that
companies holding stock in treasury tag these instead, and that they should be tried as a fallback.
No code path tries them. `share_flows()` reads `sec['shares_retired']` and nothing else, so for Home
Depot it returns an empty study. Applied by hand in the test driver. This is the failure mode the
methodology predicted in its own section 6 and the template acknowledged in a comment without
implementing.

**Defect 2 — the concept parser cannot see earnings per share, on any company.** `parse_concept()`
scans only the `USD` and `shares` unit buckets. Diluted earnings per share is filed by every
registrant under `USD/shares`. The template therefore returns an *empty series* for diluted earnings
per share for every company in existence, which silently disables the earnings-per-share attribution,
the multiple paid, the market multiple, and the entire timing test. This never surfaced on Apple
because that build read earnings per share from the engine's committed comma-separated files rather
than from the Securities and Exchange Commission. **This is the most serious finding: a core measure
of the study returns nothing, and returns nothing quietly.**

**Defect 3 — one tag name per quantity is not enough.** Pretax income needed two different tags to
cover Home Depot's window: the `...BeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`
variant from fiscal 2020 forward and the `...MinorityInterestAndIncomeLossFromEquityMethod...`
variant before it. Gross debt was worse. The tags the Apple build used return two years out of
eighteen for Home Depot; the series had to be rebuilt from
`LongTermDebtAndCapitalLeaseObligations`, its `Current` variant, and `CommercialPaper`. The template
needs an ordered alternates list per quantity, and it needs to fail loudly on short coverage rather
than treat a missing tag as a zero.

**Defect 4 — the zero-issuance default, and why Salesforce is the case that matters.** When no year
has both a filed retirement count and a share-count movement, the template computes its fallback
issuance rate as `(sum(obs)/len(obs)) if obs else 0.0` — and the explanatory note that would tell the
reader an estimate was used is appended only `if obs:`. So for a company with no observable issuance
the rate is silently set to zero, shares retired collapses to the net reduction in shares
outstanding, and the dilution offset is reported as 0.0 percent **for exactly the companies where
dilution is the whole story**.

Salesforce tags neither `StockRepurchasedAndRetiredDuringPeriodShares` nor
`TreasuryStockSharesAcquired`. Under the zero default its fiscal 2025 comes out as $7,829 million
spent retiring 9 million shares, an implied average price of **$869.89 a share** against a stock
whose highest trade in that fiscal year was $369.00. The price validator catches it, which is the
system working. The default that caused it is silent, which is the system failing.

**Defect 5 — the issuance-rate fallback averages the wrong years.** Even where observations exist,
the template takes the plain mean across all of them. Home Depot's treasury tag begins in fiscal
2016, by which time option exercise had fallen away; the mean rate of 0.277 percent of opening shares
was then applied backward to 2012 and 2013, when Home Depot's equity plans were far larger. The
result was an implied average price of $69.58 for fiscal 2013 against a fiscal-year mean market price
of $56.38 — a 23 percent overshoot, caught by the traded-range validator. Apple's study avoided this
by *judgment*: it held the earlier years at the 0.70 percent observed in the earliest tagged years
rather than extrapolating off a later downtrend. The template automates the wrong default. Where the
observable years are all recent and the series trends, the rate must be taken from the earliest
observable years, and the choice must be stated.

**Defect 6 — the sign guard is one-sided.** It suppresses the return on incremental operating capital
when the change in net operating assets is negative. It does not suppress when the change is
positive but trivially small relative to the capital base, which produces a ratio just as meaningless
and far more likely to be believed. Home Depot's fiscal 2013 to fiscal 2019 window moved net
operating assets by −$533 million on a base of about $26 billion — a two percent drift — and was
correctly suppressed. Had it drifted two percent the *other* way, the template would have printed a
return of roughly two thousand percent with no warning at all. The guard should test the magnitude of
the denominator against the capital base, not merely its sign.

**Defect 7 — a missing component is silently zero.** `comp_wedge()` reads
`PaymentsRelatedToTaxWithholdingForShareBasedCompensation` through a getter that substitutes zero for
anything absent. Home Depot does not tag it. The grant-versus-delivery wedge came out at −$178
million against an accounting charge of $4,622 million, and nothing in the output says a component of
the calculation was missing. On Apple that same line was $45.8 billion. A study can be understated by
tens of billions of dollars with no visible warning.

**Defect 8 — the fiscal-year-end price lookup assumes a September-like year.** `fy_end_price()` looks
up the fiscal-year-end month of the label year. For a January fiscal year end the label year and the
calendar year of the closing month coincide only by accident of the keying convention, and the
function returned nothing. The terminal valuation for the internal rate of return fell back to the
last available month. This needs to be derived from the same mapping `fiscal_months()` already uses
rather than assembled independently.

**Defect 9 — no reporting path exists for a dilution offset at or above one hundred percent.**
`report()` prints the offset as a bare percentage with no threshold logic. The methodology says that
at that point the correct description is not a repurchase program at all. Nothing in the code says
so.

---

## 3 · What worked, and is worth recording as working

The split machinery came through clean. Home Depot's last split was 1999, the configuration carries
an empty split list, and every factor evaluated to exactly 1.0 — Apple's twenty-eight did not leak.
The fiscal-month mapping produced sensible fiscal-year mean prices for a February-to-January year.

The traded-range validator earned its place twice. It caught defect 5 on Home Depot and defect 4 on
Salesforce, and in both cases the underlying cause was a silent estimate rather than a loud one. The
methodology's insistence that every implied average price must be a price that actually existed is
the single guard that turned two invisible failures into visible ones.

The sign guard did not over-fire on Home Depot. It suppressed one window of four, and that window
genuinely had a falling denominator. That was the specific property the Apple run could not test.

**The fiscal-year labelling is internally consistent but does not match the company's own naming.**
The parser keys a filing by the calendar year in which the fiscal year ends, so Home Depot's fiscal
2024 — which closed on 2 February 2025 — is carried as label 2025. Everything downstream is
consistent with that convention, and the fiscal-month mapping agrees with it, so no number is wrong.
But every year in the output is labelled one higher than Home Depot labels it, and a report published
that way would be read as wrong even though it is not. The template must carry a display offset
alongside the internal key, and state which convention a published table is on.

---

## 4 · What the Home Depot run actually found, in passing

Not the point of the exercise, but worth keeping. Home Depot spent $92.7 billion retiring 678 million
shares over the fourteen years to fiscal 2025 at a dollar-weighted average of $136.80 and a
dollar-weighted 20.48 times earnings. Its execution within the year was one percent better than the
market's own average multiple over the same years, and its allocation across years was 0.3 percent
better than equal weighting — so unlike Apple, which was good at execution and poor at allocation,
Home Depot was mildly good at both. Its dilution offset is 7.5 percent of shares retired, so the
program is almost entirely a return of capital.

One caution attaches to the return on incremental operating capital. The fiscal 2019 to fiscal 2025
window prints 9.7 percent, but net operating assets over that window rose by $41.7 billion, of which
a large part is the SRS Distribution acquisition and the lease liabilities recognized on the adoption
of the leases standard. A return on incremental capital struck across an acquisition window measures
the acquisition, not reinvestment in the existing business. That is an economic caveat rather than a
template defect, but the template should flag windows containing a material acquisition.

---

## 5 · Priority order for fixing the template

Defect 2 first, because it disables a core measure on every company. Then defects 4 and 5 together,
because they are the two that produce a wrong published number rather than a missing one. Then
defect 1, which blocks an entire class of company. Then 3, 6 and 7, which are all instances of the
same underlying rule: **a missing input must never be silently treated as zero, and an estimated
input must always be announced.** Then 8 and 9, which are presentation.

The template should not be treated as settled, and no company report should be generated from it,
until defects 1 through 5 are closed and this Home Depot run is repeated against the fixed version
with the same findings file regenerated.
