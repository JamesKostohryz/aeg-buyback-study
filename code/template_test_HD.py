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
_FIXTURE_ALIAS = {'treasury_shares_balance': 'TreasuryStockShares',
                  'treasury_shares_balance_alt': 'TreasuryStockCommonShares',
                  'treasury_value_balance': 'TreasuryStockValue',
                  'treasury_shares_reissued': 'StockIssuedDuringPeriodSharesTreasuryStockReissued',
                  'shares_issued': 'CommonStockSharesIssued'}

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
            'issuance_proceeds', 'sbc', 'tax_withholding', 'shares_outstanding',
            # added 2026-08-13 for treasury permanence (addendum item 4). Home
            # Depot renamed TreasuryStockShares to TreasuryStockCommonShares in
            # 2024, which is exactly the rename the template's merge machinery
            # exists for, and is why BOTH are carried.
            'treasury_shares_balance', 'treasury_shares_balance_alt',
            'treasury_value_balance', 'treasury_shares_reissued',
            'shares_issued'):
    SEC[key] = parse_concept(RAW.get(_FIXTURE_ALIAS.get(key, key), {'units': {}}))


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

# ======================= treasury permanence (addendum item 4, 2026-08-13)
# Home Depot is the treasury case. It holds every share it has ever repurchased
# since 1999 and has cancelled none of them, which is why section 7's word
# "permanently" cannot be used on it.
_t = study.treasury_status()
check("item 4 - Home Depot is detected as a TREASURY company from the filings, not assumed",
      _t['holds_treasury'] is True and _t['basis'] == 'treasury',
      _t['evidence'])

check("item 4 - the treasury balance survives Home Depot's 2024 tag rename",
      _t['overhang_shares_latest'] is not None and _t['overhang_shares_latest'] > 700,
      f"{_t['overhang_shares_latest']:,.0f}mn shares; TreasuryStockShares runs to FY2023 and "
      "TreasuryStockCommonShares from FY2021, and a single-tag read would have stopped in 2023")

_nc = study.net_retirement_cost()
check("item 4 - the label is 'withdrawn from the float', never 'permanently removed'",
      _nc['label'] == 'withdrawn from the float',
      f"B = ${_nc['B_per_share']:,.2f} per share {_nc['label']}")

check("item 4 - the reissuable overhang exceeds everything the company retired in the window",
      _t['overhang_shares_latest'] > _nc['gross_retired'],
      f"{_t['overhang_shares_latest']:,.0f}mn held against {_nc['gross_retired']:,.0f}mn retired, "
      f"{_t['overhang_shares_latest']/_nc['gross_retired']:.2f}x")

check("item 4 - the arithmetic is unchanged; A is still cash over gross retirement",
      abs(_nc['A_gross_price'] - _nc['cash'] / _nc['gross_retired']) < 1e-9
      and abs(_nc['B_per_share'] - _nc['cash'] / _nc['net_reduction']) < 1e-9,
      f"A ${_nc['A_gross_price']:,.2f}, B ${_nc['B_per_share']:,.2f} - same ratios as before "
      "item 4; only the word attached to B, C and D changed")

# A RETIRING company must still get the permanence language, or the fix has
# simply moved the error rather than removed it.
_ret_syn = BuybackStudy(CFG, FIN,
                        {'shares_retired': SEC['shares_retired'] or
                         {2013: {'val': 1e6, 'filed': '2020-01-01'}},
                         'repurchase_cash': SEC['repurchase_cash']},
                        PRICES, DEFL, COE)
check("item 4 - a company that cancels its shares still reads 'permanently removed' (synthetic)",
      _ret_syn.treasury_status()['basis'] == 'retired'
      and _ret_syn.PERMANENCE_LABEL['retired'] == 'permanently removed',
      "the fix must not relabel companies for which the original word was correct")

# And silence must not be read as cancellation.
_unk = BuybackStudy(CFG, FIN, {'repurchase_cash': SEC['repurchase_cash']},
                    PRICES, DEFL, COE)
check("item 4 - a company tagging neither is UNDETERMINED, not silently 'retired'",
      _unk.treasury_status()['basis'] == 'undetermined'
      and _unk.treasury_status()['holds_treasury'] is None,
      "absence of a treasury tag is not evidence of cancellation")

