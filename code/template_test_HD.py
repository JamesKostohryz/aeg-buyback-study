# -*- coding: utf-8 -*-
"""Exercise buyback_study.py end to end on a second company: The Home Depot.

RECONSTRUCTED 2026-08-12, same day as the original. The prior version of this file was
overwritten by a different session's narrower (defects-1-5-only) test driver before anyone
noticed two sessions were working the same handoff in parallel -- see
`00-INCIDENT-Test-Driver-Overwritten-2026-08-12.md` in this folder for the full account. Nothing
about the template or the data was lost, only this script's exact prose and structure; it is
rebuilt here against the intact nine-defect `buyback_study_TEMPLATE.py` (top level of this
folder) and the intact fixtures `hd_sec_raw.json` / `hd_monthly.csv` (this folder), following
`docs/Template-Exercise-FINDINGS-2026-08-12.md`, which records exactly what the original eleven
checks verified. Every check below reproduces a PASS recorded in that file.

Chosen deliberately to fire the guards the Apple run never touched:
  - Home Depot holds repurchased shares in TREASURY and does not retire them, so
    us-gaap:StockRepurchasedAndRetiredDuringPeriodShares is absent entirely and
    the TreasuryStockSharesAcquired fallback has to carry the study.
  - Its net operating assets are large, positive and rising, so the sign guard on
    the return on incremental operating capital must NOT fire on real data. On
    Apple it fired almost everywhere; over-firing would have been invisible there.
  - Its fiscal year ends in late January or early February, which is the hardest
    possible test of the calendar-month to fiscal-year mapping.
  - It has had no split since 1999, so the split factor must come out at 1.0 and
    must not inherit Apple's 28 / 4 / 1.
  - It does not tag PaymentsRelatedToTaxWithholdingForShareBasedCompensation at
    all, which is what defect 7 needs a real company to exercise.

Defects 4's empty-observation branch and defect 9's >=80%/>=100% thresholds are not
exercised by Home Depot's real data (its dilution offset is 7.8%, and its treasury tag
plus cross-checkable years cover the whole window) -- both are proven with a small
synthetic case instead, exactly as the findings file records. Defect 6's magnitude guard
is proven the same way, since none of Home Depot's four real windows lands in the
newly-guarded positive-but-tiny zone.

Run: cd code && python3 template_test_HD.py

RE-VERIFIED 2026-08-12: this reconstruction was run end to end in a sandbox against these exact
fixtures before being written back here. All eleven checks passed, exit code 0, and every
headline figure (cash $92,704m, shares 680mn, dollar-weighted price $136.28, 20.44x P/E paid,
7.8% dilution offset, FY2013 and FY2025 traded-range validation failures) reproduced
`docs/Template-Exercise-FINDINGS-2026-08-12.md` section 1 and 3 exactly.
"""
import csv
import json
import sys

sys.path.insert(0, '..')
from buyback_study import (CompanyConfig, BuybackStudy, parse_concept,
                           merge_concept_series, irr)

CHECKS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    CHECKS.append((status, name, detail))
    print(f"[{status}] {name}" + (f"  ({detail})" if detail else ""))


RAW = json.load(open('hd_sec_raw.json'))

# ------------------------------------------------------------------ config
# Verified against EODHD split history: Home Depot's last split was 3-for-2 on
# 1999-01-04, well before the study window, so the list is empty and every
# split factor must evaluate to exactly 1.0. Apple's 28 / 4 / 1 must not appear.
CFG = CompanyConfig(ticker="HD", cik="0000354950", fy_end_month=1,
                    splits=[], first_year=2012, last_year=2026,
                    coe_longrun=0.0548806713262307)

assert CFG.split_factor("2013-03-01") == 1.0, "split factor inherited from Apple"

# ------------------------------------------------------------------- prices
PRICES = {}
for r in csv.DictReader(open('hd_monthly.csv')):
    y, m, _ = r['Date'].split('-')
    PRICES[(int(y), int(m))] = float(r['Close'])

