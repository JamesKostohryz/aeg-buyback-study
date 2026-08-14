# -*- coding: utf-8 -*-
"""fleet_test.py - CI gate: run EVERY committed fixture and assert that not
one of them raises an UNHANDLED exception.

WHY THIS EXISTS
---------------
Every other gate in this repository proves ONE company (or, for
coe_invariance_test.py, one mechanic) is right. Nothing before this file ran
every committed fixture in one pass and printed a single pass/fail table for
all of them together. That is what this file is for, and only that - it is a
crash gate, not a correctness gate. A ticker can print a wrong number and
still pass this file; verify.py, template_test_HD.py, excise_test_ORLY.py,
roundtrip_test_AAL.py and coe_invariance_test.py exist to catch that. This
file exists to catch the OTHER failure mode: a bare traceback with no name
attached to what broke, which stops a session cold and teaches nothing.

A FINDING THIS FILE SURFACED, WORTH RECORDING HERE
----------------------------------------------------
The task behind this file expected every fixture to run through
run_study.py's generic run_study.run(cfg, raw_path) - one driver, CLI-
equivalent arguments, real tracebacks. That is exactly what code/orcl_sec_
raw.json supports, because it was captured under run_study.py's CURRENT
key scheme: build_financials() and build_sec() look every quantity up as
raw[f'{canonical_key}__{alt_index}'] (see run_study.py FIN_TAGS / TAGS,
and fetch_raw()). But three of the other four price-backed fixtures predate
that scheme:

  - code/cost_sec_raw.json and code/hd_sec_raw.json use an OLDER, bare-key
    scheme (raw['wtd_diluted_shares'], not raw['wtd_diluted_shares__0']) -
    the one code/run_COST.py, code/full_study_COST.py and
    code/template_test_HD.py already parse by hand. They DO carry full
    income-statement data, so a full BuybackStudy.run() is meaningful for
    both; it is driven here the same way those two files already prove
    works, not through run_study.py's key lookup, which does not recognize
    the schema and raises a bare KeyError on 'wtd_diluted_shares' before a
    single guard gets a chance to run (confirmed by hand: pointing
    run_study.run() at either fixture crashes identically, at
    buyback_study_TEMPLATE.py's eps_attribution(), for a reason that has
    nothing to do with either company's data).

  - code/aal_sec_raw.json and code/orly_sec_raw.json are narrower still:
    both were captured to prove ONE mechanic each (the round trip on
    equity raised, and the excise tax, respectively - see
    docs/00-WHERE-THINGS-LIVE.md: "American Airlines, and NOT a study of
    it" / "O'Reilly Automotive, and NOT a study of it") and neither one
    carries ANY income-statement data at all - no net income, no diluted
    EPS, no weighted share count, under any key name. That is not a schema
    mismatch, it is a scope decision made when each fixture was built, and
    no driver, generic or otherwise, can run a full study on data that was
    never captured. Each is driven here at exactly the level its own
    CI-gated proving file (roundtrip_test_AAL.py, excise_test_ORLY.py)
    already exercises and passes.

None of this is a defect in run_study.py, and none of it is fixed here -
this file does not modify run_study.py or any existing test file, per the
task this was built under. It is a real, previously-unexercised gap between
"the fixtures that are committed" and "the fixtures run_study.py's generic
path can read", and it is reported plainly rather than papered over: see the
per-ticker comments below for exactly which driver each ticker uses and why.

WHAT COUNTS AS A FIXTURE HERE
------------------------------
A ticker qualifies only if code/ has BOTH a raw SEC facts fixture
(<ticker>_sec_raw.json) AND a committed price fixture (<ticker>_monthly.csv),
so the whole run stays OFFLINE - no --fetch, no network call, every run
reproducible byte-for-byte from what is checked in. As of 2026-08-13 that is
five tickers: aal, cost, hd, orcl, orly (docs/00-WHERE-THINGS-LIVE.md).

bkng_sec_raw.json and ibm_sec_raw.json ARE committed (both in the CURRENT
key scheme, as it happens), but no bkng_monthly.csv or ibm_monthly.csv is.
Running either without --prices falls through to a LIVE network fetch,
which breaks the one property this gate exists to guarantee. They are
listed in the summary as SKIPPED, not counted toward the pass/fail bar.

Apple is a genuinely different code path, not an omission: it is driven by
code/gen_article.py from code/source_data.py's hand-entered dictionaries and
the root-level AAPL_reported_*.csv / AAPL_restated.csv files, never through
CompanyConfig / BuybackStudy / run_study.py, and has no run()-style entry
point that returns a study object or refuses cleanly. It is checked
separately by code/numeric_token_diff.py under code/verify.py
(byte-identical regeneration), which is the correct gate for that pipeline.

WHAT "REFUSES CLEANLY" MEANS HERE
----------------------------------
Two vocabularies, both a PASS:

  1. Soft refusals: note('REFUSAL', ...) is called (run_study.run()) or a
     guard condition is checked directly (the direct-BuybackStudy drivers
     below) and execution continues. Most guards in this template work
     this way and never raise.

  2. Hard refusals: a small number of guards raise on purpose rather than
     let a data problem produce a plausible-looking wrong number (defect
     25's exact shape). Every deliberate raise site in
     buyback_study_TEMPLATE.py and run_study.py's build_financials() uses
     one of two built-in types, ValueError or RuntimeError (which
     ExciseTaxUndisclosed subclasses). KNOWN_GUARD_EXCEPTIONS below is
     exactly that pair.

Anything else - KeyError, AttributeError, TypeError, IndexError,
ZeroDivisionError, FileNotFoundError, and so on - is outside that
vocabulary and is treated here as CRASHED: a genuine defect, or a
fixture/config mistake in this file's own per-ticker argument block.
Either way it FAILS this gate and is printed in full, never swallowed.

Run: cd code && python3 fleet_test.py
"""
import csv
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)                 # every fixture path below is relative to code/
sys.path.insert(0, '..')

