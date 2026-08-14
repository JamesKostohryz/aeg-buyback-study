# -*- coding: utf-8 -*-
"""run_study.py - ONE driver, any ticker. No company-specific code in this file.

WHY THIS EXISTS
---------------
Until 2026-08-13 the sentence "the template works on any company" was true of the
MEASUREMENTS and false of everything around them. `code/gen_article.py` carried
ninety-three references to Apple and `code/run_COST.py` was a Costco script.
Pointing the study at a new ticker meant writing a new driver, and a new driver
is a new place for a measure to be defined a second time - which is the defect
this repository has met eight times, most of them a number that was silently
wrong or silently inert while every gate reported success.

This file is the driver. What stays per company is a StudyConfig: the central
index key, the fiscal year end, the splits, the window, where the price series
comes from, which deflator to use, the real cost of equity, and any figure that
has to be read off a filing by a person - the excise tax being the standing
example, because most companies that disclose it use their own extension element
and it cannot be reached through the structured interface at all. Everything else
comes from buyback_study_TEMPLATE.py.

WHAT A GOOD RUN LOOKS LIKE
--------------------------
Not a clean sheet. A refusal is a PASS: it means a guard saw something it could
not honestly measure and said so instead of printing a number. Every refusal,
fallback and suppression this driver meets is collected and printed at the end
under REFUSALS, FALLBACKS AND SUPPRESSIONS, and a run that reports none on an
unfamiliar company should be read with suspicion rather than satisfaction.

USAGE
    python3 run_study.py --ticker ORCL --cik 0001341439 --fy-end-month 5 \
        --first-year 2013 --last-year 2025 --coe 0.055 --prices orcl_monthly.csv
    python3 run_study.py --config my_company.json
    python3 run_study.py --probe --ticker ORCL --cik 0001341439   # tags only

    --fetch writes the raw structured data to <ticker>_sec_raw.json so the run
    can be repeated OFFLINE against a committed fixture, which is how every
    gated test in this repository works. Without --fetch the fixture is read.
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.request

sys.path.insert(0, '..')
from buyback_study_TEMPLATE import (      # noqa: E402
    CompanyConfig, BuybackStudy, ExciseTaxUndisclosed, TAGS,
    parse_concept, merge_concept_series, irr,
)
import timing_decomposition as td          # noqa: E402,F401

UA = "AEG buyback study (james@jameskostohryz.com)"

# ---------------------------------------------------------------------------
# The financial statement lines the study needs, and every element name a
# company might file them under. ALTERNATES ARE NOT A CONVENIENCE. A company
# that renames a line partway through its history - dividends moving from
# PaymentsOfDividends to PaymentsOfDividendsCommonStock is the common case, and
# Costco does exactly that in fiscal 2022 - produces two half-length series, and
# a study built on either half alone is short by years without saying so.
# merge_concept_series() joins them and reports what it did.
# ---------------------------------------------------------------------------
FIN_TAGS = {
    # Alternates are not a convenience; see build_financials(). International
    # Business Machines files NetIncomeLoss only from 2015 and the earlier years
    # sit under ProfitLoss, which is why this line has three names on it.
    'net_income':          (['NetIncomeLoss', 'ProfitLoss',
                             'NetIncomeLossAvailableToCommonStockholdersBasic'],
                            'update', 1e6),
    'diluted_eps':         (['EarningsPerShareDiluted'], 'update', 1.0),
    'wtd_diluted_shares':  (['WeightedAverageNumberOfDilutedSharesOutstanding'], 'update', 1e6),
    'operating_income':    (['OperatingIncomeLoss'], 'update', 1e6),
    'pretax_income':       (['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                             'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments'],
                            'update', 1e6),
    'tax_provision':       (['IncomeTaxExpenseBenefit'], 'update', 1e6),
    'common_equity':       (['StockholdersEquity'], 'update', 1e6),
    'dividends':           (['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock'], 'update', 1e6),
    'financial_assets':    (['CashAndCashEquivalentsAtCarryingValue'], 'update', 1e6),
    'total_debt_nc':       (['LongTermDebtNoncurrent'], 'update', 1e6),
    'total_debt_c':        (['LongTermDebtCurrent'], 'update', 1e6),
    'ocf':                 (['NetCashProvidedByUsedInOperatingActivities'], 'update', 1e6),
    'capex':               (['PaymentsToAcquirePropertyPlantAndEquipment'], 'update', 1e6),
}

# Repurchase-side elements come straight from the template's own TAGS map, so a
# tag added there for one company is available to every company at once. That is
# the whole point: there is one list, in one place.
DEI_TAGS = {'shares_outstanding_dei': 'EntityCommonStockSharesOutstanding'}

# Every element name under which a company might file a dividend. If NONE of
# them is present, the company almost certainly pays no dividend - which is a
# fact worth stating rather than a hole worth defaulting. AutoZone is the
# archetype and it is not a rarity: it is the pure form of the thing this whole
# study is about, a company that returns everything through repurchases.
DIVIDEND_EVIDENCE_TAGS = (
    'PaymentsOfDividends', 'PaymentsOfDividendsCommonStock',
    'PaymentsOfDistributionsToAffiliates', 'Dividends', 'DividendsCommonStock',
    'CommonStockDividendsPerShareDeclared', 'CommonStockDividendsPerShareCashPaid',
)


SEC_KEYS = list(TAGS) + list(DEI_TAGS)


def _get(url, tries=4):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception as exc:                       # noqa: BLE001
            if getattr(exc, 'code', None) == 404:
                return None
            if i == tries - 1:
                return None
            time.sleep(1.5 * (i + 1))
    return None


def fetch_raw(cik, path):
    """Every element this study can use, in one file, so the run repeats offline.

    A tag the company does not file comes back 404 and is recorded as ABSENT -
    which is a fact about the company, not a missing input, and is a different
    thing from a filed zero. The distinction is defect 7 and it is why this
    stores the absence explicitly rather than just leaving the key out.
    """
    raw, absent = {}, []
    wanted = dict(TAGS)
    for k, (alts, _m, _s) in FIN_TAGS.items():
        for i, a in enumerate(alts):
            wanted[f'{k}__{i}'] = a
    for key, tag in wanted.items():
        d = _get(f"https://data.sec.gov/api/xbrl/companyconcept/"
                 f"CIK{cik}/us-gaap/{tag}.json")
        if d is None:
            absent.append(f'{key} ({tag})')
        else:
            raw[key] = d
        time.sleep(0.12)                    # the SEC asks for ten a second
    # The cover-page share count lives in the dei taxonomy, not us-gaap, and it
    # is the only share count a large number of filers still publish (defect 17).
    for key, tag in DEI_TAGS.items():
        d = _get(f"https://data.sec.gov/api/xbrl/companyconcept/"
                 f"CIK{cik}/dei/{tag}.json")
        if d is None:
            absent.append(f'{key} (dei:{tag})')
        else:
            raw[key] = d
        time.sleep(0.12)
    # Evidence for "this company pays no dividend", gathered rather than assumed.
    div_found = []
    for tag in DIVIDEND_EVIDENCE_TAGS:
        d = _get(f"https://data.sec.gov/api/xbrl/companyconcept/"
                 f"CIK{cik}/us-gaap/{tag}.json")
        if d is not None:
            div_found.append(tag)
            raw[f'divev__{tag}'] = d
        time.sleep(0.12)
    raw['__dividend_elements__'] = div_found
    raw['__absent__'] = absent
    with open(path, 'w') as f:
        json.dump(raw, f)
    return raw


def dividend_gap_verdict(raw, gap_years):
    """Is a hole in the dividend series a fact about the company or a hole in
    the data?

    DEFECT 19 (2026-08-13, found on Boeing). merge_concept_series refuses a
    series that does not cover the requested window, and it is right to: a
    missing year silently treated as zero is how this project has been bitten
    repeatedly. But Boeing genuinely paid no dividend from 2020 to 2024. A rule
    that cannot tell "the company suspended its dividend" from "somebody forgot
    a tag" will either crash on every dividend suspension or swallow every
    renamed element.

    So the question is settled on EVIDENCE. If NO dividend element of any known
    name covers the gap years, the company paid nothing in them. If one does,
    the gap is a tagging gap, the driver is told which element to add, and
    nothing is assumed.
    """
    covered = {}
    for tag in DIVIDEND_EVIDENCE_TAGS:
        d = raw.get(f'divev__{tag}')
        if not d:
            continue
        ys = set(parse_concept(d))
        hit = sorted(set(gap_years) & ys)
        if hit:
            covered[tag] = hit
    return covered


# Which statement lines are quoted PER SHARE and which are share COUNTS. A
# split restates both, in opposite directions, and getting this wrong is defect
# 25 - the worst thing found in the 2026-08-13 hardening pass.
PER_SHARE_LINES = ('diluted_eps',)
SHARE_COUNT_LINES = ('wtd_diluted_shares',)


def build_financials(raw, expected_years, cfg_obj=None):
    """The statement lines, in millions, with every alternate merged.

    A line the company files under none of its known names comes back missing
    and is reported. It is NOT defaulted to zero: a study that silently treats
    an untagged dividend stream as no dividends will close every identity it has
    and be wrong about the company.
    """
    fin, missing, gaps = {}, [], []
    for key, (alts, mode, scale) in FIN_TAGS.items():
        parts = [parse_concept(raw[f'{key}__{i}'])
                 for i in range(len(alts)) if f'{key}__{i}' in raw]
        parts = [p for p in parts if p]
        if not parts:
            missing.append(f'{key} ({" or ".join(alts)})')
            continue
        try:
            merged = (parts[0] if len(parts) == 1 else
                      merge_concept_series(parts, mode=mode,
                                           expected_years=expected_years, label=key))
        except ValueError as exc:
            # Coverage short. For most lines that is a data problem and the
            # refusal stands. For dividends it is usually a suspension, and
            # defect 19 settles which on evidence rather than on a default.
            merged = {}
            for pt in parts:
                merged.update(pt)
            gap = [y for y in expected_years if y not in merged]
            if key == 'dividends':
                covered = dividend_gap_verdict(raw, gap)
                if covered:
                    raise ValueError(
                        f"dividends are missing for {gap} and the element(s) "
                        f"{covered} DO cover those years. This is a tagging gap, "
                        "not a suspension. Add the element to FIN_TAGS and "
                        "re-fetch; nothing here will assume a zero.") from exc
                gaps.append(
                    f"dividends: no element of any known name covers {gap}, so the "
                    "company paid no dividend in those years. Taken as a genuine "
                    "zero on that evidence, not as a default.")
            else:
                gaps.append(f"{key}: coverage short, missing {gap}. {exc}")
        # DEFECT 25 (2026-08-13, found on Booking Holdings, and the most
        # dangerous defect in this session). Share counts were being restated
        # onto today's split basis - share_flows() multiplies every filed count
        # by the cumulative split factor - and prices were being restated, and
        # EARNINGS PER SHARE WAS NOT. Booking Holdings split twenty-five for one
        # on 6 April 2026, after the end of the study window, so every as-filed
        # earnings-per-share figure in the window is twenty-five times the
        # restated one. The study duly reported forward real earnings yields of
        # 87, 143 and 151 percent and a break-even real cost of equity of 92.72
        # percent, all of it internally consistent, all of it closing every
        # identity the template checks, and all of it wrong by a factor of
        # twenty-five.
        #
        # Apple never exposed this because its driver supplies an
        # already-restated earnings series from a committed file. Every company
        # read straight from the structured interface was exposed to it, and any
        # company with a split in or after its window would have published
        # nonsense.
        #
        # A per-share amount is DIVIDED by the factor a share count is
        # multiplied by. Both are done here, from the filed date of each fact,
        # and the template refuses the whole run if a driver forgets.
        if cfg_obj is not None and (key in PER_SHARE_LINES or key in SHARE_COUNT_LINES):
            per_share = key in PER_SHARE_LINES
            fin[key] = {}
            for y, e in merged.items():
                f = cfg_obj.split_factor(e['filed'])
                v = e['val'] / f if per_share else e['val'] * f
                fin[key][y] = v / scale
        else:
            fin[key] = {y: e['val'] / scale for y, e in merged.items()}
    debt_parts = [fin.pop(k) for k in ('total_debt_nc', 'total_debt_c') if k in fin]
    if debt_parts:
        ys = set().union(*[set(d) for d in debt_parts])
        fin['total_debt'] = {y: sum(d.get(y, 0.0) for d in debt_parts) for y in ys}
    return fin, missing, gaps


def build_sec(raw):
    return {k: parse_concept(raw[k]) for k in SEC_KEYS if k in raw}


def load_prices(path):
    """Monthly closes, already on today's split basis, keyed (year, month)."""
    px = {}
    for r in csv.DictReader(open(path)):
        y, m = r['Date'].split('-')[:2]
        px[(int(y), int(m))] = float(r['Close'])
    return px


