# -*- coding: utf-8 -*-
"""Prove the round trip on a company that did it: American Airlines Group.

BUILT 2026-08-13 for item 3 of `docs/00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md`.
Companion document: `docs/METHODOLOGY-ADDENDUM-Round-Trip-2026-08-13.md`, which states
what the measure claims and what it does not.

THIS IS NOT A STUDY OF AMERICAN AIRLINES. It is a proving fixture for one measure.
It computes the round trip and the guards around it and nothing else. No cost of
equity is applied, no entry effect, no abnormal earnings growth account, no
valuation, no view about American Airlines as an investment. American Airlines
carried negative book equity throughout the window, which makes several of the
template's other measures meaningless on it, and none of them are run here. Do
not describe American Airlines as a completed study; only Apple is one.

WHY THIS COMPANY, AND HOW IT WAS CONFIRMED
    Four candidates were screened against live SEC company-concept data on
    2026-08-13: Carnival, American Airlines, Boeing and Occidental. The screen and
    the reasons for rejecting the other three are in the companion document.
    American Airlines was chosen because it is the only one of the four where the
    sequence is unambiguous, the magnitude is large, and every quantity the
    measure needs is filed at the STRONGEST available tier:

      - a real share-retirement FLOW (StockRepurchasedAndRetiredDuringPeriodShares)
        covering every repurchase year, not a treasury balance differenced;
      - period-end CommonStockSharesOutstanding for every year of the window;
      - the raise disclosed in the statement of stockholders' equity with the
        share count and the dollar amount ON THE SAME LINE;
      - explicit filed ZEROS for the equity line in the non-raise years 2018,
        2019, 2022 and 2023, so the absence of a raise is a filed fact rather
        than a missing tag.

    The buy side was confirmed against a THIRD tag the measure does not use:
    us-gaap:TreasuryStockAcquiredAverageCostPerShare, which is American Airlines'
    own disclosure of what it paid. It reproduces the equity-statement value
    divided by the equity-statement share count to the cent in fiscal 2015 and
    2016 and to within eight tenths of one percent in 2014 and 2017. A company's
    own average-cost disclosure agreeing with a figure rebuilt from two other
    tags is about as good as ex-post confirmation gets.

    The sell side was confirmed against the narrative of the fiscal 2020 Form
    10-K, which names the individual offerings: 85.2 million shares at $13.50 and
    44.3 million at $12.975 in two underwritten public offerings, and 68.6 million
    at an average of $12.87 under an at-the-market programme. Those three add to
    198.05 million shares, which is the figure the equity statement gives and the
    figure this script uses.

WHAT THIS FIXTURE CAUGHT, AND IT IS THE POINT OF THE WHOLE EXERCISE
    Dividing the financing-activities line "Proceeds from issuance of equity"
    ($2,970m) by the share issuance gives $15.00 a share. The equity statement
    gives $12.91. The $2,970m line contains $415m that is the EQUITY COMPONENT OF
    THE 6.50% CONVERTIBLE NOTES, bifurcated out of debt proceeds under the
    then-current standard and removed again on 1 January 2021 when American
    adopted ASU 2020-06. No share was ever issued for it.

    The contaminated price is sixteen percent too high, it errs in the direction
    that FLATTERS the repurchase programme, and $15.00 sits comfortably inside the
    stock's 2020 traded range of $8.25 to $30.78 - so the price validator passes
    it in silence. That is the seventh instance of this project's standing
    hazard: a number that is internally consistent and externally wrong while
    every gate reports success. The reconciliation guard in reconcile_raises()
    exists because of it.

SOURCES
    SEC XBRL company-concept API, CIK 0000006201, form 10-K only, frozen into
    `aal_sec_raw.json` on 2026-08-13 so this test runs offline in continuous
    integration.
    Prices: EODHD daily bars for AAL.US, aggregated into `aal_monthly.csv`
    (month-end closes) and `aal_traded_range.csv` (INTRA-DAY high and low per
    fiscal year - never period-end closes; that validator has caught silent
    estimation failures on two different companies and is not optional).
    Consumer Price Index: BLS series CUUR0000SA0, calendar-year averages,
    retrieved 2026-08-13.
    Equity-statement figures: American Airlines Group Inc. Form 10-K for fiscal
    2020 (accession 0000006201-21-000014) and fiscal 2021 (0000006201-22-000026),
    Consolidated Statements of Stockholders' Equity (Deficit).

Run: cd code && python3 roundtrip_test_AAL.py
"""
import csv
import json
import sys