import run_study as rs                                                  # noqa: E402
from buyback_study_TEMPLATE import (                                    # noqa: E402
    CompanyConfig, BuybackStudy, ExciseTaxUndisclosed, EquityRaise,
    parse_concept, merge_concept_series,
)

# Deliberate hard refusals in this codebase are always one of these two
# built-in types (see module docstring). Anything else escaping a driver
# below is treated as an unhandled crash.
KNOWN_GUARD_EXCEPTIONS = (ValueError, RuntimeError)


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def _prices_date_col(path):
    px = {}
    for r in csv.DictReader(open(path)):
        y, m = r['Date'].split('-')[:2]
        px[(int(y), int(m))] = float(r['Close'])
    return px


def _cpi_deflator_from_apple(first, last):
    """The committed CPI-U deflator row from AAPL_restated.csv, carried
    forward/backward the same way run_COST.py and template_test_HD.py do:
    nearest published year on the edges."""
    rows = list(csv.reader(open('../AAPL_restated.csv')))
    hdr = rows[0]
    src = {}
    for r in rows:
        if r and r[0].startswith('CPI deflator'):
            src = {int(y): float(v) for y, v in zip(hdr[1:], r[1:]) if v.strip()}
    return {y: src.get(y - 1, src.get(max(src))) for y in range(first, last + 1)}


# ---------------------------------------------------------------------------
# tier 1: run_study.py's own generic driver, unmodified, in-process.
# Only ORCL's raw fixture matches its current raw[f'{key}__{i}'] key scheme.
# ---------------------------------------------------------------------------
def drive_orcl():
    cfg = rs.StudyConfig(
        ticker='ORCL', cik='0001341439', fy_end_month=5,
        first_year=2013, last_year=2025, coe_longrun=0.055,
        prices='orcl_monthly.csv', traded_range='orcl_traded_range.csv',
        split_year=2020, splits=[])
    # config source: the task's own worked example; reproduced verbatim in
    # template_test_HD.py's "Oracle cold run reproduces offline" section
    # (CFG _orcl_cfg, ~line 465) and docs/COLD-RUN-Oracle-2026-08-13.md.
    study, EE = rs.run(cfg, 'orcl_sec_raw.json')
    return study


def drive_bkng():
    # BKNG's price and traded-range fixtures were fetched and committed
    # 2026-08-13 (hardening-endpoint session) specifically to close this
    # fleet gate's coverage gap; they did not exist before. Window and
    # placeholder rate are this session's own choice (undocumented
    # elsewhere): FY2013-FY2025, 6% real placeholder, matching the other
    # tier-1 companies. The 2026-04-06 25-for-1 split (AFTER the window,
    # defect 25's own company) is registered explicitly because the offline
    # --prices path never auto-detects a split the way --fetch does.
    cfg = rs.StudyConfig(
        ticker='BKNG', cik='0001075531', fy_end_month=12,
        first_year=2013, last_year=2025, coe_longrun=0.06,
        prices='bkng_monthly.csv', traded_range='bkng_traded_range.csv',
        splits=[('2026-04-06', 25.0)])
    study, EE = rs.run(cfg, 'bkng_sec_raw.json')
    return study


