# Apple share repurchase study — findings

**Version 2, corrected 2026-08-09. Companion to `00-Buyback-Study-METHODOLOGY-2026-08-09.md` and
`Buyback-Study-AAPL.html`. Fiscal years 2013 through 2025. All figures computed from Securities
and Exchange Commission XBRL primary source plus the engine's committed outputs at HEAD.**

> **Corrections against version 1, both made 2026-08-09.**
>
> 1. Version 1 said "the dollar-weighted average price paid was $62.12." **Wrong label.** $62.12 is
>    total cash over total shares retired, which is weighted by **shares**. The **dollar**-weighted
>    average price paid is **$114.08**. Both are correct measures of different things and the study
>    now reports both.
> 2. Gross debt came from the engine's vendor balance-sheet feed, whose total-debt line changes
>    definition in fiscal 2024. Gross borrowings added are **$98.7 billion**, not $112.4 billion; the
>    increase in net financial obligations is **$87.5 billion**, not $101.2 billion. See methodology
>    section 2 and the reissued capital-decomposition addendum.

## The data problem that had to be solved first

The vendor cash-flow feed in the repository cannot support this study. In
`outputs/AAPL_reported_cf.csv` the line labelled "Repurchase of Capital Stock" is, for every year
through the early 2000s, the negative absolute value of the "Net Common Stock Issuance" line above
it — so a year of net issuance appears as a repurchase. Gross issuance is populated for four years
out of forty. The study was rebuilt on the SEC XBRL company-concept interface, which is free, needs
no key, and carries shares actually retired. That permitted the central measure of the whole study:
the true average price paid, being cash divided by shares retired, with no proxy.

A second vendor line had to be rejected later. The balance-sheet "Total Debt" row agrees with primary
source to the dollar for fiscal 2012 through 2021 and then begins folding capitalized lease
liabilities in, from fiscal 2024, without restating the earlier years. Since fiscal 2025 is an
endpoint, the series could not be differenced across the break. Gross borrowings now come from
`LongTermDebtNoncurrent` plus `LongTermDebtCurrent` plus `CommercialPaper`.

Apple did not tag shares retired for fiscal 2014 through 2017. Those years are derived from the
share-count identity and validated two ways; see methodology section 3. The validation is strong —
in the eight years where retirement counts are filed rather than derived, the implied average price
paid independently reproduces the fiscal year's mean market price to within about one percent in six
of them.

## Headline findings

**Earnings per share grew at 12.71 percent a year; net income grew at 7.89 percent.** The share
count accounts for $1.79 of the $5.89 increase in earnings per share, or 30.4 percent.

**Apple spent $816.3 billion retiring 13,140 million shares, 43.8 percent of the fiscal 2012
count.** It paid **$62.12 for each share it retired** — total cash over total shares, weighted by
shares. Weighted instead by where the money went, the average price paid is **$114.08**, struck at
22.3 times trailing earnings. The gap between the two is the program in one number: 54 percent of the
dollars were spent in the last five fiscal years and bought 20 percent of the shares.

**The immediate return fell by more than half.** The forward real earnings yield on each year's
repurchases ran 9.1 percent in fiscal 2013 and 3.8 percent in fiscal 2024. Against the engine's flat
long-run real cost of equity of 5.4881 percent the spread turns negative in fiscal 2021; against the
company's own year-by-year real cost of equity history it turns negative earlier. The sign change is
robust to which rate is used; the crossover year is not. Both are disclosed.

**The internal rate of return depends almost entirely on the terminal valuation.** Over the full
program, valuing retired shares at the fiscal 2025 market price gives 25.4 percent nominal and 21.7
percent real. Holding each tranche at the multiple Apple itself paid gives 18.8 percent. Valuing at
Neutral Value gives 12.1 percent. Over the last five years alone the same three read 17.4 percent,
0.0 percent and −16.2 percent. **Strip out re-rating and the recent program returned nothing.**

**Break-even.** For the whole program Apple's shares needed to be worth $86.92 at fiscal 2025 year
end to clear the long-run real cost of equity plus two and a half points of inflation. They traded
at $254.63. For the last five years the break-even is $202.87 — 26 percent below the actual price,
and the entire margin sits in the multiple.

**Timing splits in two, and Apple is good at one half and poor at the other.** Execution inside each
year was slightly better than the market: 19.90 times paid against a 20.14 times market average, an
edge of 1.2 percent. Allocation across years was poor: the dollar-weighted multiple paid is 22.34
times, 12.2 percent above the equal-weighted figure, because Apple spent progressively more as the
shares got more expensive. Reporting only the combined figure hides which is which.

