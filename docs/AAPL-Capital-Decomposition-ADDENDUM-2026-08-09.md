# Addendum — capital decomposition, the Real Capital Base, RORE and ROIIC

**Version 2, reissued 2026-08-09. Extends `00-Buyback-Study-METHODOLOGY-2026-08-09.md`. Commissioned
by James to separate financial engineering from operating growth, to restore the equity base consumed
by repurchases, and to measure the return on incremental capital including the change in leverage.
Full numeric output in `run7_corrected.txt`; code in `code/run7_capital_decomposition.py`.**

> **VERSION 1 IS SUPERSEDED AND ITS FIGURES MUST NOT BE REUSED.** Version 1 took gross debt from the
> engine's vendor balance-sheet feed, whose "Total Debt" line changes definition in fiscal 2024 —
> it begins folding capitalized lease liabilities into total debt and does not restate the earlier
> years. Fiscal 2025 is an endpoint of this decomposition, so the series could not be differenced
> across the break. Gross borrowings are now taken from Securities and Exchange Commission tags
> throughout. What moved:
>
> | | Version 1 | Version 2 |
> |---|---|---|
> | Gross debt added | $112.4bn | **$98.7bn** |
> | Increase in net financial obligations | $101.2bn | **$87.5bn** |
> | Leverage-funded share of repurchases | 12.4% | **10.7%** |
> | EPS from leverage / from retention | $0.222 / $1.566 | **$0.192 / $1.596** |
> | Increase in net operating assets | $56.7bn | **$43.0bn** |
> | Return on incremental operating capital | 125.0% | **164.9%** |
> | Capital split, shares / business | 94.0% / 6.5% | **95.5% / 5.0%** |
> | Rolling window FY2019–25 | 95.9% | **123.7%** |
>
> Version 1 also said annual return on retained earnings is negative in four of thirteen years. It is
> **five**: fiscal 2013, 2016, 2019, 2023 and 2024.
>
> Full detail of the defect is in methodology section 2. **It is not fixed in the engine**, where the
> same feed drives `AAPL_dupont.csv` and contaminates the reformulated leverage and
> return-on-net-operating-assets series from fiscal 2024 forward. That is a defect-register item.

Abnormal earnings growth is AEG, return on retained earnings is RORE, return on incremental
invested capital is ROIIC, net operating assets is NOA, net financial obligations is NFO.

---

## 0 · The control that runs first

The equity roll-forward has to close before anything downstream is read. Opening common equity
plus earnings, less dividends and repurchases, plus share-based compensation, less cash tax on
employee awards, plus equity plan proceeds, reproduces reported closing equity to within $4.67
billion on $816 billion of repurchases — a residual of 0.57 percent, being other comprehensive
income and items not separately modelled. The same residual appears, with the same magnitude and the
opposite sign, on the uses side of the sources-and-uses statement below. That agreement is the check.

---

## 1 · Financial engineering versus operating growth

Growth in diluted earnings per share, fiscal 2012 to fiscal 2025, is $5.888. It divides:

| Channel | Per share | Share |
|---|---|---|
| Operating business | $4.159 | 70.6% |
| Share count | $1.787 | 30.4% |
| Net interest — the direct effect of leverage | −$0.058 | −1.0% |
| **Financial engineering (share count + net interest)** | **$1.729** | **29.4%** |

**The share-count channel then splits by what funded the repurchases.** Of $816.3 billion spent,
$87.5 billion came from the increase in net financial obligations and $728.8 billion from
retention. Applying that split:

| Sub-channel | Per share | Share of total EPS growth |
|---|---|---|
| Share count funded by increased leverage | $0.192 | 3.3% |
| Share count funded by retention | $1.596 | 27.1% |

**The correction this makes.** The first version of this study reported leverage's contribution
as −$0.058, essentially nil, because it measured the net interest line. That measures the wrong
thing, as James pointed out. Apple's gross borrowings went from nothing to $98.7 billion while its net
financial position fell from $121.3 billion of net financial assets to $33.8 billion. Financial
leverage — NFO over common equity — moved from **−1.03 to −0.46** on the definition used here, a rise
of 0.57 of a turn of equity, and from −0.25 to +0.65 on the engine's reformulated statements at HEAD.
The two differ in level because the engine reclassifies some securities as operating, and the
engine's closing figure additionally inherits the vendor break described above; they agree on the
direction and on the order of magnitude. **A company with no debt at all can lever up substantially
by spending its financial assets, and the interest line cannot see it.**

---

## 2 · The Real Capital Base — net-buyback restoration

James proposed treating a repurchase as an acquisition: capitalize it, with the excess over the
retired shares' book value sitting in a goodwill-like account, and recompute returns on the
restored base.

**This is the same operation the project already performs on the S&P 500 economic book under the
name net-buyback restoration, producing the Real Capital Base.** It also lands on the same total
as the acquisition analogy, because acquisition accounting adds the whole purchase price to the
asset side — net assets acquired plus goodwill — and leaves equity unchanged. The split between
the two pieces is a labelling question, and for Apple it is nearly immaterial: **92 percent of
the cumulative restoration is premium over book value.**

*This section is unaffected by the version 1 correction: it uses common equity and repurchase cash
only, neither of which moved.*

| Fiscal year | Reported equity $m | Real Capital Base $m | Reported ROE | ROE on Real Capital Base |
|---|---|---|---|---|
| 2013 | 123,549 | 145,879 | 30.6% | 28.0% |
| 2016 | 128,249 | 258,786 | 36.9% | 19.1% |
| 2019 | 90,488 | 391,555 | 55.9% | 15.1% |
| 2022 | 50,672 | 597,485 | 175.5% | 17.9% |
| 2025 | 73,733 | 883,756 | 171.4% | 13.5% |

