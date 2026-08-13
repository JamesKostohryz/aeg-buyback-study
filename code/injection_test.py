# -*- coding: utf-8 -*-
"""Injection / corruption test suite for buyback_study_TEMPLATE.py.

THIS IS A DISCOVERY REPORT, NOT A PASS/FAIL CI GATE (yet). It exits 0
regardless of outcome. Its job is to find out, honestly, which of ten
plausible input corruptions the current template catches with a NAMED,
attributable guard (an exception, an explicit study.notes entry, or some
other explicit signal) and which ones it walks through in silence and
publishes as if nothing were wrong. A corruption that is NOT caught is a
valid and expected finding, not a bug in this test script -- do not read a
FAIL below as "the test is broken." Nothing in this file may modify
buyback_study_TEMPLATE.py, buyback_study.py or run_study.py, and it does
not: it only reads them.

Methodology
-----------
Two known-good baselines are built, both from committed fixtures / hand-built
numbers, both offline (no network calls):

  1. HD_GOOD -- the real Home Depot run, same fixtures and same construction
     as code/template_test_HD.py (hd_sec_raw.json, hd_monthly.csv,
     ../AAPL_restated.csv for the CPI deflator row). Used for every
     corruption that does not need an in-window stock split.

  2. SYN_GOOD -- a small, hand-built, five-fiscal-year synthetic company with
     one clean 2-for-1 split effective mid-window (2014-07-01, between FY2013
     and FY2014). Home Depot has had no split since 1999 (splits=[]), so it
     cannot exercise anything split-related; this codebase's own established
     practice (see template_test_HD.py's defects 4, 6, 9) is to build a small
     synthetic case for shapes no real fixture reaches, rather than force a
     real company to fit. Used only for corruptions 1 and 9, the two that are
     specifically about the split mechanism.

For each of the ten corruptions: start from a FRESH copy of the good inputs
(the loader functions below re-read the fixtures / rebuild the dicts from
scratch every time, so nothing leaks between tests), apply exactly one
corruption, construct a new BuybackStudy, and run it inside a try/except.
Whatever happens -- a raised exception, a note appended to study.notes naming
the problem, or neither -- is recorded and printed. No guard is invented, no
threshold is loosened, and the template is never modified to make a
corruption easier or harder to catch.

Run: cd code && python3 injection_test.py
"""
import copy
import csv
import io
import json
import sys
import traceback

sys.path.insert(0, '..')
from buyback_study import (CompanyConfig, BuybackStudy, parse_concept,
                           merge_concept_series)

RESULTS = []  # (num, description, guard, PASS/FAIL, detail)


def record(num, desc, guard, passed, detail):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((num, desc, guard, status, detail))
    print(f"[{status}] #{num}: {desc}")
    print(f"    guard fired : {guard}")
    print(f"    what happened to the numbers: {detail}")
    print()


def notes_matching(study, *keywords):
    """Return every note containing ALL of the given keywords (case-insensitive)."""
    out = []
    for n in getattr(study, 'notes', []):
        low = n.lower()
        if all(k.lower() in low for k in keywords):
            out.append(n)
    return out


# =============================================================================
# BASELINE 1: HOME DEPOT (real fixtures, exactly as template_test_HD.py builds it)
# =============================================================================
_HD_FIXTURE_ALIAS = {'treasury_shares_balance': 'TreasuryStockShares',
                      'treasury_shares_balance_alt': 'TreasuryStockCommonShares',
                      'treasury_value_balance': 'TreasuryStockValue',
                      'treasury_shares_reissued': 'StockIssuedDuringPeriodSharesTreasuryStockReissued',
                      'shares_issued': 'CommonStockSharesIssued'}