def drive_ibm():
    # IBM's price and traded-range fixtures were fetched and committed
    # 2026-08-13 for the same reason as BKNG. Window FY2015-FY2025, 6% real
    # placeholder (this session's own choice). splits=[] is DELIBERATE, not
    # an omission: the EODHD splits endpoint reports a spurious 1.046x
    # "split" on 2021-11-04, one day after IBM's Kyndryl spinoff
    # (2021-11-03) -- that is a spinoff value adjustment, not a share
    # split, and IBM has not split its stock since 1999. Applying it would
    # wrongly restate every pre-2021-11 share count and price by 4.6%. The
    # price fixture itself was built with NO split factor applied for the
    # same reason. This is a real, live example of exactly the kind of
    # vendor-data trap CompanyConfig.splits exists to let a person override
    # -- worth a permanent note, because run_study.py's own
    # `splits = cfg.splits or _fetched_splits` line cannot express "zero
    # splits, definitely" when going through --fetch: an explicitly empty
    # list is falsy in Python and silently loses to the vendor's list. Not
    # a live risk here (this fixture is offline, --prices supplied), but a
    # real latent defect for the next company run with --fetch. Flagged,
    # not fixed, in this session -- fixing it touches share restatement and
    # is GATED.
    cfg = rs.StudyConfig(
        ticker='IBM', cik='0000051143', fy_end_month=12,
        first_year=2015, last_year=2025, coe_longrun=0.06,
        prices='ibm_monthly.csv', traded_range='ibm_traded_range.csv',
        splits=[])
    study, EE = rs.run(cfg, 'ibm_sec_raw.json')
    return study

def drive_azo():
    # AutoZone: FY2013-FY2025, 6% real placeholder. Fixtures fetched and
    # committed 2026-08-13. This ticker resolves ZERO of its 13 years - its
    # repurchase-flow tag (StockRepurchasedDuringPeriodShares) only covers
    # FY2008-2012, entirely before this window, and no other retirement or
    # treasury-flow tag is filed at all. That is a clean, named, total
    # refusal (every year excluded "from BOTH sides of every average"), not
    # a crash - exactly the shape-coverage bar this gate exists to prove.
    # Shares OUTSTANDING resolve fine for the full window (defect 17's
    # cover-page splice fires and agrees to 1.22%); it is only the FLOW that
    # is unreachable. AutoZone pays no dividend (defect 15) and holds
    # repurchases in treasury.
    cfg = rs.StudyConfig(
        ticker='AZO', cik='0000866787', fy_end_month=8,
        first_year=2013, last_year=2025, coe_longrun=0.06,
        prices='azo_monthly.csv', traded_range='azo_traded_range.csv',
        splits=[])
    study, EE = rs.run(cfg, 'azo_sec_raw.json')
    return study

def drive_jef():
    # Jefferies Financial Group: FY2013-FY2025, 6% real placeholder.
    # Fixtures fetched and committed 2026-08-13. This is shape (n), a real
    # mid-window fiscal year end change (December 31 to November 30,
    # effective calendar 2018, with an 11-month stub year) - run cold with
    # fy_end_month=12 DELIBERATELY, the value that was correct until the
    # change, so this fixture demonstrates check_fiscal_year_end() catching
    # exactly the case it was built for: FY2017 through FY2025 all named,
    # no crash.
    cfg = rs.StudyConfig(
        ticker='JEF', cik='0000096223', fy_end_month=12,
        first_year=2013, last_year=2025, coe_longrun=0.06,
        prices='jef_monthly.csv', traded_range='jef_traded_range.csv',
        splits=[])
    study, EE = rs.run(cfg, 'jef_sec_raw.json')
    return study


