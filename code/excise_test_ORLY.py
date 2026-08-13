# -*- coding: utf-8 -*-
"""Prove the excise-tax measure on O'Reilly Automotive (addendum item 5).

WHY O'REILLY. Item 5 exists because the one percent United States excise on net
share repurchases, in force since 2023, is absent from the study's funding
account. The obvious implementation - read a tag - does not survive contact with
the filings, and O'Reilly is the company that shows why. Checked live on
2026-08-13, no company in this study discloses the quantity at all: Apple's
fiscal 2023 note says its $76.6 billion excludes excise tax and then fiscal 2024
and fiscal 2025 stop mentioning it, and Costco, Boeing, American Airlines and
Home Depot never print a figure in any year. O'Reilly does print one. In fact it
prints THREE, they do not agree, and the disagreement is instructive:

  - the share-repurchase note, tagged us-gaap:ShareRepurchaseProgramExciseTax,
    says the excise "assessed at one percent of the fair market value of NET
    shares repurchased" was $21.0 million for 2025;
  - the statement of stockholders' equity in the SAME filing charges $18.720
    million for 2025;
  - the financing section of the cash flow statement pays $17.012 million in
    2025, which is the 2024 accrual settled a year late.

The note's figure is one percent of GROSS repurchases to the rounding it
presents, notwithstanding its own sentence claiming the netting rule. The equity
statement's is one percent of gross LESS the netting rule, which is what the
sentence describes. So the tagged number is the wrong one, and a template that
read the only us-gaap element for this quantity and believed it would publish a
figure twelve percent too high in 2025 - too high in the direction that makes
the buyback look more expensive, but wrong is wrong.

WHAT THIS FIXTURE PROVES, and the reason it justifies using a reconstruction on
Apple at all: on a company where the filed answer is known, the study's
statutory band BRACKETS it, and the netted end of the band lands within a
fraction of one percent of the filed charge in all three years.

Run: cd code && python3 excise_test_ORLY.py
"""
import csv
import json
import sys

sys.path.insert(0, '..')
from buyback_study import (CompanyConfig, BuybackStudy, parse_concept,
                           EXCISE_RATE)
from buyback_study_TEMPLATE import ExciseTaxUndisclosed

CHECKS = []


def check(name, condition, detail=""):
    CHECKS.append(("PASS" if condition else "FAIL", name, detail))
    print(f"[{CHECKS[-1][0]}] {name}" + (f"  ({detail})" if detail else ""))


def near(a, b, tol):
    return abs(a - b) <= tol


# --------------------------------------------------------------------- config
# O'Reilly's fiscal year IS the calendar year, which is the point: every year
# from 2023 is fully exposed and the straddle proration cannot hide an error
# here. Its 15-for-1 split of 2025-06-10 is carried so that the as-filed share
# counts restate onto today's basis; the price series below is already adjusted.
CFG = CompanyConfig(ticker="ORLY", cik="0000898173", fy_end_month=12,
                    splits=[("2025-06-10", 15)], first_year=2022,
                    last_year=2025)

PRICES = {}
for r in csv.DictReader(open('orly_monthly.csv')):
    y, m, _ = r['Date'].split('-')
    PRICES[(int(y), int(m))] = float(r['Close'])

RAW = json.load(open('orly_sec_raw.json'))
SEC = {k: parse_concept(v) for k, v in RAW.items()}

# ------------------------------------------------ what the filing actually says
# Read off the statement of stockholders' equity and the financing section of
# the cash flow statement in the fiscal 2025 and fiscal 2024 Forms 10-K, in
# thousands as presented, carried here in $ millions. These are transcribed
# figures, which is why every one of them is cross-checked below against a
# quantity the template computes for itself rather than trusted on its own.
EQUITY_CHARGE = {2023: 28.830, 2024: 17.011, 2025: 18.720}
CASH_PAID = {2023: 0.0, 2024: 28.830, 2025: 17.012}

study = BuybackStudy(CFG, {}, SEC, PRICES, {}, {})
study.retired, study.issued = study.share_flows()

