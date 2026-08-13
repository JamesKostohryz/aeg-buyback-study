# Share Repurchases and Abnormal Earnings Growth — Study Methodology

**Internal methodology document. Version 2, 2026-08-09. Company studied: Apple Inc. (AAPL),
fiscal years 2013 through 2025. Written to be applied to any company.**

**Version 2 changes, all made 2026-08-09 in the session that folded the capital-decomposition
addendum into the study: section 2 gains a second rejected vendor line and the gross-borrowings
tags; section 4.4 tightens the sign guard; section 6 is rewritten against an actual second-company
run; section 7 records the new reconciliations. Version 1 is superseded, and the figures it carried
for gross debt, net financial obligations and the return on incremental operating capital must not
be reused.**

Abnormal earnings growth is written out as AEG on first use. Neutral Value is NV, Neutral
Earnings Power is NEP. Real Value Analysis terminology governs: Neutral Value, Intrinsic
Value and Price are three distinct quantities and are never used as synonyms.

---

## 1 · What this study is for

Two questions are being answered at once, and keeping them apart is the whole discipline.

The first is descriptive. How much of a company's growth in earnings per share came from
retiring shares rather than from the business, and what did the money spent on retiring
them actually earn? This is arithmetic plus a price series. It requires no view about what
the shares are worth.

The second is evaluative. Did the repurchases create or destroy value? This cannot be
answered without a view on Intrinsic Value, which is exactly the quantity in dispute. The
study therefore does not assert one. It states the test precisely, computes the break-even,
and reports what the price paid implies — the same restraint implied-expectations work
applies elsewhere.

A third purpose is structural. The measures defined here are intended to become a standard
company-level report, so every one of them is specified in a form that generalizes.

---

## 2 · Data sources, and the two vendor lines that had to be rejected

**Rejected, first: the vendor cash-flow feed carried in the engine.** In `AAPL_reported_cf.csv`,
the line labelled "Repurchase of Capital Stock" is not an independently sourced gross
figure. For every year through the early 2000s it is the negative absolute value of the
"Net Common Stock Issuance" line directly above it, so a year in which the company issued
$82 million of stock and repurchased nothing appears as an $82 million repurchase. Gross
"Common Stock Issuance" is populated for four years out of forty. The single most important
pair of variables in this study — gross repurchases and gross issuance, separately — is
precisely what the vendor feed does not carry. Any company-level template built on it would
inherit the defect silently.

**Rejected, second, and found in version 2: the vendor balance-sheet total-debt line.** In
`AAPL_reported_bs.csv` the "Total Debt" line agrees with Securities and Exchange Commission
primary source *to the dollar* for fiscal 2012 through fiscal 2021, and then diverges — by $812
million in fiscal 2022, $859 million in fiscal 2023, $12,430 million in fiscal 2024 and $13,720
million in fiscal 2025. The fiscal 2024 and 2025 gaps are Apple's capitalized lease liabilities,
$11,534 million and $12,490 million, plus its finance leases. The vendor began folding leases into
total debt in fiscal 2024 and did not restate the earlier years.

**The objection is not that leases are or are not debt. It is that the series changes definition in
the middle, and fiscal 2025 is an endpoint of this study.** A series whose definition moves cannot
be differenced across the break, whatever one concludes about the classification question. Gross
borrowings are therefore taken from the Securities and Exchange Commission throughout, as
`LongTermDebtNoncurrent` plus `LongTermDebtCurrent` plus `CommercialPaper`, falling back to
`LongTermDebt` plus `CommercialPaper` in years where the components are not separately tagged.

The correction is verified two ways. The first is decompositional: gross debt raised less the change
in financial assets reproduces the change in net financial obligations exactly. The second is
genuinely independent of the balance sheet: cumulated net debt issuance from the cash flow statement
gives $98,810 million against $98,657 million of Securities and Exchange Commission borrowings, an
agreement of 0.15 percent. **On the vendor basis that same check failed by twelve percent, and that
failure is what exposed the break.** It was found only because the verification standard in the
house conventions requires a second independent route; a study that had computed the figure once
would have published it.