**Dilution offset is modest.** Net shares issued under employee plans were 12.3 percent of shares
retired and 13.5 percent of dollars spent. Roughly 86 percent of the program was a genuine return of
capital rather than an absorption of dilution.

**The grant-versus-delivery wedge is large and appears in no account.** The market value of shares
delivered to employees, plus cash paid for their withholding taxes, less proceeds received from
them, comes to $149.8 billion against $88.3 billion charged to earnings — a factor of 1.70 and a
wedge of $61.5 billion, or 6.9 percent of cumulative net income. This is not an unrecorded expense:
expensing at grant-date value is correct and charging the offsetting repurchase again would be
double counting. It measures value transferred by share-price appreciation between grant and
delivery, over and above what the accounts recorded. Only the cumulative figure is meaningful.

**Where the money came from.** $728.8 billion, or 89 percent, was current retention after $175.1
billion of dividends. The balance came from the balance sheet: the net financial position went from
$121.3 billion of net financial assets to $33.8 billion, and gross borrowings from nothing to $98.7
billion. That contribution is non-repeatable by construction. Leverage must be read twice — its
direct earnings contribution is −$0.06 of the $5.89 of earnings-per-share growth, essentially nil,
because rising interest expense cancelled forgone interest income; through the repurchases it
financed it contributed +$0.19, or 3.3 percent. A study reporting only the direct effect would record
leverage as a small negative when its actual contribution was a positive three times larger in
magnitude. Pre-2018 borrowing was a workaround for trapped offshore cash rather than a capital
structure decision, and reading it otherwise misreads it.

**The number that reframes the argument.** Between fiscal 2012 and fiscal 2025 Apple's after-tax
operating income rose $70.9 billion while net operating assets rose $43.0 billion — a return on
incremental operating capital of **164.9 percent**, or 135.4 percent holding the tax rate at its 2012
level. Annual ratios are suppressed because Apple's net operating assets were negative in nine of the
thirteen years; a template computing this annually without a guard will emit nonsense on many
companies.

**The capital split that makes it land.** Of $854.7 billion of incremental capital, **95.5 percent
went into Apple's own shares** at an entry earnings yield of about 4.5 percent, and the 5.0 percent
that went into the business earned 164.9 percent.

**The capital base is an artifact and has to be restored.** Reported return on equity of 171 percent
rises as the equity base is consumed by the repurchases themselves. On the Real Capital Base — net
buyback restoration — it is 13.5 percent, declining from 28.0 percent in fiscal 2013. Reported
invested capital is negative in nine of thirteen years, so reported return on invested capital is
undefined rather than merely misleading.

**Return on retained earnings is 12.32 percent** real over the full period against a 5.4881 percent
real cost of equity at a retention rate of 0.804, verified two independent ways at 5.49 and 5.46
percent a year. Annual figures run from −14.0 to +84.4 percent and are negative in five of thirteen
years, so only the full-period figure is published.

## Engine anchor, read from HEAD

`outputs/AAPL_summary.csv`, run vintage 2026-08-09: Neutral Value $115.46 per share, being Neutral
Earnings Power of $6.34 capitalized at a real cost of equity of 5.4881 percent, a Neutral P/E of
18.2 times. Against the $326.16 real price at that run, the shares traded at 51.5 times Neutral
Earnings Power, a 182 percent premium to Neutral Value. The generator now reads this file at build
time rather than carrying the figures as constants.

## What was deliberately not done

No estimate of Intrinsic Value is stated. No attribution of Apple's own multiple expansion to float
shrinkage is attempted — it is not identifiable from this data. The engine's normal-earnings
benchmark is unchanged; this is ex-post disclosure and moves no valuation numbers. The ex-ante
benchmark that charges every capital source remains gated work, per
`claude/AEG-Capital-Attribution-SPEC-2026-08-08.md`.

## Open items

The two coexisting real costs of equity are disclosed rather than resolved. Cash-versus-accrual
timing on accelerated share repurchase agreements is disclosed rather than adjusted. The vendor
total-debt definitional break is corrected in this study but not in the engine, where it still
contaminates `AAPL_dupont.csv` from fiscal 2024 forward.

## Next

The template has now been exercised on Home Depot and probed on Salesforce; nine defects are recorded
in `Template-Exercise-FINDINGS-2026-08-09.md` and methodology section 6. It is not settled and no
company report should be generated from it until the first five are closed.
