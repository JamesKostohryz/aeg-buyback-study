# -*- coding: utf-8 -*-
"""The earnings-timing decomposition of the entry effect.

WHAT PROBLEM THIS SOLVES
------------------------
The entry effect on a repurchase tranche is

    entry[t] = shares_retired[t] * (real_eps[t+1] - rho * real_price_paid[t])

The price paid is a transacted fact. The earnings figure is a single accounting year,
selected only because it happens to follow the purchase, and it carries the whole verdict.

On a cyclical company that inverts the measure. At a cycle peak the market applies a low
multiple to peak earnings, so the earnings yield at the price paid is high and the entry
effect prints large and POSITIVE -- praising a repurchase made at the top. At a trough the
reverse. The measure systematically praises the worst-timed repurchases and condemns the best.

WHAT THIS MODULE DOES, AND WHAT IT REFUSES TO DO
------------------------------------------------
It SPLITS the entry effect. It does not correct it, replace it, or drop any tranche.

    entry[t] = decision[t] + timing[t]

    decision[t] = shares[t] * (trend_eps[t+1] - rho * real_price_paid[t])
    timing[t]   = shares[t] * (real_eps[t+1]  - trend_eps[t+1])

The two sum to the published entry effect exactly, by construction -- it is an identity,
not an adjustment. Every tranche and every year stays in the account. No published figure
moves. Neutral Earnings Power never enters the entry effect.

`timing[t]` contains NO interest rate. The cyclicality diagnostic is therefore rate-agnostic
by construction, and hard-codes no rate anywhere in this file.

THE TREND LEVEL IS NOT POINT-IDENTIFIED, AND THAT IS A PUBLISHED RESULT
----------------------------------------------------------------------
Defensible trend estimators fall into two families that can disagree on the SIGN of the
decision component. This is structural, not noise:

  * BACKWARD-LOOKING estimators (the engine's own normalizer, any window) stand at t+1 and
    look only backward. They are built for the END OF A FORECAST, where no future data
    exists by definition.
  * SYMMETRIC estimators (log-linear fit, centred geometric mean) use the whole realised
    path, including what came after.

On an EX-POST study the backward-only constraint does not bind: we have the future, and the
question being asked is precisely whether an earnings year turned out to be representative.
Apple is the worked case -- its FY2021 earnings jump did NOT revert (real EPS 4.24 -> 6.94 in
2021, still 7.77 in 2025), so a backward estimator standing in 2021 labels a durable step
change as a ~50%-above-trend spike. The symmetric family is therefore taken as PRIMARY here
and the backward family is reported alongside, never suppressed.

Both families are always computed and both are published as a band. Reporting a point
estimate would conceal the disagreement, which is itself the finding.
"""
import math
import statistics

__all__ = ["trend_loglinear", "trend_centered", "trend_engine_normalizer",
           "SYMMETRIC_ESTIMATORS", "BACKWARD_ESTIMATORS", "ALL_ESTIMATORS",
           "decompose", "decomposition_band", "timing_dependence", "break_even_rate"]


# --------------------------------------------------------------- trend estimators
def trend_loglinear(eps, years=None):
    """PRIMARY (symmetric). Least-squares fit of log(eps) on the year index, over the whole
    window, evaluated at any year.

    One fitted growth rate, no window to choose, no truncation at either end of the sample --
    unlike a centred average, it is defined at every year including the last. Assumes a single
    constant real growth rate, which is its weakness on a company whose growth rate shifted;
    `trend_centered` is the independent cross-check that does not make that assumption.

    Returns a callable, plus the fitted annual growth rate for disclosure.
    """
    ys = sorted(years if years is not None else eps)
    ys = [y for y in ys if eps.get(y) is not None and eps[y] > 0]
    if len(ys) < 3:
        raise ValueError("log-linear trend needs at least three positive observations; "
                         f"got {len(ys)}. Do not silently fall back -- report the shortfall.")
    lg = [math.log(eps[y]) for y in ys]
    n = len(ys)
    mx = sum(ys) / n
    my = sum(lg) / n
    denom = sum((x - mx) ** 2 for x in ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(ys, lg)) / denom
    icpt = my - slope * mx
    fn = lambda N: math.exp(icpt + slope * N)          # noqa: E731
    fn.growth = math.exp(slope) - 1.0
    fn.n_obs = n
    fn.span = (ys[0], ys[-1])
    return fn


def trend_centered(eps, k=3):
    """CROSS-CHECK (symmetric). Geometric mean of real earnings over [N-k, N+k].

    Makes no functional-form assumption. Its weakness is the mirror of the log-linear's: the
    window TRUNCATES within k years of either end of the sample, where it degenerates toward a
    one-sided average. `decompose` records, per tranche, whether the window was full or
    truncated, so a truncated reading is never presented as a centred one.
    """
    def fn(N):
        w = [eps[y] for y in range(N - k, N + k + 1) if eps.get(y) is not None and eps[y] > 0]
        if not w:
            raise ValueError(f"no positive earnings observations in [{N-k}, {N+k}]")
        return math.exp(sum(math.log(v) for v in w) / len(w))
    fn.k = k
    fn.is_truncated = lambda N: any(
        (y not in eps or eps.get(y) is None) for y in range(N - k, N + k + 1))
    return fn