**This carries to the engine and is not fixed here.** The same feed drives `AAPL_dupont.csv`, so the
engine's reformulated leverage and return-on-net-operating-assets series inherit the break from
fiscal 2024 forward. That is an engine defect-register item.

**Adopted: the SEC XBRL company-concept application programming interface**, at
`data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json`, restricted to form 10-K
and to full-fiscal-year periods. It is free, requires no key, and returns as-filed values.
The tags used are:

| Quantity | Tag |
|---|---|
| Cash paid for repurchases | `PaymentsForRepurchaseOfCommonStock` |
| Repurchases per the equity statement | `StockRepurchasedAndRetiredDuringPeriodValue` |
| Shares actually retired | `StockRepurchasedAndRetiredDuringPeriodShares` |
| Shares acquired into treasury (fallback) | `TreasuryStockSharesAcquired` |
| Proceeds from stock issuance | `ProceedsFromIssuanceOfCommonStock` |
| Share-based compensation | `ShareBasedCompensation` |
| Cash tax on net share settlement | `PaymentsRelatedToTaxWithholdingForShareBasedCompensation` |
| Shares outstanding at year end | `CommonStockSharesOutstanding` |
| Gross borrowings | `LongTermDebtNoncurrent` + `LongTermDebtCurrent` + `CommercialPaper` |

**Tag names are not stable across companies or across years**, and the template exercise proved it.
Every quantity needs an ordered list of alternates and a loud failure when coverage is short. A
missing tag must never be silently treated as zero. See section 6.

Prices are EODHD monthly closes for the listed line, converted to today's split basis.
Earnings, share counts, balance-sheet items, the consumer price index deflator and the
company's real cost of equity history are read from the engine's committed outputs at HEAD,
with the exception of gross borrowings noted above.
Engine valuation figures are read from `outputs/AAPL_summary.csv` at HEAD, run vintage
2026-08-09, in accordance with the standing rule in the house conventions. **The generator now reads
that file rather than carrying the figures as constants**, so a stale valuation cannot survive a
rebuild.

**Split restatement.** As-filed share counts sit on the split basis in force at the filing
date, not on today's basis, and mixing them is the easiest way to produce a study that is
wrong by a factor of four. Every share figure is multiplied by the cumulative split factor
between its filing date and today. For Apple that is 28 for filings before June 2014, 4 for
filings between June 2014 and August 2020, and 1 thereafter. **A template applied to a new
company must derive this factor from that company's split history, not inherit Apple's.** The Home
Depot run confirms the machinery does this correctly: its last split was in 1999, the configuration
carries an empty split list, and every factor evaluated to exactly one.

---

## 3 · The one derived series, and how it is validated

Apple did not tag `StockRepurchasedAndRetiredDuringPeriodShares` for fiscal 2014 through
2017, and its fiscal 2013 tagged value covers only part of the year. Those five years are
derived from the share-count identity

    shares retired(t) = shares outstanding(t-1) - shares outstanding(t) + shares issued(t)

where every term but the last is observed exactly. Shares issued under equity plans, net of
shares withheld for employee taxes, is itself observable for fiscal 2018 through 2025 by
running the same identity in reverse against the tagged retirement figures. Expressed as a
percentage of opening shares outstanding it comes out at 0.669, 0.703, 0.680, 0.625, 0.521,
0.487, 0.423 and 0.387 — flat near 0.68 percent through 2020 and declining after, as a
rising share price delivered fewer shares per dollar of award. Fiscal 2013 through 2017 are
therefore held at 0.70 percent, the level actually observed in 2018 through 2020, rather
than extrapolated off the later downtrend.

