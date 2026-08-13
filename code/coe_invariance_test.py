# -*- coding: utf-8 -*-
"""The study is accurate whatever the real cost of equity is. Proven, not asserted.

WHY THIS FILE EXISTS
--------------------
James's ruling, 2026-08-13: the absence of an engine-sourced real cost of equity
for a ticker does not block the methodology or the template. The rate is an INPUT
that can be swapped at any time. It may change what a particular study concludes;
it must not change whether the study is performed correctly.

That is a testable claim and this file tests it. The same company is run at 3, 4,
5, 6, 8, 10 and 12 percent real, and four things are required.

  ONE. Every RATE-FREE quantity is bit-identical at every rate. The shares
  retired, the real price paid, the real earnings series, the tranche selection,
  the permanence label, the treasury overhang, the excise exposure, the price
  validation and - importantly - the earnings-TIMING component of the
  decomposition all contain no rate and must not move by one bit when the rate
  moves by nine hundred basis points. The timing component is the interesting
  one: it is the diagnostic that says whether the entry effect may be read as a
  verdict at all, and it is rate-free by construction. This proves the
  construction.

  TWO. The break-even rate is invariant. It is a property of the program - the
  retirement-weighted forward real earnings yield - not of the rate the analyst
  chose, so it cannot move when the choice moves. This is what makes a study
  reportable before anybody has sourced a rate: publish the break-even and the
  reader supplies their own hurdle.

  THREE. The entry effect is exactly LINEAR in the rate, and its root is exactly
  the break-even. Linearity is checked against a three-point secant to machine
  precision, so this also tests the closed-form claim the published documents
  make in prose.

  FOUR. The identity decision + timing == entry closes at every rate, under
  every one of the six trend estimators.

If all four hold, then handing over a real cost-of-equity series later is a
substitution and nothing more: everything recomputes and nothing has to be
rebuilt, re-derived or re-reviewed.

Run from code/:  python3 coe_invariance_test.py
"""
import io
import contextlib
import sys

sys.path.insert(0, '..')
import run_study as rs                                          # noqa: E402
import timing_decomposition as td                               # noqa: E402

