# -*- coding: utf-8 -*-
"""Fourth company exercise for buyback_study_TEMPLATE.py: Costco.

Picked after McDonald's exposed a real limit (see run_MCD.py and the
2026-08-12 findings): the "balance-only" tagging pattern McDonald's,
PepsiCo and Procter & Gamble share cannot be reliably reconstructed from
structured SEC data alone. Costco tags the DIRECT flow -
StockRepurchasedAndRetiredDuringPeriodShares - the same clean pattern
Apple's own hand-curated study used, so this run needed none of the
fallback machinery HD or MCD needed.

CORRECTED 2026-08-12, same day, after James asked why the first COST report
was so much thinner than Apple's: the study window is FY2015-FY2025 (11
years), NOT FY2017-FY2025 as first landed here. StockRepurchasedAndRetired
DuringPeriodShares actually covers FY2015 onward directly - filed, zero
derived years, zero price-validator failures across all eleven years. The
original claim ("Costco tags nothing usable before FY2017") was simply
wrong; it was not checked carefully enough the first time. Fiscal 2012-2014
still has no usable share-count tag (real repurchase cash exists - $632m,
$36m, $334m - but no retirement or treasury-acquired flow to pair it with)
and remain outside the window, correctly.

This driver now also exercises every measure the template's own docstring
promises but the first pass never printed: EPS growth channel attribution,
the abnormal earnings growth account (entry effect / continuing effect per
retired-share tranche), a two-of-three IRR (market and at-the-multiple-paid;
"at Neutral Value" is not available - no AEG engine valuation run exists for
Costco), the net retirement cost measures (here: not meaningful, since
shares outstanding ROSE over the window), funding sources, a sources-and-
uses table, and the Real Capital Base / restored return on equity. All of
this mirrors 00-Buyback-Study-METHODOLOGY-2026-08-09.md sections 4.1-4.9,
written for Apple but specified to generalize. The full narrative writeup
with every number below explained is
docs/Costco-Buyback-Study-2026-08-12.docx; this script is what produced the
figures in it.

GENUINE GAPS, not fixed here, and flagged everywhere they matter: no AEG-
engine cost-of-equity history or Neutral Value/Neutral Earnings Power exists
for Costco, so the entry-effect/AEG account and return-on-retained-earnings
section use a single PLACEHOLDER 5.5% real cost of equity, not an
engine-sourced rate - every figure that depends on it is provisional, not
settled. ProceedsFromIssuanceOfCommonStock is not tagged by Costco at all,
so the compensation wedge, net retirement cost measure C, and the Real
Capital Base restoration are all understated by an unknown amount.

TWO TAG SWITCHES WORTH KNOWING ABOUT: dividends move from PaymentsOfDividends
(through fy2021) to PaymentsOfDividendsCommonStock (fy2022 on) - merged with
merge_concept_series, not a data problem. Costco's fiscal year end wobbles
between late August and early September (Sunday closest to August 31), the
same style of wobble Home Depot's January/February year end has - handled
by CompanyConfig(fy_end_month=8) and the same fiscal_months() machinery
defect 8 fixed.

Costco pays large, irregular SPECIAL dividends on top of its regular one
(three-to-four-billion-dollar special dividends landed in fiscal 2017, 2021
and 2024, plus a smaller one in 2015) - visible in the dividend figures
below and worth knowing before reading the internal-rate-of-return section,
which assumes ALL dividends accrue to shares still held, special or not.

DATA. cost_sec_raw.json and cost_monthly.csv sit alongside this file, both
built live 2026-08-12 from data.sec.gov and Yahoo Finance. AAPL_restated.csv
(CPI deflator only, a borrowed input - Costco's own deflator index was not
sourced this run) is one level up.

Run from this directory: python3 run_COST.py
"""
import csv
import json
import sys

sys.path.insert(0, '..')
from buyback_study_TEMPLATE import (
    CompanyConfig, BuybackStudy, irr, parse_concept, merge_concept_series, solve,
)

RAW = json.load(open('cost_sec_raw.json'))
STUDY_YEARS = list(range(2015, 2026))

CFG = CompanyConfig(ticker="COST", cik="0000909832", fy_end_month=8,
                    splits=[], first_year=2015, last_year=2025,
                    coe_longrun=0.055)  # PLACEHOLDER - see note below

# Costco's last split was 2-for-1 in March 2000, decades before this window.
assert CFG.split_factor("2018-03-01") == 1.0