**That last choice is a judgment, and it is the right default rather than an Apple convenience.**
The Home Depot run shows what happens without it: taking the plain mean of every observable year
and applying it backward produced an implied average price 23 percent above the fiscal year's mean
market price. Where the observable years are all recent and the series trends, the rate must be
taken from the earliest observable years and the choice must be stated in the output.

**Two independent checks, both required before any sentence is written about the result.**

*First, the implied average price must be a price that existed.* Dividing repurchase cash
by derived shares retired gives an implied average price paid, and it must fall inside the
fiscal year's traded range. It does, in every derived year. Note that the range must be the
intra-month high and low, not the range of month-end closes: fiscal 2015's implied $26.59
sits below the lowest month-end close of $27.00 but comfortably inside the true traded low
of $23.00 reached in August 2015. Using month-end closes alone would have produced a false
failure.

**This validator is the most valuable guard in the whole study and it must never be made
optional.** In the second-company exercise it was the only thing that caught two separate silent
estimation failures, on two different companies, in two different code paths. See section 6.

*Second, the same calculation on the years that are not derived must agree with the market.*
For fiscal 2018 through 2025, where shares retired is taken straight from the filings, the
implied average price paid lands within roughly one percent of the fiscal year's mean market
price in six of eight years, and within six percent in the other two. That agreement is not
assumed anywhere in the construction, so it is a genuine test — of the split restatement, of
the price series, and of the fiscal-year mapping simultaneously.

**Sensitivity.** Because net issuance runs at roughly 12 percent of shares retired, a large
error in the issuance estimate produces a small error in the derived retirement figure. At
half and one-and-a-half times the assumed issuance rate, fiscal 2015's implied price paid
moves from $26.83 to $28.48 and $24.94 respectively — a range of about six percent either
side. Every conclusion in the study survives that range.

**Cash versus accrual.** Cash paid for repurchases and the equity statement's retirement
value differ in years containing accelerated share repurchase agreements, where shares are
delivered in one period and settled in another. Apple's fiscal 2013 shows $22.86 billion of
cash against $9.00 billion in the equity statement for this reason. Individual years
therefore carry timing noise; the cumulative figures do not. Single-year average prices
should be read as approximate, and the dollar-weighted average over the full program is the
timing-robust number.

**Treasury accounting.** A company that holds repurchased shares in treasury rather than retiring
them will not tag the retirement element at all, and `TreasuryStockSharesAcquired` carries the count
instead. The study must say which tag it used. A company that tags neither — Salesforce is one — has
no observable share retirement at all, and the derived series is then only as good as the issuance
estimate, which in that case has nothing to anchor on. **For such a company the study should decline
to report a price paid rather than derive one.**

---

## 4 · The measures

### 4.1 Attribution of growth in earnings per share

Arithmetic, exact, no assumption:

    change in EPS(t) = [NI(t) - NI(t-1)] / S(t)  +  EPS(t-1) x [S(t-1)/S(t) - 1]

with S the weighted average diluted share count. The first term is the earnings channel, the
second is the share-count channel. The earnings channel is split further using reported
figures only, and it reconciles exactly:

    NI = [operating income + other income, net] x (1 - effective tax rate)

so the change in net income divides without residual into an operating contribution and a
financial contribution. Note what this does and does not capture: borrowing appears in the
financial contribution only through its effect on interest, not through the repurchases it
financed. The leverage channel must therefore be reported twice — once for its direct
earnings effect, which is usually near zero, and once for the share of repurchases it
funded, which is usually large. Reporting only the first understates leverage badly.

**The funding split.** The share-count channel is divided in the same proportion as the funding of
the repurchases themselves: the increase in net financial obligations over the period as a share of
total repurchase spending, and the balance to retention. For Apple that is $87.5 billion of $816.3
billion, or 10.7 percent, giving $0.192 of earnings-per-share growth to leverage and $1.596 to
retention against a total of $5.888. Reported on the direct interest line alone, leverage is a
negative $0.058. It is the same decision measured two ways, and only one of the two is informative.