# =============================================================================
# DEFECT 13, AND THE COLD RUN (added 2026-08-13, close-out session)
# =============================================================================
# These checks are in the template's regression gate rather than in a fifth CI
# job because they are about the TEMPLATE, not about a company. Home Depot is
# the fixture that proves the template survives a company it was not written
# for; Oracle is now the second, and it is here because running it cold is what
# found defect 13 in the first place.
#
# DEFECT 13. eps_attribution() split the earnings channel into operating and
# financial by striking an effective tax rate off pretax income. It built that
# rate only for the years it could, then read the result unconditionally, and
# died with a bare KeyError on the first year it could not. Oracle stops tagging
# IncomeLossFromContinuingOperationsBeforeIncomeTaxes... after fiscal 2018,
# under either of its two element names, so the generic driver crashed on the
# first company it was pointed at. The crash was the good outcome; the shape of
# the bug in general is a study that quietly drops the years it cannot split and
# publishes an attribution over a shorter window than the one in its heading.
print()
print("--- defect 13: a missing pretax income line must not crash or shorten the window ---")

_d13_fin = {
    'net_income':         {y: 1000.0 + 50 * (y - 2013) for y in range(2012, 2026)},
    'diluted_eps':        {y: 1.00 + 0.05 * (y - 2013) for y in range(2012, 2026)},
    'wtd_diluted_shares': {y: 1000.0 - 10 * (y - 2013) for y in range(2012, 2026)},
    'operating_income':   {y: 1200.0 + 60 * (y - 2013) for y in range(2012, 2026)},
    'tax_provision':      {y: 300.0 for y in range(2012, 2026)},
    # tagged to 2018 and then not, exactly as Oracle files it
    'pretax_income':      {y: 1300.0 + 65 * (y - 2013) for y in range(2012, 2019)},
    'dividends':          {y: 200.0 for y in range(2012, 2026)},
    'common_equity':      {y: 5000.0 for y in range(2012, 2026)},
    'total_debt':         {y: 2000.0 for y in range(2012, 2026)},
}
_d13 = BuybackStudy(
    CompanyConfig(ticker="D13", cik="0000000000", fy_end_month=12, splits=[],
                  first_year=2013, last_year=2025),
    _d13_fin, {'repurchase_cash': {}}, {}, {y: 1.0 for y in range(2011, 2027)},
    {y: 0.05 for y in range(2011, 2027)})
_d13_rows = _d13.eps_attribution()
check("defect 13: attribution covers the whole window, not just the splittable years",
      sorted(_d13_rows) == list(range(2013, 2026)),
      f"{len(_d13_rows)} years, FY{min(_d13_rows)}-FY{max(_d13_rows)}")
check("defect 13: the two channels that need no tax rate are computed in every year",
      all(r['from_earnings'] is not None and r['from_share_count'] is not None
          for r in _d13_rows.values()))
check("defect 13: the operating/financial split is None where it is not determinable",
      all(_d13_rows[y]['operating'] is None for y in range(2020, 2026))
      and _d13_rows[2018]['operating'] is not None,
      "None is visible in a table; a dropped year is not")
check("defect 13: the years without a split are NAMED in the notes",
      any('EARNINGS ATTRIBUTION NOT SPLIT' in n for n in _d13.notes))

# THE ENTRY EFFECT'S OWN GUARDS, on the template rather than on Apple.
print()
print("--- the entry effect refuses rather than guesses ---")
_ee_sec = {'repurchase_cash': {y: {'val': 1000e6, 'filed': '2026-01-01'}
                               for y in range(2013, 2026)}}
_ee = BuybackStudy(
    CompanyConfig(ticker="EE", cik="0000000000", fy_end_month=12, splits=[],
                  first_year=2013, last_year=2025),
    _d13_fin, _ee_sec, {}, {y: 1.0 for y in range(2011, 2027)},
    {y: 0.05 for y in range(2011, 2027)},
    shares_out={y: 1000.0 - 10 * (y - 2013) for y in range(2012, 2026)})
_ee.retired = {y: 10.0 for y in range(2013, 2026)}
_ee.issued = {y: 2.0 for y in range(2013, 2026)}

_refused = False
try:
    _ee.entry_effect()
except ValueError:
    _refused = True
check("entry_effect() refuses to default the cost of equity", _refused,
      "a rate that arrives by default rather than by decision has twice "
      "determined the sign of a result in this project")

_EE = _ee.entry_effect(rho=0.05)
check("entry effect drops the final year and says why",
      _EE['tranches'] == list(range(2013, 2025))
      and 2025 in _EE['excluded_years'],
      _EE['excluded_years'].get(2025, ''))