def load_deflator(path, first, last):
    """The committed calendar-year CPI-U row, base 335.123.

    It is a MULTIPLIER: nominal times this equals base-year dollars. The row says
    so in its own label. A driver that divides by it produces a real series that
    leans the wrong way with time, and because the error is smooth and small in
    any one year no range check will catch it. This is not hypothetical - it was
    found in code/full_study_COST.py on 2026-08-13, where it had been sitting
    beside the template's own correct use of the same dictionary.
    """
    src = {}
    for r in csv.reader(open(path)):
        if r and r[0].startswith('CPI deflator'):
            hdr = list(csv.reader(open(path)))[0]
            src = {int(y): float(v) for y, v in zip(hdr[1:], r[1:]) if v.strip()}
    if not src:
        raise SystemExit(f"no CPI deflator row found in {path}")
    out, extrapolated = {}, []
    for y in range(first - 1, last + 2):
        if y in src:
            out[y] = src[y]
        else:
            out[y] = src[max(src)] if y > max(src) else src[min(src)]
            extrapolated.append(y)
    return out, extrapolated



# ---------------------------------------------------------------------------
# PRICES AND SPLITS, FETCHED RATHER THAN HANDED IN (2026-08-13)
# ---------------------------------------------------------------------------
# Until now a price series was a comma-separated file somebody built by hand and
# a split list was something somebody typed into a CompanyConfig. Both are inputs
# that a person can get wrong silently: a missed split restates every share count
# in the window by a factor of two or seven and the study still closes every
# identity it has. Apple's own list carries a seven-for-one and a four-for-one,
# and getting either wrong would move every figure in the published document.
#
# So both are read from the vendor and the split list is CHECKED rather than
# trusted: the raw close is adjusted by the cumulative split factor and the
# result must land inside the vendor's own dividend-and-split adjusted series
# to a tolerance, which it cannot do if a split is missing.
#
# WHY NOT JUST USE adjusted_close. It strips dividends as well as splits. A
# repurchase happened at a price somebody actually paid, and a dividend-adjusted
# price is not one. The study needs split-adjusted-only, which is why the
# factors are applied here rather than taken from the vendor.
EODHD_TOKEN_PATHS = (
    '/sessions/admiring-modest-hypatia/mnt/AEG-Project/.eodhd-token',
    os.path.expanduser('~/.eodhd-token'),
    '.eodhd-token', '../.eodhd-token',
)