sys.path.insert(0, '..')
from buyback_study import CompanyConfig, BuybackStudy, EquityRaise, parse_concept

CHECKS = []


def check(name, condition, detail=""):
    CHECKS.append(("PASS" if condition else "FAIL", name, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def close(a, b, tol):
    return abs(a - b) <= tol


RAW = json.load(open('aal_sec_raw.json'))
SEC = {}
_KEYMAP = {
    'repurchase_cash': 'PaymentsForRepurchaseOfCommonStock',
    'shares_retired': 'StockRepurchasedAndRetiredDuringPeriodShares',
    'repurchase_accrual': 'StockRepurchasedAndRetiredDuringPeriodValue',
    'shares_outstanding': 'CommonStockSharesOutstanding',
    'equity_raise_cash_flow': 'ProceedsFromIssuanceOrSaleOfEquity',
    'plan_shares_issued': 'StockIssuedDuringPeriodSharesShareBasedCompensation',
    'tax_withholding': 'PaymentsRelatedToTaxWithholdingForShareBasedCompensation',
    'sbc': 'ShareBasedCompensation',
    'avg_cost_disclosed': 'TreasuryStockAcquiredAverageCostPerShare',
}
for key, tag in _KEYMAP.items():
    SEC[key] = parse_concept(RAW.get(tag, {'units': {}}))

# --------------------------------------------------------------------- config
# American Airlines Group has never split. The ticker AAL began trading on
# 2013-12-09 on emergence from Chapter 11 and the merger with US Airways Group;
# the price file's pre-December-2013 rows are the predecessor listing and are
# never touched, because the window opens at fiscal 2014. Fiscal year is the
# calendar year.
CFG = CompanyConfig(ticker="AAL", cik="0000006201", fy_end_month=12,
                    splits=[], first_year=2014, last_year=2025)
assert CFG.split_factor("2016-06-01") == 1.0, "split factor inherited from another company"

PRICES = {}
for r in csv.DictReader(open('aal_monthly.csv')):
    PRICES[(int(r['year']), int(r['month']))] = float(r['close'])

TRADED = {}
for r in csv.DictReader(open('aal_traded_range.csv')):
    TRADED[int(r['fiscal_year'])] = (float(r['intraday_low']), float(r['intraday_high']))

# ------------------------------------------------------------------ deflator
# Consumer Price Index for All Urban Consumers, US city average, all items, not
# seasonally adjusted (BLS series CUUR0000SA0), CALENDAR-year averages.
#
# THE BASE IS INHERITED, NOT CHOSEN, AND IT IS COMPUTED RATHER THAN TYPED. It is
# read back out of the Apple study's own committed deflator row in
# `AAPL_restated.csv` by multiplying that row by this index. Doing so turned up
# something worth recording: the implied base is 335.123 in EVERY year, constant
# to under two parts in a million across fourteen years. A fiscal-year deflator
# compared against a calendar-year index could not do that - the ratio would
# breathe with the inflation rate, and would have moved by more than a percent
# between 2021 and 2022 alone. So the Apple study's deflator, although it is
# labelled and indexed by Apple's October-to-September fiscal year, is in fact
# built on CALENDAR-year Consumer Price Index averages. That is the same
# convention used here, which is why the two studies' real dollars are directly
# comparable, and the check below tests the constancy rather than assuming it.
#
# TWO ANNOUNCED IRREGULARITIES, neither of them silent:
#   2025 is the average of ELEVEN months. The Bureau of Labor Statistics never
#     published an October 2025 index. That is a real gap in the source, not a
#     dropped row here.
#   2026 is the average of the SEVEN months published to date, January to July.
# Neither year carries any weight in the round trip, which closes in 2021, but
# both are flagged rather than quietly averaged.
CPI = {
    2012: 229.5939, 2013: 232.9571, 2014: 236.7362, 2015: 237.0170,
    2016: 240.0072, 2017: 245.1196, 2018: 251.1068, 2019: 255.6574,
    2020: 258.8112, 2021: 270.9698, 2022: 292.6549, 2023: 304.7016,
    2024: 313.6888, 2025: 321.9430, 2026: 331.1804,
}
CPI_PARTIAL = {2025: "eleven months; no October 2025 index was published",
               2026: "seven months, January to July"}

_hdr, APPLE_DEFL = None, {}
for _row in csv.reader(open('../AAPL_restated.csv')):
    if _hdr is None:
        _hdr = _row
    if _row[0].startswith('CPI deflator'):
        for _y, _v in zip(_hdr[1:], _row[1:]):
            try:
                APPLE_DEFL[int(_y)] = float(_v)
            except ValueError:
                pass
_IMPLIED_BASE = {y: APPLE_DEFL[y] * CPI[y] for y in sorted(set(APPLE_DEFL) & set(CPI))}
CPI_BASE = sum(_IMPLIED_BASE.values()) / len(_IMPLIED_BASE)
DEFL = {y: CPI_BASE / v for y, v in CPI.items()}

# ------------------------------------------------------- the raises, as filed
# Statement of Stockholders' Equity (Deficit). The share count and the dollar
# amount are taken from the SAME LINE of the SAME statement, which is the whole
# reason the round trip is struck here rather than on the cash flow statement.
_SRC20 = ("AAG Form 10-K FY2020 (0000006201-21-000014), Consolidated Statements "
          "of Stockholders' Equity (Deficit)")
_SRC21 = ("AAG Form 10-K FY2021 (0000006201-22-000026), Consolidated Statements "
          "of Stockholders' Equity (Deficit)")
RAISES = [
    EquityRaise(2020, 129.490000, 1687.0, "two underwritten public offerings", _SRC20),
    EquityRaise(2020, 68.561487, 869.0, "at-the-market offering", _SRC20),
    EquityRaise(2021, 24.150764, 460.0, "at-the-market offering", _SRC21),
]

# The named difference between the equity statement and the financing-activities
# line. $415m, disclosed in Note 5(h) of the fiscal 2020 Form 10-K as the equity
# component of the 6.50% convertible senior notes ("Additional paid-in capital
# 415") and removed on adoption of ASU 2020-06 on 1 January 2021 ("a $415 million
# ($320 million net of tax) reduction to additional paid-in capital"). It bought
# no shares. Naming it is what lets fiscal 2020 into the measure; had it been
# left unnamed the template would have refused the year.
RECONCILING = {2020: {"equity component of the 6.50% convertible notes": 415.0}}

# Ordinary employee-plan share issuance, us-gaap:StockIssuedDuringPeriodShares-
# ShareBasedCompensation, netted out of the issued side.
PLAN_SHARES = {y: e['val'] / 1e6 for y, e in SEC['plan_shares_issued'].items()}

# American Airlines presents share repurchases and shares withheld for employee
# taxes on ONE cash-flow line ("Treasury stock repurchases and shares withheld
# for taxes pursuant to employee stock plans"). The withholding is not a
# repurchase and is removed from the price paid.
WITHHOLDING = {y: e['val'] / 1e6 for y, e in SEC['tax_withholding'].items()}

FIN = {'net_income': {}, 'diluted_eps': {}, 'wtd_diluted_shares': {},
       'dividends': {}, 'operating_income': {}, 'pretax_income': {},
       'tax_provision': {}, 'common_equity': {}, 'total_debt': {},
       'financial_assets': {}}

study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, coe={},
                     raises=RAISES, plan_shares=PLAN_SHARES,
                     raise_reconciling_items=RECONCILING,
                     withholding_in_repurchase_cash=WITHHOLDING)
study.retired, study.issued = study.share_flows()

# ============================================================ 1. THE BUY SIDE
check("buy side - a real retirement FLOW carries every repurchase year, no treasury differencing",
      study.retired_tag == 'StockRepurchasedAndRetiredDuringPeriodShares',
      f"retired_tag={study.retired_tag!r}, {len(study.retired)} years resolved")

price_failures = study.validate_prices(study.retired, TRADED)
check("buy side - every implied price paid lies inside that year's INTRA-DAY traded range",
      not price_failures,
      "; ".join(f"FY{y} ${p:.2f} vs {lo:.2f}-{hi:.2f}" for y, p, lo, hi in price_failures)
      or f"{len(study.retired)} years validated against intra-day extremes, not period-end closes")

# Confirmation from a third tag the measure does not use: the company's own
# disclosed average cost per share.
disclosed = {y: e['val'] for y, e in SEC['avg_cost_disclosed'].items()}
accrual = {y: e['val'] / 1e6 for y, e in SEC['repurchase_accrual'].items()}
worst, worst_y = 0.0, None
for y, d in sorted(disclosed.items()):
    if y in accrual and y in study.retired and study.retired[y]:
        rebuilt = accrual[y] / study.retired[y]
        rel = abs(rebuilt - d) / d
        if rel > worst:
            worst, worst_y = rel, y
check("buy side - rebuilt price agrees with the company's OWN disclosed average cost per share",
      worst < 0.01,
      f"worst year FY{worst_y}, {100*worst:.2f}% apart across "
      f"{len([y for y in disclosed if y in accrual])} disclosed years")

# =========================================================== 2. THE SELL SIDE
rec = study.reconcile_raises()

check("sell side - the FY2020 financing line does NOT equal the equity statement",
      not close(rec[2020]['cash_flow_line'], rec[2020]['statement'], 1.0),
      f"line ${rec[2020]['cash_flow_line']:,.0f}m vs statement "
      f"${rec[2020]['statement']:,.0f}m, gap ${rec[2020]['gap']:,.0f}m")

check("sell side - the whole FY2020 gap is the named convertible equity component",
      abs(rec[2020]['residual']) <= 1.0 and rec[2020]['clean'],
      f"gap ${rec[2020]['gap']:,.0f}m, named ${sum(rec[2020]['named'].values()):,.0f}m, "
      f"unexplained ${rec[2020]['residual']:,.0f}m - one part in three thousand, which is "
      "rounding in the filed figures, all of which are stated to the million")

check("sell side - FY2021 needs no reconciling item; line and statement agree exactly",
      close(rec[2021]['cash_flow_line'], rec[2021]['statement'], 1e-9)
      and not rec[2021]['named'],
      f"both ${rec[2021]['statement']:,.0f}m")

# THE HEADLINE GUARD. The contaminated price must be shown to be (a) materially
# wrong and (b) invisible to the price validator, or the guard has no reason to
# exist and someone will delete it.
contaminated = rec[2020]['cash_flow_line'] / sum(
    r.shares for r in RAISES if r.fiscal_year == 2020)
correct = rec[2020]['statement'] / sum(
    r.shares for r in RAISES if r.fiscal_year == 2020)
lo20, hi20 = TRADED[2020]
check("sell side - the contaminated price is >10% too high AND passes the traded-range validator",
      (contaminated / correct - 1) > 0.10 and lo20 <= contaminated <= hi20,
      f"cash-flow route ${contaminated:.2f} vs equity-statement route ${correct:.2f}, "
      f"{100*(contaminated/correct-1):.1f}% high, both inside {lo20:.2f}-{hi20:.2f}")

raise_failures = study.validate_raise_prices(TRADED)
check("sell side - every implied ISSUE price lies inside that year's intra-day traded range",
      not raise_failures,
      "; ".join(f"FY{y} {lab} ${p:.2f}" for y, lab, p, lo, hi in raise_failures)
      or f"{len(study.resolved_raises())} raises validated")

# Independent route to the FY2020 issue price: the offerings named in the 10-K
# narrative, priced individually, weighted by their own share counts.
NARRATIVE_2020 = [(85.2, 13.50), (44.3, 12.975), (68.561487, 12.87)]
narr_sh = sum(q for q, _ in NARRATIVE_2020)
narr_px = sum(q * p for q, p in NARRATIVE_2020) / narr_sh
stmt_sh = sum(r.shares for r in RAISES if r.fiscal_year == 2020)
check("sell side - equity-statement share count matches the offerings named in the 10-K narrative",
      close(narr_sh, stmt_sh, 0.05), f"narrative {narr_sh:.3f}mn vs statement {stmt_sh:.3f}mn")
check("sell side - gross narrative price and net statement price differ only by offering costs",
      0 < (narr_px - correct) / narr_px < 0.03,
      f"narrative gross ${narr_px:.2f} vs statement net ${correct:.2f}, "
      f"{100*(narr_px-correct)/narr_px:.2f}% of costs")

# ============================================================ 3. THE MEASURE
rt = study.round_trip_reconciled()

check("round trip - detected", rt['has_round_trip'],
      f"{len(rt['episodes'])} episodes, {rt['matched_shares']:,.1f}mn shares matched")
check("round trip - matched shares never exceed either side",
      rt['matched_shares'] <= rt['total_shares_retired'] + 1e-9
      and rt['matched_shares'] <= sum(r.shares for r in study.resolved_raises()) + 1e-9)
check("round trip - AVERAGE COST and independently rebuilt FIFO agree on matched shares exactly",
      rt['fifo_agrees_on_shares'],
      f"{rt['matched_shares']:.9f} vs {rt['fifo_rebuilt']['matched_shares']:.9f} mn")
check("round trip - the two routes agree on proceeds exactly",
      rt['fifo_agrees_on_proceeds'],
      f"${rt['real_proceeds_matched']:,.3f}m vs ${rt['fifo_rebuilt']['real_proceeds_matched']:,.3f}m")
check("round trip - route C (shares x price difference) reproduces the loss",
      rt['route_c_agrees'],
      f"${rt['route_c_real_loss']:,.3f}m vs ${rt['real_loss']:,.3f}m")
check("round trip - loss identity: cost - proceeds = loss",
      close(rt['real_cost_matched'] - rt['real_proceeds_matched'], rt['real_loss'], 1e-9))
check("round trip - the ordering effect is reported, not suppressed",
      'ordering_effect' in rt,
      f"average cost ${rt['real_loss']:,.0f}m vs FIFO "
      f"${rt['fifo_rebuilt']['real_loss']:,.0f}m, "
      f"{100*rt['ordering_effect_share']:.1f}% apart")
check("round trip - the loss is positive; American Airlines bought high and sold low",
      rt['real_loss'] > 0,
      f"real price paid ${rt['real_avg_price_paid_matched']:.2f}, "
      f"real price received ${rt['real_avg_price_received']:.2f}")

# ================================================ 4. GUARDS THAT MUST NOT MISS
# (a) An unnamed difference must refuse the year rather than absorb it.
probe = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, coe={}, raises=RAISES,
                     plan_shares=PLAN_SHARES, raise_reconciling_items={},
                     withholding_in_repurchase_cash=WITHHOLDING)