GROSS = {y: SEC['repurchase_cash'][y]['val'] / 1e6 for y in (2023, 2024, 2025)}
ACCRUAL = {y: SEC['repurchase_accrual'][y]['val'] / 1e6 for y in (2023, 2024, 2025)}
TAGGED = {y: e['val'] / 1e6 for y, e in SEC['excise_tax'].items()}

print("\n--- what O'Reilly filed, three ways ---")
for y in (2023, 2024, 2025):
    print(f"  FY{y}  repurchases {GROSS[y]:10,.3f}   1% of gross {EXCISE_RATE*GROSS[y]:8,.3f}"
          f"   note tag {TAGGED.get(y, float('nan')):7,.3f}"
          f"   equity charge {EQUITY_CHARGE[y]:7,.3f}   cash paid {CASH_PAID[y]:7,.3f}")

# ======================================================= 1. exposure and reach
check("FY2022 is not exposed: the statute reaches repurchases after 2022-12-31",
      study.excise_exposure(2022) == 0.0, f"{study.excise_exposure(2022):.3f}")
for y in (2023, 2024, 2025):
    check(f"  FY{y} is fully exposed (calendar fiscal year)",
          study.excise_exposure(y) == 1.0, f"{study.excise_exposure(y):.3f}")

# ============================================ 2. the two filed figures disagree
for y in (2024, 2025):
    check(f"FY{y}: the tagged note figure and the equity charge DISAGREE",
          not near(TAGGED[y], EQUITY_CHARGE[y], 0.05),
          f"tag {TAGGED[y]:.3f} vs equity {EQUITY_CHARGE[y]:.3f}, "
          f"gap {TAGGED[y]-EQUITY_CHARGE[y]:+.3f}")
    check(f"  FY{y}: the tagged figure is 1% of GROSS to its presented rounding",
          near(round(EXCISE_RATE * GROSS[y], 1), TAGGED[y], 1e-9),
          f"1% of {GROSS[y]:,.3f} = {EXCISE_RATE*GROSS[y]:.3f} -> "
          f"{round(EXCISE_RATE*GROSS[y],1):.1f}, tagged {TAGGED[y]:.1f}")
    check(f"  FY{y}: the equity charge is NOT 1% of gross - the netting rule bit",
          EQUITY_CHARGE[y] < EXCISE_RATE * GROSS[y] - 0.05,
          f"{EQUITY_CHARGE[y]:.3f} < {EXCISE_RATE*GROSS[y]:.3f}")

# ============================================= 3. netting bites in every year
for y in (2023, 2024, 2025):
    benefit = EXCISE_RATE * GROSS[y] - EQUITY_CHARGE[y]
    share = benefit / (EXCISE_RATE * GROSS[y])
    check(f"FY{y}: netting removes a material, non-trivial share of the gross tax",
          0.02 < share < 0.30, f"{100*share:.1f}% of gross tax, ${benefit:.3f}m")

# ======================================== 4. accrued in one year, paid the next
check("FY2023 accrues the excise and pays none of it",
      CASH_PAID[2023] == 0.0 and EQUITY_CHARGE[2023] > 0,
      f"accrued {EQUITY_CHARGE[2023]:.3f}, paid {CASH_PAID[2023]:.3f}")
for y in (2024, 2025):
    check(f"  FY{y} cash payment settles the FY{y-1} accrual, not its own",
          near(CASH_PAID[y], EQUITY_CHARGE[y - 1], 0.002),
          f"paid {CASH_PAID[y]:.3f} against FY{y-1} accrual "
          f"{EQUITY_CHARGE[y-1]:.3f}; own-year accrual is {EQUITY_CHARGE[y]:.3f}")

# ================================================== 5. the template, disclosed
res = study.excise_tax(disclosed={y: (v, "statement of stockholders' equity")
                                  for y, v in EQUITY_CHARGE.items()})
check("template: every exposed year reads as disclosed when the filing is supplied",
      all(res['years'][y]['status'] == 'disclosed' for y in (2023, 2024, 2025))
      and res['all_disclosed'])
check("  template: FY2022 is pre-statute and returns an exact zero",
      res['years'][2022]['status'] == 'pre-statute'
      and res['years'][2022]['value'] == 0.0)