def _normal_line_growth(eps, N, X):
    """Verbatim re-implementation of pipeline/convergence.py::_normal_line_growth from the
    valuation engine, at commit 33a6b5a. Median year-over-year growth across the X years
    before N, with year N excluded from its own trend estimate.

    Reproduced rather than imported because this repository does not depend on the engine
    repository. If the engine's definition changes, this copy must be re-synced deliberately.
    """
    rates = []
    lo = min(eps) + 1 if eps else 1
    for t in range(max(lo, N - X + 1), N):
        a, b = eps.get(t - 1), eps.get(t)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a > 0:
            rates.append(b / a - 1.0)
    return statistics.median(rates) if rates else 0.0


def trend_engine_normalizer(eps, X=4):
    """DISCLOSED ALTERNATIVE (backward-looking). The valuation engine's own sanctioned
    normalized level: walk each of the last X years forward to N at the median trailing
    growth rate, take the median of those anchors.

    This is the quantity the engine's Gate B uses to decide whether a forecast's terminal year
    is representative. It is included because it is the sanctioned definition of the normal
    level, and it is NOT taken as primary here for the reason given in the module docstring:
    it is backward-only by design, which is correct at a forecast horizon and wrong in
    hindsight.
    """
    def fn(N):
        g = _normal_line_growth(eps, N, X)
        anc = [eps[N - a] * (1 + g) ** a
               for a in range(1, X + 1)
               if eps.get(N - a) is not None]
        return statistics.median(anc) if anc else eps.get(N)
    fn.X = X
    return fn


SYMMETRIC_ESTIMATORS = ("loglinear", "centered3", "centered2")
BACKWARD_ESTIMATORS = ("normalizer4", "normalizer6", "normalizer8")
ALL_ESTIMATORS = SYMMETRIC_ESTIMATORS + BACKWARD_ESTIMATORS


def build_estimators(eps, window=None):
    """Every estimator, keyed by name, built against one real-earnings series."""
    return {
        "loglinear":   trend_loglinear(eps, window),
        "centered3":   trend_centered(eps, 3),
        "centered2":   trend_centered(eps, 2),
        "normalizer4": trend_engine_normalizer(eps, 4),
        "normalizer6": trend_engine_normalizer(eps, 6),
        "normalizer8": trend_engine_normalizer(eps, 8),
    }


# --------------------------------------------------------------- the decomposition
def decompose(shares, real_eps, real_px, rho, tranches, trend_fn):
    """Split the entry effect into decision and timing, tranche by tranche.

    `tranches` are the repurchase years t for which real_eps[t+1] is observable. A tranche
    whose following year has not been reported is NOT given an estimated earnings figure and
    is NOT silently dropped -- it is excluded by the caller's choice of `tranches` and must be
    disclosed there, exactly as the published entry-effect table already excludes the final
    year.

    Returns per-tranche rows and totals. The identity decision + timing == entry holds to
    floating-point exactness and is asserted by the caller's verification, not assumed here.
    """
    rows = {}
    for t in tranches:
        if real_eps.get(t + 1) is None:
            raise ValueError(f"tranche {t} has no observable earnings at {t+1}; "
                             "exclude it explicitly rather than estimating one")
        tr = trend_fn(t + 1)
        entry = shares[t] * (real_eps[t + 1] - rho * real_px[t])
        decision = shares[t] * (tr - rho * real_px[t])
        timing = shares[t] * (real_eps[t + 1] - tr)
        rows[t] = {"shares": shares[t], "real_px": real_px[t],
                   "eps_next": real_eps[t + 1], "trend_next": tr,
                   "entry": entry, "decision": decision, "timing": timing,
                   "truncated": bool(getattr(trend_fn, "is_truncated", lambda n: False)(t + 1))}
    return {"rows": rows,
            "entry": sum(r["entry"] for r in rows.values()),
            "decision": sum(r["decision"] for r in rows.values()),
            "timing": sum(r["timing"] for r in rows.values())}


def break_even_rate(shares, eps_source, real_px, tranches, trend_fn=None):
    """The real cost of equity at which a cumulative effect crosses zero.

    With trend_fn None this is the published headline break-even, struck on reported earnings.
    With a trend_fn it is the decision component's own break-even. Both are closed-form roots
    of a linear function of rho, so neither is searched for.
    """
    num = sum(shares[t] * (trend_fn(t + 1) if trend_fn else eps_source[t + 1]) for t in tranches)
    den = sum(shares[t] * real_px[t] for t in tranches)
    return num / den if den else float("nan")


def decomposition_band(shares, real_eps, real_px, rho, tranches, estimators):
    """Run the decomposition under every estimator and report the range.

    A point estimate would conceal the disagreement between the symmetric and backward-looking
    families, and that disagreement is a published result rather than an inconvenience.
    """
    out = {}
    for name, fn in estimators.items():
        d = decompose(shares, real_eps, real_px, rho, tranches, fn)
        d["break_even"] = break_even_rate(shares, real_eps, real_px, tranches, fn)
        d["family"] = "symmetric" if name in SYMMETRIC_ESTIMATORS else "backward"
        out[name] = d
    return out


def timing_dependence(entry_total, timing_total):
    """|timing| / |entry|, the standing cyclicality diagnostic.

    Read it as: how large is the accident of which years happened to follow, measured against
    the headline verdict it is embedded in. Above 100% the timing accident is larger than the
    result itself, and the entry effect should not be read as a verdict on the price decision.

    Deliberately NOT a pass/fail gate and deliberately NOT thresholded here: it reports a
    magnitude and leaves the judgment to a person, which is the standing rule for anything
    that touches the business cycle.
    """
    if not entry_total:
        return float("inf") if timing_total else 0.0
    return abs(timing_total) / abs(entry_total)