def load_hd():
    """Rebuild the Home Depot CFG/FIN/SEC/PRICES/DEFL/COE from scratch, fresh
    every call, so corruptions applied to one call's output never leak into
    the next call's baseline."""
    RAW = json.load(open('hd_sec_raw.json'))

    CFG = CompanyConfig(ticker="HD", cik="0000354950", fy_end_month=1,
                        splits=[], first_year=2012, last_year=2026,
                        coe_longrun=0.0548806713262307)

    PRICES = {}
    for r in csv.DictReader(open('hd_monthly.csv')):
        y, m, _ = r['Date'].split('-')
        PRICES[(int(y), int(m))] = float(r['Close'])

    DEFL_SRC = {}
    rows = list(csv.reader(open('../AAPL_restated.csv')))
    hdr = rows[0]
    for r in rows:
        if r[0].startswith('CPI deflator'):
            DEFL_SRC = {int(y): float(v) for y, v in zip(hdr[1:], r[1:]) if v.strip()}

    SEC = {}
    for key in ('repurchase_cash', 'repurchase_accrual', 'shares_retired',
                'treasury_shares_acquired', 'treasury_value_acquired',
                'issuance_proceeds', 'sbc', 'tax_withholding', 'shares_outstanding',
                'treasury_shares_balance', 'treasury_shares_balance_alt',
                'treasury_value_balance', 'treasury_shares_reissued',
                'shares_issued'):
        SEC[key] = parse_concept(RAW.get(_HD_FIXTURE_ALIAS.get(key, key), {'units': {}}))

    def series(key, scale=1e6):
        return {y: e['val'] / scale for y, e in parse_concept(RAW[key]).items()}

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
    DEFL = {y: DEFL_SRC.get(y - 1, DEFL_SRC.get(max(DEFL_SRC))) for y in range(2010, 2027)}

    return CFG, FIN, SEC, PRICES, DEFL, COE


def run_hd(CFG=None, FIN=None, SEC=None, PRICES=None, DEFL=None, COE=None):
    """Build and .run() a BuybackStudy on whatever HD-shaped inputs are given
    (defaults: a fresh, uncorrupted set). Returns (study, exception_or_None)."""
    if CFG is None:
        CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
    study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, COE,
                         engine={'coe_longrun': CFG.coe_longrun})
    try:
        with io.StringIO() as _silence:
            study.run()
        return study, None
    except Exception as e:
        return study, e


print("=" * 90)
print("BASELINE SANITY CHECK: the uncorrupted Home Depot run must complete cleanly")
print("=" * 90)
_hd_good, _hd_err = run_hd()
if _hd_err is not None:
    print("FATAL: the UNCORRUPTED baseline itself failed to run:")
    traceback.print_exception(type(_hd_err), _hd_err, _hd_err.__traceback__)
    sys.exit(1)
print(f"OK: Home Depot baseline ran clean. retired_tag={_hd_good.retired_tag!r}, "
      f"{len(_hd_good.retired)} years resolved, {len(_hd_good.price_failures)} price failures, "
      f"dividends FY2020 = ${_hd_good.fin['dividends'][2020]:,.0f}m (nonzero, confirms HD pays a "
      "real dividend before we zero it in corruption 8).")
print()

# =============================================================================
# BASELINE 2: SYNTHETIC IN-WINDOW-SPLIT COMPANY (hand-built, no fixture covers
# an in-window split for real -- Home Depot's splits=[] and every other
# committed *_sec_raw.json in this folder belongs to a company with no split
# inside its own study window either). Five clean fiscal years, one clean
# 2-for-1 split effective 2014-07-01, i.e. between FY2013's typical filing
# date (2014-02-15, BEFORE the split) and FY2014's (2015-02-15, AFTER it).
# FY2012 and FY2013 are therefore filed on the OLD (pre-split) share basis and
# must be doubled by split_factor(); FY2014-2016 are already filed on the NEW
# basis and must not be touched. All dollar figures are unaffected by a split
# and are supplied directly on a single consistent basis throughout.
# =============================================================================