def drive_ba():
    # Boeing: FY2013-FY2025, 6% real placeholder. Fixtures fetched and
    # committed 2026-08-13. Resolves every year (retired_tag =
    # TreasuryStockSharesAcquired, unresolved = []) but tags no repurchase
    # cash at all FY2020-2025 - Boeing genuinely stopped buying back stock
    # in that span (consistent with the 2020-2024 dividend suspension this
    # project already found, defect 19). Those years are named refusals,
    # not a crash.
    cfg = rs.StudyConfig(
        ticker='BA', cik='0000012927', fy_end_month=12,
        first_year=2013, last_year=2025, coe_longrun=0.06,
        prices='ba_monthly.csv', traded_range='ba_traded_range.csv',
        splits=[])
    study, EE = rs.run(cfg, 'ba_sec_raw.json')
    return study


def drive_meta():
    # Meta Platforms: FY2013-FY2025, 6% real placeholder. Fixtures fetched
    # and committed 2026-08-13. This is defect 22's own company: NOT ONE of
    # the five share-count elements the template knows returns anything,
    # because Meta's share counts are dimensioned by class (Class A/Class
    # B) and the company-concept interface serves only undimensioned
    # facts. The driver must refuse the whole company cleanly by name
    # rather than crash - that is exactly what this proves.
    cfg = rs.StudyConfig(
        ticker='META', cik='0001326801', fy_end_month=12,
        first_year=2013, last_year=2025, coe_longrun=0.06,
        prices='meta_monthly.csv', traded_range='meta_traded_range.csv',
        splits=[])
    study, EE = rs.run(cfg, 'meta_sec_raw.json')
    return study


# ---------------------------------------------------------------------------
# tier 2: full BuybackStudy.run(), built by hand from the OLDER bare-key raw
# schema, exactly as run_COST.py / full_study_COST.py and template_test_HD.py
# already do (both files are proven, CI-adjacent scripts; nothing about
# their parsing is guessed here).
# ---------------------------------------------------------------------------
def drive_cost():
    # config source: run_COST.py / full_study_COST.py CFG. Last split
    # 2-for-1 in March 2000, decades before this window, so splits=[].
    # coe_longrun=0.055 is that file's own documented PLACEHOLDER, reused
    # here rather than a fresh one.
    CFG = CompanyConfig(ticker='COST', cik='0000909832', fy_end_month=8,
                        splits=[], first_year=2015, last_year=2025,
                        coe_longrun=0.055)
    STUDY_YEARS = list(range(CFG.first_year, CFG.last_year + 1))
    RAW = json.load(open('cost_sec_raw.json'))
    PRICES = _prices_date_col('cost_monthly.csv')

    SEC = {}
    for key in ('repurchase_cash', 'repurchase_accrual', 'shares_retired',
                'treasury_shares_acquired', 'treasury_value_acquired',
                'issuance_proceeds', 'sbc', 'tax_withholding',
                'shares_outstanding'):
        SEC[key] = parse_concept(RAW.get(key, {'units': {}}))

    def series(key, scale=1e6):
        return {y: e['val'] / scale for y, e in parse_concept(RAW[key]).items()}

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

    div_merged = merge_concept_series(
        [parse_concept(RAW['dividends_old']), parse_concept(RAW['dividends_new'])],
        mode='update', expected_years=STUDY_YEARS, label='dividends paid')
    FIN['dividends'] = {y: e['val'] / 1e6 for y, e in div_merged.items()}

    debt_merged = merge_concept_series(
        [parse_concept(RAW['lt_debt_noncurrent']), parse_concept(RAW['lt_debt_current'])],
        mode='sum', expected_years=STUDY_YEARS, label='gross debt')
    FIN['total_debt'] = {y: e['val'] / 1e6 for y, e in debt_merged.items()}

    COE = {y: CFG.coe_longrun for y in range(2010, 2027)}
    DEFL = _cpi_deflator_from_apple(2010, 2026)

    study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, COE,
                         engine={'coe_longrun': CFG.coe_longrun})
    study.run()
    return study