check("the break-even is the exact root: the entry effect is zero at it",
      abs(sum(_ee.retired[t] * (_EE['real_eps'][t + 1]
                                - _EE['break_even'] * _EE['real_price_paid'][t])
              for t in _EE['tranches'])) < 1e-8)
check("decision + timing == entry, every estimator, to floating-point exactness",
      _EE['identity_residual'] < 1e-6, f"residual {_EE['identity_residual']:.2e}")
check("the deflator is applied as a MULTIPLIER, not a divisor",
      abs(_ee.real_eps()[2020] - _d13_fin['diluted_eps'][2020] * 1.0) < 1e-12)

# DEFECT 10 inside the entry effect: a year whose only repurchase cash is
# employee tax withholding on the same line is not a repurchase year.
_ee2 = BuybackStudy(
    CompanyConfig(ticker="EE2", cik="0000000000", fy_end_month=12, splits=[],
                  first_year=2013, last_year=2025),
    _d13_fin, _ee_sec, {}, {y: 1.0 for y in range(2011, 2027)},
    {y: 0.05 for y in range(2011, 2027)},
    shares_out={y: 1000.0 - 10 * (y - 2013) for y in range(2012, 2026)},
    withholding_in_repurchase_cash={2018: 1000.0})
_ee2.retired = {y: 10.0 for y in range(2013, 2026)}
_ee2.issued = {y: 2.0 for y in range(2013, 2026)}
_t2, _x2 = _ee2.entry_tranches()
check("defect 10 inside the entry effect: a withholding-only year is refused",
      2018 not in _t2 and 'withholding' in _x2.get(2018, ''),
      _x2.get(2018, 'NOT REFUSED'))

# THE EARNINGS SPAN IS A CONVENTION, not whatever the source file reaches back
# to. Two of the three trend estimators read neighbouring years out of this
# series, so a company handed forty years of history and another handed twelve
# would not be comparable - and extending a source file backwards would silently
# move a published figure.
_ee.fin = dict(_d13_fin)
_ee.fin['diluted_eps'] = {y: 1.0 for y in range(1985, 2026)}
check("the earnings span is the study window plus its opening year, not the file",
      _ee.earnings_span() == list(range(2012, 2026))
      and min(_ee.real_eps()) == 2012,
      "source reaches back to 1985; the span binds at 2012")

# -----------------------------------------------------------------------------
# DEFECT 14 (2026-08-13, found by running Union Pacific cold, third company in a
# row to expose the same class of bug). Every quantity in the timing test and in
# the report header is a ratio, and each assumed its denominator was non-empty.
# A window in which nothing resolves - Union Pacific tags a retirement element
# but files no annual figure this template can pair with repurchase cash in any
# year - divided by zero and killed the run.
#
# The general lesson, recorded because it is worth more than the fix: a template
# written against one company encodes that company's COMPLETENESS as well as its
# arithmetic. Apple has every line in every year. Six untouched companies
# produced three crashes, every one of them an input assumed present.
print()
print("--- defect 14: an empty window refuses, it does not divide by zero ---")

_e14_fin = {
    'net_income':         {y: 1000.0 for y in range(2012, 2026)},
    'diluted_eps':        {y: 1.00 for y in range(2012, 2026)},
    'wtd_diluted_shares': {y: 1000.0 for y in range(2012, 2026)},
    'operating_income':   {y: 1200.0 for y in range(2012, 2026)},
    'tax_provision':      {y: 300.0 for y in range(2012, 2026)},
    'pretax_income':      {y: 1300.0 for y in range(2012, 2026)},
    'dividends':          {y: 200.0 for y in range(2012, 2026)},
    'common_equity':      {y: 5000.0 for y in range(2012, 2026)},
    'total_debt':         {y: 2000.0 for y in range(2012, 2026)},
}
_e14 = BuybackStudy(
    CompanyConfig(ticker="E14", cik="0000000000", fy_end_month=12, splits=[],
                  first_year=2013, last_year=2025),
    _e14_fin, {'repurchase_cash': {}}, {(y, 12): 50.0 for y in range(2012, 2026)},
    {y: 1.0 for y in range(2011, 2027)}, {y: 0.05 for y in range(2011, 2027)},
    shares_out={y: 1000.0 for y in range(2012, 2026)})
_e14.retired, _e14.issued = {}, {}
_e14.unresolved_years = set(range(2013, 2026))
_t14 = _e14.timing(_e14.retired)
check("defect 14: the timing test returns unavailable, not a zero",
      _t14['available'] is False
      and _t14['dollar_weighted_pe_paid'] is None,
      "None is unmistakable in a table; 0.00 is not")