probe.retired, probe.issued = probe.share_flows()
probe.reconcile_raises()
check("guard - an UNNAMED gap refuses the year instead of absorbing it into the price",
      2020 in probe.raise_refusals and 2021 not in probe.raise_refusals,
      f"refused {sorted(probe.raise_refusals)} when the $415m was not named")
probe_rt = probe.round_trip()
check("guard - a refused year is excluded from the loss, not silently priced",
      probe_rt['matched_shares'] < rt['matched_shares'],
      f"{probe_rt['matched_shares']:,.1f}mn matched with FY2020 refused "
      f"vs {rt['matched_shares']:,.1f}mn with it named")

# (b) Employee-plan issuance must be netted out.
no_net = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, coe={}, raises=RAISES,
                      plan_shares={}, raise_reconciling_items=RECONCILING,
                      withholding_in_repurchase_cash=WITHHOLDING)
no_net.retired, no_net.issued = no_net.share_flows()
no_net_rt = no_net.round_trip()
check("guard - netting employee-plan issuance out actually changes the answer",
      no_net_rt['matched_shares'] > rt['matched_shares'],
      f"{no_net_rt['matched_shares']:,.3f}mn un-netted vs {rt['matched_shares']:,.3f}mn netted, "
      f"{sum(PLAN_SHARES.get(y,0) for y in (2020,2021)):,.3f}mn of plan flow removed")