# ------------------------------------------------------------------- prices
PRICES = {}
for r in csv.DictReader(open('cost_monthly.csv')):
    y, m, _ = r['Date'].split('-')
    PRICES[(int(y), int(m))] = float(r['Close'])

# ------------------------------------------------------------ SEC concepts
SEC = {}
for key in ('repurchase_cash', 'repurchase_accrual', 'shares_retired',
            'treasury_shares_acquired', 'treasury_value_acquired',
            'issuance_proceeds', 'sbc', 'tax_withholding',
            'shares_outstanding'):
    SEC[key] = parse_concept(RAW.get(key, {'units': {}}))


def series(key, scale=1e6):
    return {y: e['val'] / scale for y, e in parse_concept(RAW[key]).items()}


print("=" * 90)
print("COSTCO - FOURTH COMPANY EXERCISE  (direct-tag pattern, same as Apple's own study)")
print("=" * 90)

# -------------------------------------------------------------- financials
FIN = {
    'net_income': series('net_income'),
    'diluted_eps': series('diluted_eps', 1.0),
    'wtd_diluted_shares': series('wtd_diluted_shares'),
    'operating_income': series('operating_income'),
    'tax_provision': series('tax_provision'),
    'common_equity': series('common_equity'),
    'cash': series('cash'),
    'pretax_income': series('pretax_income'),
}
FIN['financial_assets'] = FIN['cash']

# Dividend tag switch, fy2021 -> fy2022 (mode='update', no overlap).
div_old = parse_concept(RAW['dividends_old'])
div_new = parse_concept(RAW['dividends_new'])
div_merged = merge_concept_series([div_old, div_new], mode='update',
                                  expected_years=STUDY_YEARS,
                                  label='dividends paid')
FIN['dividends'] = {y: e['val'] / 1e6 for y, e in div_merged.items()}

# Gross debt: two components, both cover the study window.
lt_nc = parse_concept(RAW['lt_debt_noncurrent'])
lt_c = parse_concept(RAW['lt_debt_current'])
debt_merged = merge_concept_series([lt_nc, lt_c], mode='sum',
                                   expected_years=STUDY_YEARS,
                                   label='gross debt')
FIN['total_debt'] = {y: e['val'] / 1e6 for y, e in debt_merged.items()}

# ------------------------------------------------------------------- COE
# PLACEHOLDER: 5.5% real, NOT sourced from the AEG engine's own
# cost-of-equity curve for COST (this exercise has no engine connection).
COE_RATE = CFG.coe_longrun
INFLATION = 0.025
COE = {y: COE_RATE for y in range(2010, 2027)}
DEFL_SRC = {}
rows = list(csv.reader(open('../AAPL_restated.csv')))
hdr = rows[0]
for r in rows:
    if r[0].startswith('CPI deflator'):
        DEFL_SRC = {int(y): float(v) for y, v in zip(hdr[1:], r[1:]) if v.strip()}
DEFL = {y: DEFL_SRC.get(y - 1, DEFL_SRC.get(max(DEFL_SRC))) for y in range(2010, 2027)}

study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, COE,
                     engine={'coe_longrun': CFG.coe_longrun})
study.notes.append(
    "COST OF EQUITY IS A PLACEHOLDER (5.5% real, not sourced from the AEG "
    "engine's own cost-of-equity curve for COST) - do not quote the real "
    "earnings-yield spread or break-even figures from this run without "
    "replacing it.")
study.run()

S = study.shares_outstanding()
print()
print(f"shares-retired source: {study.retired_tag}")
print()
print(f"{'FY':>6}{'sh.out':>10}{'retired':>10}{'issued':>9}{'cash$m':>10}"
      f"{'px paid':>9}{'FY mean px':>11}{'ratio':>8}")
for y in study.years():
    if y not in study.retired:
        continue
    cash = SEC['repurchase_cash'].get(y, {}).get('val', 0) / 1e6
    px = cash / study.retired[y] if study.retired[y] else float('nan')
    mp = study.fy_mean_price(y)
    print(f"{y:>6}{S.get(y,0):>10,.0f}{study.retired[y]:>10,.1f}"
          f"{study.issued[y]:>9,.1f}{cash:>10,.0f}{px:>9,.2f}{mp:>11,.2f}"
          f"{px/mp:>8.2f}")

unresolved = sorted(getattr(study, 'unresolved_years', set()))
derived = sorted(getattr(study, 'derived_years', set()))
print()
print(f"years resolved from filed data: {len(study.years()) - len(unresolved)} "
      f"of {len(study.years())}; derived (estimated) years: {derived}; "
      f"unresolved: {unresolved}")

