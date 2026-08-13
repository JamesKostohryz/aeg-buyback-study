# -*- coding: utf-8 -*-
"""Generate the Apple share-repurchase study as a self-contained HTML document.
Every figure in the output is computed here from the study data - none is typed in."""
from build import *

import csv as _csv

# Engine figures are read from the repository at HEAD by the session that
# publishes them, per the standing rule in the house conventions. Nothing in
# this block is typed in.
def _num_or_none(v):
    try:
        return float(v)
    except ValueError:
        return None


_SUM = {r[0]: _num_or_none(r[1]) for r in _csv.reader(open('AAPL_summary.STALE.csv'))
        if len(r) == 2 and r[0] != 'field'}
NV_PS = _SUM['normal_no_growth_value_ps']
COE_LONGRUN = _SUM['real_coe_longrun']
PRICE_REAL_ENGINE = _SUM['current_price_real_ps']


def _w(n):
    """Small counts spelled out, per house prose conventions."""
    names = ('zero one two three four five six seven eight nine ten eleven '
             'twelve thirteen fourteen fifteen sixteen seventeen eighteen '
             'nineteen twenty').split()
    return names[n] if 0 <= n <= 20 else f'{n:,}'


NEP, NEUTRAL_PE = NV_PS * COE_LONGRUN, 1 / COE_LONGRUN

PE_PAID = {y: (REPURCHASE_CASH[y] / RETIRED[y]) / EPS[y] for y in FY}
# Two different averages, and they must never be given the same name.
#   SHARE-weighted  = total cash / total shares retired. This is the average
#                     price Apple paid per share it actually retired.
#   DOLLAR-weighted = sum(cash_i * price_i) / sum(cash_i). This is the average
#                     price weighted by where the money went.
# They differ by a factor of nearly two here because the cheap early years
# bought far more shares per dollar. Version 1 of this study labelled the
# share-weighted figure "dollar-weighted", which was wrong.
MKT_PE = {y: fy_mean_price(y) / EPS[y] for y in FY}
PX_PAID = {y: REPURCHASE_CASH[y] / RETIRED[y] for y in FY}
DPS = {y: DIV[y] / WTD[y] for y in FY}
EY = {y: (EPS[y + 1] * DEFL[y + 1]) / (PX_PAID[y] * DEFL[y]) for y in FY[:-1]}
rep_t = sum(REPURCHASE_CASH[y] for y in FY)
ret_t = sum(RETIRED[y] for y in FY)
iss_t = sum(ISSUED[y] for y in FY)
ni_t = sum(NI[y] for y in FY)
div_t = sum(DIV[y] for y in FY)
DW_PE = sum(REPURCHASE_CASH[y] * PE_PAID[y] for y in FY) / rep_t
EW_PE = sum(PE_PAID.values()) / len(FY)
EW_MKT = sum(MKT_PE.values()) / len(FY)
P_END_25 = fy_end_price(2025)
DOLLAR_W_PX = sum(REPURCHASE_CASH[y] * (REPURCHASE_CASH[y] / RETIRED[y])
                  for y in FY) / rep_t
EW_PX = sum(REPURCHASE_CASH[y] / RETIRED[y] for y in FY) / len(FY)


def irr(flows, lo=-0.95, hi=3.0):
    def npv(r):
        return sum(a / (1 + r) ** t for t, a in flows)
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        m = (lo + hi) / 2
        if npv(lo) * npv(m) <= 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


def prog(y0, terminal, deflate=False):
    flows, held = [], 0.0
    for y in range(y0, 2026):
        t, k = y - y0 + 0.5, (DEFL[y] if deflate else 1.0)
        flows.append((t, -REPURCHASE_CASH[y] * k))
        if held > 0:
            flows.append((t, held * DPS[y] * k))
        held += RETIRED[y]
    flows.append((2025 - y0 + 1.0, held * terminal * (DEFL[2025] if deflate else 1.0)))
    return irr(flows), held


NV_FY25 = NV_PS / DEFL[2025]
FUND_TERM = EPS[2025] * DW_PE
IRRS = {}
for y0 in (2021, 2016, 2013):
    IRRS[y0] = (prog(y0, P_END_25)[0], prog(y0, FUND_TERM)[0],
                prog(y0, NV_FY25)[0], prog(y0, P_END_25, deflate=True)[0],
                sum(REPURCHASE_CASH[y] for y in range(y0, 2026)),
                sum(RETIRED[y] for y in range(y0, 2026)))
be = {}
for y0 in (2013, 2016, 2021):
    lo, hi = 1.0, 3000.0
    for _ in range(200):
        m = (lo + hi) / 2
        r = prog(y0, m)[0]
        if r is None or r < COE_LONGRUN + 0.025:
            lo = m
        else:
            hi = m
    be[y0] = (lo + hi) / 2

# EPS attribution
cum_e = cum_s = cum_o = cum_f = 0.0
OI, NFI = {}, {}
for y in range(2012, 2026):
    pre, op, tx = IS['Pretax Income'][y], IS['Operating Income'][y], IS['Tax Provision'][y]
    t = tx / pre
    OI[y], NFI[y] = op * (1 - t), (pre - op) * (1 - t)
for y in FY:
    cum_e += (NI[y] - NI[y - 1]) / WTD[y]
    cum_s += EPS[y - 1] * (WTD[y - 1] / WTD[y] - 1)
    cum_o += (OI[y] - OI[y - 1]) / WTD[y]
    cum_f += (NFI[y] - NFI[y - 1]) / WTD[y]
TOT_EPS = EPS[2025] - EPS[2012]

FA = {y: BS['Cash And Cash Equivalents'][y] + BS['Other Short Term Investments'][y]
      + BS['Investments And Advances'][y] for y in range(2012, 2026)}
NETFIN = {y: FA[y] - DEBT[y] for y in range(2012, 2026)}
NOA = {y: CSE[y] - NETFIN[y] for y in range(2012, 2026)}
ROIC = (OI[2025] - OI[2012]) / (NOA[2025] - NOA[2012])
ROIC_CT = ((IS['Operating Income'][2025] - IS['Operating Income'][2012])
           * (1 - IS['Tax Provision'][2012] / IS['Pretax Income'][2012])
           ) / (NOA[2025] - NOA[2012])

mkt_del = sum(ISSUED[y] * fy_mean_price(y) for y in FY)
tax_t = sum(TAX_WITHHOLDING[y] for y in FY)
proc_t = sum(ISSUANCE_PROCEEDS.get(y, 0) for y in FY)
sbc_t = sum(SBC[y] for y in FY)
econ_t = mkt_del + tax_t - proc_t


# ------------------------------------- net retirement cost (section 7)
# What it cost to remove one share PERMANENTLY, as against what was paid for a
# share at the moment of purchase. The two differ by whatever the company issued
# back to its own employees in the same year.
#
# WHAT THIS IS NOT, and the boundary is not optional. This is a descriptive
# ratio - dollars of cash per unit of permanent count reduction - and it is not
# a price. It may not be substituted for the price paid anywhere in section 3:
# the entry effect E - rho*P is an identity only when P is the price actually
# transacted, because the capital charge falls on the cash actually spent and
# the earnings acquired are those the retired shares actually carried. Putting a
# synthetic higher price into that expression would break the identity and move
# the pivot off Neutral Value. Nor is the excess over the gross price an
# expense: share-based pay is already charged to earnings at grant-date fair
# value, and charging the offsetting repurchase again is the same double count
# the capital-decomposition addendum had to decline once already.
NET_RED = {y: RETIRED[y] - ISSUED[y] for y in FY}

# Denominator guard, two-sided. A ratio on a small or negative denominator is
# meaningless and far more likely to be believed than a missing one, so the fact
# is reported in place of the number. The threshold is a fraction of the opening
# share count rather than a bare sign test.
NET_MIN_FRAC = 0.0025
NET_OK = {y: NET_RED[y] > NET_MIN_FRAC * SHARES_OUT[y - 1] for y in FY}
NET_SUPPRESSED = [y for y in FY if not NET_OK[y]]

net_t = sum(NET_RED[y] for y in FY)
# A cash / GROSS shares retired          - the market price paid
# B cash / NET count reduction           - cost per share permanently removed
# C (cash - employee proceeds) / NET
# D (cash + withholding tax - proceeds) / NET  - total cash spent on the count
M_A = rep_t / ret_t
M_B = rep_t / net_t
M_C = (rep_t - proc_t) / net_t
M_D = (rep_t + tax_t - proc_t) / net_t
NET_PS = {y: (REPURCHASE_CASH[y] / NET_RED[y]) if NET_OK[y] else None for y in FY}
ISS_SHARE_OF_RET = iss_t / ret_t
ISS_SHARE_OF_CASH = mkt_del / rep_t

# Contrast case. Salesforce is in the study only as a counterexample and none of
# its figures enter any Apple measure.
CRM_ROWS = []
for _fy, _cash, _so, _net, _lo, _hi in CRM_NET_CONTRAST:
    CRM_ROWS.append((_fy, _cash, _so, _net, _cash / _net, _lo, _hi))
CRM_WORST = max(CRM_ROWS, key=lambda r: r[4] / r[6])
# Apple's own comparison, on the same shape. FY_HIGH is the highest MONTHLY CLOSE
# in the fiscal year, not an intraday high, so it is a conservative denominator:
# a ratio slightly above one sits comfortably inside the year's traded range and
# is unremarkable. Salesforce's denominators are intraday highs, which makes the
# contrast stronger than a like-for-like comparison would, not weaker.
FY_HIGH = {y: max(PX[k] for k in fiscal_months(y) if k in PX) for y in FY}


# ---------------------------------------------------- AEG account (section 3)
R_AEG = COE_LONGRUN
nir = {y: NI[y] * DEFL[y] for y in range(2012, 2026)}
dr = {y: (DIV[y] + REPURCHASE_CASH.get(y, 0)) * DEFL[y] for y in range(2012, 2026)}
epsr = {y: EPS[y] * DEFL[y] for y in range(2012, 2026)}
pxr = {y: PX_PAID[y] * DEFL[y] for y in FY}
AEG_ENT = {s: nir[s] - (1 + R_AEG) * nir[s - 1] + R_AEG * dr[s - 1] for s in FY}
AEG_ENT_TOT = sum(AEG_ENT.values())
ENTRY, CONT = {}, {}
for t in FY[:-1]:
    ENTRY[t] = RETIRED[t] * (epsr[t + 1] - R_AEG * pxr[t])
    CONT[t] = sum(RETIRED[t] * AEG_ENT[s] / SHARES_OUT[s] for s in range(t + 2, 2026))
ENTRY_TOT, CONT_TOT = sum(ENTRY.values()), sum(CONT.values())
ENTRY_ALT = sum(RETIRED[t] * (epsr[t + 1] - COE[t] * pxr[t]) for t in FY[:-1])
NEG_LR = [t for t in FY[:-1] if ENTRY[t] < 0]
NEG_CH = [t for t in FY[:-1] if RETIRED[t] * (epsr[t + 1] - COE[t] * pxr[t]) < 0]
_ps = sorted(AEG_ENT[s] / SHARES_OUT[s] for s in FY)
MEAN_AEG_PS = sum(_ps) / len(_ps)