def _eodhd_token(explicit=None):
    for p in ((explicit,) if explicit else ()) + EODHD_TOKEN_PATHS:
        if p and os.path.exists(p):
            return open(p).read().strip()
    raise SystemExit(
        "no EODHD token found. It lives at C:\\Users\\james\\AEG-Project\\.eodhd-token; "
        "pass --eodhd-token PATH if it is somewhere else. Never print it.")


def _eod(path, token, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://eodhd.com/api/{path}?{q}&fmt=json&api_token={token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}),
                                timeout=60) as r:
        return json.loads(r.read().decode())


def fetch_prices(ticker, token, first_year, last_year, exchange='US'):
    """Monthly closes and intra-month extremes, on TODAY'S split basis, plus the
    split list read from the vendor rather than typed in.

    Returns (prices, traded_range_by_calendar_month, splits, checks).
    """
    sym = f"{ticker}.{exchange}"
    start = f"{first_year - 3}-01-01"
    rows = _eod(f"eod/{sym}", token, period='m', **{'from': start, 'to': '2099-01-01'})
    try:
        splits_raw = _eod(f"splits/{sym}", token, **{'from': start, 'to': '2099-01-01'})
    except Exception:                                    # noqa: BLE001
        splits_raw = []
    splits = []
    rejected_pseudo_splits = []
    # DEFECT (2026-08-13, found on General Electric during the second
    # convergence batch; the same shape was flagged but not fixed on IBM
    # earlier the same day). The vendor's splits endpoint reports a SPINOFF
    # value adjustment in exactly the same feed and exactly the same shape
    # as a genuine share split: General Electric shows FOUR entries in its
    # window, and only one - 2021-08-02, "1.000000/8.000000", the real
    # 1-for-8 reverse split - is one. The other three land within a few
    # weeks of GE's HealthCare spinoff (2023-01-04) and GE Vernova spinoff
    # (2024-04-02), plus a fourth, unexplained one (2019-02-26), and all
    # three report as an ugly, un-reduced fraction over a large denominator:
    # "1281.000000/1000.000000", "1253.000000/1000.000000",
    # "104.000000/100.000000" - a shape no company ever declares a real
    # split in (nobody splits their stock 1281-for-1000). IBM's Kyndryl
    # spinoff (2021-11-04) shows the identical signature,
    # "1046.000000/1000.000000". A genuine split - every one seen in this
    # repository, including Booking Holdings' 25-for-1 - is reported by the
    # SAME vendor as a small, already-clean fraction: "25.000000/1.000000",
    # "1.000000/8.000000". So a raw fraction is trusted as a real split only
    # if BOTH sides, AS THE VENDOR STATED THEM, before any reduction, are
    # no larger than 50 - comfortably above every real split ratio this
    # project has met (the largest is 50-for-1, which is itself the
    # threshold) and comfortably below every spinoff-adjustment fraction
    # met so far, which all carry a denominator of 100 or 1000. Rejected
    # entries are not silently dropped; they are named so a person can
    # decide whether one of them is a real split this threshold was wrong
    # to exclude.
    MAX_SPLIT_FRACTION_TERM = 50
    for s in splits_raw or []:
        a, _, b = (s.get('split') or '').partition('/')
        try:
            fa, fb = float(a), float(b)
            f = fa / fb
        except (ValueError, ZeroDivisionError):
            continue
        if not f or abs(f - 1.0) <= 1e-9:
            continue
        if fa > MAX_SPLIT_FRACTION_TERM or fb > MAX_SPLIT_FRACTION_TERM:
            rejected_pseudo_splits.append((s['date'], a.strip(), b.strip(), f))
            continue
        splits.append((s['date'], f))
    splits.sort()
    if rejected_pseudo_splits:
        note('SPLIT VENDOR DATA REJECTED',
             f"{ticker}: the price vendor's splits feed reported " +
             ", ".join(f"{d} ({a}/{b}, ratio {f:.4f})"
                       for d, a, b, f in rejected_pseudo_splits) +
             " - rejected as a genuine share split because one side of the "
             "raw fraction exceeds "
             f"{MAX_SPLIT_FRACTION_TERM}. This shape (an un-reduced fraction "
             "over a denominator of 100 or 1000) has twice now been a "
             "SPINOFF value adjustment, not a split, on IBM and General "
             "Electric. If this company genuinely did split its stock by an "
             "unusual ratio, this rejection is wrong and the split must be "
             "supplied explicitly via --config/splits instead of --fetch.")

    def factor(datestr):
        """Cumulative split factor to apply to a price quoted on `datestr` to
        put it on today's basis. Same convention as CompanyConfig.split_factor."""
        f = 1.0
        for d, k in splits:
            if datestr < d:
                f *= k
        return f

    prices, rng, checks = {}, {}, []
    worst = 0.0
    for r in rows:
        d = r['date']
        k = factor(d)
        y, m = int(d[:4]), int(d[5:7])
        prices[(y, m)] = r['close'] / k
        rng[(y, m)] = (r['low'] / k, r['high'] / k)
        # The vendor's own adjusted series differs from ours only by dividends,
        # which are never negative, so ours must sit AT OR ABOVE it and within a
        # plausible cumulative dividend yield. A missing split shows up here as
        # a factor-of-two or factor-of-seven miss, not as a rounding difference.
        adj = r.get('adjusted_close')
        if adj:
            ratio = (r['close'] / k) / adj
            worst = max(worst, abs(math.log(ratio)) if ratio > 0 else 99)
    checks.append(('split reconciliation', worst))
    return prices, rng, splits, checks