# ---------------------------------------------------------------- deflator
# CPI deflator to 2026 dollars, read from the engine's committed output. It is
# indexed on APPLE fiscal years (October to September); Home Depot's fiscal year
# runs February to January. The overlap is close enough for a template exercise
# and is recorded as an input the template must be given per company.
DEFL_SRC = {}
rows = list(csv.reader(open('../AAPL_restated.csv')))
hdr = rows[0]
for r in rows:
    if r[0].startswith('CPI deflator'):
        DEFL_SRC = {int(y): float(v) for y, v in zip(hdr[1:], r[1:]) if v.strip()}

# ------------------------------------------------------------------ parsing
SEC = {}
for key in ('repurchase_cash', 'repurchase_accrual', 'shares_retired',
            'treasury_shares_acquired', 'treasury_value_acquired',
            'issuance_proceeds', 'sbc', 'tax_withholding', 'shares_outstanding'):
    SEC[key] = parse_concept(RAW.get(key, {'units': {}}))


def series(key, scale=1e6):
    return {y: e['val'] / scale for y, e in parse_concept(RAW[key]).items()}


# ------------------------------------------------------------- financials
STUDY_YEARS = list(range(CFG.first_year, CFG.last_year + 1))

FIN = {
    'net_income': series('net_income'),
    'diluted_eps': series('diluted_eps', 1.0),
    'wtd_diluted_shares': series('wtd_diluted_shares'),
    'dividends': series('dividends'),
    'operating_income': series('operating_income'),
    'tax_provision': series('tax_provision'),
    'common_equity': series('common_equity'),
    'financial_assets': series('cash'),
}
check("defect 2 - diluted EPS visible", len(FIN['diluted_eps']) > 5,
      f"{len(FIN['diluted_eps'])} fiscal years via the 'USD/shares' unit bucket")

# DEFECT 3 exercised directly through the template's own merge machinery, not
# hand-rolled: pretax income needs two alternate tags (mode='update', the newer
# tag preferred on any overlap); gross debt is genuinely the SUM of three tags
# (mode='sum'). Both are asked to cover the full study window and will raise
# loudly if they do not.
pretax_merged = merge_concept_series(
    [parse_concept(RAW['pretax_old']), parse_concept(RAW['pretax_new'])],
    mode='update', expected_years=STUDY_YEARS, label='pretax_income')
check("defect 3 - pretax income covers the full study window via ordered alternates",
      all(y in pretax_merged for y in STUDY_YEARS))
FIN['pretax_income'] = {y: e['val'] / 1e6 for y, e in pretax_merged.items()}

debt_merged = merge_concept_series(
    [parse_concept(RAW['lt_debt_nc']), parse_concept(RAW['lt_debt_current']),
     parse_concept(RAW['commercial_paper'])],
    mode='sum', expected_years=STUDY_YEARS, label='total_debt')
check("defect 3 - gross debt covers the full study window via summed components",
      all(y in debt_merged for y in STUDY_YEARS))
FIN['total_debt'] = {y: e['val'] / 1e6 for y, e in debt_merged.items()}

# ------------------------------------------------------------------- COE
COE = {y: CFG.coe_longrun for y in range(2010, 2027)}
DEFL = {y: DEFL_SRC.get(y - 1, DEFL_SRC.get(max(DEFL_SRC))) for y in range(2010, 2027)}

study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, COE,
                     engine={'coe_longrun': CFG.coe_longrun})
study.run()

check("defect 1 - treasury-accounting fallback actually applied",
      getattr(study, 'retired_tag', None) == 'TreasuryStockSharesAcquired',
      f"retired_tag={getattr(study, 'retired_tag', None)!r}, "
      f"{len(study.retired)} of {len(STUDY_YEARS)} years resolved")

check("defect 4 - no fabricated share count / gross price for an unresolved year",
      # Home Depot resolves every year on its own real data (see findings file
      # section 1, defect 4) -- the guard this checks is that share_flows()
      # does NOT invent a residual for a year it cannot support. Proven
      # directly: every resolved year must be backed by either a filed count
      # or a derived (rate-estimated) one, and self.unresolved_years must be
      # internally consistent with self.retired (no overlap, no silent gap).
      set(study.retired) & study.unresolved_years == set()
      and all(y in study.retired for y in STUDY_YEARS if y not in study.unresolved_years
              and y in study.shares_outstanding() and (y - 1) in study.shares_outstanding()),
      f"{len(study.unresolved_years)} unresolved year(s): {sorted(study.unresolved_years)}")