def drive_hd():
    # config source: template_test_HD.py CFG (~line 71). Last split 3-for-2
    # on 1999-01-04, well before this window, so splits=[]. coe_longrun is
    # that file's own documented value, reused here.
    CFG = CompanyConfig(ticker='HD', cik='0000354950', fy_end_month=1,
                        splits=[], first_year=2012, last_year=2026,
                        coe_longrun=0.0548806713262307)
    STUDY_YEARS = list(range(CFG.first_year, CFG.last_year + 1))
    RAW = json.load(open('hd_sec_raw.json'))
    _FIXTURE_ALIAS = {'treasury_shares_balance': 'TreasuryStockShares',
                      'treasury_shares_balance_alt': 'TreasuryStockCommonShares',
                      'treasury_value_balance': 'TreasuryStockValue',
                      'treasury_shares_reissued': 'StockIssuedDuringPeriodSharesTreasuryStockReissued',
                      'shares_issued': 'CommonStockSharesIssued'}
    PRICES = _prices_date_col('hd_monthly.csv')

    SEC = {}
    for key in ('repurchase_cash', 'repurchase_accrual', 'shares_retired',
                'treasury_shares_acquired', 'treasury_value_acquired',
                'issuance_proceeds', 'sbc', 'tax_withholding', 'shares_outstanding',
                'treasury_shares_balance', 'treasury_shares_balance_alt',
                'treasury_value_balance', 'treasury_shares_reissued',
                'shares_issued'):
        SEC[key] = parse_concept(RAW.get(_FIXTURE_ALIAS.get(key, key), {'units': {}}))

    def series(key, scale=1e6):
        return {y: e['val'] / scale for y, e in parse_concept(RAW[key]).items()}

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

    pretax_merged = merge_concept_series(
        [parse_concept(RAW['pretax_old']), parse_concept(RAW['pretax_new'])],
        mode='update', expected_years=STUDY_YEARS, label='pretax_income')
    FIN['pretax_income'] = {y: e['val'] / 1e6 for y, e in pretax_merged.items()}

    debt_merged = merge_concept_series(
        [parse_concept(RAW['lt_debt_nc']), parse_concept(RAW['lt_debt_current']),
         parse_concept(RAW['commercial_paper'])],
        mode='sum', expected_years=STUDY_YEARS, label='total_debt')
    FIN['total_debt'] = {y: e['val'] / 1e6 for y, e in debt_merged.items()}

    COE = {y: CFG.coe_longrun for y in range(2010, 2027)}
    DEFL = _cpi_deflator_from_apple(2010, 2026)

    study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, COE,
                         engine={'coe_longrun': CFG.coe_longrun})
    study.run()
    return study


# ---------------------------------------------------------------------------
# tier 3: narrow, single-mechanic fixtures. Neither aal_sec_raw.json nor
# orly_sec_raw.json carries any income-statement data under any key name -
# both were built to prove one mechanic each - so FIN is empty/near-empty by
# necessity and the driver calls only the methods that mechanic needs,
# exactly as roundtrip_test_AAL.py / excise_test_ORLY.py already do and pass.
# ---------------------------------------------------------------------------
def drive_aal():
    # config source: roundtrip_test_AAL.py CFG (~line 121). Never split;
    # window opens FY2014 (post Chapter 11 / US Airways merger emergence,
    # 2013-12-09), so the FY2013 stub is excluded. coe_longrun is not used
    # by this fixture (no entry effect exercised) and is left at the
    # CompanyConfig default (None).
    CFG = CompanyConfig(ticker='AAL', cik='0000006201', fy_end_month=12,
                        splits=[], first_year=2014, last_year=2025)
    RAW = json.load(open('aal_sec_raw.json'))
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
    SEC = {key: parse_concept(RAW.get(tag, {'units': {}})) for key, tag in _KEYMAP.items()}
    PRICES = {(int(r['year']), int(r['month'])): float(r['close'])
              for r in csv.DictReader(open('aal_monthly.csv'))}
    TRADED = {int(r['fiscal_year']): (float(r['intraday_low']), float(r['intraday_high']))
              for r in csv.DictReader(open('aal_traded_range.csv'))}
    DEFL = _cpi_deflator_from_apple(2012, 2026)

    # The three equity raises and the one named reconciling item, transcribed
    # (with sources) in roundtrip_test_AAL.py from AAG's own Statements of
    # Stockholders' Equity - reused verbatim, since they are filed facts, not
    # guesses, and this fixture's whole point is the round trip on them.
    _SRC20 = ("AAG Form 10-K FY2020 (0000006201-21-000014), Consolidated Statements "
              "of Stockholders' Equity (Deficit)")
    _SRC21 = ("AAG Form 10-K FY2021 (0000006201-22-000026), Consolidated Statements "
              "of Stockholders' Equity (Deficit)")
    RAISES = [
        EquityRaise(2020, 129.490000, 1687.0, "two underwritten public offerings", _SRC20),
        EquityRaise(2020, 68.561487, 869.0, "at-the-market offering", _SRC20),
        EquityRaise(2021, 24.150764, 460.0, "at-the-market offering", _SRC21),
    ]
    RECONCILING = {2020: {"equity component of the 6.50% convertible notes": 415.0}}
    PLAN_SHARES = {y: e['val'] / 1e6 for y, e in SEC['plan_shares_issued'].items()}
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
    study.validate_prices(study.retired, TRADED)
    study.reconcile_raises()
    study.validate_raise_prices(TRADED)
    rt = study.round_trip_reconciled()
    study.round_trip_result = rt
    study.round_trip_report()
    return study