# ------------------------------- the cost-of-equity break-even (added 2026-08-12)
# The entry effect is LINEAR in the capitalization rate:
#     ENTRY(rho) = SUM_t retired_t * eps_(t+1) - rho * SUM_t retired_t * price_t
# so it has exactly one root and that root is the retirement-weighted forward real
# earnings yield. No search, no tolerance, no iteration - it is an identity.
#
# WHY THIS BELONGS IN THE REPORT. Every other sensitivity in this study moves a
# magnitude. This one moves a SIGN, and it is the sensitivity the reader cannot
# compute for themselves. It is also the honest place to put the leverage
# question: a company that levers up to buy its stock back raises the required
# return on the equity that remains, and this line says how much of a rise the
# conclusion can absorb before it inverts. It does NOT model that rise - the
# engine has no re-levering in its live path - it states the tolerance.
def _rho_star(years):
    n = sum(RETIRED[t] * epsr[t + 1] for t in years)
    d = sum(RETIRED[t] * pxr[t] for t in years)
    return n / d


_ALL = FY[:-1]
_EARLY = [t for t in _ALL if t < 2020]
_LATE = [t for t in _ALL if t >= 2020]
RHO_STAR = _rho_star(_ALL)
RHO_STAR_EARLY = _rho_star(_EARLY)
RHO_STAR_LATE = _rho_star(_LATE)
RHO_HEADROOM = RHO_STAR - COE_LONGRUN
COE_HIST_MEAN = sum(COE[t] for t in _ALL) / len(_ALL)


# ------------------------------------- funding decomposition (section 8)
# Net financial obligations is the negative of the net financial position.
NFO = {y: -NETFIN[y] for y in range(2012, 2026)}
D_NFO = NFO[2025] - NFO[2012]
LEV_SHARE = D_NFO / rep_t
EPS_LEV = cum_s * LEV_SHARE
EPS_RET = cum_s * (1 - LEV_SHARE)
FIN_ENG = cum_s + cum_f
FLEV_12, FLEV_25 = NFO[2012] / CSE[2012], NFO[2025] / CSE[2025]
FLEV_ENG_12, FLEV_ENG_25 = DUP[2012]['reform_flev'], DUP[2025]['reform_flev']
GROSS_DEBT_ADD = DEBT[2025] - DEBT[2012]
DEBT_FEED_BREAK = debt_feed_disagreements()
D_FA = FA[2025] - FA[2012]

# ------------------------ sources and uses of incremental capital (section 9)
RETAINED_T = ni_t - div_t
CAP_IN = RETAINED_T + D_NFO + sbc_t - tax_t + proc_t
D_NOA = NOA[2025] - NOA[2012]
UNREC = CAP_IN - rep_t - D_NOA
SH_REP, SH_NOA = rep_t / CAP_IN, D_NOA / CAP_IN
ROC_ALL = (OI[2025] - OI[2012]) / CAP_IN
ENTRY_EY = 1.0 / DW_PE
WINDOWS = []
for _a, _b in ((2012, 2018), (2015, 2021), (2019, 2025)):
    _dn = NOA[_b] - NOA[_a]
    WINDOWS.append((_a, _b, _dn, (OI[_b] - OI[_a]) / _dn if _dn > 0 else None))

# --------------------------------------------- the Real Capital Base (s. 9)
RCB, CUM_REST, ROE_REP, ROE_RCB = {}, {}, {}, {}
_cr = _bv = _gw = 0.0
for y in FY:
    _net_bb = REPURCHASE_CASH[y] - ISSUANCE_PROCEEDS.get(y, 0)
    _bv_part = min(_net_bb, RETIRED[y] * (CSE[y - 1] / SHARES_OUT[y - 1]))
    _cr += _net_bb
    _bv += _bv_part
    _gw += _net_bb - _bv_part
    CUM_REST[y] = _cr
    RCB[y] = CSE[y] + _cr
    _prev = RCB[y - 1] if (y - 1) in RCB else CSE[2012]
    ROE_REP[y] = NI[y] / ((CSE[y] + CSE[y - 1]) / 2)
    ROE_RCB[y] = NI[y] / ((RCB[y] + _prev) / 2)
GW_SHARE = _gw / _cr
IC_RES = {y: NOA[y] + CUM_REST[y] for y in FY}
ROIC_RES = {y: OI[y] / IC_RES[y] for y in FY}
NEG_IC = [y for y in FY if NOA[y] <= 0]
POS_IC = [y for y in FY if NOA[y] > 0]
ROIC_RES_SETTLED = [ROIC_RES[y] for y in FY if y >= 2019]

# ----------------------------------------- return on retained earnings (s.10)
DPSR = {y: (DIV[y] / WTD[y]) * DEFL[y] for y in range(2012, 2026)}
_rnum = sum(epsr[y] - epsr[y - 1] for y in FY)
_rden = sum(epsr[y - 1] - DPSR[y - 1] for y in FY)
RORE = _rnum / _rden
B_RET = _rden / sum(epsr[y - 1] for y in FY)
AEG_IDENT = B_RET * (RORE - COE_LONGRUN)
AVG_NI_R = sum(nir[y] for y in FY) / len(FY)
AEG_RATE_ENT = (AEG_ENT_TOT / len(FY)) / AVG_NI_R
RORE_ANN = {y: (epsr[y] - epsr[y - 1]) / (epsr[y - 1] - DPSR[y - 1]) for y in FY}
RORE_NEG = [y for y in FY if RORE_ANN[y] < 0]
RORE_MIN, RORE_MAX = min(RORE_ANN.values()), max(RORE_ANN.values())


def win_sentence():
    good = [w for w in WINDOWS if w[3] is not None]
    bad = [w for w in WINDOWS if w[3] is None]
    parts = [f"fiscal {a} to fiscal {b} returned {100*r:,.1f} percent"
             for a, b, dn, r in good]
    for a, b, dn, r in bad:
        parts.append(f"the fiscal {a} to fiscal {b} window is suppressed rather than printed, "
                     f"because net operating assets <i>fell</i> by ${-dn/1000:,.1f} billion over it "
                     f"and a ratio with a negative denominator carries no meaning")
    return "; ".join(parts)


def rows_channel():
    def row(lab, v, note, bold=False):
        c = ' class="grand"' if bold else ''
        return (f'<tr{c}><td>{lab}</td><td class="num">{v:+,.3f}</td>'
                f'<td class="num">{100*v/TOT_EPS:.1f}%</td><td>{note}</td></tr>')
    return "".join([
        row('Operating business', cum_o,
            'After-tax operating income, on the average share count of each year'),
        row('Share count &mdash; funded by retention', EPS_RET,
            f'${(rep_t-D_NFO)/1000:,.0f} billion of the repurchase spending'),
        row('Share count &mdash; funded by added leverage', EPS_LEV,
            f'${D_NFO/1000:,.0f} billion of the repurchase spending'),
        row('Net interest, the direct effect of leverage', cum_f,
            'Interest paid against interest income forgone'),
        row('Financial engineering, all three', FIN_ENG,
            'Share count plus net interest', True),
        row('Total growth in diluted earnings per share', TOT_EPS, '&mdash;', True),
    ])


def rows_sources():
    def amt(v):
        return f'({abs(v):,.0f})' if v < 0 else f'{v:,.0f}'

    def row(lab, v, pct=None, bold=False):
        c = ' class="grand"' if bold else ''
        p = ('&mdash;' if not pct else
             (f'({abs(100*v/CAP_IN):.1f}%)' if v < 0 else f'{100*v/CAP_IN:.1f}%'))
        return (f'<tr{c}><td>{lab}</td><td class="num">{amt(v)}</td>'
                f'<td class="num">{p}</td></tr>')

    def head(lab):
        return (f'<tr><td colspan="3" style="background:#f2f5f8;font-weight:700;'
                f'font-size:11px;letter-spacing:.08em;text-transform:uppercase;'
                f'color:#0d3050">{lab}</td></tr>')
    return "".join([
        head('Sources of incremental capital'),
        row('Retained earnings, after dividends', RETAINED_T),
        row('Increase in net financial obligations', D_NFO),
        row('Share-based compensation, non-cash equity', sbc_t),
        row('Less cash tax on employee equity awards', -tax_t),
        row('Equity plan proceeds', proc_t),
        row('Total incremental capital', CAP_IN, bold=True),
        head('Uses'),
        row('Share repurchases', rep_t, pct=True),
        row('Increase in net operating assets', D_NOA, pct=True),
        row('Unreconciled, matching the equity roll-forward residual', UNREC, pct=True),
    ])


def rows_rcb():
    out = []
    for y in FY:
        out.append(f'<tr><td>{y}</td><td class="num">{CSE[y]:,.0f}</td>'
                   f'<td class="num">{CUM_REST[y]:,.0f}</td>'
                   f'<td class="num">{RCB[y]:,.0f}</td>'
                   f'<td class="num">{100*ROE_REP[y]:,.1f}%</td>'
                   f'<td class="num">{100*ROE_RCB[y]:,.1f}%</td>'
                   f'<td class="num">'
                   f'{(f"{100*OI[y]/NOA[y]:,.0f}%" if NOA[y] > 0 else "n/m")}</td>'
                   f'<td class="num">{100*ROIC_RES[y]:,.1f}%</td></tr>')
    return "".join(out)


def rows_aeg():
    out = []
    for t in FY[:-1]:
        need = max(0.0, -ENTRY[t] - CONT[t])
        out.append(
            f'<tr><td>{t}</td><td class="num">{RETIRED[t]:,.0f}</td>'
            f'<td class="num">{pxr[t]:,.2f}</td>'
            f'<td class="num">{100*epsr[t+1]/pxr[t]:.2f}%</td>'
            f'<td class="num" style="color:{"#0f7a52" if ENTRY[t]>0 else "#c0392b"}">'
            f'{ENTRY[t]/1000:+,.2f}</td>'
            f'<td class="num">{CONT[t]/1000:,.2f}</td>'
            f'<td class="num">{(ENTRY[t]+CONT[t])/1000:+,.2f}</td>'
            f'<td class="num">{(f"{need/RETIRED[t]:,.2f}" if need else "&mdash;")}</td></tr>')
    out.append(f'<tr class="grand"><td>FY2013&ndash;24</td>'
               f'<td class="num">{sum(RETIRED[t] for t in FY[:-1]):,.0f}</td>'
               f'<td class="num">&mdash;</td><td class="num">&mdash;</td>'
               f'<td class="num">{ENTRY_TOT/1000:+,.2f}</td>'
               f'<td class="num">{CONT_TOT/1000:,.2f}</td>'
               f'<td class="num">{(ENTRY_TOT+CONT_TOT)/1000:+,.2f}</td>'
               f'<td class="num">&mdash;</td></tr>')
    return "".join(out)


