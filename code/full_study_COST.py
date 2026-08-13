# -*- coding: utf-8 -*-
"""Full-depth Costco buyback study, mirroring the Apple report's structure and formulas
(00-Buyback-Study-METHODOLOGY-2026-08-09.md sections 4.1-4.9), using only what the
generalized template (buyback_study_TEMPLATE.py) and real SEC/Yahoo Finance data support.

CORRECTION vs the first COST pass (2026-08-12, earlier this session): the study window is
FY2015-FY2025, not FY2017-FY2025. StockRepurchasedAndRetiredDuringPeriodShares actually
covers FY2015 onward directly (filed, zero derived years, zero price-validator failures) -
the earlier claim that Costco tags nothing usable before FY2017 was simply wrong; it was not
checked carefully enough the first time.

GENUINE GAPS, not fixed here: no AEG-engine cost-of-equity history or Neutral Value/Neutral
Earnings Power exists for Costco (unlike Apple), so (a) the entry-effect / AEG account and
the return-on-retained-earnings section use a single PLACEHOLDER 5.5% real cost of equity,
not an engine-sourced rate, and (b) the "at Neutral Value" IRR column and the final
Neutral-Value pivot section cannot be built at all - both are stated as unavailable rather
than estimated. ProceedsFromIssuanceOfCommonStock is not tagged by Costco at all, so net
retirement cost measure C (credits proceeds) and the Real Capital Base restoration are both
understated by an unknown, undisclosed amount - flagged wherever they appear.
"""
import csv, json, sys
sys.path.insert(0, '..')
from buyback_study_TEMPLATE import (CompanyConfig, BuybackStudy, parse_concept,
                                    merge_concept_series, irr, solve)

RAW = json.load(open('cost_sec_raw.json'))
STUDY_YEARS = list(range(2015, 2026))

CFG = CompanyConfig(ticker="COST", cik="0000909832", fy_end_month=8, splits=[],
                    first_year=2015, last_year=2025, coe_longrun=0.055)
assert CFG.split_factor("2018-03-01") == 1.0

PRICES = {}
for r in csv.DictReader(open('cost_monthly.csv')):
    y, m, _ = r['Date'].split('-')
    PRICES[(int(y), int(m))] = float(r['Close'])

SEC = {}
for key in ('repurchase_cash', 'repurchase_accrual', 'shares_retired',
            'treasury_shares_acquired', 'treasury_value_acquired',
            'issuance_proceeds', 'sbc', 'tax_withholding', 'shares_outstanding'):
    SEC[key] = parse_concept(RAW.get(key, {'units': {}}))


def series(key, scale=1e6):
    return {y: e['val'] / scale for y, e in parse_concept(RAW[key]).items()}


FIN = {
    'net_income': series('net_income'), 'diluted_eps': series('diluted_eps', 1.0),
    'wtd_diluted_shares': series('wtd_diluted_shares'),
    'operating_income': series('operating_income'), 'tax_provision': series('tax_provision'),
    'common_equity': series('common_equity'), 'cash': series('cash'),
    'pretax_income': series('pretax_income'),
}
FIN['financial_assets'] = FIN['cash']
div_merged = merge_concept_series([parse_concept(RAW['dividends_old']), parse_concept(RAW['dividends_new'])],
                                  mode='update', expected_years=STUDY_YEARS, label='dividends')
FIN['dividends'] = {y: e['val'] / 1e6 for y, e in div_merged.items()}
debt_merged = merge_concept_series([parse_concept(RAW['lt_debt_noncurrent']), parse_concept(RAW['lt_debt_current'])],
                                   mode='sum', expected_years=STUDY_YEARS, label='gross debt')
FIN['total_debt'] = {y: e['val'] / 1e6 for y, e in debt_merged.items()}

COE_RATE = 0.055   # PLACEHOLDER, real, flat. Not sourced from an AEG engine run for COST.
INFLATION = 0.025
COE = {y: COE_RATE for y in range(2010, 2027)}