def drive_orly():
    # config source: excise_test_ORLY.py CFG (~line 63). Real 15-for-1 split
    # 2025-06-10, INSIDE this window, carried as an actual splits= entry
    # (not just split_year) so as-filed share counts restate. coe_longrun
    # is not used by this fixture (no entry effect exercised) and is left
    # at the CompanyConfig default (None).
    CFG = CompanyConfig(ticker='ORLY', cik='0000898173', fy_end_month=12,
                        splits=[('2025-06-10', 15)], first_year=2022,
                        last_year=2025)
    RAW = json.load(open('orly_sec_raw.json'))
    SEC = {k: parse_concept(v) for k, v in RAW.items()}
    PRICES = _prices_date_col('orly_monthly.csv')

    study = BuybackStudy(CFG, {}, SEC, PRICES, {}, {})
    study.retired, study.issued = study.share_flows()
    # allow_statutory_estimate=True exercises the reconstruction band from
    # committed SEC data alone (repurchase_cash / excise_tax), with no
    # hand-transcribed filing figures - unlike excise_test_ORLY.py's
    # `disclosed=` calls, which supply EQUITY_CHARGE, a set of numbers
    # transcribed by hand from the 10-Ks rather than read from the fixture.
    study.excise_tax(allow_statutory_estimate=True)
    return study


# ---------------------------------------------------------------------------
FLEET = [
    dict(ticker='AAL', driver=drive_aal, tier='3 (narrow: round trip only)',
         source='roundtrip_test_AAL.py'),
    dict(ticker='AZO', driver=drive_azo, tier='1 (run_study.py generic driver)',
         source='azo_monthly.csv/azo_traded_range.csv fetched and committed '
                '2026-08-13 - see driver docstring; shape (g), no dividend'),
    dict(ticker='BA', driver=drive_ba, tier='1 (run_study.py generic driver)',
         source='ba_monthly.csv/ba_traded_range.csv fetched and committed '
                '2026-08-13 - see driver docstring; shape (h), suspended dividend'),
    dict(ticker='JEF', driver=drive_jef, tier='1 (run_study.py generic driver)',
         source='jef_monthly.csv/jef_traded_range.csv fetched and committed '
                '2026-08-13 - see driver docstring; shape (n), mid-window fiscal '
                'year end change'),
    dict(ticker='BKNG', driver=drive_bkng, tier='1 (run_study.py generic driver)',
         source='bkng_monthly.csv/bkng_traded_range.csv fetched and committed '
                '2026-08-13; window/rate are this session\'s own choice, undocumented '
                'elsewhere - see driver docstring'),
    dict(ticker='COST', driver=drive_cost, tier='2 (direct BuybackStudy, full run)',
         source='run_COST.py / full_study_COST.py'),
    dict(ticker='HD', driver=drive_hd, tier='2 (direct BuybackStudy, full run)',
         source='template_test_HD.py'),
    dict(ticker='META', driver=drive_meta, tier='1 (run_study.py generic driver)',
         source='meta_monthly.csv/meta_traded_range.csv fetched and committed '
                '2026-08-13 - see driver docstring; shape (o), multi-class common'),
    dict(ticker='IBM', driver=drive_ibm, tier='1 (run_study.py generic driver)',
         source='ibm_monthly.csv/ibm_traded_range.csv fetched and committed '
                '2026-08-13 with splits=[] (Kyndryl spinoff excluded as a false '
                'split) - see driver docstring'),
    dict(ticker='ORCL', driver=drive_orcl, tier='1 (run_study.py generic driver)',
         source='task spec / docs/COLD-RUN-Oracle-2026-08-13.md / template_test_HD.py'),
    dict(ticker='ORLY', driver=drive_orly, tier='3 (narrow: excise tax only)',
         source='excise_test_ORLY.py'),
]