check("defect 14: and it says so in the notes",
      any('TIMING TEST NOT COMPUTED' in n for n in _e14.notes))
_e14.timing_result = _t14
_e14.wedge = {'economic_cost': 0, 'accounting_charge': 0, 'wedge': 0, 'multiple': 0,
              'caveat': '', 'missing_components': []}
_e14.price_failures = []
_r14 = _e14.report()
check("defect 14: report() refuses the whole window instead of crashing",
      'NO MEASURABLE REPURCHASE IN THIS WINDOW' in _r14)
check("defect 14: the refusal names the window and the unresolved years",
      'FY2013' in _r14 and 'FY2025' in _r14 and 'Unresolved years' in _r14)
check("defect 14: the refusal does NOT claim the company made no repurchase",
      'statement about what the filings support, not about the company' in _r14,
      "a template that cannot read a tag has learned nothing about the business")

# DEFECT 13, SECOND PASS. The first pass guarded the tax-rate inputs and left
# the earnings channel reading net income unconditionally; International
# Business Machines files NetIncomeLoss only from 2015 and the very next company
# died on the very next line.
_d13b_fin = dict(_d13_fin)
_d13b_fin['net_income'] = {y: 1000.0 for y in range(2016, 2026)}
_d13b = BuybackStudy(
    CompanyConfig(ticker="D13B", cik="0000000000", fy_end_month=12, splits=[],
                  first_year=2013, last_year=2025),
    _d13b_fin, {'repurchase_cash': {}}, {}, {y: 1.0 for y in range(2011, 2027)},
    {y: 0.05 for y in range(2011, 2027)})
_d13b_rows = _d13b.eps_attribution()
check("defect 13 second pass: a short net income series does not crash",
      sorted(_d13b_rows) == list(range(2017, 2026)))
check("defect 13 second pass: the years with no attribution at all are NAMED",
      any('EARNINGS ATTRIBUTION NOT COMPUTED AT ALL' in n for n in _d13b.notes))

# THE COLD RUN, REPRODUCED OFFLINE. Oracle, fiscal year ending 31 May, never
# touched by this project before 2026-08-13. Run live that day through
# code/run_study.py; the fixtures are committed so it repeats without a network.
print()
print("--- the Oracle cold run reproduces offline ---")
import run_study as _rs                                            # noqa: E402

_orcl_cfg = _rs.StudyConfig(
    ticker="ORCL", cik="0001341439", fy_end_month=5, splits=[],
    first_year=2013, last_year=2025, coe_longrun=0.055,
    prices='orcl_monthly.csv', traded_range='orcl_traded_range.csv',
    split_year=2020)
_rs.REF.clear()
import io as _io                                                   # noqa: E402
import contextlib as _cl                                           # noqa: E402
with _cl.redirect_stdout(_io.StringIO()):
    _ostudy, _oEE = _rs.run(_orcl_cfg, 'orcl_sec_raw.json')

check("Oracle: shares retired come from the filed flow, nothing derived",
      _ostudy.retired_tag == 'StockRepurchasedAndRetiredDuringPeriodShares'
      and not _ostudy.derived_years and not _ostudy.unresolved_years)
check("Oracle: every implied price paid sits inside its own year's traded range",
      _ostudy.price_failures == [],
      "checked against intra-month extremes, not period-end closes")
check("Oracle: read as a CANCELLING company from its own filings",
      _ostudy.net_cost['basis'] == 'retired',
      "no treasury element of any name is filed in any year")
check("Oracle: the excise tax REFUSES - fiscal 2023 straddles 2022-12-31",
      any('excise tax REFUSED' in t for _k, t in _rs.REF),
      "42% exposed by month, no filed figure, no estimate opted into")
check("Oracle: timing dependence above 100%, so the headline is not a verdict",
      _oEE['timing_dependence'] > 1.0,
      f"{100*_oEE['timing_dependence']:.0f}% of the headline entry effect")
check("Oracle: the estimator families disagree on the sign of the price decision",
      _oEE['families_disagree_on_sign'])
check("Oracle: the break-even sits within a point of the placeholder rate",
      abs(_oEE['break_even'] - 0.055) < 0.01,
      f"break-even {100*_oEE['break_even']:.2f}% against a 5.50% placeholder - "
      "the sign of the headline is decided by a rate nobody has sourced")
check("Oracle: the run reports guards rather than a clean sheet",
      len(_rs.REF) >= 20, f"{len(_rs.REF)} guard messages")

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