def load_syn():
    CFG = CompanyConfig(ticker="SYN", cik="0000000001", fy_end_month=12,
                        splits=[("2014-07-01", 2)], first_year=2012, last_year=2016,
                        coe_longrun=0.05)

    # as-filed (raw) share counts: pre-split years on the OLD basis, so that
    # split_factor() doubling them lands on the same post-split trend
    # (510, 500, 490, 480, 470, 460mn) as the post-split years, which are
    # already reported on the new basis and get factor 1.0.
    SEC = {
        'shares_outstanding': {
            2011: {'val': 255e6, 'filed': '2012-02-15'},   # pre-split, *2 -> 510
            2012: {'val': 250e6, 'filed': '2013-02-15'},   # pre-split, *2 -> 500
            2013: {'val': 245e6, 'filed': '2014-02-15'},   # pre-split, *2 -> 490
            2014: {'val': 480e6, 'filed': '2015-02-15'},   # post-split, x1 -> 480
            2015: {'val': 470e6, 'filed': '2016-02-15'},   # post-split, x1 -> 470
            2016: {'val': 460e6, 'filed': '2017-02-15'},   # post-split, x1 -> 460
        },
        'shares_retired': {
            2012: {'val': 12e6, 'filed': '2013-02-15'},    # pre-split, *2 -> 24
            2013: {'val': 12e6, 'filed': '2014-02-15'},    # pre-split, *2 -> 24
            2014: {'val': 22e6, 'filed': '2015-02-15'},    # post-split, x1 -> 22
            2015: {'val': 21e6, 'filed': '2016-02-15'},    # post-split, x1 -> 21
            2016: {'val': 20e6, 'filed': '2017-02-15'},    # post-split, x1 -> 20
        },
        'repurchase_cash': {},   # filled in below, after the price ramp is built
    }

    FIN = {
        # net income and weighted-average diluted shares: plain per-year
        # figures already on a consistent (post-split) basis, as GAAP requires
        # for a company's own current comparative filings -- unlike the raw
        # XBRL share-count facts above, which retain the basis in force on
        # their OWN filing date and are why split_factor() exists at all.
        'net_income':         {2011: 800.0, 2012: 850.0, 2013: 900.0, 2014: 950.0,
                                2015: 1000.0, 2016: 1050.0},
        'wtd_diluted_shares': {2011: 512.0, 2012: 505.0, 2013: 495.0, 2014: 485.0,
                                2015: 475.0, 2016: 465.0},
        # diluted EPS = net_income / wtd_diluted_shares, i.e. correctly
        # RESTATED onto today's post-split basis, the properly-restated
        # figure a company's current 10-K actually prints. Corruption 9
        # substitutes the AS-FILED (pre-restatement) figure for the two years
        # filed before the split instead.
        'diluted_eps': {2011: 800.0 / 512.0, 2012: 850.0 / 505.0, 2013: 900.0 / 495.0,
                        2014: 950.0 / 485.0, 2015: 1000.0 / 475.0, 2016: 1050.0 / 465.0},
        'dividends':        {2012: 255.0, 2013: 270.0, 2014: 285.0, 2015: 300.0, 2016: 315.0},
        'operating_income': {2011: 1050.0, 2012: 1100.0, 2013: 1150.0, 2014: 1200.0,
                              2015: 1250.0, 2016: 1300.0},
        'tax_provision':    {2012: 250.0, 2013: 265.0, 2014: 280.0, 2015: 295.0, 2016: 310.0},
        'pretax_income':    {2012: 1100.0, 2013: 1165.0, 2014: 1230.0, 2015: 1295.0, 2016: 1360.0},
        'common_equity':    {2011: 4000.0, 2012: 4200.0, 2013: 4400.0, 2014: 4600.0,
                              2015: 4800.0, 2016: 5000.0},
        'total_debt':       {y: 1500.0 for y in range(2011, 2017)},
        'financial_assets': {y: 300.0 for y in range(2011, 2017)},
    }

    # smooth, continuous, ALREADY split-adjusted monthly closes -- no jump at
    # the split date, exactly as the PRICES contract in buyback_study_TEMPLATE
    # requires ("split-adjusted close"). Linear ramp $37 (Jan 2012) to $58.5
    # (Dec 2016), comfortably bracketing every implied price paid above.
    PRICES = {}
    months = [(y, m) for y in range(2011, 2018) for m in range(1, 13)]
    n = len(months)
    for i, (y, m) in enumerate(months):
        PRICES[(y, m)] = 30.0 + 35.0 * i / (n - 1)

    COE = {y: 0.05 for y in range(2010, 2018)}
    DEFL = {2010: 1.20, 2011: 1.18, 2012: 1.15, 2013: 1.12, 2014: 1.09,
            2015: 1.06, 2016: 1.03, 2017: 1.00}

    # repurchase cash is built AFTER the price ramp above so the implied price
    # paid (cash / post-split shares retired) lands exactly on that year's
    # mean traded price and never trips the price validator on its own --
    # cash is a dollar figure and is never touched by split_factor().
    retired_post_split = {2012: 24e6, 2013: 24e6, 2014: 22e6, 2015: 21e6, 2016: 20e6}
    for y, q in retired_post_split.items():
        fy_mean = sum(PRICES[(y, m)] for m in range(1, 13)) / 12.0
        SEC['repurchase_cash'][y] = {'val': q * fy_mean, 'filed': SEC['shares_retired'][y]['filed']}

    return CFG, FIN, SEC, PRICES, DEFL, COE