def traded_range_by_fiscal_year(rng, cfg_like, first_year, last_year):
    """Intra-month extremes rolled up to fiscal years, using the SAME
    calendar-month-to-fiscal-year map the rest of the study uses. A second,
    independently written definition of 'which months are in fiscal year y' is
    exactly the shape of defect 8."""
    out = {}
    for fy in range(first_year, last_year + 1):
        vals = [rng[k] for k in cfg_like.fiscal_months(fy) if k in rng]
        if vals:
            out[fy] = (min(v[0] for v in vals), max(v[1] for v in vals))
    return out

# ---------------------------------------------------------------------------
class StudyConfig:
    """Everything that legitimately varies by company, and nothing else."""

    def __init__(self, ticker, cik, fy_end_month, first_year, last_year,
                 coe_longrun, prices, splits=None, deflator='../AAPL_restated.csv',
                 split_year=None, coe_by_year=None, excise_disclosed=None,
                 allow_statutory_excise_estimate=False,
                 withholding_in_repurchase_cash=None, raises=None,
                 plan_shares=None, raise_reconciling_items=None,
                 coe_is_placeholder=True, notes=None, traded_range=None,
                 eodhd_token=None, exchange='US'):
        self.__dict__.update(locals())
        del self.__dict__['self']
        self.splits = splits or []
        self.notes = notes or []

    @classmethod
    def from_json(cls, path):
        d = json.load(open(path))
        d['splits'] = [tuple(s) for s in d.get('splits', [])]
        if d.get('coe_by_year'):
            d['coe_by_year'] = {int(k): v for k, v in d['coe_by_year'].items()}
        if d.get('excise_disclosed'):
            d['excise_disclosed'] = {int(k): v for k, v in d['excise_disclosed'].items()}
        if d.get('withholding_in_repurchase_cash'):
            d['withholding_in_repurchase_cash'] = {
                int(k): v for k, v in d['withholding_in_repurchase_cash'].items()}
        return cls(**d)