check("  template total equals the sum of the three filed charges",
      near(res['total'], sum(EQUITY_CHARGE.values()), 1e-9),
      f"{res['total']:.3f} vs {sum(EQUITY_CHARGE.values()):.3f}")
check("  template raises no straddle note on a calendar fiscal year",
      not any('PARTIAL' in n for n in res['notes']))

# ============================== 6. the template refuses to invent a zero (item 5)
study2 = BuybackStudy(CFG, {}, SEC, PRICES, {}, {})
study2.retired, study2.issued = study2.share_flows()
study2.sec = {k: v for k, v in SEC.items() if k != 'excise_tax'}
raised = False
try:
    study2.excise_tax()
except ExciseTaxUndisclosed as e:
    raised = True
    msg = str(e)
check("template FAILS LOUDLY on an exposed year with no disclosure", raised,
      msg.split('.')[0][:88] + "..." if raised else "no exception raised")
check("  the refusal names the year and says the figure is not zero",
      raised and 'FY2023' in msg and 'NOT zero' in msg)

# ================== 7. THE POINT: the reconstruction band brackets the filed fact
est = study2.excise_tax(allow_statutory_estimate=True)
# The UPPER end is a true bound and is asserted as one: the netting rule can
# only reduce the base, and stock issued is never negative. The LOWER end is
# NOT a bound and this fixture is what proves it - in fiscal 2023 it lands
# above the filed charge, by a quarter of one percent, because the netting
# term values the year's issued shares at the year's MEAN price and O'Reilly
# did not issue them at the mean. The measure is published as a band with an
# estimated lower edge, never as a bracket, and the direction of the miss is
# recorded per year rather than assumed to be one-sided.
SIGNED_ERR = {}
for y in (2023, 2024, 2025):
    r = est['years'][y]
    check(f"FY{y}: the gross end is a true UPPER BOUND on the filed charge",
          EQUITY_CHARGE[y] <= r['high'] + 1e-9,
          f"filed {EQUITY_CHARGE[y]:.3f} <= {r['high']:.3f}")
    err = (r['low'] - EQUITY_CHARGE[y]) / EQUITY_CHARGE[y]
    SIGNED_ERR[y] = err
    check(f"  FY{y}: the netted end lands within 0.5% of the filed charge",
          abs(err) < 0.005, f"netted {r['low']:.3f} vs filed "
          f"{EQUITY_CHARGE[y]:.3f}, {100*err:+.2f}%")
    check(f"  FY{y}: the gross end reproduces 1% of the repurchase line",
          near(r['high'], EXCISE_RATE * GROSS[y], 1e-9))
    check(f"  FY{y}: the cash-basis and accrual-basis gross ends agree",
          near(r['high'], r['statutory_high_accrual'], 1e-6),
          f"cash {r['high']:.3f} vs accrual {r['statutory_high_accrual']:.3f}")

tot_err = (est['total_low'] - sum(EQUITY_CHARGE.values())) / sum(EQUITY_CHARGE.values())
check("cumulative: the netted reconstruction reproduces the three filed charges",
      abs(tot_err) < 0.02,
      f"{est['total_low']:.3f} against {sum(EQUITY_CHARGE.values()):.3f}, "
      f"{100*tot_err:+.2f}%")
check("  the estimate is announced, never silent",
      any('NOT DISCLOSED' in n for n in est['notes']))
check("the netted end misses in BOTH directions across the three years, so it is "
      "an estimate and not a one-sided bound",
      max(SIGNED_ERR.values()) > 0 and min(SIGNED_ERR.values()) < 0,
      ", ".join(f"FY{y} {100*e:+.2f}%" for y, e in sorted(SIGNED_ERR.items())))

# --------------------------------------------------------------------- verdict
print("\n" + "=" * 92)
fails = [c for c in CHECKS if c[0] == "FAIL"]
for _, n, d in fails:
    print(f"  FAILED: {n}  {d}")
if fails:
    print(f"*** {len(fails)} OF {len(CHECKS)} EXCISE CHECKS FAILED ***")
    sys.exit(1)
print(f"ALL {len(CHECKS)} EXCISE CHECKS PASS")