def run_syn(CFG=None, FIN=None, SEC=None, PRICES=None, DEFL=None, COE=None):
    if CFG is None:
        CFG, FIN, SEC, PRICES, DEFL, COE = load_syn()
    study = BuybackStudy(CFG, FIN, SEC, PRICES, DEFL, COE,
                         engine={'coe_longrun': CFG.coe_longrun})
    try:
        study.run()
        return study, None
    except Exception as e:
        return study, e


print("=" * 90)
print("BASELINE SANITY CHECK: the uncorrupted synthetic in-window-split company")
print("=" * 90)
_syn_good, _syn_err = run_syn()
if _syn_err is not None:
    print("FATAL: the UNCORRUPTED synthetic baseline itself failed to run:")
    traceback.print_exception(type(_syn_err), _syn_err, _syn_err.__traceback__)
    sys.exit(1)
_syn_cfg = load_syn()[0]
assert _syn_cfg.split_factor("2013-06-01") == 2.0, "synthetic split factor wrong pre-split"
assert _syn_cfg.split_factor("2015-06-01") == 1.0, "synthetic split factor wrong post-split"
print(f"OK: synthetic baseline ran clean. retired_tag={_syn_good.retired_tag!r}, "
      f"retired={ {y: round(v,1) for y,v in _syn_good.retired.items()} }, "
      f"unresolved={_syn_good.unresolved_years}, price_failures={_syn_good.price_failures}")
print()

# =============================================================================
# GUARD DETECTION
# =============================================================================
# Rather than grep the notes for loose keywords (which false-positives badly
# -- e.g. eps_attribution()'s routine "...SPLIT into operating and financial"
# note contains the substring "split" and would wrongly look like a guard
# against corruption 1/9's STOCK split, even in an UNCORRUPTED run), this
# builds an explicit allow-list of the distinctive, ALL-CAPS/named guard
# phrases actually used by buyback_study_TEMPLATE.py's notes.append() calls
# (found by grepping every such call in the file) and only credits a
# corruption with being "caught" if (a) it raises an exception, or (b) it
# causes a NEW note -- one absent from the matching uncorrupted baseline's
# own notes -- that contains one of those phrases.
GUARD_SIGNATURES = [
    "SHARE COUNT FROM THE COVER PAGE",
    "SHARE COUNT EXTENDED FROM THE COVER PAGE",
    "COVER-PAGE SHARE COUNT REFUSED",
    "NO SHARE COUNT IS REACHABLE THROUGH THE STRUCTURED INTERFACE",
    "ISSUANCE-RATE FALLBACK REFUSED",
    "NEGATIVE RETIREMENT REFUSED",
    "NO SHARE COUNT for",
    "NO GROSS PRICE",
    "EARNINGS ATTRIBUTION NOT COMPUTED AT ALL",
    "EARNINGS ATTRIBUTION NOT SPLIT",
    "TIMING TEST EXCLUDES",
    "TIMING TEST NOT COMPUTED",
    "NO DIVIDEND",
    "ENTRY EFFECT, TIMING DEPENDENCE AT OR ABOVE 100 PERCENT",
    "ENTRY EFFECT, TIMING DEPENDENCE ELEVATED",
    "disagree on the SIGN",
    "EQUITY RAISE REFUSED",
    "IMPLIED PRICE OUTSIDE TRADED RANGE",
    "IMPLIED ISSUE PRICE OUTSIDE TRADED RANGE",
    "COMPENSATION WEDGE MISSING COMPONENT",
    "NO MEASURABLE REPURCHASE IN THIS WINDOW",
    "NOT A REPURCHASE PROGRAM",
]


