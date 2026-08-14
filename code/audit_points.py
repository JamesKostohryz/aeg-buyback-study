# -*- coding: utf-8 -*-
"""audit_points.py - the fifteen permanent audit points, run on every study.

WHY THIS EXISTS
---------------
A green light on the four hardening-endpoint criteria (docs/00-GREEN-LIGHT-
2026-08-13.md) means the template and its generic driver are trustworthy
ENOUGH TO STOP HARDENING AND START PUBLISHING. It does not mean any individual
study is trusted because it ran. The hardening-endpoint spec
(docs/00-PASTE-THIS-Hardening-Endpoint.md) requires fifteen checks - I1-I6
internal coherence, E1-E9 external coherence - on EVERY live study, forever,
with the result of each one published. This file is that implementation.

WHAT "REFUSE" MEANS HERE
-------------------------
The spec says a failing audit point "refuses the study rather than annotating
it, unless James overrides in writing and the override is recorded in the
output." This driver's own established idiom for that (see run_study.py:
`note('REFUSAL', ...)`, the module-level REF log, and the "REFUSALS,
FALLBACKS AND SUPPRESSIONS" block at the end of every run) is a NAMED, LOUD
statement plus exclusion of the tainted quantity, never a program abort - a
crash on an unfamiliar company is a defect, not a refusal, and the fleet gate
exists specifically to catch that class of failure. This file follows that
same idiom: it never raises and never calls sys.exit. It returns a structured
verdict per check, and run_study.py's driver is the one that turns a FAIL into
an unmissable "STUDY REFUSED" banner and a REFUSAL note under every affected
quantity, exactly as it already does for `study.price_failures`.

E3 is the one point the spec itself says to flag rather than refuse ("judgment
about a business cycle stays with a person") - it is scored FLAG, never FAIL,
and never triggers the refusal banner.

A check that cannot be computed from what this driver has plumbed in is scored
UNAVAILABLE, not skipped and not silently passed. "Unavailable" is itself the
answer for E6, E7 and E8 today, and the reason is stated in the detail string
rather than assumed away - see the docstring on each for exactly what would
have to be built for it to become computable.

HOW THIS RUNS WITHOUT RISK TO THE SEALED TEMPLATE
---------------------------------------------------
This module imports nothing from buyback_study_TEMPLATE.py and is called by
run_study.py's own `run()` function, AFTER `study.run()` and `entry_effect()`
have both already completed - never from inside the sealed template, and never
from anything `code/gen_article.py` touches. The Apple article is built by
`code/gen_article.py` calling `BuybackStudy` directly through `build.py`; it
never calls `run_study.run()` at all, so nothing in this file can move a
single byte of `Buyback-Study-AAPL.html`. That independence is what makes this
an additive, SAFE-adjacent change even though it changes what the CLI prints -
the four-method reasoning this project uses elsewhere does not apply here
(there is no sealed numeric tie in this repository the way there is in the
separate AEG valuation engine), but the same discipline - prove nothing that
was previously byte-identical moved - is what was actually checked before this
landed.

USAGE
    from audit_points import run_audit_points
    results = run_audit_points(study, EE, traded_range=tr)
    # results is an OrderedDict: code -> {'status', 'detail', 'would_catch'}
    # status is one of 'PASS', 'FAIL', 'FLAG', 'UNAVAILABLE'
"""
from collections import OrderedDict

import timing_decomposition as td

PASS, FAIL, FLAG, UNAVAILABLE = 'PASS', 'FAIL', 'FLAG', 'UNAVAILABLE'