WINDOWS = [(2015, 2020), (2020, 2025), (2015, 2025)]
study.eps_attribution()
ric = study.return_on_incremental_capital(WINDOWS)
print()
print("RETURN ON INCREMENTAL OPERATING CAPITAL")
noa = study._noa
for y in (2015, 2020, 2025):
    if y in noa:
        print(f"  net operating assets FY{y}: {noa[y]:,.0f}m")
for (a, b), r in sorted(ric.items()):
    if r['suppressed']:
        print(f"  FY{a}-FY{b}  SUPPRESSED  d.NOA {r['d_noa']:,.0f}  ({r['why']})")
    else:
        print(f"  FY{a}-FY{b}  {100*r['ratio']:8.1f}%   d.OI {r['d_oi']:,.0f} "
              f"on d.NOA {r['d_noa']:,.0f}")

print()
print("DIVIDENDS PAID BY YEAR (special dividends will show as spikes)")
for y in sorted(FIN['dividends']):
    if y in STUDY_YEARS:
        print(f"  FY{y}: ${FIN['dividends'][y]:,.0f}m")

print()
print("PROGRAM INTERNAL RATE OF RETURN, TWO WAYS (market, and at the multiple paid)")
print("(a third column, 'at Neutral Value', is standard in this series but is NOT")
print(" available here - no AEG engine valuation run exists for Costco)")
term_mkt = study.fy_end_price(CFG.last_year)
if term_mkt is None:
    term_mkt = PRICES[max(PRICES)]
dw_mult_paid = study.timing_result['dollar_weighted_pe_paid']
term_at_mult = FIN['diluted_eps'][CFG.last_year] * dw_mult_paid
for y0 in (2021, 2016, 2015):
    f, held = study.program_flows(y0, study.retired, term_mkt)
    r = irr(f)
    f_m, _ = study.program_flows(y0, study.retired, term_at_mult)
    r_m = irr(f_m)
    if r is None:
        print(f"  from FY{y0}: no sign change in flows, IRR undefined")
        continue
    print(f"  from FY{y0}: {100*r:6.1f}% nominal @ market   {100*r_m:6.1f}% @ multiple paid   "
          f"on {held:,.0f}mn shares held at ${term_mkt:,.2f}")


def breakeven_price(y0):
    hurdle = COE_RATE + INFLATION
    return solve(lambda p: irr(study.program_flows(y0, study.retired, p)[0]), hurdle, 1.0, 5000.0)


print(f"  break-even terminal price, full program: ${breakeven_price(2015):,.2f}")

print()
print("TIMING")
t = study.timing_result
print(f"  dollar-weighted multiple paid {t['dollar_weighted_pe_paid']:.2f}x   "
      f"equal-weighted {t['equal_weighted_pe_paid']:.2f}x   "
      f"market {t['market_pe']:.2f}x")
print(f"  execution within year {100*t['execution_within_year']:+.1f}%   "
      f"allocation across years {100*t['allocation_across_years']:+.1f}%")

# ------------------------------------------------- net retirement cost check
print()
print("NET RETIREMENT COST")
gross_retired = sum(study.retired[y] for y in study.years() if y in study.retired)
net_change = S[CFG.last_year] - S[CFG.first_year - 1]
print(f"  gross retired {gross_retired:,.1f}mn   NET change in shares out "
      f"{net_change:+,.1f}mn ({'ROSE' if net_change > 0 else 'fell'})")
if net_change < 0:
    print(f"  net retirement cost = cash / |net change| = "
          f"{sum(SEC['repurchase_cash'][y]['val']/1e6 for y in study.years() if y in study.retired)/abs(net_change):,.2f}")
else:
    print("  NOT MEANINGFUL: shares outstanding rose over the window, so there is no "
          "'share removed for good' to cost out. Reporting the fact instead of a ratio, "
          "the same guard the template's own RIC check applies to a bad-sign denominator.")

print()
print(study.report())

study.to_csv('COST_buyback_dataset.csv')
print()
print("Wrote COST_buyback_dataset.csv")
print()
print("Full narrative writeup (EPS attribution, AEG account / entry effect, sources and")
print("uses, Real Capital Base, return on retained earnings - all with real numbers, all")
print("placeholder-COE and missing-tag caveats disclosed): docs/Costco-Buyback-Study-2026-08-12.docx")