def guard_hits(study, baseline):
    """NEW notes (absent from `baseline`'s own notes) that contain one of the
    named GUARD_SIGNATURES. Returns the list of matching note strings."""
    baseline_notes = set(baseline.notes)
    new_notes = [n for n in study.notes if n not in baseline_notes]
    return [n for n in new_notes if any(sig in n for sig in GUARD_SIGNATURES)]


def guard_name(hits):
    names = []
    for h in hits:
        for sig in GUARD_SIGNATURES:
            if sig in h:
                names.append(sig)
                break
    return "; ".join(sorted(set(names))) if names else "NONE"


# =============================================================================
# THE TEN CORRUPTIONS
# =============================================================================

# ----------------------------------------------------------------- #1
print("=" * 90)
print("#1  delete a split from the split list (synthetic in-window-split case)")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_syn()
CFG_bad = CompanyConfig(ticker=CFG.ticker, cik=CFG.cik, fy_end_month=CFG.fy_end_month,
                        splits=[],                       # <-- the split is deleted
                        first_year=CFG.first_year, last_year=CFG.last_year,
                        coe_longrun=CFG.coe_longrun)
s1, e1 = run_syn(CFG_bad, FIN, SEC, PRICES, DEFL, COE)
if e1 is not None:
    guard, passed = f"exception ({type(e1).__name__})", True
    detail = f"raised {type(e1).__name__}: {e1}"
else:
    hits = guard_hits(s1, _syn_good)
    guard = guard_name(hits)
    passed = bool(hits)
    detail = (f"good retired={ {y: round(v,1) for y,v in _syn_good.retired.items()} } vs "
              f"corrupted retired={ {y: round(v,1) for y,v in s1.retired.items()} }. FY2012/13 "
              f"share counts and shares-retired counts are no longer doubled (still on the "
              f"pre-split basis), so implied price paid roughly doubles in those years: "
              f"price_failures={s1.price_failures} (good baseline had none). new guard notes={hits}")
record(1, "delete a split from the split list", guard, passed, detail)

# ----------------------------------------------------------------- #2
print("=" * 90)
print("#2  multiply one year's filed share count by 1,000 (a unit error)")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
YR2 = 2018
before = SEC['shares_outstanding'][YR2]['val']
SEC['shares_outstanding'][YR2]['val'] = before * 1000
s2, e2 = run_hd(CFG, FIN, SEC, PRICES, DEFL, COE)
if e2 is not None:
    guard, passed = f"exception ({type(e2).__name__})", True
    detail = f"raised {type(e2).__name__}: {e2}"