### 4.2 The AEG version, and the trap it avoids

Attributing growth in earnings per share to its sources will always show the repurchase
channel contributing a large positive number. Attributing *abnormal* earnings growth is a
different exercise, because a repurchase enters twice and with opposite signs: it lifts
earnings per share, and it consumes capital that must be charged at the real cost of equity.

The house position, settled in the conventions, is the governing one and it is narrower
than the claim it replaced. Earnings-per-share accretion is positive at any price a solvent
company could pay, so the sign of the accretion carries no information. But a repurchase
does produce positive measured abnormal earnings growth whenever the price paid sits below
earnings divided by the real cost of equity — that is, below Neutral Value. The two
statements are compatible and the study must keep them apart.

Per-share clean surplus is invalid once the share count moves, which is why the engine's
valuation tab works per anchor share. The account below is built to avoid that problem
entirely: the entity-level series is share-count invariant by construction, and the per-share
terms allocate an entity-level quantity rather than compute a per-share clean-surplus series.

**Two levels, kept apart.**

*Entity level, total dollars.* Abnormal earnings growth in the cum-dividend form,

    AEG(s) = NI(s) - (1 + r) x NI(s-1) + r x D(s-1)

with D every distribution to shareholders, dividends and repurchases alike, all in real terms.
This is share-count invariant, it charges every use of capital, and it requires no
funding-attribution convention at all — which disposes of the debt-versus-equity attribution
question rather than answering it. A repurchase neither creates nor destroys anything in this
series: cash leaves the company and the benchmark for next year's earnings falls by exactly the
return that cash would have earned. That is the point. The series measures the operating
business, clean of the buyback.

*Continuing-shareholder level, per share.* A repurchase transfers value between the
shareholders who sold and those who stayed, and that only appears per share. It splits in two:

    entry effect(t)      = N(t) x [ real EPS(t+1) - r x real price paid(t) ]
    continuing effect(t) = sum over s > t+1 of  N(t) x AEG_entity(s) / shares(s)

The **entry effect** is felt in the first year and it is objective. It uses the price actually
paid, the earnings actually acquired, and a stated cost of equity. It is negative precisely
when the earnings yield at the price paid is below the real cost of equity — that is, when the
price paid is above Neutral Value. No estimate of Intrinsic Value enters it.

The **continuing effect** is the retired shares' claim on whatever abnormal earnings growth the
business subsequently generated. It is the term that can retrospectively justify a purchase
made at a low earnings yield: buy above Neutral Value and you are behind on day one, but if the
business then grows at an abnormal rate, that growth accrues to the holders who stayed and the
tranche can catch up. **It is real, and it is not knowable at the time of purchase.**

**The pivot is Neutral Value, not Intrinsic Value. Settled by James, 2026-08-09.** Intrinsic
Value is a judgment, and no past year has an objective one to appeal to. What is objectively
known for every past year is the earnings yield at the price paid and the cost of equity, and
those settle the entry effect completely. That a purchase at a low earnings yield may be
justified later by abnormal growth is a statement about which year the abnormal earnings growth
is recognized in — not a reason to move the pivot. Substituting Intrinsic Value would make an
objective measure depend on an undisclosed judgment.

**Two reporting guards.** The continuing effect is not comparable across tranches, because an
early tranche has had many years to accumulate and a recent one none; the requirement is
therefore restated as abnormal earnings growth still owed per retired share, and as a number of
years of the company's own average performance. And because the choice of cost of equity can
flip the sign of the program total rather than move a decimal — on Apple it does — the entry
effect is reported on both rates the engine carries, with neither suppressed.

### 4.3 What the repurchases earned

The forward real earnings yield at the price actually paid:

    earnings yield(t) = real EPS(t+1) / real average price paid(t)