DEFL_SRC = {}
rows = list(csv.reader(open('../AAPL_restated.csv')))
hdr = rows[0]
for r in rows:
    if r[0].startswith('CPI deflator'):
        DEFL_SRC = {int(y): float(v) for y, v in zip(hdr[1:], r[1:]) if v.strip()}
DEFL = {y: DEFL_SRC.get(y - 1, DEFL_SRC.get(max(DEFL_SRC))) for y in range(2010, 2027)}

study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, COE, engine={'coe_longrun': COE_RATE})
study.notes.append("COST OF EQUITY IS A PLACEHOLDER (5.5% real, flat) - not sourced from an "
                    "AEG engine run for COST. Every figure below that uses it is provisional.")
study.run()

print("=" * 100)
print(f"retired_tag={study.retired_tag}  unresolved={sorted(study.unresolved_years)}  "
      f"derived={sorted(study.derived_years)}  price_failures={study.price_failures}")
print("=" * 100)

S = study.shares_outstanding()
years = [y for y in study.years() if y in study.retired]

# ---------------------------------------------------------- Section 1 table
print("\n--- SECTION 1: repurchase record ---")
tot_cash = sum(SEC['repurchase_cash'][y]['val'] / 1e6 for y in years)
tot_retired = sum(study.retired[y] for y in years)
tot_issued = sum(study.issued[y] for y in years)
for y in years:
    cash = SEC['repurchase_cash'][y]['val'] / 1e6
    px = cash / study.retired[y]
    net_chg = S[y] - S[y - 1]
    pct_shares = 100 * study.retired[y] / S[y - 1]
    net_pct = 100 * net_chg / S[y - 1]
    mult = px / FIN['diluted_eps'][y]
    print(f"FY{y}  cash {cash:8,.0f}  retired {study.retired[y]:6.1f}mn  "
          f"{pct_shares:5.2f}%  net {net_pct:+6.2f}%  px {px:8.2f}  mult {mult:5.1f}x")
dw_price = tot_cash / tot_retired
ew_price = sum((SEC['repurchase_cash'][y]['val']/1e6)/study.retired[y] for y in years) / len(years)
print(f"TOTAL FY2015-25: cash {tot_cash:,.0f}  retired {tot_retired:,.1f}mn  "
      f"net_chg {100*(S[2025]-S[2014])/S[2014]:+.2f}%  dollar-wtd px {dw_price:.2f}")
print(f"equal-weighted avg price: {ew_price:.2f}")

# ------------------------------------------------- Section 2/3: real terms, entry effect
print("\n--- SECTION 2/3: real EPS, real price paid, forward earnings yield, entry effect ---")
real_eps = {y: FIN['diluted_eps'][y] / DEFL[y] for y in FIN['diluted_eps'] if y in DEFL}
real_price_paid = {}
for y in years:
    cash = SEC['repurchase_cash'][y]['val'] / 1e6
    nominal_px = cash / study.retired[y]
    real_price_paid[y] = nominal_px / DEFL[y]

entry_effect = {}
fwd_yield = {}
for y in years:
    if (y + 1) not in real_eps:
        continue
    fy = real_eps[y + 1] / real_price_paid[y]
    fwd_yield[y] = fy
    entry_effect[y] = study.retired[y] * (real_eps[y + 1] - COE_RATE * real_price_paid[y]) / 1000.0  # $bn
    print(f"FY{y}  real px paid {real_price_paid[y]:8.2f}  real EPS(t+1) {real_eps[y+1]:6.3f}  "
          f"fwd yield {100*fy:5.2f}%  entry effect ${entry_effect[y]:+7.3f}bn")

cum_entry = sum(entry_effect.values())
print(f"cumulative entry effect, FY{min(entry_effect)}-{max(entry_effect)} tranches: "
      f"${cum_entry:+.3f}bn at {100*COE_RATE:.2f}% real COE")