else:
    hits = guard_hits(s2, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    retired_diff = {y: round(v, 1) for y, v in s2.retired.items() if y in (YR2 - 1, YR2, YR2 + 1)}
    issued_diff = {y: round(v, 1) for y, v in s2.issued.items() if y in (YR2 - 1, YR2, YR2 + 1)}
    detail = (f"FY{YR2} shares_outstanding forced from {before/1e6:.1f}mn to "
              f"{before*1000/1e6:.1f}mn (1000x). retired/issued around FY{YR2}: "
              f"retired={retired_diff}, issued={issued_diff} (good baseline "
              f"retired={ {y: round(v,1) for y,v in _hd_good.retired.items() if y in (YR2-1,YR2,YR2+1)} }, "
              f"issued={ {y: round(v,1) for y,v in _hd_good.issued.items() if y in (YR2-1,YR2,YR2+1)} }). "
              f"price_failures={s2.price_failures} (good had {_hd_good.price_failures}). "
              f"new guard notes={hits}")
record(2, "multiply one year's filed share count by 1,000 (unit error)", guard, passed, detail)

# ----------------------------------------------------------------- #3
print("=" * 90)
print("#3  invert the deflator (divide where the convention multiplies)")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
DEFL_bad = {y: (1.0 / v if v else v) for y, v in DEFL.items()}
s3, e3 = run_hd(CFG, FIN, SEC, PRICES, DEFL_bad, COE)
if e3 is not None:
    guard, passed = f"exception ({type(e3).__name__})", True
    detail = f"raised {type(e3).__name__}: {e3}"
else:
    hits = guard_hits(s3, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    y_probe = 2020
    real_eps_good = _hd_good.real_eps().get(y_probe)
    real_eps_bad = s3.real_eps().get(y_probe)
    detail = (f"deflator convention is 'MULTIPLY nominal by this' per the class docstring; "
              f"nothing in the template checks the deflator's own plausibility (it is never "
              f"compared to 1.0, to a CPI bound, or to its neighbouring years). FY{y_probe} "
              f"real EPS: good={real_eps_good:.4f} (deflator {DEFL[y_probe]:.4f}) vs "
              f"inverted={real_eps_bad:.4f} (deflator {DEFL_bad[y_probe]:.4f}) — a "
              f"{100*(real_eps_bad/real_eps_good-1):.1f}% distortion that propagates through "
              f"every real-dollar figure in the report (entry effect, AEG, round trip). "
              f"new guard notes={hits}")
record(3, "invert the deflator (divide instead of multiply)", guard, passed, detail)

# ----------------------------------------------------------------- #4
print("=" * 90)
print("#4  shift the price series by one year (a stale series)")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
PRICES_bad = {(y + 1, m): v for (y, m), v in PRICES.items()}
s4, e4 = run_hd(CFG, FIN, SEC, PRICES_bad, DEFL, COE)
if e4 is not None:
    guard, passed = f"exception ({type(e4).__name__})", True
    detail = f"raised {type(e4).__name__}: {e4}"
else:
    hits = guard_hits(s4, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    good_fails = sorted(y for y, *_ in _hd_good.price_failures)
    bad_fails = sorted(y for y, *_ in s4.price_failures)
    detail = (f"every calendar month's close is relabelled one year later, so validate_prices() "
              f"compares each year's real implied price against last year's traded range. "
              f"good baseline price_failures years={good_fails}; corrupted={bad_fails}. "
              f"new guard notes={hits}")
record(4, "shift the price series by one year (stale series)", guard, passed, detail)

# ----------------------------------------------------------------- #5
print("=" * 90)
print("#5  substitute another company's price series entirely (Oracle for Home Depot)")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
ORCL_PRICES = {}
for r in csv.DictReader(open('orcl_monthly.csv')):
    y, m, _ = r['Date'].split('-')
    ORCL_PRICES[(int(y), int(m))] = float(r['Close'])
s5, e5 = run_hd(CFG, FIN, SEC, ORCL_PRICES, DEFL, COE)
if e5 is not None:
    guard, passed = f"exception ({type(e5).__name__})", True
    detail = f"raised {type(e5).__name__}: {e5}"
else:
    hits = guard_hits(s5, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    good_fails = sorted(y for y, *_ in _hd_good.price_failures)
    bad_fails = sorted(y for y, *_ in s5.price_failures)
    detail = (f"Home Depot's own price series (roughly $180-$430/share across the window) is "
              f"replaced wholesale with Oracle's (roughly $20-$225/share, code/orcl_monthly.csv). "
              f"good baseline price_failures years={good_fails}; with Oracle's prices={bad_fails}. "
              f"new guard notes={hits}")
record(5, "substitute another company's price series entirely (ORCL for HD)", guard, passed, detail)

# ----------------------------------------------------------------- #6
print("=" * 90)
print("#6  truncate the share-count series before the end of the window")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
CUT_AFTER = 2022   # study window runs to 2026; drop FY2023-FY2026 of the raw share count
SEC['shares_outstanding'] = {y: v for y, v in SEC['shares_outstanding'].items() if y <= CUT_AFTER}
s6, e6 = run_hd(CFG, FIN, SEC, PRICES, DEFL, COE)
if e6 is not None:
    guard, passed = f"exception ({type(e6).__name__})", True
    detail = f"raised {type(e6).__name__}: {e6}"
else:
    hits = guard_hits(s6, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    unresolved_new = sorted(y for y in s6.unresolved_years if y > CUT_AFTER)
    no_count_new = sorted(getattr(s6, 'no_share_count_years', set()))
    detail = (f"CommonStockSharesOutstanding truncated after FY{CUT_AFTER} ({len(SEC['shares_outstanding'])} "
              f"years remain of {len(_hd_good.retired)+len(_hd_good.unresolved_years)+len(getattr(_hd_good,'no_share_count_years',set()))} in the full window). "
              f"unresolved_years after cut={unresolved_new}, no_share_count_years={no_count_new}, "
              f"years actually resolved in retired dict after cut={sorted(y for y in s6.retired if y > CUT_AFTER)}. "
              f"new guard notes={hits}")
record(6, "truncate the share-count series before the end of the window", guard, passed, detail)

# ----------------------------------------------------------------- #7
print("=" * 90)
print("#7  make one year's shares retired negative")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
YR7 = 2020
assert YR7 in SEC['treasury_shares_acquired'], "pick a year the fixture actually has data for"
SEC['treasury_shares_acquired'][YR7]['val'] = -abs(SEC['treasury_shares_acquired'][YR7]['val'])
s7, e7 = run_hd(CFG, FIN, SEC, PRICES, DEFL, COE)
if e7 is not None:
    guard, passed = f"exception ({type(e7).__name__})", True
    detail = f"raised {type(e7).__name__}: {e7}"
else:
    hits = guard_hits(s7, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    detail = (f"FY{YR7} TreasuryStockSharesAcquired forced negative. "
              f"FY{YR7} in s7.retired? {YR7 in s7.retired}; "
              f"negative_retirement_years={getattr(s7, 'negative_retirement_years', None)}; "
              f"FY{YR7} in unresolved_years? {YR7 in s7.unresolved_years}. new guard notes={hits}")
record(7, "make one year's shares retired negative", guard, passed, detail)

# ----------------------------------------------------------------- #8
print("=" * 90)
print("#8  zero a dividend series that genuinely exists (Home Depot)")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
real_div_sample = {y: FIN['dividends'][y] for y in sorted(FIN['dividends'])[:5]}
assert all(v > 0 for v in FIN['dividends'].values()), \
    "HD must genuinely pay a dividend every year for this test to mean anything"
FIN['dividends'] = {y: 0.0 for y in FIN['dividends']}   # keys survive, all values zeroed
s8, e8 = run_hd(CFG, FIN, SEC, PRICES, DEFL, COE)
if e8 is not None:
    guard, passed = f"exception ({type(e8).__name__})", True
    detail = f"raised {type(e8).__name__}: {e8}"
else:
    hits = guard_hits(s8, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    detail = (f"HD genuinely pays a real dividend (five sample years of FIN['dividends']: "
              f"{ {y: f'${v:,.0f}m' for y,v in real_div_sample.items()} }). Every value is "
              f"zeroed while the dict itself and its keys survive, so "
              f"`self.fin.get('dividends') is None` is False and the guard at "
              f"real_distributions() -- which only fires when the dividends KEY is absent, "
              f"raising ValueError unless `dividends_are_zero` was explicitly set -- never "
              f"triggers, because a present-but-zero series looks identical to it as a "
              f"genuinely unprofitable/non-paying year. new guard notes={hits}")
record(8, "zero a dividend series that genuinely exists (HD)", guard, passed, detail)

# ----------------------------------------------------------------- #9
print("=" * 90)
print("#9  feed AS-FILED (unrestated) EPS to a company with an in-window split (synthetic)")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_syn()
good_eps = dict(FIN['diluted_eps'])
# The two years filed BEFORE the split (FY2012, FY2013) are replaced with their
# AS-FILED (pre-restatement) figure -- i.e. computed against the smaller,
# pre-split share count actually in force when those years were first filed,
# roughly DOUBLE the properly-restated post-split figure. This is exactly
# what a naive scrape of the earliest-filed EPS fact for each year (rather
# than the latest-filed, restated one) would hand the template.
FIN['diluted_eps'][2012] = good_eps[2012] * 2.0
FIN['diluted_eps'][2013] = good_eps[2013] * 2.0
s9, e9 = run_syn(CFG, FIN, SEC, PRICES, DEFL, COE)
if e9 is not None:
    guard, passed = f"exception ({type(e9).__name__})", True
    detail = f"raised {type(e9).__name__}: {e9}"
else:
    hits = guard_hits(s9, _syn_good)
    guard = guard_name(hits)
    passed = bool(hits)
    attr_good = _syn_good.eps_attribution()
    attr_bad = s9.eps_attribution()
    detail = (f"FY2012/13 diluted EPS doubled to simulate the as-filed (pre-restatement) "
              f"figure a company filed before its own split — good EPS "
              f"{ {y: round(v,3) for y,v in good_eps.items() if y in (2012,2013,2014)} } vs "
              f"corrupted { {y: round(FIN['diluted_eps'][y],3) for y in (2012,2013,2014)} }. "
              f"diluted_eps is never passed through cfg.split_factor() anywhere in "
              f"buyback_study_TEMPLATE.py (confirmed by inspection: split_factor() is applied "
              f"only to share-count and price quantities, never to per-share EPS), so nothing "
              f"cross-checks EPS against the split at all. eps_attribution() FY2014 "
              f"from_earnings good={attr_good[2014]['from_earnings']:.4f} vs "
              f"corrupted={attr_bad[2014]['from_earnings']:.4f} (FY2013 EPS jump swallowed the "
              f"FY2013->FY2014 growth calc without complaint). new guard notes={hits}")
record(9, "feed AS-FILED (unrestated) EPS across an in-window split (synthetic)", guard, passed, detail)

# ----------------------------------------------------------------- #10
print("=" * 90)
print("#10  duplicate a fiscal year in one input series")
print("=" * 90)
CFG, FIN, SEC, PRICES, DEFL, COE = load_hd()
DUP_SRC, DUP_DST = 2019, 2020
before_val = FIN['net_income'][DUP_DST]
FIN['net_income'][DUP_DST] = FIN['net_income'][DUP_SRC]   # FY2020 = an exact copy of FY2019
s10, e10 = run_hd(CFG, FIN, SEC, PRICES, DEFL, COE)
if e10 is not None:
    guard, passed = f"exception ({type(e10).__name__})", True
    detail = f"raised {type(e10).__name__}: {e10}"
else:
    hits = guard_hits(s10, _hd_good)
    guard = guard_name(hits)
    passed = bool(hits)
    detail = (f"FY{DUP_DST} net_income overwritten with an EXACT copy of FY{DUP_SRC}'s value "
              f"(${FIN['net_income'][DUP_SRC]:,.0f}m, was ${before_val:,.0f}m — a "
              f"{100*(FIN['net_income'][DUP_SRC]/before_val - 1):.1f}% change). Nothing in the "
              f"template checks for adjacent-year values that are suspiciously (or exactly) "
              f"identical; a genuinely flat business and a copy-paste error are indistinguishable "
              f"to it. new guard notes={hits}")
record(10, "duplicate a fiscal year in one input series (FY2020 net_income = FY2019's)", guard, passed, detail)

# =============================================================================
# SUMMARY
# =============================================================================
print()
print("=" * 90)
print("SUMMARY")
print("=" * 90)
hdr = f"{'#':>2}  {'PASS/FAIL':9}  {'guard fired':55}  description"
print(hdr)
print("-" * len(hdr))
for num, desc, guard, status, detail in RESULTS:
    g = guard if len(guard) <= 53 else guard[:50] + "..."
    print(f"{num:>2}  {status:9}  {g:55}  {desc}")

n_pass = sum(1 for *_, status, _ in RESULTS if status == "PASS")
n_fail = len(RESULTS) - n_pass
print()
print(f"{n_pass} of {len(RESULTS)} corruptions caught by a named guard; "
      f"{n_fail} walked through with no attributable signal.")
print("This is a discovery report, not a gate: exiting 0 regardless.")
sys.exit(0)
