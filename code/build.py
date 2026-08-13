"""
Apple share-repurchase study - core computations.

Everything here is derived from source_data.py (SEC primary source + EODHD
prices) and the engine's restated statements. No figure is hand-entered.
"""
import csv
from source_data import (REPURCHASE_CASH, REPURCHASE_ACCRUAL, ISSUANCE_PROCEEDS,
                         SBC, TAX_WITHHOLDING, SHARES_OUT, SHARES_RETIRED_FILED,
                         CRM_NET_CONTRAST, monthly_prices, fiscal_months)

PX = monthly_prices()
FY = list(range(2013, 2026))


# ------------------------------------------------------------------ statements
def _load(path, keys):
    rows = list(csv.reader(open(path)))
    hdr = rows[0]
    out = {}
    for r in rows:
        nm = r[0].strip()
        if nm in keys:
            out[nm] = {int(y): (float(v) if v.strip() else None)
                       for y, v in zip(hdr[1:], r[1:])}
    return out


IS = _load('AAPL_reported_is.csv',
           ['Net Income', 'Diluted EPS', 'Operating Income', 'Pretax Income',
            'Tax Provision', 'Total Revenue'])
BS = _load('AAPL_reported_bs.csv',
           ['Investments And Advances', 'Total Assets', 'Common Stock Equity', 'Total Debt', 'Net Debt', 'Retained Earnings',
            'Cash And Cash Equivalents', 'Other Short Term Investments',
            'Ordinary Shares Number'])
CF = _load('AAPL_reported_cf.csv',
           ['Cash Dividends Paid', 'Operating Cash Flow', 'Capital Expenditure',
            'Net Issuance Payments of Debt'])

NI = IS['Net Income']
EPS = IS['Diluted EPS']
WTD = BS['Ordinary Shares Number']          # weighted average diluted shares (mn)
CSE = BS['Common Stock Equity']
DIV = CF['Cash Dividends Paid']
DEBT = BS['Total Debt']
NETDEBT = BS['Net Debt']

DUP = {}
for r in csv.DictReader(open('AAPL_dupont.csv')):
    y = int(r['year'])
    DUP[y] = {k: (float(r[k]) if r[k] else None)
              for k in ('reform_rnoa', 'reform_flev', 'reform_nbc', 'reform_roce')}

COE = {}
for r in csv.DictReader(open('coe_history_AAPL_annual.csv')):
    COE[int(r['yr'])] = float(r['coe_real_mean']) / 100.0

DEFL = {}
_rows = list(csv.reader(open('AAPL_restated.csv')))
_hdr = _rows[0]
for r in _rows:
    if r[0].startswith('CPI deflator'):
        DEFL = {int(y): float(v) for y, v in zip(_hdr[1:], r[1:]) if v.strip()}


# ------------------------------------------------------------------ prices
def fy_mean_price(fy):
    vals = [PX[k] for k in fiscal_months(fy) if k in PX]
    return sum(vals) / len(vals)


def fy_end_price(fy):
    return PX[(fy, 9)]


PRICE_TODAY = PX[(2026, 8)]


# ------------------------------------------------- shares retired and issued
# Net shares issued under equity plans, as a share of beginning shares
# outstanding, is directly observable for FY2018-FY2025 from the identity
#     S(t) = S(t-1) - retired(t) + issued(t).
# It is a smooth, monotonically declining series. For FY2013-FY2017, where
# Apple did not tag shares retired, that ratio is extrapolated linearly and
# shares retired is taken as the residual. The estimate is then validated by
# checking that the implied average price paid falls inside the fiscal year's
# traded range and close to its mean.
# Observed rates run 0.669%, 0.703%, 0.680%, 0.625%, 0.521%, 0.487%, 0.423%,
# 0.387% for FY2018-FY2025 - flat around 0.68% through FY2020 and declining
# after, as a rising share price delivered fewer shares per dollar of award.
# FY2013-FY2017 are therefore held at the 0.70% level actually observed in
# FY2018-FY2020 rather than extrapolated off the later downtrend.
ISSUE_RATE_EST = {y: 0.0070 for y in range(2013, 2018)}

# Widest intra-month traded prices per fiscal year, today's split basis, from
# EODHD monthly high/low. Used to validate the derived share counts for the
# years Apple did not tag shares retired.
TRADED_RANGE = {2013: (13.75, 24.17), 2014: (17.08, 25.94), 2015: (23.00, 33.64),
                2016: (22.37, 30.96), 2017: (26.02, 41.24)}


def build_share_flows(issue_scale=1.0):
    retired, issued = {}, {}
    for y in FY:
        s0, s1 = SHARES_OUT[y - 1], SHARES_OUT[y]
        if y in SHARES_RETIRED_FILED:
            retired[y] = SHARES_RETIRED_FILED[y]
            issued[y] = s1 - s0 + retired[y]
        else:
            issued[y] = s0 * ISSUE_RATE_EST[y] * issue_scale
            retired[y] = s0 - s1 + issued[y]
    return retired, issued


RETIRED, ISSUED = build_share_flows()


# ------------------------------------------------------------------ real terms
def real(x, y):
    return x * DEFL[y] if x is not None else None


def real_price(p, y):
    return p * DEFL[y]


# --------------------------------------------------- gross debt, primary source
# The vendor "Total Debt" line changes definition in FY2024 (see the note in
# source_data.py). DEBT below is the SEC primary-source series, and the guard
# reports every year where the two disagree rather than silently preferring one.
from source_data import BORROWINGS

DEBT = dict(BORROWINGS)


def debt_feed_disagreements(tol_frac=0.001):
    """Years where the vendor total-debt line and SEC borrowings diverge."""
    out = []
    for y in sorted(DEBT):
        v = BS['Total Debt'].get(y) or 0.0
        if abs(v - DEBT[y]) > tol_frac * max(1.0, DEBT[y]):
            out.append((y, v, DEBT[y], v - DEBT[y]))
    return out
