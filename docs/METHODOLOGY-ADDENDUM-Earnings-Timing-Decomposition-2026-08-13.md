# Methodology addendum: the earnings-timing decomposition of the entry effect

**2026-08-13. Approved by James Kostohryz before it was built. Supersedes item 1 of
`00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md`, which proposed a suppression rule.
That proposal is withdrawn, and section 2 below says why.**

## 1. The defect

The entry effect on a repurchase tranche is

```
entry[t] = shares_retired[t] x (real_eps[t+1] - rho x real_price_paid[t])
```

The price paid is a transacted fact. The earnings figure is one accounting year, selected for no
reason other than that it follows the purchase, and it carries the entire verdict on that purchase.

On a company whose earnings move with a cycle this inverts the measure. At a cycle peak the market
applies a low multiple to peak earnings, so the forward earnings yield at the price paid runs high
and the entry effect prints large and positive — flattering a repurchase made at the top. At a
trough the reverse happens and a well-timed purchase is condemned. Left alone, the measure
systematically praises the worst-timed repurchase programs in the market and condemns the best.
Apple's earnings are comparatively smooth, which is the only reason the defect went unnoticed as
long as it did.

## 2. Why suppression was the wrong instrument, and is withdrawn

The 2026-08-12 addendum proposed suppressing the entry effect for any tranche whose earnings anchor
sat far from the valuation engine's own sustained-trend level, on the expectation that the rule
would barely fire on Apple. It was built and measured before anything landed. At the engine's own
fifteen percent threshold it fires on **six of Apple's thirteen years** — fiscal 2013, 2014, 2015,
2021, 2022 and 2025.

A repurchase account that silently drops six of thirteen tranches is not an account of the eight
hundred and sixteen billion dollar program, and no threshold rescues it: fiscal 2013 and 2014 read
eighty-three and one hundred thirty-two percent off-trend at any window, purely because their
lookback reaches into the 2009 to 2012 period when Apple's earnings were compounding at rates the
later business never repeated. James ruled that no year and no repurchase may be excluded from the
study. That ruling is correct and this addendum implements it.

## 3. What replaces it: an exact decomposition

Split the published entry effect into the part attributable to the price paid and the part
attributable to which year happened to follow:

```
entry[t]    = decision[t] + timing[t]

decision[t] = shares[t] x (trend_eps[t+1] - rho x real_price_paid[t])
timing[t]   = shares[t] x (real_eps[t+1]  - trend_eps[t+1])
```

The properties that matter, each of them tested in `code/verify.py` rather than asserted here:

**It is an identity, not an adjustment.** The two components sum to the entry effect exactly, in
every row and in total, under every trend estimator. The residual is at floating-point zero.

**No tranche and no year is removed.** All thirteen repurchase years remain in the account at their
reported figures.

**No published figure moves.** The decomposition describes what is already inside the entry effect.
Every number published before this addendum is unchanged, including the cumulative entry effect of
plus four point five six billion dollars and the break-even real cost of equity of five point nine
nine percent.

**Neutral Earnings Power never enters the entry effect.** The trend level used here is a descriptive
statistic of realized earnings, computed after the fact. It is not Neutral Earnings Power, it is not
a forecast, and it enters no valuation anywhere in this study. That distinction is deliberate: the
prior work order forbade substituting Neutral Earnings Power into the entry effect, because doing so
would change what the measure means, and this addendum does not do it.

**The timing component is rate-agnostic by construction.** It is shares times an earnings
difference. It contains no cost of equity, hard-codes no rate, and cannot be tuned by an argument
about the capitalization rate. `verify.py` recomputes it at three times the engine rate and confirms
it does not move.

## 4. The trend level is not point-identified, and that is a published result

Two families of estimator are defensible and they disagree on the **sign** of the price-decision
component on Apple.

| Family | Estimators | Decision component | Decision break-even |
|---|---|---|---|
| Symmetric | log-linear fit, centered geometric mean at plus or minus two and three years | +3.55 to +3.88 bn | 5.88% to 5.92% |
| Backward-looking | the valuation engine's own normalizer at four, six and eight year windows | −1.79 to −4.48 bn | 4.99% to 5.29% |