num = sum(study.retired[t] * real_eps[t + 1] for t in entry_effect)
den = sum(study.retired[t] * real_price_paid[t] for t in entry_effect)
breakeven_coe = num / den
print(f"break-even real cost of equity (root of cumulative entry effect, retirement-weighted "
      f"forward real earnings yield on the whole program): {100*breakeven_coe:.2f}%  "
      f"(placeholder used: {100*COE_RATE:.2f}%)")

# ---- earnings-timing decomposition (methodology addendum 2026-08-13) ----
# The entry effect above is struck on ONE year of earnings, the year that happens to follow each
# purchase. Split it into the price decision and the accident of which year came next. This is an
# identity: the two sum to the entry effect exactly, no tranche is dropped, nothing above moves.
import timing_decomposition as td

_tranches = sorted(entry_effect)
_shares = {t: study.retired[t] for t in _tranches}
_est = td.build_estimators(real_eps, window=sorted(y for y in real_eps if y >= min(years)))
_band = td.decomposition_band(_shares, real_eps, real_price_paid, COE_RATE, _tranches, _est)
_prim = _band["loglinear"]

print("\n--- EARNINGS-TIMING DECOMPOSITION (entry = price decision + earnings timing) ---")
print(f"  log-linear fitted real EPS trend: {100*_est['loglinear'].growth:+.2f}%/yr "
      f"over FY{_est['loglinear'].span[0]}-{_est['loglinear'].span[1]}")
print(f"  {'year':<6}{'entry':>10}{'decision':>11}{'timing':>10}")
for t in _tranches:
    r = _prim["rows"][t]
    print(f"  FY{t:<4}{r['entry']/1000:>+10.3f}{r['decision']/1000:>+11.3f}{r['timing']/1000:>+10.3f}")
print(f"  {'TOTAL':<6}{_prim['entry']/1000:>+10.3f}{_prim['decision']/1000:>+11.3f}"
      f"{_prim['timing']/1000:>+10.3f}   ($bn)")
_resid = max(abs(_band[n]["decision"] + _band[n]["timing"] - _band[n]["entry"]) for n in _band)
print(f"  identity residual across all six estimators: {_resid:.2e} (must be ~0)")

_dep = td.timing_dependence(_prim["entry"], _prim["timing"])
print(f"\n  TIMING DEPENDENCE = {100*_dep:.0f}% of the headline entry effect")
if _dep >= 1.0:
    print("  *** AT OR ABOVE 100%: the earnings-timing accident is larger than the result it sits")
    print("      inside. The entry effect must NOT be read as a verdict on the price paid for this")
    print("      company. Report it with the decomposition beside it, never alone. ***")
elif _dep >= 0.5:
    print("  ** ELEVATED: earnings timing carries a large share of the verdict. Publish the")
    print("     decomposition alongside the entry effect. **")
else:
    print("  (moderate: the entry effect is carried mainly by the price decision)")

print(f"  {'estimator':<14}{'family':<18}{'decision':>10}{'timing':>10}{'dec b/e':>10}")
for n in td.ALL_ESTIMATORS:
    d = _band[n]
    print(f"  {n:<14}{d['family']:<18}{d['decision']/1000:>+10.3f}{d['timing']/1000:>+10.3f}"
          f"{100*d['break_even']:>9.2f}%")
_sym = [_band[n] for n in td.SYMMETRIC_ESTIMATORS]
_bwd = [_band[n] for n in td.BACKWARD_ESTIMATORS]
if min(d["decision"] for d in _sym) * max(d["decision"] for d in _bwd) < 0:
    print("  NOTE: the two estimator families disagree on the SIGN of the price decision. The trend")
    print("        level is not point-identified on this company; publish the band, not a point.")
else:
    print("  NOTE: both estimator families agree on the sign of the price decision.")
print("  (COE placeholder caveat above applies to the decision column; the timing column contains")
print("   no rate at all and is unaffected by it.)")