compared against the company's real cost of equity. Real terms throughout, because a company
that keeps pace with inflation is worth its earnings capitalized at the real rate, and
comparing an earnings yield against a nominal required return makes every repurchase look
worse than it is.

**This test is exact, and it answers the AEG question rather than the value question.** The
capital charge on a repurchase is the real cost of equity times the price paid. The earnings
acquired are the earnings the retired shares carried. The contribution to measured abnormal
earnings growth is therefore the second less the first, and it is positive precisely when the
earnings yield exceeds the real cost of equity — that is, when the price paid sits below
Neutral Value. **No estimate of Intrinsic Value enters this test at any point.** Settled by
James, 2026-08-09: Intrinsic Value is a judgment and a separate question, and it does not
govern the accounting of abnormal earnings growth in the interim.

The value question has a different pivot: price against Intrinsic Value. For a company
expected to grow faster than a neutral rate, Intrinsic Value sits above Neutral Value, so
there exists a band of prices in which a repurchase reduces measured abnormal earnings growth
in the near term and still creates value, because the earnings acquired go on growing. The two
questions pivot at different prices and must never be collapsed. A study that substitutes
Intrinsic Value for Neutral Value in the earnings-yield test has silently changed the question
it is answering, and has made the answer depend on a judgment it did not disclose.

**Timing, not pivot.** Because the contribution credits a repurchase only with the earnings it
acquired immediately and not with the growth of those earnings, the measure is back-loaded for
a company with genuine abnormal growth: it understates the repurchase in the year it happens
and recovers the difference later. That is a statement about when abnormal earnings growth is
recognized. It is not a reason to move the pivot.

**Both cost-of-equity bases are shown.** The engine currently carries two real costs of
equity: a flat long-run rate of 5.4881 percent, and a year-by-year company history that
ranges from 5.89 to 10.26 percent over this period. That divergence is a known open item in
the house conventions. Rather than choose silently, the study reports the spread on both. The
conclusion — that Apple's repurchases moved from a clearly positive spread in the 2010s to a
clearly negative one in the 2020s — holds on either basis; only the crossover year moves.

### 4.4 Return on incremental capital

    return on incremental operating capital = change in after-tax operating income
                                              / change in net operating assets

where net operating assets equals common equity plus net financial obligations, and net
financial obligations equals gross borrowings less cash, short-term investments and long-term
marketable securities.

**Annual ratios are not reported, and the reason generalizes.** A company whose net
operating assets are small, negative, or moving in the opposite direction to earnings will
produce annual ratios that are meaningless or infinite. Apple's net operating assets were
negative in nine of the thirteen years of this period. The measure is therefore computed over
multi-year windows with a guard, and the fact is reported instead of a number when the guard
fires.

**The guard is two-sided, amended in version 2.** Suppressing only a negative change in net
operating assets is not enough. A change that is positive but trivially small relative to the
capital base produces a ratio just as meaningless and far more likely to be believed. Home Depot's
fiscal 2013 to fiscal 2019 window moved net operating assets by −$533 million on a base of about
$26 billion and was correctly suppressed; the identical drift in the other direction would have
printed a return of roughly two thousand percent with no warning. **The guard must test the
magnitude of the denominator against the capital base, not merely its sign.**

**Acquisitions.** A return on incremental capital struck across a window containing a material
acquisition measures the acquisition, not reinvestment in the existing business. Home Depot's
fiscal 2019 to fiscal 2025 window is dominated by SRS Distribution and by lease liabilities
recognized on adoption of the leases standard. Such windows must be flagged.

Because a change in the statutory tax rate moves after-tax operating income without any
change in the business, the measure is also reported holding the effective tax rate at the
opening year's level. For Apple the 2017 tax act moves the answer by thirty
percentage points, so reporting only one of the two would be misleading.

### 4.5 Internal rate of return on the repurchase program