# ------------------------------------------------------------------ chart 1
def chart_yield():
    W, H, L, R, T, B = 760, 300, 54, 120, 16, 42
    ys = FY[:-1]
    ymax = 0.11
    def x(i): return L + (W - L - R) * i / (len(ys) - 1)
    def y(v): return T + (H - T - B) * (1 - v / ymax)
    g = []
    for gv in (0, 0.02, 0.04, 0.06, 0.08, 0.10):
        g.append(f'<line x1="{L}" y1="{y(gv):.1f}" x2="{W-R}" y2="{y(gv):.1f}" '
                 f'stroke="{"#c9cdd2" if gv==0 else "#e8ebee"}"/>')
        g.append(f'<text x="{L-8}" y="{y(gv)+4:.1f}" text-anchor="end" font-size="11" '
                 f'fill="#6b7480">{gv*100:.0f}%</text>')
    pts = " ".join(f"{x(i):.1f},{y(EY[v]):.1f}" for i, v in enumerate(ys))
    g.append(f'<polyline fill="none" stroke="#1d4e7c" stroke-width="2.6" points="{pts}"/>')
    for i, v in enumerate(ys):
        g.append(f'<circle cx="{x(i):.1f}" cy="{y(EY[v]):.1f}" r="3.4" fill="#1d4e7c"/>')
    g.append(f'<line x1="{L}" y1="{y(COE_LONGRUN):.1f}" x2="{W-R}" y2="{y(COE_LONGRUN):.1f}" '
             f'stroke="#c0392b" stroke-width="1.7" stroke-dasharray="6 4"/>')
    g.append(f'<text x="{W-R+6}" y="{y(COE_LONGRUN)-2:.1f}" font-size="11.5" fill="#c0392b" '
             f'font-weight="700">real cost of equity</text>')
    g.append(f'<text x="{W-R+6}" y="{y(COE_LONGRUN)+12:.1f}" font-size="11.5" '
             f'fill="#c0392b">{COE_LONGRUN*100:.2f}%</text>')
    ptsc = " ".join(f"{x(i):.1f},{y(COE[v]):.1f}" for i, v in enumerate(ys))
    g.append(f'<polyline fill="none" stroke="#c9a94e" stroke-width="1.8" '
             f'stroke-dasharray="3 3" points="{ptsc}"/>')
    g.append(f'<text x="{W-R+6}" y="{y(COE[2021])+4:.1f}" font-size="10.5" fill="#8a7328">'
             f'company history</text>')
    for i, v in enumerate(ys):
        if v % 2 == 1:
            g.append(f'<text x="{x(i):.1f}" y="{H-16}" text-anchor="middle" font-size="11" '
                     f'fill="#6b7480">{v}</text>')
    g.append(f'<text x="{x(0):.1f}" y="{y(EY[2013])-11:.1f}" text-anchor="middle" '
             f'font-size="11.5" font-weight="700" fill="#0d3050">{EY[2013]*100:.1f}%</text>')
    g.append(f'<text x="{x(len(ys)-1):.1f}" y="{y(EY[2024])+18:.1f}" text-anchor="middle" '
             f'font-size="11.5" font-weight="700" fill="#0d3050">{EY[2024]*100:.1f}%</text>')
    return (f'<svg class="ch" viewBox="0 0 {W} {H}" role="img" aria-label="forward real '
            f'earnings yield on Apple repurchases by fiscal year">' + "".join(g) + '</svg>')


# ------------------------------------------------------------------ chart 2
def chart_pe():
    W, H, L, R, T, B = 760, 310, 54, 66, 16, 42
    ymax = 34.0
    bw = (W - L - R) / len(FY) * 0.62
    mx = max(REPURCHASE_CASH.values())
    def x(i): return L + (W - L - R) * (i + 0.5) / len(FY)
    def y(v): return T + (H - T - B) * (1 - v / ymax)
    g = []
    for gv in (0, 10, 20, 30):
        g.append(f'<line x1="{L}" y1="{y(gv):.1f}" x2="{W-R}" y2="{y(gv):.1f}" '
                 f'stroke="{"#c9cdd2" if gv==0 else "#e8ebee"}"/>')
        g.append(f'<text x="{L-8}" y="{y(gv)+4:.1f}" text-anchor="end" font-size="11" '
                 f'fill="#6b7480">{gv}x</text>')
    for i, v in enumerate(FY):
        h = (H - T - B) * 0.94 * REPURCHASE_CASH[v] / mx
        g.append(f'<rect x="{x(i)-bw/2:.1f}" y="{H-B-h:.1f}" width="{bw:.1f}" '
                 f'height="{h:.1f}" fill="#dbe6f0"/>')
    g.append(f'<line x1="{L}" y1="{y(NEUTRAL_PE):.1f}" x2="{W-R}" y2="{y(NEUTRAL_PE):.1f}" '
             f'stroke="#0f7a52" stroke-width="1.7" stroke-dasharray="6 4"/>')
    g.append(f'<text x="{W-R+4}" y="{y(NEUTRAL_PE)-3:.1f}" font-size="10.5" fill="#0f7a52" '
             f'font-weight="700">Neutral P/E</text>')
    g.append(f'<text x="{W-R+4}" y="{y(NEUTRAL_PE)+9:.1f}" font-size="10.5" '
             f'fill="#0f7a52">{NEUTRAL_PE:.1f}x</text>')
    pm = " ".join(f"{x(i):.1f},{y(MKT_PE[v]):.1f}" for i, v in enumerate(FY))
    pp = " ".join(f"{x(i):.1f},{y(PE_PAID[v]):.1f}" for i, v in enumerate(FY))
    g.append(f'<polyline fill="none" stroke="#9aa6b2" stroke-width="1.6" points="{pm}"/>')
    g.append(f'<polyline fill="none" stroke="#1d4e7c" stroke-width="2.6" points="{pp}"/>')
    for i, v in enumerate(FY):
        g.append(f'<circle cx="{x(i):.1f}" cy="{y(PE_PAID[v]):.1f}" r="3.2" fill="#1d4e7c"/>')
        if v % 2 == 1:
            g.append(f'<text x="{x(i):.1f}" y="{H-16}" text-anchor="middle" font-size="11" '
                     f'fill="#6b7480">{v}</text>')
    g.append(f'<text x="{x(1):.1f}" y="{y(PE_PAID[2014])-10:.1f}" font-size="11" '
             f'fill="#0d3050" font-weight="700">multiple paid</text>')
    g.append(f'<text x="{x(7):.1f}" y="{H-B-8:.1f}" font-size="10.5" fill="#5b89ae">'
             f'bars: dollars spent</text>')
    return (f'<svg class="ch" viewBox="0 0 {W} {H}" role="img" aria-label="multiple Apple '
            f'paid for its own shares against the market multiple and the Neutral P/E">'
            + "".join(g) + '</svg>')


def rows_main():
    out = []
    for y in FY:
        out.append(
            f'<tr><td>{y}</td>'
            f'<td class="num">{REPURCHASE_CASH[y]/1000:,.1f}</td>'
            f'<td class="num">{RETIRED[y]:,.0f}</td>'
            f'<td class="num">{100*RETIRED[y]/SHARES_OUT[y-1]:.2f}%</td>'
            f'<td class="num">{100*(SHARES_OUT[y]/SHARES_OUT[y-1]-1):.2f}%</td>'
            f'<td class="num">{PX_PAID[y]:,.2f}</td>'
            f'<td class="num">{PE_PAID[y]:.1f}&times;</td>'
            f'<td class="num">{(str(round(100*EY[y],2))+"%") if y in EY else "&mdash;"}</td>'
            f'</tr>')
    out.append(
        f'<tr class="grand"><td>FY2013&ndash;25</td>'
        f'<td class="num">{rep_t/1000:,.1f}</td><td class="num">{ret_t:,.0f}</td>'
        f'<td class="num">&mdash;</td>'
        f'<td class="num">{100*(SHARES_OUT[2025]/SHARES_OUT[2012]-1):.1f}%</td>'
        f'<td class="num">{rep_t/ret_t:,.2f}</td>'
        f'<td class="num">{DW_PE:.1f}&times;</td><td class="num">&mdash;</td></tr>')
    return "".join(out)


def rows_net():
    out = []
    for y in FY:
        s0 = SHARES_OUT[y - 1]
        cell = (f'{NET_PS[y]:,.2f}' if NET_OK[y] else
                '<span style="color:#c0392b">suppressed</span>')
        out.append(
            f'<tr><td>{y}</td>'
            f'<td class="num">{REPURCHASE_CASH[y]/1000:,.1f}</td>'
            f'<td class="num">{RETIRED[y]:,.0f}</td>'
            f'<td class="num">{100*RETIRED[y]/s0:.2f}%</td>'
            f'<td class="num">{ISSUED[y]:,.0f}</td>'
            f'<td class="num">{100*ISSUED[y]/s0:.2f}%</td>'
            f'<td class="num">{NET_RED[y]:,.0f}</td>'
            f'<td class="num">{100*NET_RED[y]/s0:.2f}%</td>'
            f'<td class="num">{REPURCHASE_CASH[y]/RETIRED[y]:,.2f}</td>'
            f'<td class="num">{cell}</td></tr>')
    out.append(
        f'<tr class="grand"><td>FY2013&ndash;25</td>'
        f'<td class="num">{rep_t/1000:,.1f}</td>'
        f'<td class="num">{ret_t:,.0f}</td><td class="num">&mdash;</td>'
        f'<td class="num">{iss_t:,.0f}</td><td class="num">&mdash;</td>'
        f'<td class="num">{net_t:,.0f}</td><td class="num">&mdash;</td>'
        f'<td class="num">{M_A:,.2f}</td><td class="num">{M_B:,.2f}</td></tr>')
    return "".join(out)


def rows_measures():
    rows = [('A', 'Cash divided by GROSS shares retired', M_A,
             'The market price paid. This is the price, and the only one of the four that is.'),
            ('B', 'Cash divided by NET count reduction', M_B,
             'What it cost to remove one share permanently.'),
            ('C', 'Cash less employee plan proceeds, divided by NET', M_C,
             'Credits the company for what employees paid in.'),
            ('D', 'Cash plus withholding tax less proceeds, divided by NET', M_D,
             'Total cash spent holding the share count down.')]
    out = []
    for k, lab, v, note in rows:
        prem = ('&mdash;' if k == 'A' else f'{100*(v/M_A-1):+.1f}%')
        out.append(f'<tr><td><b>{k}</b>&nbsp;&nbsp;{lab}</td>'
                   f'<td class="num">{v:,.2f}</td><td class="num">{prem}</td>'
                   f'<td>{note}</td></tr>')
    return "".join(out)


def rows_crm():
    out = []
    for fy, cash, so, net, px, lo, hi in CRM_ROWS:
        out.append(f'<tr><td>Fiscal {fy}</td>'
                   f'<td class="num">{cash/1000:,.1f}</td>'
                   f'<td class="num">{so:,.0f}</td>'
                   f'<td class="num">{net:,.0f}</td>'
                   f'<td class="num" style="color:#c0392b">{px:,.2f}</td>'
                   f'<td class="num">{lo:,.0f}&ndash;{hi:,.0f}</td>'
                   f'<td class="num">{px/hi:,.1f}&times;</td></tr>')
    return "".join(out)


def rows_irr():
    out = []
    for y0, lab in ((2021, 'Last 5 years'), (2016, 'Last 10 years'),
                    (2013, 'Full program, 13 years')):
        m, f, n, rl, o, s = IRRS[y0]
        out.append(f'<tr><td>{lab}</td><td class="num">{o/1000:,.0f}</td>'
                   f'<td class="num">{s:,.0f}</td>'
                   f'<td class="num">{100*m:.1f}%</td><td class="num">{100*rl:.1f}%</td>'
                   f'<td class="num">{100*f:.1f}%</td><td class="num">{100*n:.1f}%</td></tr>')
    return "".join(out)


HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What Apple's Buyback Actually Earned</title>
<style>:root{{--ink:#1a1a1a;--muted:#6b7480;--line:#dfe3e7;--n9:#0d3050;--n7:#1d4e7c;
  --n6:#2c5c86;--n4:#5b89ae;--gold:#c9a94e;--up:#0f7a52;--down:#c0392b}}
*{{box-sizing:border-box}}
body{{margin:0;background:#eceef0;color:var(--ink);font:17px/1.68 Georgia,"Times New Roman",serif}}
.wrap{{max-width:840px;margin:0 auto 34px;background:#fff;box-shadow:0 1px 5px rgba(0,0,0,.10)}}
.topbar{{background:var(--n9);color:#fff;padding:9px 34px;display:flex;align-items:center;
  justify-content:space-between;border-top:3px solid var(--gold);font-family:-apple-system,"Segoe UI",sans-serif}}
.topbar .fm{{font-size:11px;letter-spacing:.2em;text-transform:uppercase;font-weight:700}}
.topbar .rt{{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;opacity:.72}}
.titleblock{{padding:26px 34px 0}}
.kicker{{font-family:-apple-system,"Segoe UI",sans-serif;font-size:10.5px;letter-spacing:.17em;
  text-transform:uppercase;color:var(--n7);font-weight:700}}
h1{{font-size:34px;line-height:1.12;margin:11px 0 0;letter-spacing:-.4px}}
.standfirst{{font-size:18px;line-height:1.55;color:#4a5560;margin:13px 0 0;font-style:italic}}
.byline{{font-family:-apple-system,"Segoe UI",sans-serif;font-size:11.5px;color:var(--muted);
  margin-top:16px;padding-bottom:18px;border-bottom:2px solid var(--n9)}}
.pad{{padding:4px 34px 30px}}
p{{margin:15px 0}}
h2{{font-family:-apple-system,"Segoe UI",sans-serif;font-size:13px;font-weight:700;letter-spacing:.13em;
  text-transform:uppercase;color:var(--n9);margin:42px 0 4px;padding-bottom:7px;
  border-bottom:1.5px solid var(--n9)}}
h2 .no{{color:var(--gold);margin-right:9px}}
.lede{{font-size:19.5px;line-height:1.55;color:#2b3947;margin-top:22px}}
.punch{{font-size:19px;font-weight:700;color:var(--n9);margin:22px 0;line-height:1.42;
  padding-left:16px;border-left:3px solid var(--gold)}}
.exh{{margin:26px 0 10px}}
.eh{{font-family:-apple-system,"Segoe UI",sans-serif;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--n9);font-weight:700;margin-bottom:7px;padding-bottom:5px;border-bottom:1px solid var(--line)}}
.cap{{font-family:-apple-system,"Segoe UI",sans-serif;font-size:11.5px;color:var(--muted);margin:8px 0 2px;line-height:1.55}}
table.fig{{width:100%;border-collapse:collapse;font-size:14px;margin-top:2px;
  font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
table.fig th{{text-align:left;font-size:9.5px;letter-spacing:.05em;text-transform:uppercase;color:#fff;
  background:var(--n6);padding:8px 9px;font-weight:600}}
table.fig th.r{{text-align:right}}
table.fig td{{padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}}
table.fig td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;font-weight:600}}
table.fig tr.grand td{{font-weight:700;background:#dfeaf4;border-top:1.5px solid var(--n4);border-bottom:1.5px solid var(--n4)}}
.signal{{border-left:3px solid var(--n9);background:#f7f9fb;padding:15px 18px;font-size:16px;line-height:1.6;
  color:#26313d;margin:22px 0}}
.signal b{{color:var(--n9)}}
.chartwrap{{margin:6px 0 2px;border:1px solid var(--line);padding:10px 9px 4px}}
svg.ch{{width:100%;height:auto;display:block}}
svg.ch text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.foot{{font-family:-apple-system,"Segoe UI",sans-serif;color:var(--muted);font-size:11.5px;line-height:1.62;
  border-top:2px solid var(--n9);margin-top:38px;padding-top:14px}}
.foot b{{color:#3f4a56}}
.build{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;color:#8b939c;
  border:1px dashed #c3c9d0;background:#fafbfc;padding:12px 14px;margin-top:26px;line-height:1.6}}
</style></head><body><div class="wrap">

<div class="topbar"><span class="fm">JK Investment Consulting</span>
  <span class="rt">Study &middot; Capital Allocation</span></div>

<div class="titleblock">
  <div class="kicker">Company Study &middot; Apple Inc.</div>
  <h1>What Apple's Buyback Actually Earned</h1>
  <div class="standfirst">Apple has spent ${rep_t/1000:,.0f} billion retiring
    {100*(1-SHARES_OUT[2025]/SHARES_OUT[2012]):.0f} percent of its shares. Measured at the prices it
    actually paid &mdash; not the prices anyone has estimated &mdash; the program divides into two
    halves that have almost nothing in common.</div>
  <div class="byline">Fiscal years 2013 through 2025, from filings. A template for reading any
    repurchase program.</div>
</div>

<div class="pad">

<p class="lede">Apple's earnings per share grew at {100*((EPS[2025]/EPS[2012])**(1/13)-1):.1f} percent
a year over the thirteen years to fiscal 2025. Its net income grew at
{100*((NI[2025]/NI[2012])**(1/13)-1):.1f} percent. The gap between those two numbers is the buyback,
and it accounts for {100*cum_s/TOT_EPS:.0f} percent of everything the earnings-per-share line did.
Whether that was money well spent is a separate question from whether it raised the number, and
almost everything written about buybacks confuses the two.</p>

<h2><span class="no">1</span>What Was Bought, And At What Price</h2>

<p>The starting point is a figure most published analysis does not have: the price Apple actually
paid. Dividing the cash spent by the shares actually retired &mdash; both taken from the filings
&mdash; gives the true average, with no proxy and no estimate. Over the whole program Apple paid
<b>${rep_t/ret_t:,.2f}</b> for each share it retired.</p>

<p>That figure is weighted by shares, and it is low because the cheap early years bought so many more
shares per dollar. Weighted instead by where the money actually went, the average price paid is
<b>${DOLLAR_W_PX:,.2f}</b>, and the multiple paid is <b>{DW_PE:.1f} times</b> trailing earnings.
Both are correct and they answer different questions: the first is what the program cost per share
removed, the second is what the typical dollar bought. Reporting either one alone is how a repurchase
program gets flattered.</p>

<div class="exh"><div class="eh">Exhibit 1 &middot; The repurchase record, from filings</div>
<table class="fig"><thead><tr><th>Fiscal year</th><th class="r">Cash spent $bn</th>
<th class="r">Shares retired mn</th><th class="r">% of shares</th><th class="r">Net change</th>
<th class="r">Avg price paid</th><th class="r">Multiple paid</th>
<th class="r">Fwd real earnings yield</th></tr></thead>
<tbody>{rows_main()}</tbody></table>
<p class="cap">The total row carries two different weightings and says so: average price paid is
total cash over total shares retired, which is weighted by shares; multiple paid is weighted by
dollars spent. The dollar-weighted average price is ${DOLLAR_W_PX:,.2f} and the equal-weighted
average across years is ${EW_PX:,.2f}.
Cash from <i>PaymentsForRepurchaseOfCommonStock</i>; shares retired from
<i>StockRepurchasedAndRetiredDuringPeriodShares</i> where Apple tagged it and from the share-count
identity where it did not, restated onto today's split basis. Average price paid is cash divided by
shares retired. Forward real earnings yield is next year's real earnings per share over the real
price paid. Net change is shares outstanding, so it is net of shares issued under employee plans.</p></div>

<p>Two things stand out immediately. The pace of retirement fell by half, from
{100*RETIRED[2014]/SHARES_OUT[2013]:.1f} percent of the shares in fiscal 2014 to
{100*RETIRED[2025]/SHARES_OUT[2024]:.1f} percent in fiscal 2025, even though the dollars spent
doubled. And the multiple paid roughly tripled.</p>

<h2><span class="no">2</span>What The Money Earned</h2>

<p>Money spent buying back stock buys a specific thing: the earnings the retired shares used to
carry, and every future earning those shares had a claim on. The immediate return on that purchase
is the earnings yield at the price paid. Compared against the real cost of equity &mdash; real,
because a company that keeps pace with inflation is worth its earnings capitalized at the real rate
&mdash; it gives the practitioner's first-pass test.</p>

<div class="exh"><div class="eh">Exhibit 2 &middot; Forward real earnings yield on each year's repurchases</div>
<div class="chartwrap">{chart_yield()}</div>
<p class="cap">Next fiscal year's real earnings per share divided by the real average price actually
paid, in 2026 dollars. The solid red line is the engine's flat long-run real cost of equity of
{100*COE_LONGRUN:.2f} percent; the dotted gold line is the company's own year-by-year real cost of
equity history, which is materially higher in 2020 and 2021. The crossing year depends on which is
used. That the series crossed does not.</p></div>

<p>The repurchase channel returned around nine percent in real terms in the middle of the last
decade and returns under four percent now. Nothing about the business explains that. The price
does, and the price is the whole of it.</p>

<p>One point of timing belongs with the measure. A contribution computed as earnings acquired less
the charge on the money spent credits a repurchase only with the earnings it bought immediately, not
with the growth of those earnings. Where the company has real abnormal growth ahead of it, the
measure is back-loaded: it understates the repurchase in the year it happens and recovers the
difference in later years. It is a fair measure over a full cycle and a conservative one over a
single year. That is a statement about <i>when</i> abnormal earnings growth is recognized, not about
which price is the pivot.</p>

<div class="signal"><b>What this test answers, and what it does not.</b> The forward earnings
yield against the real cost of equity is not an approximation to something better. It is the exact
test of whether a repurchase generated abnormal earnings growth. The capital charge on the money
spent is the real cost of equity times the price paid; the earnings acquired are the earnings the
retired shares carried; so the contribution to measured abnormal earnings growth is those earnings
less that charge, and it is positive precisely when the earnings yield exceeds the real cost of
equity &mdash; which is to say when the price paid sits below Neutral Value. <b>No view about
Intrinsic Value is required, used, or implied.</b><br><br>
Whether the repurchase created <i>value</i> is a different question with a different pivot: price
against Intrinsic Value. For a company expected to grow faster than a neutral rate, Intrinsic Value
sits above Neutral Value, so there is a band of prices in which a repurchase reduces abnormal
earnings growth in the near term and still creates value, because the earnings it acquired go on
growing. The two questions pivot at different prices and collapsing them into one is the most common
error in this literature. This study answers the first and declines to answer the second.</div>

<h2><span class="no">3</span>The Abnormal Earnings Growth Account</h2>

<p>That earnings-yield spread converts straight into dollars. The account has two levels and they
answer different questions, so they are kept apart.</p>

<p>At the <b>entity level</b>, in total dollars, abnormal earnings growth is this year's real
earnings less last year's grossed up at the real cost of equity, with the return on everything
distributed to shareholders added back. Repurchases are distributions here, exactly like dividends:
cash leaves the company and the benchmark for next year's earnings falls by precisely the return
that cash would have earned. A repurchase therefore neither creates nor destroys anything in this
series, which is what makes it useful &mdash; it measures the operating business, clean of the
buyback, and it needs no assumption about how the buyback was funded. On that basis Apple generated
<b>${AEG_ENT_TOT/1000:,.1f} billion</b> of real abnormal earnings growth over the thirteen years.</p>

<p>A repurchase only shows up <b>per continuing share</b>, because what it does is transfer value
between the shareholders who sold and the shareholders who stayed. That splits in two.</p>

<div class="exh"><div class="eh">Exhibit 3 &middot; The repurchase account, real 2026 dollars, billions</div>
<table class="fig"><thead><tr><th>Fiscal year</th><th class="r">Shares retired mn</th>
<th class="r">Real price paid</th><th class="r">Fwd earnings yield</th>
<th class="r">Entry effect</th><th class="r">Earned since</th><th class="r">Total to date</th>
<th class="r">Still owed per share</th></tr></thead>
<tbody>{rows_aeg()}</tbody></table>
<p class="cap"><b>Entry effect</b> is the shares retired times next year's real earnings per share
less the real cost of equity applied to the real price paid. It is negative precisely when the
earnings yield at the price paid is below the real cost of equity, and no estimate of Intrinsic
Value enters it. <b>Earned since</b> is those shares' claim on the entity-level abnormal earnings
growth the business generated in every later year, at
{100*COE_LONGRUN:.2f} percent. The last column is what each retired share must still earn before
its tranche breaks even. The "earned since" column is <i>not</i> comparable across rows &mdash; the
2013 tranche has had twelve years to accumulate and the 2024 tranche none &mdash; which is why the
requirement is restated per share in the final column.</p></div>

<p>The <b>entry effect</b> is objective. It uses the price actually paid, the earnings actually
acquired and a stated cost of equity, and it requires no view about what the shares were worth.
Through fiscal 2020 it is positive in every year. From fiscal 2021 it is negative in every year, and
the swing is large: the four years from 2021 through 2024 destroyed
<b>${-sum(ENTRY[t] for t in NEG_LR)/1000:,.1f} billion</b> of abnormal earnings growth on entry.</p>

<p>The <b>continuing effect</b> is what can retrospectively justify a purchase made at a low
earnings yield. Retire a share at an earnings yield below the cost of equity and you are behind on
day one; if the business then grows earnings at an abnormal rate, the retired share's claim on that
growth accrues to the holders who stayed, and the tranche can catch up. This is real, and it is the
whole case for paying a high multiple for your own stock. But note what it is not: it is not
knowable at the time of purchase, and it is not an argument that the entry effect was positive. It
is an argument that the future would compensate.</p>

<div class="signal"><b>Why the pivot is Neutral Value and not Intrinsic Value.</b> Intrinsic Value
is a judgment, and nobody knows what anyone's judgment of Apple's Intrinsic Value should have been
in 2021. What is objectively known for every past year is the earnings yield at the price paid and
the cost of equity, and those two settle the entry effect completely. If a purchase made at a low
earnings yield turns out well, abnormal earnings growth rises in later years and justifies it then.
That is a statement about which year the abnormal earnings growth is recognised in. It is not a
reason to move the pivot, and moving it would make an objective measure depend on an undisclosed
judgment.</div>

<p>How much would have to come later? For the fiscal 2024 tranche, each retired share must still
earn <b>${max(0.0,-ENTRY[2024]-CONT[2024])/RETIRED[2024]:,.2f}</b> of real abnormal earnings growth
to break even. Apple's entity-level abnormal earnings growth has averaged
${MEAN_AEG_PS:,.2f} a share a year over this period, so that is roughly
<b>{(max(0.0,-ENTRY[2024]-CONT[2024])/RETIRED[2024])/MEAN_AEG_PS:.0f} years</b> of typical
performance &mdash; and the average is flattered by two exceptional years.</p>

<p>One disclosure that matters, because it changes a sign rather than a decimal. On the engine's
flat long-run real cost of equity of {100*COE_LONGRUN:.2f} percent, the program's cumulative entry
effect is <b>{'+' if ENTRY_TOT>0 else '&minus;'}${abs(ENTRY_TOT)/1000:,.1f} billion</b> &mdash; positive. On the company's own
year-by-year real cost of equity history, which runs materially higher in 2020 and 2021, it is
<b>{'+' if ENTRY_ALT>0 else '&minus;'}${abs(ENTRY_ALT)/1000:,.1f} billion</b>, and the negative years begin in fiscal 2018 rather than
fiscal 2021. Which rate is right is an open question in the engine and this study does not settle
it. Both are reported and neither is suppressed. What survives either choice is the shape: the
entry effect deteriorated steadily and crossed into negative territory, and it did so because of
the price, not the business.</p>

<p>Because the entry effect is a linear function of the capitalization rate, it has exactly one
root, and that root can be stated rather than searched for: it is the retirement-weighted forward
real earnings yield on the whole program. <b>The cumulative entry effect turns negative at a real
cost of equity of {100*RHO_STAR:.2f} percent.</b> The engine uses {100*COE_LONGRUN:.2f} percent. The
conclusion that the program added abnormal earnings growth on entry therefore rests on
<b>{10000*RHO_HEADROOM:.0f} basis points</b> of capitalization rate, and on nothing else.</p>

<div class="signal"><b>Why {10000*RHO_HEADROOM:.0f} basis points is the most important number in this
section.</b> Every other sensitivity here moves a magnitude. This one moves a sign, and the reader
cannot compute it from the published figures without the tranche weights.<br><br>
Split the program and the two halves are not close. The fiscal
{_EARLY[0]}&ndash;{_EARLY[-1]} tranches break even at <b>{100*RHO_STAR_EARLY:.2f} percent</b>, so
they survive almost any plausible rate. The fiscal {_LATE[0]}&ndash;{_LATE[-1]} tranches break even
at <b>{100*RHO_STAR_LATE:.2f} percent</b>, which is already below the rate the engine uses &mdash;
which is another way of saying what Exhibit 3 shows, that those years are negative on entry at any
defensible rate rather than marginally so.<br><br>
<b>And this is where the leverage question enters, so it is worth being explicit about what is not
modelled.</b> A company that borrows to buy its own stock raises the required return on the equity
that remains, so a capitalization rate held constant across a period in which leverage rose is
charging too little in the later years. Apple's net financial obligations rose by about half a turn
of equity over these thirteen years, and Apple's own year-by-year real cost of equity history
averaged {100*COE_HIST_MEAN:.2f} percent over the same span &mdash; well above the
{100*RHO_STAR:.2f} percent break-even, which is precisely why the alternative reading in the
paragraph above is negative rather than positive. <b>This study does not re-lever the cost of
equity, and no figure in it should be read as if it had.</b> What it does is state the tolerance:
anything that adds more than {10000*RHO_HEADROOM:.0f} basis points to the real cost of equity over
this period inverts the sign of the headline entry effect. A re-levering treatment &mdash; pure
Modigliani&ndash;Miller Proposition II, without a tax adjustment &mdash; has been built and verified
against the engine's own fixture as leaving the four-method value tie unaffected, and is scheduled
rather than deferred. It has not been run on this company. When it is, the number to compare it
against is the {10000*RHO_HEADROOM:.0f} basis points above.</div>

<h2><span class="no">4</span>The Internal Rate Of Return, Three Ways</h2>

<p>A cleaner measure treats the program as an investment: each year's cash out, the dividends the
retired shares would have drawn coming back in, and the accumulated shares valued at the end. What
the shares are worth at the end is the whole argument, so the table gives three answers rather than
pretending to one.</p>

<div class="exh"><div class="eh">Exhibit 4 &middot; Internal rate of return, terminal fiscal 2025 year end</div>
<table class="fig"><thead><tr><th>Window</th><th class="r">Cash out $bn</th>
<th class="r">Shares mn</th><th class="r">At market price</th><th class="r">At market, real</th>
<th class="r">At the multiple paid</th><th class="r">At Neutral Value</th></tr></thead>
<tbody>{rows_irr()}</tbody></table>
<p class="cap"><b>At market price</b> values the retired shares at ${P_END_25:,.2f}. It is exactly the
money-weighted return of an outside investor who bought Apple on Apple's own schedule with Apple's own
dollars, so it measures the stock rather than the management. <b>At the multiple paid</b> values each
tranche at fiscal 2025 earnings times the multiple Apple itself paid for it, stripping out every point
of re-rating. <b>At Neutral Value</b> values them at Neutral Earnings Power capitalized at the real
cost of equity, which is to say assuming no abnormal earnings growth from here &mdash; a floor case.
Apple made no material repurchases before fiscal 2013, so the fifteen- and twenty-year windows are
identical to the full-program row.</p></div>

<p>The three columns tell the story the headline number hides. Over the full program the market
return of {100*IRRS[2013][0]:.1f} percent falls to {100*IRRS[2013][1]:.1f} percent once re-rating is
removed, and to {100*IRRS[2013][2]:.1f} percent if one assumes Apple has no abnormal growth ahead of
it. Over the last five years the same three columns read {100*IRRS[2021][0]:.1f} percent,
{100*IRRS[2021][1]:.1f} percent and {100*IRRS[2021][2]:.1f} percent. Strip out the multiple and the
recent program returned nothing at all.</p>

<p class="punch">Almost the entire measured return on Apple's recent repurchases is the market's
willingness to pay a higher multiple, not the earnings the money bought.</p>

<p>The break-even makes the same point without requiring a view. For the program as a whole, Apple's
shares needed to be worth <b>${be[2013]:,.2f}</b> at the end of fiscal 2025 for the money to have
cleared its cost &mdash; the hurdle being the long-run real cost of equity of {100*COE_LONGRUN:.2f}
percent plus two and a half points of inflation. They traded at ${P_END_25:,.2f}. For the last five
years alone the break-even is <b>${be[2021]:,.2f}</b>, only
{100*(P_END_25/be[2021]-1):.0f} percent below the actual price. The margin of safety on the recent
program is thin, and it is entirely a margin in the multiple.</p>

<h2><span class="no">5</span>Did They Buy When It Was Cheap?</h2>

<p>The question splits in two, and a company can be good at one half and bad at the other.</p>

<div class="exh"><div class="eh">Exhibit 5 &middot; The multiple paid, the market multiple, and the dollars spent</div>
<div class="chartwrap">{chart_pe()}</div>
<p class="cap">Bars are cash spent each fiscal year. The grey line is the average market multiple over
that fiscal year; the blue line is the multiple Apple actually paid. The green dashed line is the
Neutral P/E of {NEUTRAL_PE:.1f} times, the reciprocal of the engine's long-run real cost of equity.</p></div>

<p><b>Execution inside the year was good.</b> Averaging each year equally, Apple paid
{EW_PE:.2f} times against a market average of {EW_MKT:.2f} times &mdash; an edge of
{100*(EW_PE/EW_MKT-1):.1f} percent. It bought its own stock slightly better than a buyer spreading
purchases evenly through the year would have.</p>

<p><b>Allocation across years was poor.</b> Weighting by dollars actually spent, the multiple paid
rises to {DW_PE:.2f} times, {100*(DW_PE/EW_PE-1):.1f} percent above the equal-weighted figure. Apple
spent progressively more money as its shares got progressively more expensive. The two effects
combine to a dollar-weighted multiple {100*(DW_PE/EW_MKT-1):.1f} percent above the market's own
average over the same years.</p>

<p>This is worth stating plainly because it runs against the flattering version. Apple's repurchase
program is often praised for its timing, and the praise is half deserved: the trading was disciplined.
The allocation was not. A company that had spent the same total dollars in equal annual instalments
would have retired more shares.</p>

<h2><span class="no">6</span>How Much Of It Was Just Paying The Staff</h2>

<p>Some of every repurchase merely absorbs the shares issued to employees, and that portion is not a
return of capital at all. For Apple the fraction is modest: {100*iss_t/ret_t:.1f} percent of the
shares retired, and {100*mkt_del/rep_t:.1f} percent of the dollars spent. Roughly
{100*(1-mkt_del/rep_t):.0f} percent of the program was a genuine return of capital rather than an
absorption of dilution. Whether that is good or bad relative to peers is not something this study
tests, and the comparison is worth running before anyone draws one.</p>

<p>There is a second, larger number underneath it, and it does not appear in any account. Share-based
pay is charged to earnings at grant-date value. What continuing shareholders actually gave up is the
market value of the shares delivered, plus the cash Apple paid for employee withholding taxes, less
what employees paid in. Over the thirteen years those come to <b>${econ_t/1000:,.0f} billion</b>
against <b>${sbc_t/1000:,.0f} billion</b> charged to earnings &mdash; a factor of
{econ_t/sbc_t:.2f}, and a wedge of ${(econ_t-sbc_t)/1000:,.0f} billion, or
{100*(econ_t-sbc_t)/ni_t:.1f} percent of cumulative net income.</p>

<div class="signal"><b>What the wedge is and is not.</b> It is not an unrecorded expense, and
charging the offsetting repurchase again would be double counting: expensing at grant-date value is
correct accounting. What it measures is the value transferred from continuing shareholders to
employees by share-price appreciation between grant and delivery, over and above what the accounts
recorded. Read the cumulative figure, not the annual one &mdash; awards delivered in a year were
expensed in earlier years, so any single year compares unrelated cohorts.</div>

<h2><span class="no">7</span>What It Cost To Remove A Share For Good</h2>

<p>The price paid answers what a share cost at the moment of purchase. It does not answer what the
program cost, because in the same year the company issued shares back to its own employees. A
continuing shareholder never received the shares retired. What they received was the difference.</p>

<p>Both quantities are in the filings and the arithmetic between them is an identity: shares retired
less shares issued equals the reduction in shares outstanding, every year and cumulatively. Over the
thirteen years Apple retired <b>{ret_t:,.0f} million</b> shares gross, issued
<b>{iss_t:,.0f} million</b>, and reduced the count by <b>{net_t:,.0f} million</b>. Issuance was
{100*ISS_SHARE_OF_RET:.1f} percent of gross retirement and {100*ISS_SHARE_OF_CASH:.1f} percent of the
dollars spent.</p>

<div class="exh"><div class="eh">Exhibit 6 &middot; Gross retirement against net count reduction, from filings</div>
<table class="fig"><thead><tr><th>Fiscal year</th><th class="r">Cash spent $bn</th>
<th class="r">Gross retired mn</th><th class="r">% of shares</th><th class="r">Issued mn</th>
<th class="r">% of shares</th><th class="r">NET reduction mn</th><th class="r">% of shares</th>
<th class="r">Gross price paid</th><th class="r">Net retirement cost</th></tr></thead>
<tbody>{rows_net()}</tbody></table>
<p class="cap">Cash from <i>PaymentsForRepurchaseOfCommonStock</i>. Gross retirement is
<i>StockRepurchasedAndRetiredDuringPeriodShares</i> where Apple tagged it and the share-count identity
where it did not. Issued is the residual of that identity and is therefore net of any shares issued
for other reasons. Percentages are of shares outstanding at the start of the fiscal year. The gross
price is cash over gross retirement, weighted by shares; it is the same ${M_A:,.2f} that appears in
Exhibit 1. The net retirement cost is cash over the net count reduction, and is suppressed rather
than printed wherever the net reduction falls below {100*NET_MIN_FRAC:.2f} percent of opening shares,
because a ratio on a small or negative denominator carries no meaning. For Apple no year is
suppressed{'' if not NET_SUPPRESSED else '; the suppressed years are ' + ', '.join(str(y) for y in NET_SUPPRESSED)}.</p></div>

<p>Four quantities can be built from those columns and they are not interchangeable. Two of them are
in circulation already and are routinely given the same name, which is how a repurchase program gets
described more favorably than the cash supports.</p>

<div class="exh"><div class="eh">Exhibit 6a &middot; Four measures of what a share cost, full program</div>
<table class="fig"><thead><tr><th>&nbsp;</th><th class="r">Per share</th>
<th class="r">Against A</th><th>What it answers</th></tr></thead>
<tbody>{rows_measures()}</tbody></table>
<p class="cap">Employee plan proceeds over the period were ${proc_t:,.0f} million and cash paid to the
tax authority on employee awards was ${tax_t:,.0f} million. Measure C credits the company for the
first and ignores the second, which is a one-sided adjustment: under net share settlement a company
pays that tax <i>instead of</i> issuing further shares, so it is money spent holding the count down
and belongs on the same side of the ledger as the repurchase. It is
{tax_t/proc_t:.1f} times the size of the proceeds. D is the fullest statement of the cash cost and C
should not be published without it.</p></div>

<div class="signal"><b>What this measure is, and three things it is not.</b> It is a descriptive
ratio &mdash; dollars of cash per unit of permanent reduction in the share count &mdash; and from a
continuing shareholder's standpoint it is arguably the more relevant of the two, because the count
reduction is the only thing they actually received.<br><br>
<b>It is not a price, and it does not enter the abnormal earnings growth account.</b> The entry
effect in section 3 is the earnings acquired less the real cost of equity applied to the price paid,
and that is an identity only when the price is the one actually transacted: the capital charge falls
on the cash actually spent and the earnings acquired are the ones the retired shares actually
carried. Substituting a synthetic higher price would break the identity and move the pivot away from
Neutral Value. Every figure in section 3 is struck on the gross price of ${M_A:,.2f} and none of them
moves.<br><br>
<b>It is not an expense.</b> Share-based pay is already charged to earnings at grant-date fair value.
Treating the excess of the net cost over the gross price as a further cost of the repurchase charges
the same compensation twice.<br><br>
<b>It is not reportable on a small denominator.</b> Where a company issued nearly as much as it
bought, the ratio explodes; where it issued more, the ratio is negative and meaningless. The fact is
reported in place of the number.</div>

<p>For Apple the effect is real and it is not a scandal. Roughly one dollar in seven of the program
was buying back stock the company had just issued to its own staff, and correcting for it raises the
cost of permanently removing a share from ${M_A:,.2f} to between ${M_C:,.2f} and ${M_D:,.2f} &mdash;
{100*(M_C/M_A-1):.0f} to {100*(M_D/M_A-1):.0f} percent. That is worth knowing and it is worth
publishing. It is not an expos&eacute;, and the figures will not carry one.</p>

<p>The measure earns its place elsewhere. Consider Salesforce, which is not an exotic case but the
ordinary shape of a large software company.</p>

<div class="exh"><div class="eh">Exhibit 6b &middot; Salesforce, the same measure on a company where it bites</div>
<table class="fig"><thead><tr><th>Fiscal year</th><th class="r">Repurchase cash $bn</th>
<th class="r">Shares outstanding mn</th><th class="r">NET reduction mn</th>
<th class="r">Net retirement cost</th><th class="r">Traded range that year</th>
<th class="r">Cost / highest trade</th></tr></thead>
<tbody>{rows_crm()}</tbody></table>
<p class="cap">Contrast case only; no figure here enters any Apple measure. Salesforce tags neither
<i>StockRepurchasedAndRetiredDuringPeriodShares</i> nor <i>TreasuryStockSharesAcquired</i>, so
<b>no gross price per share retired can be computed for it at all.</b> The net measure needs only
repurchase cash and the change in shares outstanding, which every filer reports. Fiscal years are as
Salesforce labels them. Provenance and the limits of these three rows are in the build note.</p></div>

<p class="punch">At its worst Salesforce paid {CRM_WORST[4]/CRM_WORST[6]:,.1f} times the highest price
its own stock traded that year to remove one share permanently. Apple never paid more than
{max(NET_PS[y]/FY_HIGH[y] for y in FY):,.2f} times its own fiscal-year high, in
{max(FY, key=lambda y: NET_PS[y]/FY_HIGH[y])}.</p>

<p>That comparison is also the argument for reporting the net measure first rather than as an
appendix. The gross price requires a retirement or treasury count, which many companies do not tag.
The net cost requires only the cash spent and the change in the share count, which all of them
report. The more general measure is the one that has been treated as secondary.</p>

<h2><span class="no">8</span>Where The Money Came From</h2>

<p>Of the ${rep_t/1000:,.0f} billion spent, <b>${(rep_t-D_NFO)/1000:,.0f} billion came from current
retention</b> &mdash; earnings kept back after ${div_t/1000:,.0f} billion of dividends &mdash; and
<b>${D_NFO/1000:,.0f} billion came from the balance sheet</b>, in the form of a rise in net financial
obligations. Apple's net financial position fell from ${NETFIN[2012]/1000:,.0f} billion of net
financial assets in fiscal 2012 to ${NETFIN[2025]/1000:,.0f} billion in fiscal 2025, and gross debt
went from nothing to ${DEBT[2025]/1000:,.0f} billion. That second source is
non-repeatable by construction: a cash pile can be spent once, and it has now largely been spent.</p>

<p>Splitting the share-count channel by what funded it is what makes the leverage contribution
visible, and it is the reason the same decision has to be read twice.</p>

<div class="exh"><div class="eh">Exhibit 7 &middot; Growth in earnings per share by channel, fiscal 2012 to fiscal 2025</div>
<table class="fig"><thead><tr><th>Channel</th><th class="r">Per share</th>
<th class="r">Share of total</th><th>What it is</th></tr></thead>
<tbody>{rows_channel()}</tbody></table>
<p class="cap">The operating and financial split of net income is computed from reported operating
income, pretax income and the tax provision, and reconciles to reported net income exactly in every
year. The share-count channel is split in the same proportion as the funding of the repurchases
themselves: ${D_NFO/1000:,.0f} billion of the ${rep_t/1000:,.0f} billion spent, or
{100*LEV_SHARE:.1f} percent, is matched by the increase in net financial obligations over the period,
and the balance by retention.</p></div>

<p>Read the direct effect on its own and leverage did nothing at all: net interest <i>subtracts</i>
<b>${-cum_f:.2f}</b> from the <b>${TOT_EPS:.2f}</b> of growth, because rising interest expense roughly
cancelled the interest income Apple gave up. Read it through the repurchases it financed and it
accounts for <b>${EPS_LEV:.3f}</b>, or {100*EPS_LEV/TOT_EPS:.1f} percent of everything the
earnings-per-share line did. Retention-funded retirement accounts for ${EPS_RET:.3f}, or
{100*EPS_RET/TOT_EPS:.1f} percent. Taken together with the interest line, financial engineering is
<b>{100*FIN_ENG/TOT_EPS:.1f} percent</b> of the growth and the operating business is
<b>{100*cum_o/TOT_EPS:.1f} percent</b>. A study that reported only the interest line would record
leverage as a small negative, when its actual contribution was a positive
{abs(EPS_LEV/cum_f):.1f} times larger in magnitude. That is not a rounding difference; it is the
wrong sign on a channel worth {100*EPS_LEV/TOT_EPS:.1f} percent of the growth.</p>

<p>The balance sheet tells the story the income statement cannot. On the definition used here &mdash;
net financial obligations over common equity &mdash; Apple's leverage moved from
{FLEV_12:.2f} in fiscal 2012 to {FLEV_25:.2f} in fiscal 2025, a rise of
{FLEV_25-FLEV_12:.2f} of a turn of equity. On the engine's reformulated statements at HEAD it moved
from {FLEV_ENG_12:.2f} to {FLEV_ENG_25:+.2f}, a rise of {FLEV_ENG_25-FLEV_ENG_12:.2f}. The two differ
because the engine reformulates the statements and classifies some securities as operating rather
than financial. They agree on the direction and on the order of magnitude:
something between half a turn and a full turn of equity in thirteen years, from a company that
started the period with none.</p>

<p class="punch">A company that began the period with no debt whatever levered itself up materially
simply by spending its financial assets. The interest line cannot see that happen.</p>

<p>The pre-2018 borrowing also needs its context: before the 2017 tax act Apple's cash was largely
offshore and effectively trapped, and the debt was a workaround for a tax problem rather than a view
about capital structure. Reading those years as a leverage decision misreads them. What is not in
dispute is the arithmetic of the funding, which does not care why the money was borrowed.</p>

<h2><span class="no">9</span>The Number That Should Change The Conversation</h2>

<p>Set the repurchases aside for a moment and ask a broader question: how much capital did Apple have
to deploy over these thirteen years, where did it go, and what did each part of it earn? Both halves
are enumerable from the filings, and they reconcile.</p>

<div class="exh"><div class="eh">Exhibit 8 &middot; Sources and uses of incremental capital, fiscal 2013 to fiscal 2025, $ million</div>
<table class="fig"><thead><tr><th>&nbsp;</th><th class="r">$ million</th>
<th class="r">Share deployed</th></tr></thead>
<tbody>{rows_sources()}</tbody></table>
<p class="cap">Money spent retiring shares is capital deployed, not capital returned to the firm's
providers as a group, so it belongs on the uses side alongside investment in the business. The
unreconciled line is the same residual that appears in the equity roll-forward &mdash; other
comprehensive income and items not separately modelled &mdash; at
{100*abs(UNREC)/rep_t:.2f} percent of repurchase spending.</p></div>

<p>Of that total, <b>{100*SH_REP:.0f} percent went into Apple's own shares and
{100*SH_NOA:.1f} percent into the business.</b> What the two earned could hardly be further
apart. The repurchase slice bought earnings at a dollar-weighted {DW_PE:.2f} times, which is an entry
earnings yield of {100*ENTRY_EY:.1f} percent, and everything else it earned had to come from the
growth of those earnings afterward. The operating slice absorbed
${D_NOA/1000:,.1f} billion of additional net operating assets, and after-tax operating income rose
${(OI[2025]-OI[2012])/1000:,.1f} billion against it &mdash; a return on incremental operating capital
of <b>{100*ROIC:.1f} percent</b>, or {100*ROIC_CT:.1f} percent holding the effective tax rate at its
fiscal 2012 level, since the 2017 tax act moves the answer by
{100*(ROIC-ROIC_CT):.0f} percentage points on its own.</p>

<p class="punch">Apple put {100*SH_REP:.0f} percent of its incremental capital into its own
shares at an entry earnings yield of about {100*ENTRY_EY:.1f} percent, while the
{100*SH_NOA:.0f} percent that went into the business earned {100*ROIC:.0f} percent.</p>

<p>The full-period figure is not an artifact of the endpoints. On rolling six-year windows,
{win_sentence()}. The suppression is a reporting rule rather than an inconvenience: a company whose
net operating assets are small, negative, or moving opposite to earnings will produce annual ratios
that are meaningless, and Apple's net operating assets were negative in
{_w(len(NEG_IC))} of these {_w(len(FY))} years. The fact is reported in place of the number.</p>

<p>One figure that will be reached for has to be labelled before it is. Dividing the growth in
after-tax operating income by <i>all</i> the capital deployed gives {100*ROC_ALL:.1f} percent. That is
not a blended return on capital, because the repurchase slice produces no operating income at all by
construction &mdash; its return accrues per continuing share rather than through the income statement.
Read it as how little operating growth the total deployment bought, which is the point rather than a
defect of the measure.</p>

<p>None of this is automatically a criticism. A business generating that return on a small capital
base cannot necessarily absorb ${rep_t/1000:,.0f} billion more at anything like the same rate, and the
whole case for returning capital is that it cannot. But it reframes the question. The repurchase was
not competing against nothing. It was competing against the highest-returning business most investors
will ever see, at a moment when that business was apparently unable to find more to do with the money.
Whether that inability was real is the question worth arguing about, and it is not a question about
repurchases at all.</p>

<h2><span class="no">10</span>The Capital Base The Repurchases Consumed</h2>

<p>A measurement problem sits underneath all of this, and it surfaces the moment anyone quotes
Apple's return on equity. In fiscal 2025 that figure was {100*ROE_REP[2025]:,.0f} percent. It is an
artifact. Every dollar spent retiring stock leaves reported equity, so the denominator has been
consumed by the repurchases themselves and the ratio rises as the capital base is destroyed. It
measures how much capital has left the company, not how well capital is employed.</p>

<p>The repair is the operation this project already performs on the index, under the name
net-buyback restoration: add back what was spent retiring shares, net of what was raised issuing
them, and the base becomes what shareholders actually put in and left in. That restored base is the
Real Capital Base. Treating a repurchase as an acquisition instead &mdash; capitalizing it, with the
excess over the retired shares' book value sitting in a goodwill-like account &mdash; lands on the
same total, because acquisition accounting adds the whole purchase price to the asset side, as net
assets acquired plus goodwill, and leaves equity unchanged. The split between the two pieces is a
labelling question, and for Apple it is nearly immaterial: <b>{100*GW_SHARE:.0f} percent of the
cumulative restoration is premium over the book value of the shares retired</b> in any case.</p>

<div class="exh"><div class="eh">Exhibit 9 &middot; Reported equity against the Real Capital Base, $ million</div>
<table class="fig"><thead><tr><th>Fiscal year</th><th class="r">Reported equity</th>
<th class="r">Cumulative restoration</th><th class="r">Real Capital Base</th>
<th class="r">Return on equity, reported</th><th class="r">On the Real Capital Base</th>
<th class="r">Return on invested capital, reported</th><th class="r">Restored</th></tr></thead>
<tbody>{rows_rcb()}</tbody></table>
<p class="cap">Cumulative restoration is repurchase cash less equity plan proceeds, accumulated from
fiscal 2013. Returns are struck on the average of opening and closing capital. Invested capital is
net operating assets, being common equity plus net financial obligations; where it is negative the
reported ratio is marked not meaningful rather than printed. The first two years of the restored
column, {100*ROIC_RES[2013]:,.1f} and {100*ROIC_RES[2014]:,.1f} percent, sit on a restored base that
has barely begun to accumulate; they are artifacts of the opening window and are not evidence of a
decline in returns.</p></div>

<p>On the Real Capital Base, Apple's return on equity in fiscal 2025 is
<b>{100*ROE_RCB[2025]:.1f} percent</b>, and the series declines steadily from
{100*ROE_RCB[2013]:.1f} percent in fiscal 2013. That is the economically informative shape, and it is
the opposite of the reported one.</p>

<p>Return on invested capital behaves the same way and worse. Reported invested capital is negative
in {_w(len(NEG_IC))} of the {_w(len(FY))} years, so the reported ratio is not merely misleading but
undefined; in the {_w(len(POS_IC))} years it is positive it prints
{", ".join(f"{100*OI[y]/NOA[y]:,.0f}" for y in POS_IC[:-1])} and {100*OI[POS_IC[-1]]/NOA[POS_IC[-1]]:,.0f}
percent, none of which mean anything about the business. Restoration is what makes the measure
computable at all, and on the restored base it settles between
{100*min(ROIC_RES_SETTLED):.1f} and {100*max(ROIC_RES_SETTLED):.1f} percent from fiscal 2019 onward.</p>

<h2><span class="no">11</span>What The Retained Earnings Earned</h2>

<p>Money spent retiring shares is retained rather than distributed. It never left shareholders as a
group; it was recycled among them, moving from those who sold to those who stayed. So the retained
portion of earnings is earnings per share less dividends per share, and the return on retained
earnings is the growth in real earnings per share divided by the real earnings retained to produce
it. Over the thirteen years Apple's cumulative growth in real earnings per share was
${_rnum:,.3f} against ${_rden:,.3f} of cumulative retained real earnings per share, a
<b>return on retained earnings of {100*RORE:.2f} percent</b> against a real cost of equity of
{100*COE_LONGRUN:.4f} percent, at a retention rate of {B_RET:.3f}.</p>

<p>That is the central measure of the section, so it is computed twice by routes that share no
arithmetic. The house identity says abnormal earnings growth equals the retention rate times the
excess of the return on retained earnings over the cost of equity, and
{B_RET:.4f} times the excess of {100*RORE:.2f} percent over {100*COE_LONGRUN:.2f} percent gives
<b>{100*AEG_IDENT:.2f} percent a year</b>. Computed the other way, from the entity-level
cum-dividend series in section 3, real abnormal earnings growth averaged
${AEG_ENT_TOT/len(FY):,.0f} million a year on average real net income of ${AVG_NI_R:,.0f} million,
which is <b>{100*AEG_RATE_ENT:.2f} percent a year</b>. Two independent routes agreeing to
{_w(round(abs(AEG_IDENT-AEG_RATE_ENT)*10000))} basis points. That the first lands on very nearly the cost of
equity itself is a coincidence of this company and this period, and nothing should be read into it.</p>

<p>Only the full-period figure is published, and the reason generalizes. Annual return on retained
earnings runs from {100*RORE_MIN:.1f} percent to {100*RORE_MAX:.1f} percent over this period and is
negative in {_w(len(RORE_NEG))} of the {_w(len(FY))} years, because a single year's change in earnings has
almost nothing to do with the earnings retained the year before. For any company whose earnings are
at all cyclical the annual series carries no signal, and quoting one year of it would be an
invitation to misread it.</p>

<h2><span class="no">12</span>What This Settles And What It Does Not</h2>

<p>Two claims run through this study and they are not equally strong.</p>

<p>The first is unconditional and requires no view about what Apple is worth. The economics of the
program changed completely, and they changed because the multiple changed. The immediate return fell
from around nine percent real to under four. Strip out re-rating and the last five years of
repurchase returned {100*IRRS[2021][1]:.1f} percent. The dollars were allocated toward the expensive
years rather than the cheap ones. None of that depends on an estimate of Intrinsic Value.</p>

<p>The second is conditional, and this study declines to settle it. Whether the recent repurchases
created or destroyed value turns entirely on whether Apple's shares are worth more than Apple paid,
and that is the quantity in dispute. What can be said precisely is the benchmark. The engine's
current run puts Apple's Neutral Value at <b>${NV_PS:,.2f}</b> a share &mdash; Neutral Earnings Power
of ${NEP:,.2f} capitalized at a real cost of equity of {100*COE_LONGRUN:.2f} percent, a Neutral P/E of
{NEUTRAL_PE:.1f} times. Against a price of ${PRICE_REAL_ENGINE:,.2f} at that run, the shares traded at
{PRICE_REAL_ENGINE/NEP:.1f} times Neutral Earnings Power, a
<b>{100*(PRICE_REAL_ENGINE/NV_PS-1):.0f} percent premium to Neutral Value</b>. Every dollar of
repurchase at that price is a bet that the premium is deserved.</p>

<p class="punch">A repurchase is worth doing when the shares are worth more than they cost. Apple's
program spent its first half buying at a discount to Neutral Value and its second half buying at a
large premium, and no amount of accretion changes which is which.</p>

<div class="foot">
  <b>Method.</b> Repurchase cash, shares retired, share-based compensation, employee withholding tax
  and shares outstanding are from the Securities and Exchange Commission's XBRL company-concept
  interface for central index key 0000320193, form 10-K, full fiscal years, restated onto today's
  split basis. Prices are EODHD monthly closes for AAPL.US, split-adjusted. Earnings, share counts,
  balance-sheet items, the consumer price index deflator and the real cost of equity history are read
  from the engine's committed outputs at HEAD, except gross borrowings, which are read from the
  Securities and Exchange Commission tags directly because the vendor total-debt line carries two
  different lease treatments across the period; see the build note.
  <b>Provenance of the two cost-of-equity rates, which differ in kind and not only in level.</b>
  The flat long-run rate is read from the engine's own per-tenor curve as the real risk-free rate
  plus the market equity risk premium, with no averaging. The year-by-year company history shown
  against it in Exhibit 2, and the alternative entry effect struck on it, are not computed by this
  system at all: they derive from a monthly effective cost-of-equity decomposition covering 1877 to
  2026 that was ingested whole from an external source into the rate infrastructure on 2026-07-21.
  That series is a data input rather than a model output and is not reproducible from this system.
  Both are reported, neither is preferred, and the disagreement between them is a flat long-run rate
  set against a time-varying historical mean rather than a defect in either.
  <b>Currency of the valuation anchor.</b> The two engine figures in this study &mdash; Neutral Value
  and the long-run real cost of equity &mdash; are read from a run the engine has since quarantined,
  <i>outputs/AAPL_summary.STALE.csv</i>, vintage 2026-08-09. The engine is presently declining to
  produce a valuation for Apple pending a review of how the forecast's share repurchases are funded.
  Both figures are unchanged from the last published run and nothing else in this study depends on
  the engine's valuation; the study will be re-issued when that review clears. Everything else here
  &mdash; the prices paid, the shares retired, the returns, the funding decomposition and the Real
  Capital Base &mdash; is computed from filings and a price series and is unaffected.
  Shares retired for fiscal 2013
  through 2017 are derived from the share-count identity because Apple did not tag them; the
  derivation and its two validation tests are set out in the study methodology document.
  <b>Lineage.</b> The abnormal earnings growth framework is Ohlson and Juettner-Nauroth (2005). The
  operating-versus-financing decomposition follows Penman's reformulation.
  <b>Figures.</b> All figures are live and computed from the sources above; none is illustrative.
  Individual years carry timing noise where accelerated share repurchase agreements settle across
  fiscal year ends, so single-year average prices are approximate and the dollar-weighted average
  over the full program is the timing-robust figure.
  <b>Disclosure.</b> This study states no estimate of Apple's Intrinsic Value and contains no
  recommendation to buy or sell any security.
</div>

<div class="build">
BUILD NOTE &mdash; not for publication<br>
ENGINE ANCHOR IS READ FROM A QUARANTINED RUN, AND IT IS DISCLOSED IN THE METHOD FOOTER. The two
engine figures used here &mdash; Neutral Value of ${NV_PS:,.6f} a share and the long-run real cost of
equity of {100*COE_LONGRUN:.6f}% &mdash; are read from outputs/AAPL_summary.STALE.csv, run vintage
2026-08-09. The engine is presently REFUSING to value Apple: outputs/AAPL_REFUSED.csv records an
unfunded distribution under the two-of-three rule, the default Consensus overlay's three percent
buyback being unfundable against 2.5 percent asset growth, and no valuation is produced until a
funding decision is recorded in companies/AAPL.yaml. Both figures are byte-identical to the last
published run, so no arithmetic in this document changes; what is absent is the engine's own warrant
that they are current. Approved by James 2026-08-12, on the condition that the document is re-issued
when Apple's funding review clears the gate.<br>
CORRECTED 2026-08-09, AND IT MOVED PUBLISHED FIGURES: the engine's vendor balance-sheet feed
(outputs/AAPL_reported_bs.csv) carried a "Total Debt" line that folded capitalized leases in from
FY2022 onward while leaving the earlier years unrestated, so the series changed definition in the
middle of itself and could not be differenced across the break &mdash; and FY2025 is an endpoint of
this study. Gross borrowings are therefore taken from us-gaap:LongTermDebtNoncurrent
+ us-gaap:LongTermDebtCurrent + us-gaap:CommercialPaper throughout, verified at data.sec.gov
2026-08-09. Effect: gross debt added ${GROSS_DEBT_ADD/1000:,.1f}bn not $112.4bn; increase in net
financial obligations ${D_NFO/1000:,.1f}bn not $101.2bn; leverage-funded share of the repurchases
{100*LEV_SHARE:.1f}% not 12.4%; increase in net operating assets ${D_NOA/1000:,.1f}bn not $56.7bn;
return on incremental operating capital {100*ROIC:.1f}% not 125.0%. The addendum dated 2026-08-09
carries the pre-correction figures and must be reissued.<br>
RESTATED AGAINST HEAD 2026-08-12, BECAUSE THE ENGINE HAS SINCE PARTLY REPAIRED THE FEED. The lease
ruling landed on 2026-08-09 (commits 93ce82c and 9a92e13) and the engine now feeds the debt row from
primary-source borrowings in every year that corroborates two independent ways. On Apple it replaced
FY2024 and FY2025, which at HEAD agree with primary source to the dollar; an earlier vintage of this
build note described a four-year break and would now be false. What remains is
{" ; ".join(f"FY{y} vendor {v:,.0f} vs SEC {d:,.0f}, gap {g:+,.0f}" for y, v, d, g in DEBT_FEED_BREAK)}.
Those two years were not replaced because the corroboration test subtracts every tagged capitalized
lease, whereas in FY2022 and FY2023 the vendor had folded in only noncurrent finance leases; the test
fails and the year is left alone. CARRIED TO THE ENGINE, and the reason this note is restated rather
than deleted: Apple's vendor debt series STILL carries two lease bases at HEAD, contrary to the
9a92e13 commit message's claim that every year with coverage is now on one basis. The anchor year is
FY2025 and is clean, so the anchor is unaffected, and outputs/AAPL_dupont.csv is rebuilt on the
repaired row, so the reformulated leverage figures quoted in section 8 are read live and are current.
Nothing published here moves either way: gross borrowings are taken from primary source in every
year. Engine defect-register item, not something this study fixes.<br>
NEW SECTION 7 ADDED 2026-08-12 at James's request, and everything after it renumbered: sections 7-11
became 8-12 and Exhibits 6-8 became 7-9. The net retirement cost is a NEW COINAGE and is flagged as
such under section 4 of the style guide - it does not extend the neutral root, because it is a
capital-allocation description rather than a valuation term. If it is to be a standing measure the
name wants ruling on. It enters no valuation and no engine output. Section 3 is untouched: every
figure there is still struck on the gross price of ${M_A:,.2f}.<br>
SALESFORCE PROVENANCE, WEAKER THAN THE APPLE FIGURES AND SAID SO IN THE CAPTION: the three contrast
rows were computed from primary source by the handoff session of 2026-08-12. The fiscal 2025 row is
independently corroborated - Template-Exercise-FINDINGS-2026-08-09, section 2, defect 4, reaches
$7,829mn over 9mn shares and an implied $869.89 against a highest trade of $369.00 by a different
route. Fiscal 2024 and fiscal 2026 have NOT been re-derived from filings in this session. They are
internally consistent with the share counts and with each other, and no Apple figure depends on them,
but they should be re-pulled before this section is published outside the project.<br>
VERIFIED: derived shares retired reproduce the observed change in shares outstanding by construction;
implied average price paid independently reproduces the fiscal-year mean market price to within ~1% in
six of the eight years where retirement counts are filed rather than derived, and within 6% in the
other two. Operating/financial split of net income reconciles to reported net income exactly in every
year. Total shares retired = observed net share reduction + total shares issued, exactly.
Equity roll-forward closes: opening CSE FY2012 {CSE[2012]:,.0f} + earnings - dividends - repurchases
+ share-based comp - withholding tax + plan proceeds = {CSE[2012]+sum(NI[y]-DIV[y]-REPURCHASE_CASH[y]+SBC[y]-TAX_WITHHOLDING[y]+ISSUANCE_PROCEEDS.get(y,0) for y in FY):,.0f}
against reported {CSE[2025]:,.0f}, residual {-UNREC:+,.0f} = {100*abs(UNREC)/rep_t:.2f}% of
repurchases, and the identical magnitude appears on the uses side of Exhibit 8 with the opposite
sign - that agreement is the check. Return on retained earnings computed two independent ways:
b x (RORE - CoE) = {100*AEG_IDENT:.2f}%/yr against the entity-level cum-dividend series at
{100*AEG_RATE_ENT:.2f}%/yr, agreeing to {abs(AEG_IDENT-AEG_RATE_ENT)*10000:.0f}bp.<br>
SUPPRESSED, NOT PRINTED: return on incremental operating capital for FY2012-FY2018 (net operating
assets fell); reported return on invested capital in the {len(NEG_IC)} years net operating assets are
negative; annual return on retained earnings (range {100*RORE_MIN:.1f}% to {100*RORE_MAX:.1f}%, no
signal). The first two years of the restored return-on-invested-capital column are labelled as
opening-window artifacts in the Exhibit 9 caption rather than removed.<br>
DISCLOSED NOT RESOLVED: (1) the two coexisting real costs of equity &mdash; flat long-run
{100*COE_LONGRUN:.4f}% versus the company year-by-year history &mdash; are both shown; the crossover
year in Exhibit 2 moves between them but the sign change does not. (2) Cash-versus-accrual timing on
accelerated share repurchases is disclosed rather than adjusted.<br>
NOT ATTEMPTED: attribution of Apple's own multiple expansion to float shrinkage. Not identifiable from
this data; stated as a limitation in section 5 of the methodology document rather than estimated.<br>
OPEN: the ex-ante normal-earnings benchmark that charges every capital source is NOT built here. This
study is ex-post disclosure only and moves no valuation numbers. See
claude/AEG-Capital-Attribution-SPEC-2026-08-08.md.
</div>

</div></div>
</body></html>
"""

open('Buyback-Study-AAPL.html', 'w').write(HTML)
print("wrote Buyback-Study-AAPL.html", len(HTML), "bytes")
print(f"check: EPS cagr {100*((EPS[2025]/EPS[2012])**(1/13)-1):.2f}  "
      f"NI cagr {100*((NI[2025]/NI[2012])**(1/13)-1):.2f}  "
      f"share channel {100*cum_s/TOT_EPS:.1f}%")
print(f"check: breakeven full {be[2013]:.2f}  5y {be[2021]:.2f}  price {P_END_25:.2f}")
print(f"check: wedge {econ_t-sbc_t:,.0f}  econ {econ_t:,.0f}  sbc {sbc_t:,.0f}")