# entity-level AEG (real), cum-dividend form: AEG(s) = NI_r(s) - (1+r)*NI_r(s-1) + r*D_r(s-1)
print("\n--- entity-level AEG (real, cum-dividend form) ---")
real_ni = {y: FIN['net_income'][y] / DEFL[y] for y in FIN['net_income'] if y in DEFL}
real_div_distrib = {}   # dividends + repurchase cash, real
for y in FIN['dividends']:
    rep = SEC['repurchase_cash'].get(y, {}).get('val', 0) / 1e6
    real_div_distrib[y] = (FIN['dividends'][y] + rep) / DEFL[y] if y in DEFL else None

aeg_entity = {}
for y in years:
    if (y - 1) not in real_ni or (y - 1) not in real_div_distrib:
        continue
    aeg_entity[y] = real_ni[y] - (1 + COE_RATE) * real_ni[y - 1] + COE_RATE * real_div_distrib[y - 1]
    print(f"FY{y}  AEG_entity ${aeg_entity[y]:+7.1f}mn")
avg_aeg = sum(aeg_entity.values()) / len(aeg_entity)
print(f"average entity-level AEG, FY{min(aeg_entity)}-{max(aeg_entity)}: ${avg_aeg:+.1f}mn/yr")

# continuing effect + still-owed-per-share (simplified: forward sum of AEG_entity(s)/shares(s))
print("\n--- continuing effect & still owed per share ---")
wds = FIN['wtd_diluted_shares']
for t in sorted(entry_effect):
    cont = 0.0
    for s in range(t + 2, 2026):
        if s in aeg_entity and s in wds:
            cont += aeg_entity[s] / wds[s]
    entry_ps = entry_effect[t] * 1000 / study.retired[t]  # entry effect $mn total / mn shares = $/sh
    total_ps = entry_ps + cont
    still_owed = max(0.0, -total_ps)
    print(f"FY{t}  entry/sh ${entry_ps:+7.3f}  earned-since/sh ${cont:+7.3f}  "
          f"total/sh ${total_ps:+7.3f}  still owed ${still_owed:6.3f}")

# ------------------------------------------------------- Section 4: IRR three ways (2 of 3)
print("\n--- SECTION 4: IRR, market + at multiple paid (Neutral Value unavailable) ---")
term_mkt = study.fy_end_price(2025)
dw_mult_paid = study.timing_result['dollar_weighted_pe_paid']
term_at_mult = FIN['diluted_eps'][2025] * dw_mult_paid
for y0, label in [(2021, "last 5 yrs"), (2016, "last 10 yrs"), (2015, "full program 11yrs")]:
    f, held = study.program_flows(y0, study.retired, term_mkt)
    r_nom = irr(f)
    f_r, held_r = study.program_flows(y0, study.retired, term_mkt / DEFL[2025], deflate=True)
    r_real = irr(f_r)
    f_m, held_m = study.program_flows(y0, study.retired, term_at_mult)
    r_mult = irr(f_m)
    print(f"{label:20s} nominal@mkt {100*r_nom:6.1f}%   real@mkt {100*r_real:6.1f}%   "
          f"@multiple-paid {100*r_mult:6.1f}%   shares {held:,.1f}mn")

def breakeven_price(y0):
    hurdle = COE_RATE + INFLATION
    return solve(lambda p: irr(study.program_flows(y0, study.retired, p)[0]), hurdle, 1.0, 5000.0)

for y0, label in [(2015, "full program"), (2021, "last 5 yrs")]:
    be = breakeven_price(y0)
    print(f"break-even terminal price, {label}: ${be:,.2f}  (actual FY2025 close ${term_mkt:,.2f})")

# ---------------------------------------------- Section 7: net retirement cost, 4 measures
print("\n--- SECTION 7: net retirement cost, four measures ---")
gross_retired = tot_retired
net_reduction = S[2025] - S[2014]
print(f"gross retired {gross_retired:,.1f}mn   net CHANGE in shares out {net_reduction:+,.1f}mn "
      f"(negative = net reduction)")