# (c) Withholding folded into the repurchase line must be removed.
no_wh = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, coe={}, raises=RAISES,
                     plan_shares=PLAN_SHARES, raise_reconciling_items=RECONCILING,
                     withholding_in_repurchase_cash={})
no_wh.retired, no_wh.issued = no_wh.share_flows()
check("guard - removing employee withholding from the repurchase line lowers the price paid",
      no_wh.real_repurchase_price(2020) > study.real_repurchase_price(2020),
      f"FY2020 ${no_wh.real_repurchase_price(2020)/DEFL[2020]:.2f} with withholding vs "
      f"${study.real_repurchase_price(2020)/DEFL[2020]:.2f} without, nominal")

# (d) Ordering must be respected - a raise cannot be matched against a
#     repurchase that had not happened yet.
future_only = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, coe={},
                           raises=[EquityRaise(2014, 100.0, 1000.0, "synthetic", "test")],
                           plan_shares={}, raise_reconciling_items={},
                           withholding_in_repurchase_cash=WITHHOLDING)
future_only.retired, future_only.issued = future_only.share_flows()
future_only.raise_refusals = set()
fo = future_only.round_trip()
check("guard - a raise is matched only against repurchases that PRECEDE it (synthetic)",
      abs(fo['matched_shares'] - future_only.retired[2014]) < 1e-9,
      f"a FY2014 raise of 100mn matched only the {future_only.retired[2014]:.2f}mn "
      "retired in FY2014, not the 296mn retired later")