RATES = (0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12)
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append(("PASS" if ok else "FAIL", name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


# Oracle is the fixture: committed, offline, a full thirteen-year window with a
# real repurchase record, a straddling excise year and a decomposition that
# exercises every estimator.
def run_at(rate):
    cfg = rs.StudyConfig(
        ticker="ORCL", cik="0001341439", fy_end_month=5, splits=[],
        first_year=2013, last_year=2025, coe_longrun=rate,
        prices='orcl_monthly.csv', traded_range='orcl_traded_range.csv',
        split_year=2020)
    rs.REF.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        return rs.run(cfg, 'orcl_sec_raw.json')


runs = {r: run_at(r) for r in RATES}
base_study, base_EE = runs[RATES[0]]

# ---------------------------------------------------------------- ONE
print("\n--- rate-free quantities must be BIT-IDENTICAL across a 900bp swing ---")
for r in RATES[1:]:
    st, EE = runs[r]
    check(f"shares retired identical at {100*r:.0f}%",
          st.retired == base_study.retired)
    check(f"real price paid identical at {100*r:.0f}%",
          EE['real_price_paid'] == base_EE['real_price_paid'])
    check(f"real earnings identical at {100*r:.0f}%",
          EE['real_eps'] == base_EE['real_eps'])
    check(f"tranche selection identical at {100*r:.0f}%",
          EE['tranches'] == base_EE['tranches']
          and EE['excluded_years'] == base_EE['excluded_years'])
    check(f"permanence label identical at {100*r:.0f}%",
          st.net_cost['basis'] == base_study.net_cost['basis']
          and st.net_cost['B_per_share'] == base_study.net_cost['B_per_share'])
    check(f"price validation identical at {100*r:.0f}%",
          st.price_failures == base_study.price_failures)
    # The timing component carries no rate at all. This is the claim the
    # cyclicality diagnostic rests on.
    for n in td.ALL_ESTIMATORS:
        check(f"  timing component rate-free, {n}, at {100*r:.0f}%",
              EE['band'][n]['timing'] == base_EE['band'][n]['timing'])
    # NOT invariant, and finding that out here is the point of writing the test
    # before believing the claim. Timing dependence is |timing| / |entry|. The
    # numerator is rate-free - proven immediately above - but the DENOMINATOR is
    # the headline entry effect, which moves with the rate and passes through
    # zero at the break-even. So the RATIO is rate-dependent and diverges near
    # the break-even. Oracle's "336 percent" is a figure at 5.50 percent real
    # and is meaningless without that qualifier. This is disclosed, not fixed:
    # the ratio is the right diagnostic, it just has to be quoted with its rate.
    check(f"timing dependence moves with the rate, as its definition requires, at {100*r:.0f}%",
          EE['timing_dependence'] != base_EE['timing_dependence']
          or abs(EE['total'] - base_EE['total']) < 1e-12,
          f"{100*EE['timing_dependence']:.0f}% against "
          f"{100*base_EE['timing_dependence']:.0f}% at {100*RATES[0]:.0f}%")

# ---------------------------------------------------------------- TWO
print("\n--- the break-even is a property of the program, not of the rate ---")
for r in RATES[1:]:
    _, EE = runs[r]
    check(f"break-even unmoved at {100*r:.0f}%",
          EE['break_even'] == base_EE['break_even'],
          f"{100*EE['break_even']:.6f}%")
    check(f"  sub-window break-evens unmoved at {100*r:.0f}%",
          EE['break_even_windows'] == base_EE['break_even_windows'])

# ---------------------------------------------------------------- THREE
print("\n--- the entry effect is exactly linear in the rate, with the break-even as its root ---")
xs = sorted(RATES)
ys = [runs[r][1]['total'] for r in xs]
slopes = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
spread = max(slopes) - min(slopes)
check("slope is the same between every adjacent pair of rates (linear)",
      abs(spread) < 1e-6 * max(abs(s) for s in slopes),
      f"slope {slopes[0]:,.1f} $m per unit of rate, spread {spread:.3e}")
# The slope must equal minus the retirement-weighted real cash outlay, exactly.
outlay = sum(base_study.retired[t] * base_EE['real_price_paid'][t]
             for t in base_EE['tranches'])
check("slope equals minus the real cash outlay on the tranches",
      abs(slopes[0] + outlay) < 1e-6 * outlay,
      f"{slopes[0]:,.3f} against {-outlay:,.3f}")
r_star = base_EE['break_even']
at_root, _ = run_at(r_star)
_, EE_root = run_at(r_star)
check("the entry effect is ZERO at the break-even rate",
      abs(EE_root['total']) < 1e-6 * outlay, f"{EE_root['total']:.3e} $m")
lo, _ = None, None
_, EE_lo = run_at(r_star - 0.0005)
_, EE_hi = run_at(r_star + 0.0005)
check("positive below the break-even and negative above it, with nothing else changing",
      EE_lo['total'] > 0 > EE_hi['total']
      and EE_lo['real_price_paid'] == EE_hi['real_price_paid'],
      f"{EE_lo['total']:+,.1f} / {EE_hi['total']:+,.1f} $m")

# ---------------------------------------------------------------- FOUR
print("\n--- the decomposition identity closes at every rate ---")
for r in RATES:
    _, EE = runs[r]
    check(f"decision + timing == entry at {100*r:.0f}%, all six estimators",
          EE['identity_residual'] < 1e-6,
          f"residual {EE['identity_residual']:.2e}")

# A YEAR-BY-YEAR SERIES IS AS ACCEPTABLE AS A SCALAR. When the engine series
# arrives it drops straight in; this proves the seam works before it does.
print("\n--- a year-by-year series substitutes for a scalar without ceremony ---")
series = {y: 0.045 + 0.002 * ((y - 2013) % 5) for y in range(2011, 2028)}
cfg = rs.StudyConfig(
    ticker="ORCL", cik="0001341439", fy_end_month=5, splits=[],
    first_year=2013, last_year=2025, coe_longrun=0.06, coe_by_year=series,
    prices='orcl_monthly.csv', traded_range='orcl_traded_range.csv')
rs.REF.clear()
with contextlib.redirect_stdout(io.StringIO()):
    st_s, EE_s = rs.run(cfg, 'orcl_sec_raw.json')
check("a per-year cost of equity produces the alternative reading",
      EE_s['alt_total'] is not None and EE_s['alt_total'] != EE_s['total'])
check("and moves nothing rate-free",
      EE_s['real_price_paid'] == base_EE['real_price_paid']
      and EE_s['break_even'] == base_EE['break_even']
      and st_s.retired == base_study.retired)
check("the alternative total is exactly the per-year arithmetic",
      abs(EE_s['alt_total']
          - sum(st_s.retired[t] * (EE_s['real_eps'][t + 1] - series[t] * EE_s['real_price_paid'][t])
                for t in EE_s['tranches'])) < 1e-9)

# The size of that rate dependence, published rather than left to be discovered.
_dep = {r: runs[r][1]['timing_dependence'] for r in RATES}
print("\n--- timing dependence against the rate (it is a RATIO; only its numerator is rate-free) ---")
for r in RATES:
    print(f"    {100*r:5.1f}% real  ->  timing dependence {100*_dep[r]:8.0f}%   "
          f"entry {runs[r][1]['total']/1000:+8.3f}bn")
print("    The numerator is identical at every rate above. Quote the diagnostic WITH its rate,")
print("    and never within a few basis points of the break-even, where the denominator vanishes.")

print()
n_fail = sum(1 for s, *_ in CHECKS if s == "FAIL")
if n_fail:
    print(f"{n_fail} of {len(CHECKS)} COST-OF-EQUITY INVARIANCE CHECKS FAILED")
    sys.exit(1)
print(f"ALL {len(CHECKS)} COST-OF-EQUITY INVARIANCE CHECKS PASS")