Apple's reported return on equity of 171 percent is an artifact. The denominator has been
consumed by the repurchases themselves, and the number rises as the equity base is destroyed —
it is a measure of how much capital has left, not of how well capital is employed. On the Real
Capital Base it is 13.5 percent, and the series declines steadily from 28 percent, which is the
economically informative shape.

Return on invested capital behaves the same way and worse. Reported invested capital — NOA — is
negative in nine of the thirteen years, so reported ROIC is not merely misleading but
undefined; in the four years it is positive it prints 6,133 percent, 875 percent, 1,350 percent
and 281 percent, none of which mean anything. Restoration is what makes the measure computable
at all, and it settles between 12.9 and 20.8 percent from fiscal 2019 onward.

**Reporting guard.** The first two years of the restored series, 225.0 percent and 66.6 percent, sit
on a restored base that has barely started accumulating. They are artifacts of the opening
window and must not be read as a decline in returns.

---

## 3 · Return on retained earnings

Money spent on repurchases is retained — it never left shareholders as a group, it was recycled
among them — so retained earnings per share is earnings per share less dividends per share. Real
terms, 2026 dollars.

Over the full period, cumulative growth in real earnings per share of $5.469 against cumulative
retained real earnings per share of $44.405 gives **RORE of 12.32 percent** against a real cost
of equity of 5.49 percent, at a retention rate of 0.804.

**Two-route verification, as house convention section 6 requires.** The house identity
AEG = b × (RORE − cost of equity) gives 0.8040 × (12.32% − 5.49%) = **5.49 percent a year**.
Computed the other way, from the entity-level cum-dividend AEG series built in stage 6, real
abnormal earnings growth averaged $4,599 million a year on average real net income of $84,278
million — **5.46 percent a year**. Two independent routes, agreeing to three basis points. (It
is a coincidence that the first figure lands on the same number as the cost of equity.)

**Reporting guard.** Annual RORE runs from −14.0 percent to +84.4 percent and is negative in **five**
of thirteen years — fiscal 2013, 2016, 2019, 2023 and 2024. *Version 1 said four; that was a
miscount.* Single-year RORE carries no signal for any company whose earnings are at all cyclical.
Only the full-period figure should be quoted.

---

## 4 · Incremental capital: sources, uses and returns

| Sources of incremental capital, FY2013–FY2025 | $m |
|---|---|
| Retained earnings (net income less dividends) | 718,331 |
| Increase in net financial obligations | 87,488 |
| Share-based compensation (non-cash equity) | 88,317 |
| Less cash tax on employee equity awards | (45,772) |
| Equity plan proceeds | 6,288 |
| **Total** | **854,652** |

| Uses | $m | Share |
|---|---|---|
| Share repurchases | 816,311 | 95.5% |
| Increase in net operating assets | 43,011 | 5.0% |
| Unreconciled (matches the equity roll-forward residual) | (4,670) | −0.5% |

**Returns on each slice.**

*The operating slice.* After-tax operating income rose $70,939 million on $43,011 million of
incremental net operating assets — **164.9 percent**, or 135.4 percent holding the effective tax
rate at its fiscal 2012 level. On rolling six-year windows: fiscal 2015 to 2021, 219.5 percent;
fiscal 2019 to 2025, 123.7 percent; fiscal 2012 to 2018 suppressed, because net operating assets
fell by $12.4 billion and the ratio has no meaning.

*The repurchase slice.* Its return does not appear in operating income at all — it accrues per
share. At the dollar-weighted multiple paid of 22.34 times, the entry earnings yield is **4.5
percent**, and the full internal rate of return analysis is in the main study.

*Not a blended return.* Dividing the growth in after-tax operating income by all capital
deployed gives 8.3 percent, and that figure must be labelled carefully: the repurchase slice
produces no operating income by construction, so this is not a return on total capital. Read it
as how little operating growth the total capital deployment bought — which is the point, not a
defect of the measure.

**The finding, in one line.** Ninety-six percent of Apple's incremental capital went into its own
shares at an entry earnings yield of about four and a half percent, while the five percent that went
into the business earned over a hundred and sixty.

---

## 5 · Two methodological points recorded

**Double counting, declined.** James proposed adding retained earnings plus the increase in leverage
to the internal rate of return on the repurchases. That specific step would double count: the
repurchase internal rate of return already uses the full cash actually spent, whatever funded it, so
adding the funding sources on top would charge the same dollars twice. The substance of the request
is right and is delivered above as a separate measure — the return on all incremental capital, with
the sources enumerated and the uses split between the repurchase and the operating business. The two
measures answer different questions and both are reported.

**Two averages, two names.** The average price Apple paid is $62.12 per share retired, being total
cash over total shares retired, which is weighted by **shares**. Weighted by **dollars** — each year
weighted by the money actually spent in it — the average price paid is $114.08. Version 1 of the
findings document called the first figure "dollar-weighted," which it is not, and set it beside the
dollar-weighted multiple of 22.34 times as though the two were a matched pair; they imply earnings
per share of $2.78, which is no year Apple ever had. Both averages are correct and they answer
different questions. The gap between them is the program in one number: Apple spent 54 percent of its
dollars in the last five fiscal years and bought 20 percent of the shares with them.

---

## 6 · Carried forward

These results are folded into `Buyback-Study-AAPL.html` as of 2026-08-09, in sections 7 through 10
and exhibits 6 through 8, with forty automated checks in `code/verify.py` that fail the build if a
published figure drifts from its computed source.

Still open: the vendor total-debt break is corrected in this study but not in the engine. The two
coexisting real costs of equity are disclosed rather than resolved. Cash-versus-accrual timing on
accelerated share repurchases is disclosed rather than adjusted.