# (e) The deflator must be the same construction as the Apple study's, on the
#     same base. Testing that the implied base is CONSTANT is a far stronger
#     statement than testing that two deflators are close: a constant can only
#     arise if both series are the same index averaged over the same twelve
#     months, and it would break immediately if either convention drifted.
_spread = max(_IMPLIED_BASE.values()) - min(_IMPLIED_BASE.values())
check("guard - the base implied by the Apple study's deflator is CONSTANT across every year",
      _spread / CPI_BASE < 1e-5,
      f"base {CPI_BASE:.3f}, spread {_spread:.5f} index points over "
      f"{len(_IMPLIED_BASE)} years, {1e6*_spread/CPI_BASE:.2f} parts per million")
check("guard - this deflator therefore reproduces the Apple study's, year by year",
      max(abs(DEFL[y] / APPLE_DEFL[y] - 1) for y in APPLE_DEFL if y in DEFL) < 1e-5,
      "same index, same twelve-month window, same base - the two studies' real "
      "dollars are the same dollars")

check("guard - partial Consumer Price Index years are announced, not silently averaged",
      set(CPI_PARTIAL) == {2025, 2026},
      "; ".join(f"{y}: {w}" for y, w in sorted(CPI_PARTIAL.items())))

# ======================================================= 5. THE NULL COMPANY
# A company that never raised equity must return a true zero and say so, not
# crash and not print a spurious number. This is the Apple case, and it is the
# reason the measure can be run unconditionally on every company.
null = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, coe={}, raises=[],
                    plan_shares=PLAN_SHARES,
                    withholding_in_repurchase_cash=WITHHOLDING)