Each year's repurchase cash is an outflow at the fiscal-year midpoint. Dividends that the
retired shares would have received are inflows, because the company genuinely keeps that
cash. The accumulated retired shares are valued at a terminal date. Three terminal
valuations are reported and they answer three different questions.

**Market.** The shares are worth the market price. This is exactly the money-weighted return
of an outside investor who bought the stock on the company's own schedule with the company's
own dollars. It measures the stock, not the management.

**At the multiple paid.** Each tranche is valued at terminal earnings times the multiple the
company itself paid for it. This strips out every point of re-rating and isolates the return
that came from earnings rather than from the market's willingness to pay more for them. This
is the measure James named the fundamental internal rate of return, and it is the more
informative of the two.

**At Neutral Value.** The shares are valued at Neutral Earnings Power capitalized at the
real cost of equity — that is, assuming no abnormal earnings growth from the terminal date
forward. This is a floor case, and it is the variant that speaks to whether the shares were
bought below what they were worth rather than whether the buyer got lucky on the multiple.

Both nominal and real versions of the market variant are reported. Where a company's
repurchases begin part-way through the requested lookback, the shorter windows collapse into
the longer one and the report says so rather than presenting duplicate rows as if they were
independent results.

**Break-even.** The terminal price at which the program exactly earns the real cost of
equity plus expected inflation. It converts the evaluative question into a single number the
reader can judge without being told what the shares are worth.

### 4.6 Timing, decomposed

Comparing the dollar-weighted multiple paid against the average market multiple conflates
two different skills. The study separates them.

**Execution within the year** is the equal-weighted average multiple paid across years
against the equal-weighted average market multiple across the same years. It asks whether
the company bought at good prices inside each year.

**Allocation across years** is the dollar-weighted average multiple paid against the
equal-weighted average multiple paid. It asks whether the company spent more when the shares
were cheaper.

The two are near-independent and a company can be good at one and bad at the other. Apple is good
at execution and poor at allocation; Home Depot is mildly good at both. Reporting only the combined
figure hides which is which. Note also that comparing prices rather than
multiples is biased in any company whose earnings grew, which is why the test is run on the
multiple.

### 4.7 Dilution offset

Shares issued under equity plans as a percentage of shares retired, and the market value of
those shares as a percentage of repurchase spending. This is the number that separates
returning capital from paying employees in stock and buying it back, and for many companies
it is the whole story.

**At or above one hundred percent the correct description is not a repurchase program at all**, and
the report must say so in those words rather than printing a percentage and leaving the reader to
notice.

### 4.8 The grant-versus-delivery wedge

Share-based pay is charged to earnings at grant-date fair value. What continuing
shareholders actually give up is the market value of the shares delivered, plus the cash the
company pays for employee withholding taxes, less any proceeds received from employees:

    economic cost = shares delivered x market price + withholding tax paid - employee proceeds

The difference between that and the accounting charge is real, and it is not an additional
expense — expensing at grant-date value is correct accounting, and charging the offsetting
repurchase again would be double counting. What the wedge measures is the amount by which
share-price appreciation between grant and delivery transferred value from continuing
shareholders to employees, over and above what the accounts recorded.

**Only the cumulative figure is meaningful.** Awards delivered in a year were expensed over
prior years, so any single year compares unrelated cohorts. Even cumulatively, the opening
and closing stocks of unvested awards do not cancel exactly. The annual column is published
as indicative and the multi-year total is the number to read.

**A missing component must be declared.** Home Depot does not tag the withholding-tax element at
all, and the calculation as written substituted zero and said nothing. On Apple the same line is
$45.8 billion. The wedge must not be published where a component is unavailable.

### 4.9 The Real Capital Base and the return on retained earnings

Added in version 2, from the capital-decomposition addendum.

