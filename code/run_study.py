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
SEC_KEYS = list(TAGS)


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
    raw['__absent__'] = absent
    with open(path, 'w') as f:
        json.dump(raw, f)
    return raw


def build_financials(raw, expected_years):
    """The statement lines, in millions, with every alternate merged.

    A line the company files under none of its known names comes back missing
    and is reported. It is NOT defaulted to zero: a study that silently treats
    an untagged dividend stream as no dividends will close every identity it has
    and be wrong about the company.
    """
    fin, missing = {}, []
    for key, (alts, mode, scale) in FIN_TAGS.items():
        parts = [parse_concept(raw[f'{key}__{i}'])
                 for i in range(len(alts)) if f'{key}__{i}' in raw]
        parts = [p for p in parts if p]
        if not parts:
            missing.append(f'{key} ({" or ".join(alts)})')
            continue
        merged = (parts[0] if len(parts) == 1 else
                  merge_concept_series(parts, mode=mode,
                                       expected_years=expected_years, label=key))
        fin[key] = {y: e['val'] / scale for y, e in merged.items()}
    debt_parts = [fin.pop(k) for k in ('total_debt_nc', 'total_debt_c') if k in fin]
    if debt_parts:
        ys = set().union(*[set(d) for d in debt_parts])
        fin['total_debt'] = {y: sum(d.get(y, 0.0) for d in debt_parts) for y in ys}
    return fin, missing


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
class StudyConfig:
    """Everything that legitimately varies by company, and nothing else."""

    def __init__(self, ticker, cik, fy_end_month, first_year, last_year,
                 coe_longrun, prices, splits=None, deflator='../AAPL_restated.csv',
                 split_year=None, coe_by_year=None, excise_disclosed=None,
                 allow_statutory_excise_estimate=False,
                 withholding_in_repurchase_cash=None, raises=None,
                 plan_shares=None, raise_reconciling_items=None,
                 coe_is_placeholder=True, notes=None, traded_range=None):
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
    fin, missing = build_financials(raw, years)
    for m in missing:
        note('MISSING LINE', f"no element found for {m}; it is NOT treated as zero")
    sec = build_sec(raw)

    # The treasury balance is filed under two names by companies that renamed it
    # partway through (Home Depot and Boeing both did). Merge before use or the
    # permanence label is decided on half a history.
    for base, alt in (('treasury_shares_balance', 'treasury_shares_balance_alt'),
                      ('treasury_value_balance', 'treasury_value_balance_alt')):
        if sec.get(base) and sec.get(alt):
            sec[base] = merge_concept_series([sec[base], sec[alt]], mode='update',
                                             expected_years=years, label=base)

    prices = load_prices(cfg.prices)
    # Intra-period extremes, not the range of period-end closes. Month-end
    # closes alone produce false failures, and - more dangerous - they let a
    # wrong implied price through when it happens to sit between two closes.
    # The validator's limit is real and is worth stating: it CANNOT catch a
    # contaminated numerator whose error is small relative to the traded range,
    # which is how the American Airlines convertible nearly got through.
    tr = None
    if cfg.traded_range:
        tr = {int(r['fiscal_year']): (float(r['intraday_low']), float(r['intraday_high']))
              for r in csv.DictReader(open(cfg.traded_range))}
    else:
        note('WEAKER CHECK', "no intra-period traded range supplied, so implied prices are "
                             "validated against period-end closes only, which is the weaker test")
    defl, extrap = load_deflator(cfg.deflator, cfg.first_year, cfg.last_year)
    if extrap:
        note('DEFLATOR', f"no published index for {extrap}; the nearest published "
                         "year is carried and every real figure in those years "
                         "inherits that approximation")
    coe = cfg.coe_by_year or {y: cfg.coe_longrun for y in range(cfg.first_year - 2,
                                                               cfg.last_year + 2)}
    if cfg.coe_is_placeholder:
        note('COST OF EQUITY',
             f"the {100*cfg.coe_longrun:.2f}% real cost of equity is a PLACEHOLDER, "
             "not an engine-sourced rate for this ticker. It sets the SIGN of the "
             "entry effect, so every figure that uses it is provisional. The "
             "break-even rate below is the honest way to read it.")

    study = BuybackStudy(
        CompanyConfig(ticker=cfg.ticker, cik=cik, fy_end_month=cfg.fy_end_month,
                      splits=cfg.splits, first_year=cfg.first_year,
                      last_year=cfg.last_year, coe_longrun=cfg.coe_longrun),
        fin, sec, prices, defl, coe,
        engine={'coe_longrun': cfg.coe_longrun},
        raises=cfg.raises or [], plan_shares=cfg.plan_shares or {},
        raise_reconciling_items=cfg.raise_reconciling_items or {},
        withholding_in_repurchase_cash=cfg.withholding_in_repurchase_cash or {})
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
    p.add_argument('--coe', type=float); p.add_argument('--prices')
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
                    'coe', 'prices'):
            if getattr(a, req) is None:
                raise SystemExit(f"--{req.replace('_', '-')} is required without --config")
        cfg = StudyConfig(ticker=a.ticker, cik=a.cik, fy_end_month=a.fy_end_month,
                          first_year=a.first_year, last_year=a.last_year,
                          coe_longrun=a.coe, prices=a.prices, deflator=a.deflator,
                          split_year=a.split_year, traded_range=a.traded_range)
    raw_path = a.raw or f"{cfg.ticker.lower()}_sec_raw.json"
    run(cfg, raw_path, fetch=a.fetch, csv_out=a.csv_out)


if __name__ == '__main__':
    main()