# Any check whose FAIL should refuse the study rather than merely annotate it.
# Every code except E3 - the spec names E3 explicitly as the one exception.
REFUSING_CODES = ('I1', 'I2', 'I3', 'I4', 'I5', 'I6',
                   'E1', 'E2', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9')

# Shared numeric tolerances. Named here, once, rather than typed inline at
# each call site, so a future retune touches one number instead of nine.
_IDENTITY_TOL_MN = 1e-6          # I1: millions of shares, floating-point exactness
_ENTRY_REL_TOL = 1e-6            # I2/I3: relative to the scale of the entry effect
_BREAKEVEN_REL_TOL = 1e-6        # I3: closed-form vs. bisection agreement
_E4_MAX_FRACTION = 0.25          # E4: shares retired / opening shares ceiling
_E3_BAND = (0.005, 0.25)         # E3: forward real earnings yield, 0.5% to 25%
_E9_MAX_RELATIVE_GAP = 0.02      # E9: dei cover-page vs us-gaap outstanding count


def _result(status, detail, would_catch):
    return {'status': status, 'detail': detail, 'would_catch': would_catch}


# ===========================================================================
# INTERNAL COHERENCE - does the study agree with itself?
# ===========================================================================

def _I1(study):
    would_catch = (
        "any future edit to share_flows() that computes retired or issued "
        "independently instead of one as the residual of the other - the "
        "identity would stop closing silently, on some companies and not "
        "others, exactly the shape defect 25's fix was built to prevent."
    )
    S = study.shares_outstanding()
    years = sorted(set(study.retired) & set(study.issued))
    checked, fails = [], []
    for y in years:
        if y not in S or (y - 1) not in S:
            continue
        lhs = S[y - 1] - study.retired[y] + study.issued[y]
        gap = lhs - S[y]
        checked.append(y)
        if abs(gap) > _IDENTITY_TOL_MN:
            fails.append((y, gap))
    if not checked:
        return _result(UNAVAILABLE,
                        "no fiscal year has both a retired figure, an issued "
                        "figure and an opening AND closing share count in the "
                        "same window - the identity has nothing to check "
                        "itself against this run.",
                        would_catch)
    if fails:
        detail = ("FAILS in " + ", ".join(
            f"FY{y} (gap {g:+.4f}mn shares)" for y, g in fails) +
            f" of {len(checked)} year(s) checked.")
        return _result(FAIL, detail, would_catch)
    return _result(PASS,
                    f"closes to floating-point exactness in all {len(checked)} "
                    f"checked year(s) ({sorted(checked)}).",
                    would_catch)


def _I2(study, EE):
    would_catch = (
        "a future change to timing_decomposition.decompose() that drops a "
        "term from the split, or a change to entry_effect() that computes "
        "the entry total from a different price or share count than the one "
        "handed to the decomposition - either would move `entry` and "
        "`decision + timing` apart without moving the headline number that "
        "gets published, which is exactly the kind of silently-wrong-while-"
        "every-gate-reports-success defect this project has met six times."
    )
    band = EE.get('band')
    tranches = EE.get('tranches') or []
    if not band or not tranches:
        return _result(UNAVAILABLE,
                        EE.get('decomposition_note') or
                        "the earnings-timing decomposition was not computed "
                        "for this company (see entry_effect's own refusal "
                        "note) - there is no per-tranche band to check.",
                        would_catch)
    worst, worst_where, n_checked = 0.0, None, 0
    for name in td.ALL_ESTIMATORS:
        rows = band.get(name, {}).get('rows', {})
        for t, row in rows.items():
            n_checked += 1
            resid = row['decision'] + row['timing'] - row['entry']
            scale = max(1.0, abs(row['entry']))
            rel = abs(resid) / scale
            if rel > worst:
                worst, worst_where = rel, (name, t, resid)
        cum = band[name]
        cum_resid = cum['decision'] + cum['timing'] - cum['entry']
        cum_scale = max(1.0, abs(cum['entry']))
        rel = abs(cum_resid) / cum_scale
        if rel > worst:
            worst, worst_where = rel, (name, 'cumulative', cum_resid)
    if worst > _ENTRY_REL_TOL:
        name, where, resid = worst_where
        return _result(FAIL,
                        f"decision + timing != entry for estimator '{name}' at "
                        f"{'FY' + str(where) if where != 'cumulative' else 'the cumulative total'}"
                        f": residual {resid:+.6f} ({worst:.2e} relative).",
                        would_catch)
    return _result(PASS,
                    f"decision + timing == entry to within {worst:.2e} "
                    f"(relative) across all {len(td.ALL_ESTIMATORS)} estimators "
                    f"and {len(tranches)} tranche(s), per-tranche and "
                    f"cumulatively ({n_checked} row(s) checked). Published "
                    f"identity_residual reads {EE.get('identity_residual'):.2e}.",
                    would_catch)


def _bisect(f, lo=-0.5, hi=0.5, iters=100, expand_tries=40):
    """Independent, generic bisection - no shared code with the closed-form
    root in entry_effect() or with buyback_study_TEMPLATE.solve()."""
    flo, fhi = f(lo), f(hi)
    tries = 0
    while flo * fhi > 0 and tries < expand_tries:
        lo, hi = lo - 0.5, hi + 0.5
        flo, fhi = f(lo), f(hi)
        tries += 1
    if flo * fhi > 0:
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2
        fm = f(mid)
        if fm == 0 or (hi - lo) < 1e-15:
            return mid
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi, fhi = mid, fm
    return (lo + hi) / 2


def _I3(study, EE):
    would_catch = (
        "a future edit that changes the closed-form break-even root (the "
        "`_root()` helper inside entry_effect()) without changing the entry "
        "total it is the root of, or vice versa - the two would stop meeting "
        "at exactly zero and an independently-coded bisection is the only "
        "way to catch that a shared implementation could not."
    )
    tranches = EE.get('tranches') or []
    be = EE.get('break_even')
    if not tranches or be is None:
        return _result(UNAVAILABLE,
                        "no tranche has both a retired count and a real "
                        "repurchase price, so no break-even rate exists to "
                        "check.", would_catch)

    def total_at(rho):
        return study.entry_effect(rho=rho, tranches=tranches,
                                  decompose=False)['total']

    at_be = total_at(be)
    scale = max(1.0, sum(abs(study.retired[t] * EE['real_price_paid'][t])
                          for t in tranches))
    zero_rel = abs(at_be) / scale
    if zero_rel > _ENTRY_REL_TOL:
        return _result(FAIL,
                        f"entry_effect(rho=break_even)['total'] is "
                        f"{at_be:+.6f}, not zero ({zero_rel:.2e} relative) - "
                        "the closed-form root does not zero its own function.",
                        would_catch)

    root = _bisect(total_at, lo=be - 0.5, hi=be + 0.5)
    if root is None:
        root = _bisect(total_at)
    if root is None:
        return _result(FAIL,
                        "independent bisection found no sign change for "
                        "entry_effect()['total'] anywhere in a wide bracket "
                        "around the published break-even - the closed-form "
                        "root could not be corroborated at all.",
                        would_catch)
    be_gap = abs(root - be) / max(abs(be), 1e-9)
    if be_gap > _BREAKEVEN_REL_TOL:
        return _result(FAIL,
                        f"closed-form break-even ({100*be:.4f}%) and "
                        f"independent bisection ({100*root:.4f}%) disagree by "
                        f"{be_gap:.2e} (relative).",
                        would_catch)
    return _result(PASS,
                    f"entry effect is zero at its own break-even "
                    f"({zero_rel:.2e} relative), and the closed-form root "
                    f"({100*be:.4f}%) agrees with an independently bisected "
                    f"root ({100*root:.4f}%) to {be_gap:.2e} (relative).",
                    would_catch)


def _I4(study):
    would_catch = (
        "a future change to reconcile_raises() that stops excluding an "
        "unclean year from `raise_refusals` while still leaving it marked "
        "unclean - which would let an unreconciled equity raise back into "
        "the round trip's numerator through resolved_raises() while the "
        "study still claims, in raise_reconciliation, that the year did not "
        "reconcile."
    )
    if not hasattr(study, 'raise_reconciliation'):
        study.reconcile_raises()
    rec = study.raise_reconciliation
    if not rec:
        return _result(PASS,
                        "this company raised no equity inside the window - "
                        "sources and uses reconcile vacuously (a true zero, "
                        "not a missing check).",
                        would_catch)
    refused = getattr(study, 'raise_refusals', set())
    unclean = {y for y, r in rec.items() if r.get('clean') is False}
    unstated = {y for y, r in rec.items() if r.get('clean') is None}
    mismatch = unclean.symmetric_difference(refused)
    resolved_years = {r.fiscal_year for r in study.resolved_raises()}
    leaked = unclean & resolved_years
    if mismatch or leaked:
        detail = []
        if mismatch:
            detail.append(f"raise_reconciliation marks {sorted(unclean)} "
                          f"unclean but raise_refusals excludes {sorted(refused)}")
        if leaked:
            detail.append(f"unclean year(s) {sorted(leaked)} still appear in "
                          "resolved_raises()")
        return _result(FAIL, "; ".join(detail) + ".", would_catch)
    detail = (f"{len(rec)} raise-year(s) checked on filed facts alone "
              f"(excise tax kept outside this account, per excise_tax()'s own "
              "memorandum-line note); every unclean year "
              f"({sorted(unclean) or 'none'}) is excluded from the round trip.")
    if unstated:
        detail += (f" {sorted(unstated)} could not be cross-checked at all "
                   "(no financing-activities equity line tagged) and are used "
                   "as disclosed, which is stated rather than assumed away.")
    return _result(PASS, detail, would_catch)


def _I5(study, EE, i2_result, i3_result):
    would_catch = (
        "a measure gaining a second computational route (a new alternate "
        "estimator, a new independently-fetched input) whose disagreement "
        "with the first route then gets collapsed to a single published "
        "number instead of a stated band - the two dual-route measures this "
        "template currently has (the timing decomposition band and the "
        "break-even root) are exactly the ones I2 and I3 already watch; this "
        "check is the composite verdict across both, plus an honest count of "
        "what in THIS run has only one route."
    )
    if i2_result['status'] == FAIL:
        return _result(FAIL,
                        "I2 (decision + timing == entry under all six "
                        "estimators) failed - the timing-decomposition band, "
                        "this template's primary dual-route measure, does not "
                        "reconcile with itself.", would_catch)
    if i3_result['status'] in (FAIL,):
        return _result(FAIL,
                        "I3 (closed-form break-even == bisected break-even) "
                        "failed - the break-even root, this template's other "
                        "dual-route measure, does not reconcile with itself.",
                        would_catch)
    single_route = []
    if EE.get('alt_total') is None:
        single_route.append(
            "the entry effect headline has no coe_by_year alternate reading "
            "supplied for this company, so it is a single-rho point, not a "
            "band - the study's own PLACEHOLDER note (when coe_is_placeholder "
            "is set) is what states that rather than leaving it implicit")
    if EE.get('families_disagree_on_sign'):
        single_route.append(
            "the symmetric and backward-looking trend families disagree on "
            "the SIGN of the price decision (already surfaced as a "
            "DIAGNOSTIC note) - the trend level itself is not point-"
            "identified on this company and the band, not a point, is what "
            "was published")
    unavailable = (i2_result['status'] == UNAVAILABLE
                   or i3_result['status'] == UNAVAILABLE)
    if unavailable:
        return _result(UNAVAILABLE,
                        "I2 and/or I3 could not be computed this run (see "
                        "their own detail), so the dual-route measures this "
                        "check watches have nothing to verify.", would_catch)
    detail = "I2 and I3 both pass - the two dual-route measures agree with themselves."
    if single_route:
        detail += " Single-route this run: " + "; ".join(single_route) + "."
    return _result(PASS, detail, would_catch)


def _I6(study, EE):
    would_catch = (
        "a future refactor that reads study.retired[y] or "
        "EE['real_price_paid'][y] directly for a year an earlier guard "
        "excluded, instead of checking membership first - the classic shape "
        "of a zero standing in for an 'unavailable', which the CLI's own "
        "`_f()` and 'n/a' helpers exist to prevent at the report layer and "
        "this check exists to prove holds at the data layer too."
    )
    excluded = (set(getattr(study, 'unresolved_years', set()))
                | set(getattr(study, 'no_share_count_years', set()))
                | set(getattr(study, 'negative_retirement_years', set()))
                | set(getattr(study, 'no_repurchase_years', set())))
    leaks = []
    for y in sorted(excluded):
        if y in study.retired:
            leaks.append(f"FY{y} in study.retired despite being excluded")
        if y in study.issued:
            leaks.append(f"FY{y} in study.issued despite being excluded")
        if y in EE.get('real_price_paid', {}):
            leaks.append(f"FY{y} in EE['real_price_paid'] despite being excluded")
        if y in EE.get('per_year', {}):
            leaks.append(f"FY{y} in EE['per_year'] despite being excluded")
    overlap = set(EE.get('tranches') or []) & set(EE.get('excluded_years', {}))
    if overlap:
        leaks.append(f"FY{sorted(overlap)} appear in both EE['tranches'] and "
                     "EE['excluded_years']")
    if leaks:
        return _result(FAIL, "; ".join(leaks) + ".", would_catch)
    return _result(PASS,
                    f"{len(excluded)} excluded year(s) checked "
                    f"({sorted(excluded) or 'none this run'}) - none leaks a "
                    "number into retired, issued, or the entry-effect tables. "
                    f"{len(EE.get('excluded_years', {}))} tranche-level "
                    "exclusion(s) do not overlap the struck tranches.",
                    would_catch)


# ===========================================================================
# EXTERNAL COHERENCE - does the study agree with the world?
# ===========================================================================

def _E1(study):
    would_catch = (
        "Texas Instruments and Booking Holdings, both real cases this "
        "check already caught during hardening: an implied average price "
        "paid that fell outside the fiscal year's own intra-period traded "
        "range, in both cases traced to a share-count or split error "
        "upstream of the price. Its stated limit: a contaminated numerator "
        "whose error is small relative to the range can still pass - the "
        "American Airlines withholding-in-the-cash-line defect nearly did."
    )
    if not study.retired:
        return _result(UNAVAILABLE,
                        "no year in this window has a resolved retirement to "
                        "price.", would_catch)
    fails = getattr(study, 'price_failures', None)
    if fails:
        return _result(FAIL,
                        "implied price outside the fiscal year's traded range "
                        "in " + ", ".join(
                            f"FY{y} (${px:,.2f} vs [{lo:,.2f}, {hi:,.2f}])"
                            for y, px, lo, hi in fails) + ".",
                        would_catch)
    return _result(PASS,
                    f"every implied average price paid across "
                    f"{len(study.retired)} retirement year(s) sits inside its "
                    "own fiscal year's traded range.",
                    would_catch)


def _E2(study):
    would_catch = (
        "the Costco deflator inversion: a fitted real trend of 17.73% a "
        "year against LOWER nominal growth, arithmetically impossible once "
        "the deflator moves the right direction. Cheap, and it catches an "
        "entire class of deflator error - direction flipped, wrong base "
        "year, division where multiplication was meant."
    )
    nominal = study.fin.get('diluted_eps', {})
    real = study.real_eps()
    span = study.earnings_span()
    years = [y for y in span if nominal.get(y) not in (None, 0)
             and real.get(y) not in (None, 0)]
    if len(years) < 2:
        return _result(UNAVAILABLE,
                        "fewer than two years have both a nominal and a real "
                        "EPS figure - no growth rate can be formed.",
                        would_catch)
    first, last = min(years), max(years)
    if nominal[first] <= 0 or nominal[last] <= 0:
        return _result(UNAVAILABLE,
                        f"nominal EPS is non-positive at the window's "
                        f"endpoint(s) (FY{first}: {nominal[first]:.3f}, "
                        f"FY{last}: {nominal[last]:.3f}) - a growth RATE is "
                        "not well defined across a sign change and is not "
                        "computed rather than reported as though it were.",
                        would_catch)
    nominal_growth = nominal[last] / nominal[first] - 1
    real_growth = real[last] / real[first] - 1
    inflation_positive = study.deflator[first] > study.deflator[last] * (1 + 1e-9)
    if not inflation_positive:
        return _result(PASS,
                        f"no net inflation over FY{first}-FY{last} "
                        f"(deflator {study.deflator[first]:.5f} to "
                        f"{study.deflator[last]:.5f}), so real and nominal "
                        f"growth are not required to differ; real "
                        f"({100*real_growth:+.2f}%) vs nominal "
                        f"({100*nominal_growth:+.2f}%).",
                        would_catch)
    if real_growth > nominal_growth + 1e-9:
        return _result(FAIL,
                        f"real EPS growth ({100*real_growth:+.2f}%, FY{first}-"
                        f"FY{last}) is ABOVE nominal growth "
                        f"({100*nominal_growth:+.2f}%) despite positive "
                        "inflation over the window - arithmetically "
                        "impossible under this study's real=nominal*deflator "
                        "convention and the signature of a deflator applied "
                        "backwards.",
                        would_catch)
    return _result(PASS,
                    f"real EPS growth ({100*real_growth:+.2f}%, FY{first}-"
                    f"FY{last}) is below nominal growth "
                    f"({100*nominal_growth:+.2f}%), as positive inflation over "
                    "the window requires.",
                    would_catch)


def _E3(study, EE):
    would_catch = (
        "Booking Holdings printing forward real earnings yields of 87%, "
        "143% and 151% on individual tranches - numbers that are not wrong "
        "arithmetic but ARE a company whose earnings compounded so fast "
        "after the purchase that the entry effect is dominated by a growth "
        "accident rather than a price decision. Flagged, not refused: "
        "judgment about a business cycle stays with a person."
    )
    tranches = EE.get('tranches') or []
    if not tranches:
        return _result(UNAVAILABLE, "no struck tranche this run.", would_catch)
    lo_band, hi_band = _E3_BAND
    outside = []
    for t in tranches:
        px = EE['real_price_paid'].get(t)
        eps_next = EE['real_eps'].get(t + 1)
        if not px or px <= 0 or eps_next is None:
            continue
        yld = eps_next / px
        if not (lo_band <= yld <= hi_band):
            outside.append((t, yld))
    if outside:
        return _result(FLAG,
                        "forward real earnings yield outside the "
                        f"[{100*lo_band:.1f}%, {100*hi_band:.0f}%] plausible "
                        "band in " + ", ".join(
                            f"FY{t} ({100*y:.1f}%)" for t, y in outside) +
                        " - published as a finding, not refused.",
                        would_catch)
    return _result(PASS,
                    f"forward real earnings yield sits inside "
                    f"[{100*lo_band:.1f}%, {100*hi_band:.0f}%] on all "
                    f"{len(tranches)} struck tranche(s).",
                    would_catch)


def _E4(study):
    would_catch = (
        "a share-count or split error that manufactures an implausibly "
        "large derived retirement - the same failure mode DEFECT 11 "
        "(American Airlines, an issuance-rate fallback extrapolated from a "
        "merger year) produced before it was capped, here caught as a "
        "symptom rather than diagnosed at its source, which is the point of "
        "having more than one guard on the same failure mode."
    )
    S = study.shares_outstanding()
    bad, checked = [], []
    for y, q in study.retired.items():
        if (y - 1) not in S or not S[y - 1]:
            continue
        frac = q / S[y - 1]
        checked.append(y)
        if frac < 0 or frac > _E4_MAX_FRACTION:
            bad.append((y, frac))
    if not checked:
        return _result(UNAVAILABLE,
                        "no retirement year has an opening share count to "
                        "measure a fraction against.", would_catch)
    if bad:
        return _result(FAIL,
                        "implausible retirement fraction of opening shares in "
                        + ", ".join(f"FY{y} ({100*f:.1f}%)" for y, f in bad) +
                        f" (ceiling {100*_E4_MAX_FRACTION:.0f}%, floor 0%).",
                        would_catch)
    worst = max(checked, key=lambda y: study.retired[y] / S[y - 1])
    return _result(PASS,
                    f"shares retired stay under {100*_E4_MAX_FRACTION:.0f}% of "
                    f"opening shares and never negative in all "
                    f"{len(checked)} checked year(s); the largest is FY"
                    f"{worst} at {100*study.retired[worst]/S[worst-1]:.1f}%.",
                    would_catch)


def _E5(study, traded_range=None):
    would_catch = (
        "the same class of error E1 catches, at the level of the whole "
        "program instead of one year - a level shift or unit error that "
        "moves every year's price a little in the same direction can pass "
        "E1 year by year and still put the dollar-weighted average outside "
        "the window's own extremes."
    )
    tot_cash = sum(study.sec['repurchase_cash'][y]['val'] / 1e6
                   for y in study.retired if y in study.sec.get('repurchase_cash', {}))
    tot_q = sum(study.retired.values())
    if not tot_q:
        return _result(UNAVAILABLE,
                        "NO MEASURABLE REPURCHASE IN THIS WINDOW - the "
                        "dollar-weighted price is undefined.", would_catch)
    price = tot_cash / tot_q
    years = sorted(study.retired)
    if traded_range:
        lo_hi = [traded_range[y] for y in years if y in traded_range]
        source = "the fiscal-year traded range supplied to this run"
    else:
        lo_hi = []
        for y in years:
            v = [study.prices[k] for k in study.cfg.fiscal_months(y)
                 if k in study.prices]
            if v:
                lo_hi.append((min(v), max(v)))
        source = ("period-end closes only (no intra-period traded range was "
                  "supplied to this check) - looser than the intra-period "
                  "check and stated as such")
    if not lo_hi:
        return _result(UNAVAILABLE,
                        "no price observation covers any retirement year in "
                        "this window.", would_catch)
    lo, hi = min(v[0] for v in lo_hi), max(v[1] for v in lo_hi)
    if not (lo <= price <= hi):
        return _result(FAIL,
                        f"dollar-weighted price ${price:,.2f} falls outside "
                        f"the window's overall traded range [${lo:,.2f}, "
                        f"${hi:,.2f}] ({source}).",
                        would_catch)
    return _result(PASS,
                    f"dollar-weighted price ${price:,.2f} across "
                    f"{len(years)} year(s) sits inside the window's overall "
                    f"traded range [${lo:,.2f}, ${hi:,.2f}] ({source}).",
                    would_catch)


def _E6(_study):
    return _result(UNAVAILABLE,
                    "no market-multiple series (an index or sector P/E by "
                    "fiscal year) is plumbed into this driver at all - "
                    "StudyConfig carries no field for one and none is fetched. "
                    "Building this would mean adding a supplied series "
                    "(comparable to coe_by_year) and comparing it to the "
                    "company's own multiple paid in each tranche year; until "
                    "that exists, stated as unavailable rather than skipped.",
                    "a repurchase executed at a large, undisclosed premium or "
                    "discount to the market multiple of its own year - a real "
                    "execution finding this driver currently has no way to "
                    "surface at all, worth building deliberately rather than "
                    "improvising the day it is needed.")


def _E7(_study):
    return _result(UNAVAILABLE,
                    "fetch_prices() builds BOTH the monthly-close series used "
                    "for the price and the intra-period traded range used by "
                    "E1/E5 from ONE EODHD call ('eod/{sym}', period='m') - the "
                    "same rows, not a second source. There is currently no "
                    "second, independently-called quote anywhere in this "
                    "pipeline for E7 to check against; building one would mean "
                    "a live single-date call to a DIFFERENT EODHD endpoint for "
                    "the window's first and last fiscal year-end dates only, "
                    "made optional so the fleet gate and injection suite keep "
                    "running offline.",
                    "a defect in fetch_prices() itself - a wrong symbol, a "
                    "wrong exchange suffix, a stale cached response - that E1 "
                    "and E5 cannot catch because they are built from the same "
                    "call this check would corroborate.")


def _E8(_study):
    return _result(UNAVAILABLE,
                    "no XBRL element for a company's own CUMULATIVE "
                    "repurchase-program disclosure is in TAGS or FIN_TAGS. "
                    "StockRepurchaseProgramAuthorizedAmount1 exists in the "
                    "us-gaap taxonomy but reports the program's AUTHORIZED "
                    "size, not the amount executed to date, and is not the "
                    "same fact. This driver sums PaymentsForRepurchaseOfCommon"
                    "Stock across the window instead, which is filed cash, "
                    "not a company-stated cumulative total.",
                    "a mis-summed or double-counted cash total across the "
                    "window - the company's own cumulative disclosure, where "
                    "one exists in the filing text, is the only independent "
                    "check on that total this driver does not yet have.")


def _E9(study):
    would_catch = (
        "a splice error inside shares_outstanding()'s own cover-page "
        "fallback - the method already checks its own overlap and refuses a "
        "splice that disagrees by more than 2%, so this is a regression "
        "tripwire on that logic rather than a new source of truth. The "
        "honest limit: EntityCommonStockSharesOutstanding is a SECOND "
        "ELEMENT in the SAME 10-K filing, struck as of the filing date, not "
        "a true external third party (a transfer agent or exchange count)."
    )
    raw = study.sec.get('shares_outstanding', {})
    dei = study.sec.get('shares_outstanding_dei', {})
    if not raw or not dei:
        return _result(UNAVAILABLE,
                        "this company does not file both "
                        "CommonStockSharesOutstanding and the cover-page "
                        "EntityCommonStockSharesOutstanding, so there is no "
                        "second element to compare the closing count "
                        "against.", would_catch)
    out = {y: e['val'] * study.cfg.split_factor(e['filed']) / 1e6
           for y, e in raw.items()}
    cover = {y: e['val'] * study.cfg.split_factor(e['filed']) / 1e6
             for y, e in dei.items()}
    overlap = sorted(set(out) & set(cover))
    if not overlap:
        return _result(UNAVAILABLE,
                        "CommonStockSharesOutstanding and the cover-page count "
                        "never cover the same fiscal year in this window, so "
                        "they cannot be cross-checked against each other.",
                        would_catch)
    gaps = {y: abs(cover[y] / out[y] - 1) for y in overlap if out[y]}
    if not gaps:
        return _result(UNAVAILABLE, "overlapping year(s) have a zero-valued "
                        "us-gaap count.", would_catch)
    worst_y = max(gaps, key=gaps.get)
    worst = gaps[worst_y]
    if worst > _E9_MAX_RELATIVE_GAP:
        return _result(FAIL,
                        f"FY{worst_y}: CommonStockSharesOutstanding "
                        f"({out[worst_y]:,.1f}mn) and the cover-page count "
                        f"({cover[worst_y]:,.1f}mn) disagree by "
                        f"{100*worst:.2f}%, above the "
                        f"{100*_E9_MAX_RELATIVE_GAP:.0f}% bound "
                        "shares_outstanding() itself uses to allow a splice.",
                        would_catch)
    return _result(PASS,
                    f"CommonStockSharesOutstanding and the cover-page "
                    f"EntityCommonStockSharesOutstanding agree to within "
                    f"{100*worst:.2f}% in all {len(overlap)} overlapping "
                    f"year(s) (worst: FY{worst_y}). Cross-check only - both "
                    "elements are filed in the same 10-K, not a true external "
                    "third party.",
                    would_catch)


# ===========================================================================
# ORCHESTRATOR
# ===========================================================================

def run_audit_points(study, EE, traded_range=None):
    """Run all fifteen audit points against a completed study and its entry
    effect. Never raises, never exits - see the module docstring for why.

    `study` must already have had .run() called (retired/issued, price
    validation, raise reconciliation all populated). `EE` is the dict
    returned by study.entry_effect(). `traded_range` is the same
    {fy: (low, high)} dict, if any, that was passed to study.run(); passing
    it makes E5 use the intra-period check instead of the looser period-end
    fallback, exactly as validate_prices() already does for E1.

    Returns an OrderedDict, I1..I6 then E1..E9, each value
    {'status', 'detail', 'would_catch'}.
    """
    out = OrderedDict()
    out['I1'] = _I1(study)
    out['I2'] = _I2(study, EE)
    out['I3'] = _I3(study, EE)
    out['I4'] = _I4(study)
    out['I5'] = _I5(study, EE, out['I2'], out['I3'])
    out['I6'] = _I6(study, EE)
    out['E1'] = _E1(study)
    out['E2'] = _E2(study)
    out['E3'] = _E3(study, EE)
    out['E4'] = _E4(study)
    out['E5'] = _E5(study, traded_range)
    out['E6'] = _E6(study)
    out['E7'] = _E7(study)
    out['E8'] = _E8(study)
    out['E9'] = _E9(study)
    return out


def refused(results):
    """True if any REFUSING_CODES check FAILed - the study should not be
    published without an explicit, recorded override."""
    return any(results[c]['status'] == FAIL for c in REFUSING_CODES if c in results)