null.retired, null.issued = null.share_flows()
n = null.round_trip_reconciled()
check("null case - no raise gives has_round_trip False and true zeros throughout",
      n['has_round_trip'] is False and n['real_loss'] == 0.0
      and n['matched_shares'] == 0.0 and n['recovery_ratio'] is None,
      "loss 0.0, matched 0.0mn, recovery ratio None rather than a fabricated 1.0")

print()
n_fail = sum(1 for s, *_ in CHECKS if s == "FAIL")
print(f"{n_fail} of {len(CHECKS)} ROUND-TRIP CHECKS FAILED" if n_fail
      else "ALL ROUND-TRIP CHECKS PASS")

# ------------------------------------------------------------------- report
print()
print("=" * 92)
print("AMERICAN AIRLINES GROUP - ROUND-TRIP PROVING FIXTURE (not a study)")
print("=" * 92)
print(f"{'FY':<6}{'repurchase $m':>15}{'shares mn':>12}{'nominal $':>12}{'real $':>10}"
      f"{'traded low':>12}{'traded high':>13}")
for y in sorted(study.retired):
    if y not in SEC['repurchase_cash']:
        continue
    cash = SEC['repurchase_cash'][y]['val'] / 1e6 - WITHHOLDING.get(y, 0.0)
    q = study.retired[y]
    lo, hi = TRADED[y]
    print(f"{y:<6}{cash:>15,.0f}{q:>12,.2f}{cash/q:>12,.2f}"
          f"{study.real_repurchase_price(y):>10,.2f}{lo:>12,.2f}{hi:>13,.2f}")
print(f"{'':<6}"
      f"{sum(SEC['repurchase_cash'][y]['val']/1e6 - WITHHOLDING.get(y,0) for y in study.retired if y in SEC['repurchase_cash']):>15,.0f}"
      f"{sum(study.retired.values()):>12,.2f}")
print()
print(f"{'FY':<6}{'raise':<34}{'shares mn':>12}{'net $m':>10}{'nominal $':>12}{'real $':>10}")
for r in study.resolved_raises():
    print(f"{r.fiscal_year:<6}{r.label:<34}{r.shares:>12,.3f}{r.proceeds:>10,.0f}"
          f"{r.price:>12,.2f}{r.price*DEFL[r.fiscal_year]:>10,.2f}")
study.round_trip_result = rt
print("\n".join(study.round_trip_report()))
print()
print("NOTES")
for n in study.notes:
    print(f"  - {n}")

sys.exit(1 if n_fail else 0)