REF = []            # every refusal, fallback and suppression this run met


def note(kind, text):
    REF.append((kind, text))


def probe(cik):
    """Which elements does this company actually file? Run this before choosing
    a window, because a study window is a claim about what the data supports."""
    print(f"tag probe, CIK {cik}")
    wanted = dict(TAGS)
    for k, (alts, _m, _s) in FIN_TAGS.items():
        for i, a in enumerate(alts):
            wanted[f'{k}__{i}'] = a
    for key, tag in sorted(wanted.items()):
        d = _get(f"https://data.sec.gov/api/xbrl/companyconcept/"
                 f"CIK{cik}/us-gaap/{tag}.json")
        if d is None:
            print(f"  ABSENT   {key:<32} {tag}")
        else:
            ys = sorted(parse_concept(d))
            print(f"  present  {key:<32} {tag}  "
                  f"FY{ys[0] if ys else '-'}-{ys[-1] if ys else '-'} "
                  f"({len(ys)} annual)")
        time.sleep(0.12)


# ---------------------------------------------------------------------------
def run(cfg, raw_path, fetch=False, csv_out=None):
    cik = cfg.cik.zfill(10)
    if fetch or not os.path.exists(raw_path):
        print(f"fetching {cfg.ticker} from data.sec.gov ...")
        raw = fetch_raw(cik, raw_path)
    else:
        raw = json.load(open(raw_path))
    for a in raw.get('__absent__', []):
        note('ABSENT TAG', f"{cfg.ticker} does not file {a} in any year")

    years = list(range(cfg.first_year, cfg.last_year + 1))

    # Prices and splits. Handing in a comma-separated file still works and is
    # what the committed fixtures do, but the default is now to fetch both, and
    # to CHECK the split list rather than trust a typed one.
    if cfg.prices:
        prices = load_prices(cfg.prices)
        splits = cfg.splits
        tr = None
        if cfg.traded_range:
            tr = {int(r['fiscal_year']): (float(r['intraday_low']), float(r['intraday_high']))
                  for r in csv.DictReader(open(cfg.traded_range))}
        else:
            note('WEAKER CHECK', "no intra-period traded range supplied, so implied prices "
                                 "are validated against period-end closes only, which is "
                                 "the weaker test")
    else:
        prices, _rng, _fetched_splits, _chk = fetch_prices(
            cfg.ticker, _eodhd_token(cfg.eodhd_token), cfg.first_year, cfg.last_year)
        splits = cfg.splits or _fetched_splits
        if cfg.splits and _fetched_splits and (
                sorted(cfg.splits) != sorted(_fetched_splits)):
            note('SPLITS DISAGREE',
                 f"the configured split list {cfg.splits} is not the one the price vendor "
                 f"reports, {_fetched_splits}. A missed split restates every share count in "
                 "the window and the study still closes every identity it has. Resolve this "
                 "before reading anything below.")
        for _lab, _v in _chk:
            if _lab == 'split reconciliation' and _v > 0.55:
                note('SPLITS SUSPECT',
                     f"split-adjusted closes diverge from the vendor's own adjusted series by "
                     f"up to {100*(math.exp(_v)-1):.0f}%, which is far more than any plausible "
                     "cumulative dividend yield. A split is probably missing.")
        _cfgtmp = CompanyConfig(ticker=cfg.ticker, cik=cik, fy_end_month=cfg.fy_end_month,
                                splits=splits, first_year=cfg.first_year,
                                last_year=cfg.last_year)
        tr = traded_range_by_fiscal_year(_rng, _cfgtmp, cfg.first_year, cfg.last_year)

    # The split list has to exist before the statement lines are built: a
    # per-share figure filed before a split has to be divided by it (defect 25).
    _cfg_obj = CompanyConfig(ticker=cfg.ticker, cik=cik, fy_end_month=cfg.fy_end_month,
                             splits=splits, first_year=cfg.first_year,
                             last_year=cfg.last_year, coe_longrun=cfg.coe_longrun)
    fin, missing, gaps = build_financials(raw, years, _cfg_obj)
    for m in missing:
        note('MISSING LINE', f"no element found for {m}; it is NOT treated as zero")
    for g in gaps:
        note('COVERAGE GAP', g)
    if splits:
        note('SPLITS APPLIED',
             f"{len(splits)} split(s) {splits}: share counts are multiplied by the "
             "cumulative factor and per-share amounts divided by it, both from each "
             "fact's own filed date. A split after the end of the window still "
             "restates every year in it.")
    sec = build_sec(raw)
    for base, alt in (('treasury_shares_balance', 'treasury_shares_balance_alt'),
                      ('treasury_value_balance', 'treasury_value_balance_alt')):
        if sec.get(base) and sec.get(alt):
            # DEFECT (2026-08-13, found on Johnson & Johnson and Chipotle
            # Mexican Grill during the convergence sweep). Every OTHER merge
            # in this driver (build_financials(), above) catches a coverage
            # shortfall and turns it into a named gap; this one, alone,
            # required full coverage of the whole window and crashed instead
            # when a company's two treasury tags did not jointly reach it.
            # Falls back to the plain union - later filing wins on any
            # overlap, the same rule `mode='update'` already applies when
            # coverage IS sufficient - and names what is still missing rather
            # than defaulting it to anything.
            try:
                sec[base] = merge_concept_series([sec[base], sec[alt]], mode='update',
                                                 expected_years=years, label=base)
            except ValueError as exc:
                merged = dict(sec[base])
                merged.update(sec[alt])
                gap = [y for y in years if y not in merged]
                sec[base] = merged
                note('COVERAGE GAP',
                     f"{base}: {exc} Falling back to the union of the two tags "
                     "without requiring full coverage" +
                     (f"; still short {gap}" if gap else "") + ".")

    defl, extrap = load_deflator(cfg.deflator, cfg.first_year, cfg.last_year)
    if extrap:
        note('DEFLATOR', f"no published index for {extrap}; the nearest published year is "
                         "carried and every real figure in those years inherits that "
                         "approximation")
    # The cost of equity is an INPUT, not a property of the template. A scalar
    # and a year-by-year series are equally acceptable here and the study's
    # mechanics do not depend on which is supplied or on its level: the
    # break-even rate published alongside every entry effect is the rate-free
    # reading, and code/coe_invariance_test.py proves that swapping the rate
    # moves only the quantities that are supposed to move.
    coe = cfg.coe_by_year or {y: cfg.coe_longrun
                              for y in range(cfg.first_year - 2, cfg.last_year + 2)}
    if cfg.coe_is_placeholder:
        note('COST OF EQUITY',
             f"the {100*cfg.coe_longrun:.2f}% real cost of equity is a PLACEHOLDER for this "
             "ticker. It scales the capital charge and can move the SIGN of the entry "
             "effect, so no sign should be quoted until a real series is supplied. It "
             "changes no other mechanic: swap it and everything else recomputes.")

    study = BuybackStudy(
        CompanyConfig(ticker=cfg.ticker, cik=cik, fy_end_month=cfg.fy_end_month,
                      splits=splits, first_year=cfg.first_year,
                      last_year=cfg.last_year, coe_longrun=cfg.coe_longrun),
        fin, sec, prices, defl, coe,
        engine={'coe_longrun': cfg.coe_longrun},
        raises=cfg.raises or [], plan_shares=cfg.plan_shares or {},
        raise_reconciling_items=cfg.raise_reconciling_items or {},
        withholding_in_repurchase_cash=cfg.withholding_in_repurchase_cash or {})
    # Defect 15. "Pays no dividend" is asserted only on the evidence that no
    # dividend element of any known name is filed in any year.
    _div_elems = raw.get('__dividend_elements__')
    if _div_elems is not None and not _div_elems:
        study.dividends_are_zero = True
        note('NO DIVIDEND', f"{cfg.ticker} files none of the "
                            f"{len(DIVIDEND_EVIDENCE_TAGS)} dividend elements this driver "
                            "checks, in any year. The dividend stream is taken as a "
                            "genuine zero. That is a claim about the company; check it.")
    elif _div_elems is None and 'dividends' not in fin:
        note('REFUSAL', "no dividend series and no evidence either way - the fixture "
                        "predates the dividend probe. Re-fetch with --fetch before "
                        "trusting anything that uses distributions.")
    for n in cfg.notes:
        study.notes.append(n)
    study.run(traded_range=tr)

    print("=" * 100)
    print(f"{cfg.ticker}  FY{cfg.first_year}-FY{cfg.last_year}   CIK {cik}")
    print(f"retired tag = {study.retired_tag}   unresolved = {sorted(study.unresolved_years)}"
          f"   derived = {sorted(study.derived_years)}   price failures = {study.price_failures}")
    print("=" * 100)
    if study.derived_years:
        note('FALLBACK', f"shares retired DERIVED, not filed, in {sorted(study.derived_years)} - "
                         "the count is a residual of the share-count identity and its implied "
                         "price is checked against the year's traded range, not its close")
    if 'NONE FOUND' in (study.retired_tag or ''):
        note('REFUSAL', "no retirement or treasury flow element is tagged by this company "
                        "under any name this template knows. Probe the elements before "
                        "assuming the company did not repurchase - it may simply file the "
                        "flow under a name not yet in TAGS.")
    if study.unresolved_years:
        note('REFUSAL', f"{sorted(study.unresolved_years)} have no determinable share count and "
                        "are excluded from BOTH sides of every average, not just the share side")
    if study.price_failures:
        note('REFUSAL', f"price validator FAILED on {study.price_failures}: the implied average "
                        "price paid falls outside the year's traded range, so the derived share "
                        "count cannot be right")

    # report() returns one already-joined block, not a list of lines.
    print(study.report())

    # ------------------------------------------------------- the entry effect
    print("\n" + "-" * 100)
    print("ENTRY EFFECT, BREAK-EVEN, AND THE EARNINGS-TIMING DECOMPOSITION")
    print("-" * 100)
    try:
        EE = study.entry_effect(rho=cfg.coe_longrun, coe_by_year=cfg.coe_by_year,
                                split_year=cfg.split_year)
    except (ValueError, KeyError) as exc:
        note('REFUSAL', f"entry effect not struck at all: {exc}")
        EE = None
    if EE is None or not EE['tranches']:
        note('REFUSAL', "NO ENTRY EFFECT IN THIS WINDOW: not one repurchase year has a "
                        "retirement count, repurchase cash, a deflator and a following "
                        "year's earnings together. An empty section is never printed as "
                        "though it were an empty result.")
        print("  NOT STRUCK IN ANY YEAR. See the refusals below.")
        for y, why in sorted((EE or {}).get('excluded_years', {}).items()):
            print(f"    FY{y}: {why}")
    if EE is not None and EE['tranches']:
        for t in EE['tranches']:
            print(f"  FY{t}  retired {study.retired[t]:8,.1f}mn  real px {EE['real_price_paid'][t]:9,.2f}  "
                  f"real EPS(t+1) {EE['real_eps'][t+1]:8,.3f}  "
                  f"fwd yield {100*EE['real_eps'][t+1]/EE['real_price_paid'][t]:6.2f}%  "
                  f"entry {EE['per_year'][t]/1000:+9.3f}bn")
        for y, why in sorted(EE['excluded_years'].items()):
            note('SUPPRESSED YEAR', f"FY{y} carries no entry effect: {why}")
        print(f"  CUMULATIVE {EE['total']/1000:+.3f}bn at {100*cfg.coe_longrun:.2f}% real")
        print(f"  break-even real cost of equity: {100*EE['break_even']:.2f}%  "
              f"(headroom {100*EE['headroom']:+.2f} points)")
        for k, v in EE['break_even_windows'].items():
            if k != 'all' and v is not None:
                print(f"    {k:<6} tranches: {100*v:.2f}%")
        if EE['band'] is None:
            note('REFUSAL', EE['decomposition_note'])
        else:
            print(f"\n  real EPS trend {100*EE['trend_growth']:+.2f}%/yr; identity residual "
                  f"{EE['identity_residual']:.2e}")
            print(f"  {'estimator':<14}{'family':<12}{'decision':>11}{'timing':>10}{'dec b/e':>10}")
            for n in td.ALL_ESTIMATORS:
                d = EE['band'][n]
                print(f"  {n:<14}{d['family']:<12}{d['decision']/1000:>+11.3f}"
                      f"{d['timing']/1000:>+10.3f}{100*d['break_even']:>9.2f}%")
            print(f"  TIMING DEPENDENCE {100*EE['timing_dependence']:.0f}% of the headline")
            if EE['timing_dependence'] >= 1.0:
                note('DIAGNOSTIC', "timing dependence AT OR ABOVE 100%: the accident of which "
                                   "earnings year followed each purchase is larger than the "
                                   "headline it sits inside. The entry effect must not be read "
                                   "as a verdict on the price paid for this company.")
            elif EE['timing_dependence'] >= 0.5:
                note('DIAGNOSTIC', "timing dependence ELEVATED: publish the decomposition beside "
                                   "the entry effect, never the headline alone.")
            if EE['families_disagree_on_sign']:
                note('DIAGNOSTIC', "the symmetric and backward-looking trend families disagree on "
                                   "the SIGN of the price decision; the trend level is not "
                                   "point-identified on this company. Publish the band.")

    # -------------------------------------- net retirement cost + permanence
    print("\n" + "-" * 100)
    print("NET RETIREMENT COST, AND WHETHER THE REMOVAL IS PERMANENT")
    print("-" * 100)
    NC = study.net_retirement_cost()
    print(f"  permanence read from the filings: {NC['basis'].upper()} - \"{NC['label']}\"")
    if NC['net_reduction'] is not None and NC['net_reduction'] <= 0:
        note('UNDEFINED MEASURE',
             f"net share reduction over the window is {NC['net_reduction']:,.1f}mn - the "
             "company ended with MORE shares outstanding than it started with. The cost "
             "per share removed is undefined and is not reported; the program absorbed "
             "issuance rather than reducing the count.")
    print(f"  {NC['permanence_note']}")
    for lab, k in (("A  cash / GROSS retired (the transacted price)", 'A_gross_price'),
                   (f"B  cash / NET reduction (cost per share {NC['label']})", 'B_per_share'),
                   ("C  (cash - plan proceeds) / NET", 'C_per_share'),
                   ("D  (cash + withholding - proceeds) / NET", 'D_per_share')):
        v = NC[k]
        print(f"  {lab:<58} {'n/a' if v is None else format(v, ',.2f')}")
    if NC['suppressed_years']:
        note('SUPPRESSED YEAR',
             f"net retirement cost suppressed in FY{NC['suppressed_years']}: the net reduction is "
             f"below {100*NC['min_net_frac']:.2f}% of opening shares, and a ratio on a small or "
             "negative denominator is meaningless and far more likely to be believed than a "
             "missing one")
    if NC['basis'] != 'retired':
        note('LABEL CHANGED', f"this company does not cancel its repurchased shares "
                              f"({NC['basis']}), so 'permanently removed' is NOT available to it")

    # ------------------------------------------------------------ excise tax
    print("\n" + "-" * 100)
    print("EXCISE TAX ON NET REPURCHASES (Internal Revenue Code section 4501)")
    print("-" * 100)
    try:
        EX = study.excise_tax(
            disclosed=cfg.excise_disclosed,
            allow_statutory_estimate=cfg.allow_statutory_excise_estimate)
        for y in sorted(EX['years']):
            r = EX['years'][y]
            if r['exposure'] > 0:
                print(f"  FY{y}  exposure {100*r['exposure']:5.1f}%  "
                      f"low {r.get('low') or 0:9,.1f}  high {r.get('high') or 0:9,.1f}  "
                      f"{r.get('source', '')}")
        print(f"  BAND  {EX['total_low']:,.1f} netted (ESTIMATE) to {EX['total_high']:,.1f} gross "
              "(a true upper bound)")
        if EX['undisclosed_years']:
            note('ESTIMATE ANNOUNCED',
                 f"no filed excise figure in FY{EX['undisclosed_years']}; the numbers above are "
                 "this study's arithmetic, published as a MEMORANDUM line outside the reconciled "
                 "sources-and-uses account, and never described as the company's disclosure")
    except ExciseTaxUndisclosed as exc:
        note('REFUSAL', f"excise tax REFUSED: {exc}. The driver did not opt in to a statutory "
                        "estimate, so no number is produced. This is the default and it is "
                        "correct: no company in this study has been found disclosing one.")
        print(f"  REFUSED: {exc}")

    # The round trip is already inside report() above, and printing it twice
    # would invite a reader to treat two copies of one measure as two measures.

    # -------------------------------------------------------------- closing
    for n in study.notes:
        note('TEMPLATE NOTE', n)
    print("\n" + "=" * 100)
    print("REFUSALS, FALLBACKS AND SUPPRESSIONS")
    print("=" * 100)
    if not REF:
        print("  NONE. On an unfamiliar company that is a reason for suspicion, not comfort.")
    for kind, text in REF:
        print(f"  [{kind}] {text}")
    print("=" * 100)
    print(f"{len(REF)} guard message(s). A refusal is a pass.")

    if csv_out:
        study.to_csv(csv_out)
        print(f"wrote {csv_out}")
    return study, EE


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--config')
    p.add_argument('--ticker'); p.add_argument('--cik')
    p.add_argument('--fy-end-month', type=int)
    p.add_argument('--first-year', type=int); p.add_argument('--last-year', type=int)
    p.add_argument('--coe', type=float)
    p.add_argument('--prices', help='CSV of monthly closes; omit to fetch')
    p.add_argument('--eodhd-token')
    p.add_argument('--split-year', type=int)
    p.add_argument('--deflator', default='../AAPL_restated.csv')
    p.add_argument('--raw'); p.add_argument('--fetch', action='store_true')
    p.add_argument('--probe', action='store_true')
    p.add_argument('--traded-range')
    p.add_argument('--csv-out')
    a = p.parse_args(argv)

    if a.probe:
        return probe(a.cik.zfill(10))
    if a.config:
        cfg = StudyConfig.from_json(a.config)
    else:
        for req in ('ticker', 'cik', 'fy_end_month', 'first_year', 'last_year',
                    'coe'):
            if getattr(a, req) is None:
                raise SystemExit(f"--{req.replace('_', '-')} is required without --config")
        cfg = StudyConfig(ticker=a.ticker, cik=a.cik, fy_end_month=a.fy_end_month,
                          first_year=a.first_year, last_year=a.last_year,
                          coe_longrun=a.coe, prices=a.prices, deflator=a.deflator,
                          split_year=a.split_year, traded_range=a.traded_range,
                          eodhd_token=a.eodhd_token)
    raw_path = a.raw or f"{cfg.ticker.lower()}_sec_raw.json"
    run(cfg, raw_path, fetch=a.fetch, csv_out=a.csv_out)


if __name__ == '__main__':
    main()