**Net-buyback restoration.** Reported return on equity rises as the equity base is consumed by the
repurchases themselves, so for a large repurchaser it measures how much capital has left rather
than how well capital is employed. Adding back repurchase cash net of equity plan proceeds, and
accumulating, gives the Real Capital Base. This is the same operation the project performs on the
index. Treating a repurchase as an acquisition instead — capitalizing it with the excess over the
retired shares' book value in a goodwill-like account — lands on the same total, because acquisition
accounting adds the whole purchase price to the asset side and leaves equity unchanged. For Apple
92 percent of the restoration is premium over book in any case, so the labelling barely matters.

The restored series must carry a reporting guard for its opening window: the first two years sit on
a base that has barely begun to accumulate and their ratios are artifacts, not evidence of decline.

**Return on retained earnings.** Money spent retiring shares is retained, not distributed — it never
left shareholders as a group, it was recycled among them — so retained earnings per share is
earnings per share less dividends per share. Only the full-period figure is published. Annual
figures run from −14.0 percent to +84.4 percent on Apple and are negative in five of thirteen years,
and carry no signal for any company whose earnings are at all cyclical.

The measure is verified through the house identity, abnormal earnings growth equals the retention
rate times the excess of the return on retained earnings over the cost of equity, against the
entity-level cum-dividend series computed independently. On Apple the two give 5.49 and 5.46 percent
a year.

---

## 5 · What the study deliberately does not do

**It does not estimate Intrinsic Value.** It reports Neutral Value from the engine, the
price, the break-even, and what the price paid implies. The reader judges.

**It does not attribute the company's own multiple expansion to the repurchase.** A shrinking
float plausibly supports a higher multiple through flow effects, but the magnitude is not
identifiable from this data and no defensible number can be produced. It is stated as a
limitation rather than estimated.

**It does not change the engine's normal-earnings benchmark.** The ex-ante benchmark that
charges every capital source is the change that actually corrects valuation, and it is gated
work: it rewrites the heart of the AEG form and must be re-threaded through all four legs of
the value tie, and it depends on un-freezing the share count in Equity mode first. See
`claude/AEG-Capital-Attribution-SPEC-2026-08-08.md`. Everything in this study is ex-post
disclosure and moves no valuation numbers.

---

## 6 · Applying this to another company

**Rewritten in version 2 against an actual second-company run.** The template was exercised end to
end on The Home Depot and probed on Salesforce on 2026-08-09. Full detail, with the code, is in
`Template-Exercise-FINDINGS-2026-08-09.md`. Nine defects were found. **The template is not settled
and no company report should be generated from it until the first five are closed and the Home Depot
run is repeated against the fixed version.**

The pieces that are company-specific and must be re-derived: the central index key, the
cumulative split factors and their dates, the fiscal-year-end month and therefore the
mapping of calendar months to fiscal years, the first year of material repurchase
activity, the consumer price index deflator on that company's own fiscal calendar, and the real cost
of equity. The pieces that carry over unchanged: every identity, every measure and
every guard. **Tag names do not carry over** — see below.

**The nine defects, in priority order.**

1. `parse_concept()` scans only the `USD` and `shares` unit buckets, and diluted earnings per share
   is filed under `USD/shares`. The template therefore returns an empty earnings-per-share series
   for *every* company, silently disabling the earnings-per-share attribution, the multiple paid,
   the market multiple and the whole timing test. Apple hid this because that build read earnings
   per share from the engine's committed files instead. This is the most serious finding.
2. When no year has an observable issuance rate, the fallback is silently set to zero and the
   explanatory note is not emitted. Shares retired then collapses to the net reduction in shares
   outstanding and the dilution offset reads 0.0 percent — for exactly the companies where dilution
   is the whole story. On Salesforce this produced an implied average price of $869.89 a share for
   fiscal 2025 against a stock whose highest trade that year was $369.00.
3. Where observations do exist, the plain mean across all of them is the wrong default when they are
   all recent and the series trends. On Home Depot it produced a 23 percent overshoot in fiscal
   2013. Take the rate from the earliest observable years and say so.