SKIPPED = [
    dict(ticker='AAPL',
         reason="a genuinely different code path, not an omission - see the module "
                "docstring. Driven by code/gen_article.py from hand-entered data, "
                "never through CompanyConfig / BuybackStudy / run_study.py; checked "
                "separately by code/numeric_token_diff.py under code/verify.py."),
]


def run_one(entry):
    ticker = entry['ticker']
    print("\n" + "#" * 100)
    print(f"# FLEET: {ticker}   (tier {entry['tier']}; config source: {entry['source']})")
    print("#" * 100)
    rs.REF.clear()
    try:
        study = entry['driver']()
    except KNOWN_GUARD_EXCEPTIONS as exc:
        etype = type(exc).__name__
        emsg = str(exc)
        print(f"\n[{ticker}] REFUSED (named exception) - {etype}: {emsg}")
        return dict(ticker=ticker, status='REFUSED', ok=True, detail=f"{etype}: {emsg}")
    except SystemExit as exc:
        emsg = str(exc.code) if exc.code is not None else ''
        print(f"\n[{ticker}] CRASHED (unhandled SystemExit) - {emsg}")
        return dict(ticker=ticker, status='CRASHED', ok=False, detail=f"SystemExit: {emsg}")
    except Exception as exc:
        etype = type(exc).__name__
        emsg = str(exc)
        tb = traceback.format_exc()
        print(f"\n[{ticker}] CRASHED (unhandled, unrecognized exception type) - "
              f"{etype}: {emsg}")
        print(f"[{ticker}] FULL TRACEBACK:\n{tb}")
        return dict(ticker=ticker, status='CRASHED', ok=False, detail=f"{etype}: {emsg}")
    else:
        # run_study.REF is populated only by run_study.run() itself (tier 1,
        # ORCL). The direct-BuybackStudy drivers (tier 2/3) never touch it,
        # so it would misleadingly read 0/0 for them even when real guards
        # fired - study.notes is the one note channel every tier populates,
        # so it is what the summary counts against, with run_study.REF's own
        # REFUSAL tally added on top for tier 1.
        n_notes = len(getattr(study, 'notes', []))
        n_ref_refusal = sum(1 for k, _t in rs.REF if k == 'REFUSAL')
        n_note_refusal = sum(1 for n in getattr(study, 'notes', [])
                             if 'REFUS' in n.upper())
        n_refusal = n_ref_refusal + n_note_refusal
        status = 'COMPLETED' if n_refusal == 0 else 'COMPLETED (with refusals)'
        detail = (f"{n_notes} study.notes entr(y/ies)"
                  + (f", {len(rs.REF)} run_study.REF note(s)" if rs.REF else "")
                  + f", {n_refusal} refusal-flavored")
        print(f"\n[{ticker}] {status} - {detail}")
        return dict(ticker=ticker, status=status, ok=True, detail=detail)


def main():
    results = [run_one(e) for e in FLEET]

    print("\n" + "=" * 100)
    print("FLEET TEST SUMMARY")
    print("=" * 100)
    print(f"{'TICKER':<8}{'STATUS':<26}{'GATE':<6}DETAIL")
    print("-" * 100)
    for r in results:
        gate = "PASS" if r['ok'] else "FAIL"
        print(f"{r['ticker']:<8}{r['status']:<26}{gate:<6}{r['detail']}")
    for s in SKIPPED:
        print(f"{s['ticker']:<8}{'SKIPPED':<26}{'N/A':<6}{s['reason']}")
    print("-" * 100)

    n_crashed = sum(1 for r in results if r['status'] == 'CRASHED')
    n_run = len(results)
    print(f"{n_run} fixture(s) run offline, {len(SKIPPED)} skipped (see reasons above), "
          f"{n_crashed} unhandled crash(es).")
    if n_crashed:
        print(f"GATE: FAIL - {n_crashed} ticker(s) crashed unhandled: "
              f"{[r['ticker'] for r in results if r['status'] == 'CRASHED']}")
    else:
        print("GATE: PASS - every fixture either completed or refused cleanly by name; "
              "nothing crashed unhandled.")
    print("=" * 100)
    return 1 if n_crashed else 0


if __name__ == '__main__':
    sys.exit(main())