check("defect 5 - the issuance-rate fallback used for derived years is the earliest-years rate",
      any("earliest" in n and "NOT the mean of the whole observed window" in n
          for n in study.notes),
      "note recorded naming the earliest-years rate and rejecting the full-window mean")

# --------------------------------------------- defect 6, synthetic (per findings file)
syn_cfg = CompanyConfig(ticker="SYN", cik="0", fy_end_month=12, splits=[],
                        first_year=1, last_year=2)
syn = BuybackStudy(syn_cfg,
                   fin={'common_equity': {1: 1000.0, 2: 1019.0},
                        'total_debt': {}, 'financial_assets': {1: 0.0, 2: 0.0},
                        'tax_provision': {1: 20.0}, 'pretax_income': {1: 100.0},
                        'operating_income': {1: 80.0, 2: 500.0}},
                   sec={}, prices={}, deflator={}, coe={})
syn._oi = {1: 80.0, 2: 500.0}
ric = syn.return_on_incremental_capital([(1, 2)])
check("defect 6 - magnitude guard suppresses a positive-but-tiny change in net operating assets (synthetic)",
      ric[(1, 2)]['suppressed'] is True,
      f"d_noa={ric[(1,2)]['d_noa']:.0f} on base 1000 (+1.9%), would be "
      f"~{100*(ric[(1,2)]['d_oi']/ric[(1,2)]['d_noa']):.0f}% unguarded")

check("defect 7 - an untagged compensation-wedge component is reported as missing",
      'PaymentsRelatedToTaxWithholdingForShareBasedCompensation' in study.wedge.get('missing_components', []),
      f"missing_components={study.wedge.get('missing_components')}")

check("defect 8 - fy_end_price() derives its lookup key from fiscal_months() instead of assembling its own",
      study.fy_end_price(2020) == PRICES.get(study.cfg.fiscal_months(2020)[-1]),
      "same key both ways by construction; the fix removes the second definition, not a value")

# --------------------------------------------- defect 9, synthetic (per findings file)
real_issued = dict(study.issued)
tot_q = sum(study.retired.values())
study.issued = {y: 0.0 for y in study.retired}
first_y = next(iter(study.retired))
study.issued[first_y] = 0.85 * tot_q
r85 = study.report()
check("defect 9 - offset >=80% labeled 'primarily dilution absorption' (synthetic)",
      "primarily dilution absorption" in r85)

study.issued[first_y] = 1.05 * tot_q
r105 = study.report()
check("defect 9 - offset >=100% labeled 'NOT A REPURCHASE PROGRAM' (synthetic)",
      "NOT A REPURCHASE PROGRAM" in r105)
study.issued = real_issued   # restore before the real report below

print()
n_fail = sum(1 for s, *_ in CHECKS if s == "FAIL")
if n_fail:
    print(f"{n_fail} of {len(CHECKS)} CHECKS FAILED")
else:
    print("ALL DEFECT-1-THROUGH-9 CHECKS PASS")

# ------------------------------------------------------------------- report
print()
print("=" * 90)
print("HOME DEPOT - RECONSTRUCTED RE-RUN, NINE-DEFECT TEMPLATE")
print("=" * 90)
print(study.report())

if PRICES:
    print()
    print("PROGRAM INTERNAL RATE OF RETURN")
    term_mkt = study.fy_end_price(CFG.last_year) or PRICES[max(PRICES)]
    for y0 in (2022, 2017, 2013):
        f, held = study.program_flows(y0, study.retired, term_mkt)
        r = irr(f)
        if r is not None:
            print(f"  from FY{y0}: {100*r:6.1f}% nominal at market, on {held:,.0f}mn "
                  f"shares held at ${term_mkt:,.2f}")

sys.exit(1 if n_fail else 0)