The engine rate is 5.4881 percent, so the symmetric family puts the price decision positive and the
backward-looking family puts it negative.

The cause is fiscal 2021 and it is worth being exact. Apple's real earnings per share went from 4.24
to 6.94 that year and stood at 7.77 in fiscal 2025. **The jump did not revert.** A backward-looking
estimator standing in 2021 has no way to know that, and reads a durable step in the level of the
business as a spike far above trend.

**The ruling, and it departs from the prior work order.** The prior addendum directed that the
valuation engine's own normalizer be used. On examination that is the wrong tool for this job, and
saying so plainly is more useful than building it quietly. The engine's normalizer is backward-only
*by design* — it lives at the end of a forecast, where there is no future to look at, and being
backward-only is correct there. That constraint does not bind on a study of what already happened,
where the whole question is whether an earnings year turned out to be representative and four
further years of reported earnings are in hand. The symmetric family is therefore primary and the
backward-looking family is published alongside it.

Both are always reported as a band. A point estimate would conceal the disagreement, and the
disagreement is the finding. This follows the convention the study already uses for the cost of
equity, where two readings are published, provenance is stated, and the study declines to choose.

**Estimator choice, and its disclosed weakness.** The log-linear fit is primary because it has no
edge effect: it is defined at every year including the last. Its weakness is that it assumes one
constant real growth rate, which is a strong assumption on a company whose growth rate shifted. The
centered geometric mean makes no functional-form assumption and is the independent cross-check;
its weakness is the mirror image, since the window truncates within its half-width of either end of
the sample and degenerates toward a one-sided average there. On Apple the two agree to within nine
percent, which is what licenses presenting the symmetric reading as a single result. On the four
tranches where the centered estimator is truncated, that is disclosed in the report rather than
presented as a centered reading.

## 5. Timing dependence: the standing diagnostic

```
timing dependence = |cumulative timing| / |cumulative entry effect|
```

Read it as: how large is the accident of which years happened to follow, measured against the
headline verdict it is embedded in. Where it approaches or exceeds one hundred percent, the entry
effect is not a verdict on the price paid and must not be published alone.

It is deliberately **not** a pass/fail gate and carries no threshold in code. It reports a magnitude
and leaves the judgment to a person, which is the standing rule for anything touching the business
cycle. It is not a cycle detector: it never infers where in a cycle a year sat, and it never rules a
year in or out.

Measured so far:

| Company | Timing dependence, primary basis | Families agree on sign? |
|---|---|---|
| Apple | 15% (139% on the backward-looking basis) | **No** |
| Costco | 2% | Yes |

Apple's primary reading confirms the published conclusion by a second route: plus three point eight
eight billion dollars of the plus four point five six billion is the price decision, and the
decision break-even of five point eight eight to five point nine two percent still sits above the
engine's rate. The headline result does not depend on any single year's earnings. On the
backward-looking basis it would, and that is disclosed rather than buried.

## 6. Where it lives

`code/timing_decomposition.py` is the module and is company-agnostic. It is exercised by the Apple
build chain through `code/gen_article.py` (Exhibits 3b and 3c), by the Costco driver through
`code/full_study_COST.py`, and by ninety-eight checks in `code/verify.py`, which is gated in
continuous integration on every push.

The module re-implements the engine's `_normal_line_growth` verbatim rather than importing it, so
this repository does not depend on the engine repository. If the engine's definition changes, that
copy must be re-synced deliberately. The re-implementation is annotated with the engine commit it
was taken from.

## 7. What is not addressed here

The decomposition says how much of a verdict rests on the earnings anchor. It does not say what the
right anchor is, and on a company where both estimator families are contaminated by a cycle
occupying most of the sample, both readings will be wrong together and the spread will be
misleadingly small. That limitation is inherited from the finding document of 2026-08-11 and is not
solved by this addendum. It is stated so that nobody reads a small spread as proof of a clean
reading.