4. The `TreasuryStockSharesAcquired` fallback is documented in the tag table and never applied. Any
   company using treasury accounting returns an empty study. Home Depot is one.
5. One tag name per quantity is not enough. Home Depot needed two different pretax-income tags to
   cover its window, and a completely different debt assembly —
   `LongTermDebtAndCapitalLeaseObligations` plus its `Current` variant plus `CommercialPaper`. The
   tags the Apple build used return two years out of eighteen. Every quantity needs an ordered
   alternates list and a loud failure on short coverage.
6. The sign guard on the return on incremental capital is one-sided. See section 4.4.
7. A missing component is silently zero, in the compensation wedge and elsewhere. See section 4.8.
8. `fy_end_price()` assumes a September-like fiscal year and returns nothing for a January year end.
   It must be derived from the same mapping `fiscal_months()` uses.
9. No reporting path exists for a dilution offset at or above one hundred percent. See section 4.7.

**The underlying rule behind six of the nine: a missing input must never be silently treated as
zero, and an estimated input must always be announced.**

**Fiscal-year labelling.** The parser keys a filing by the calendar year in which the fiscal year
ends, so Home Depot's fiscal 2024 — closing 2 February 2025 — is carried as label 2025. Everything
downstream is consistent with that and no number is wrong, but every year is labelled one higher
than the company labels it. The template must carry a display offset alongside the internal key,
and any published table must state which convention it is on.

**What worked and should not be disturbed.** The split machinery: Home Depot's factors all evaluated
to exactly one and Apple's twenty-eight did not leak. The fiscal-month mapping, on a
February-to-January year. And above all the traded-range validator, which was the only thing that
caught defects 2 and 3, on two different companies, in two different code paths.

---

## 7 · Verification record

Reconciled two independent ways before any interpretation was written, per house convention
section 6:

- Derived shares retired reproduce the observed change in shares outstanding by
  construction, and the implied average price paid independently reproduces the market price
  to within one percent in six of the eight years where retirement counts are filed rather
  than derived.
- The operating and financial split of net income reconciles to reported net income exactly
  in every year, by construction from pretax income, operating income and the tax provision.
- Total shares retired over the program equals the observed net reduction in shares
  outstanding plus total shares issued, exactly.
- The sources and uses statement reconciles cumulative free cash flow, dividends, employee
  tax payments and repurchases to the observed change in the net financial position, with a
  residual attributable to items not separately modelled.

Added in version 2:

- The equity roll-forward closes to $4,670 million on $816,311 million of repurchases, a residual of
  0.57 percent, and the identical magnitude appears with the opposite sign on the uses side of the
  sources-and-uses statement. That agreement is the check.
- Gross borrowings from Securities and Exchange Commission tags reconcile with cumulated net debt
  issuance from the cash flow statement to 0.15 percent, $98,657 million against $98,810 million.
  The same check on the vendor total-debt line fails by twelve percent, which is how the vendor
  definitional break was found.
- The change in net financial obligations from balance-sheet endpoints equals gross debt raised less
  the change in financial assets, exactly.
- The Real Capital Base at fiscal 2025 computed by restoration equals the same figure computed by
  rolling opening equity forward with earnings, dividends and employee equity only — the repurchase
  line drops out — to the dollar.
- The return on retained earnings is confirmed by two independent routes, the house identity at 5.49
  percent a year and the entity-level cum-dividend series at 5.46 percent.
- Forty automated checks run in `code/verify.py` against the generated document itself, so a figure
  in the published text that drifts from its computed source fails the build.

**Open.** The two coexisting real costs of equity are disclosed rather than resolved. The
cash-versus-accrual timing difference in years containing accelerated share repurchases is
disclosed rather than adjusted. The vendor total-debt break is corrected in this study but not in
the engine, where it still contaminates `AAPL_dupont.csv` from fiscal 2024 forward.