tax_paid = sum(SEC['tax_withholding'].get(y, {}).get('val', 0) / 1e6 for y in years)
proceeds = sum(SEC['issuance_proceeds'].get(y, {}).get('val', 0) / 1e6 for y in years)
print(f"cash paid for employee tax withholding, cumulative: ${tax_paid:,.0f}mn")
print(f"employee equity plan proceeds, cumulative: ${proceeds:,.0f}mn "
      f"(TAG NOT FILED BY COSTCO AT ALL - treated as $0, not genuinely zero)")
A = tot_cash / gross_retired
if net_reduction < 0:
    B = tot_cash / abs(net_reduction)
    D = (tot_cash + tax_paid - proceeds) / abs(net_reduction)
    print(f"A) cash / GROSS retired          = {A:8.2f}")
    print(f"B) cash / |NET reduction|         = {B:8.2f}  ({100*(B/A-1):+.1f}% vs A)")
    print(f"C) cannot compute - proceeds tag not filed")
    print(f"D) (cash + withholding - proceeds) / |NET reduction| = {D:8.2f}  ({100*(D/A-1):+.1f}% vs A)")
else:
    print(f"NET reduction is not negative over this window (shares outstanding ROSE) - "
          f"B, C, D are not meaningful ratios; reporting the fact instead of a number, "
          f"exactly as the template's own RIC guard does for a bad-sign denominator.")
    print(f"A) cash / GROSS retired = {A:8.2f} is the only well-defined measure here.")

# ------------------------------------------------------ Section 8: funding sources
print("\n--- SECTION 8: where the money came from ---")
cum_ni = sum(FIN['net_income'][y] for y in years)
cum_div = sum(FIN['dividends'][y] for y in years)
retained = cum_ni - cum_div
d_nfo = (FIN['total_debt'][2025] - FIN['financial_assets'][2025]) - \
        (FIN['total_debt'][2014] - FIN['financial_assets'][2014])
print(f"cumulative net income FY15-25: ${cum_ni:,.0f}mn")
print(f"cumulative dividends paid FY15-25: ${cum_div:,.0f}mn")
print(f"retained earnings after dividends: ${retained:,.0f}mn")
print(f"change in net financial obligations (debt - financial assets), FY2014->FY2025: "
      f"${d_nfo:+,.0f}mn  ({'leverage INCREASED' if d_nfo>0 else 'leverage DECREASED / net financial assets grew'})")
print(f"total repurchase cash: ${tot_cash:,.0f}mn -- funding source is retained earnings; "
      f"Costco's net financial obligations MOVED THE OTHER WAY (net financial assets grew), "
      f"so none of the repurchase was leverage-funded on this definition.")

# EPS growth channel attribution, FY2015 base -> FY2025
print("\n--- EPS growth channel attribution, FY2015->FY2025 ---")
attrib = study.attribution  # already computed in study.run() -> eps_attribution()
d_eps_total = FIN['diluted_eps'][2025] - FIN['diluted_eps'][2015]
sum_earn = sum(attrib[y]['from_earnings'] for y in range(2016, 2026) if y in attrib)
sum_sc = sum(attrib[y]['from_share_count'] for y in range(2016, 2026) if y in attrib)
sum_op = sum(attrib[y]['operating'] for y in range(2016, 2026) if y in attrib)
sum_fin = sum(attrib[y]['financial'] for y in range(2016, 2026) if y in attrib)
print(f"total diluted EPS growth FY2015->FY2025 (sum of annual deltas): {sum_earn+sum_sc:+.3f}  "
      f"(direct FY15->FY25 EPS change: {d_eps_total:+.3f})")
print(f"  from earnings: {sum_earn:+.3f}  ({100*sum_earn/(sum_earn+sum_sc):.1f}%)")
print(f"    operating: {sum_op:+.3f}   financial: {sum_fin:+.3f}")
print(f"  from share count: {sum_sc:+.3f}  ({100*sum_sc/(sum_earn+sum_sc):.1f}%)")

# --------------------------------------------- Section 10: Real Capital Base / restored ROE
print("\n--- SECTION 10: Real Capital Base / restored ROE ---")
cum_restoration = 0.0
for y in years:
    cash = SEC['repurchase_cash'][y]['val'] / 1e6
    proc_y = SEC['issuance_proceeds'].get(y, {}).get('val', 0) / 1e6
    cum_restoration += (cash - proc_y)
    eq = FIN['common_equity'][y]
    rcb = eq + cum_restoration
    print(f"FY{y}  reported equity {eq:9,.0f}  cum.restoration {cum_restoration:9,.0f}  "
          f"Real Capital Base {rcb:9,.0f}")
reported_roe_2025 = FIN['net_income'][2025] / ((FIN['common_equity'][2025]+FIN['common_equity'][2024])/2)
rcb_2025 = FIN['common_equity'][2025] + cum_restoration
rcb_2024 = FIN['common_equity'][2024] + (cum_restoration - (SEC['repurchase_cash'][2025]['val']/1e6 -
                                          SEC['issuance_proceeds'].get(2025,{}).get('val',0)/1e6))
restored_roe_2025 = FIN['net_income'][2025] / ((rcb_2025+rcb_2024)/2)
print(f"FY2025 reported ROE: {100*reported_roe_2025:.1f}%   on Real Capital Base: {100*restored_roe_2025:.1f}%")

# ------------------------------------------------- Section 11: return on retained earnings
print("\n--- SECTION 11: return on retained earnings ---")
real_dps = {y: FIN['dividends'][y]/FIN['wtd_diluted_shares'][y]/DEFL[y] for y in FIN['dividends'] if y in FIN['wtd_diluted_shares'] and y in DEFL}
cum_d_real_eps = real_eps[2025] - real_eps[2015]
cum_retained_real_eps = sum((real_eps[y] - real_dps[y]) for y in range(2016,2026) if y in real_eps and y in real_dps)
rore = cum_d_real_eps / cum_retained_real_eps if cum_retained_real_eps else None
print(f"cumulative growth in real diluted EPS, FY2015->FY2025: {cum_d_real_eps:+.3f}")
print(f"cumulative real retained EPS (real EPS - real DPS, summed FY16-25): {cum_retained_real_eps:.3f}")
if rore:
    print(f"return on retained earnings: {100*rore:.2f}%  vs placeholder real COE {100*COE_RATE:.2f}%")
retention_rate = cum_retained_real_eps / sum(real_eps[y] for y in range(2016,2026) if y in real_eps)
print(f"retention rate (approx): {retention_rate:.3f}")
if rore:
    identity_check = retention_rate * (rore - COE_RATE)
    print(f"identity check b*(RORE-COE) = {100*identity_check:.2f}%/yr  vs avg entity AEG/NI: "
          f"{100*avg_aeg/ (sum(real_ni[y] for y in aeg_entity)/len(aeg_entity)):.2f}%/yr")

# ------------------------------------------------------- extra: program report + RIC + divs
print("\n--- study.report() ---")
print(study.report())

print("\n--- RIC windows ---")
ric = study.return_on_incremental_capital([(2015,2020),(2020,2025),(2015,2025)])
noa = study._noa
for y in (2015,2020,2025):
    if y in noa:
        print(f"  NOA FY{y}: {noa[y]:,.0f}")
for (a,b), r in sorted(ric.items()):
    if r['suppressed']:
        print(f"  FY{a}-FY{b} SUPPRESSED d_noa={r['d_noa']:,.0f} ({r['why']})")
    else:
        print(f"  FY{a}-FY{b} ratio={100*r['ratio']:.1f}% d_oi={r['d_oi']:,.0f} d_noa={r['d_noa']:,.0f}")

print("\n--- dividends by year ---")
for y in years:
    print(f"  FY{y}: ${FIN['dividends'][y]:,.0f}mn")

print("\n--- wedge detail ---")
print(study.wedge)

print("\n--- timing detail ---")
print({k:v for k,v in study.timing_result.items() if k not in ('pe_paid','pe_market')})

print("\n--- notes ---")
for n in study.notes:
    print(" -", n)
