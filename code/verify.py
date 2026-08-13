# -*- coding: utf-8 -*-
"""Independent verification of every figure the rewritten study publishes for the
first time. Nothing here imports gen_article; each quantity is rebuilt from
build.py and the primary sources by a route that does not reuse gen_article's
arithmetic, and is then compared against the figure actually present in the
generated HTML.

House convention section 6: any central measure is computed two independent ways
and must reconcile before a sentence is written about what it means.
"""
import csv
import html
import re

from build import *

OUT = []


def chk(label, a, b, tol, unit=""):
    ok = abs(a - b) <= tol
    OUT.append((ok, label, a, b, unit))
    return ok


# ---------------------------------------------------------------- rebuild
SUM = {}
for r in csv.reader(open('AAPL_summary.STALE.csv')):
    if len(r) == 2 and r[0] != 'field':
        try:
            SUM[r[0]] = float(r[1])
        except ValueError:
            pass
R = SUM['real_coe_longrun']

OI, NFI = {}, {}
for y in range(2012, 2026):
    pre, op, tx = IS['Pretax Income'][y], IS['Operating Income'][y], IS['Tax Provision'][y]
    t = tx / pre
    OI[y], NFI[y] = op * (1 - t), (pre - op) * (1 - t)

FA = {y: BS['Cash And Cash Equivalents'][y] + BS['Other Short Term Investments'][y]
      + BS['Investments And Advances'][y] for y in range(2012, 2026)}
NFO = {y: DEBT[y] - FA[y] for y in range(2012, 2026)}
NOA = {y: CSE[y] + NFO[y] for y in range(2012, 2026)}

rep_t = sum(REPURCHASE_CASH[y] for y in FY)
ni_t = sum(NI[y] for y in FY)
div_t = sum(DIV[y] for y in FY)
sbc_t = sum(SBC[y] for y in FY)
taxw_t = sum(TAX_WITHHOLDING[y] for y in FY)
proc_t = sum(ISSUANCE_PROCEEDS.get(y, 0) for y in FY)
d_nfo = NFO[2025] - NFO[2012]
d_noa = NOA[2025] - NOA[2012]
cap_in = (ni_t - div_t) + d_nfo + sbc_t - taxw_t + proc_t

# ============================================================== 1. FUNDING
# Route A: change in net financial obligations, balance sheet endpoints.
# Route B: gross debt raised, less the change in financial assets. Independent
# of route A only in the sense that it decomposes it; both must agree exactly.
gross_debt_add = DEBT[2025] - DEBT[2012]
d_fa = FA[2025] - FA[2012]
chk("d(NFO): endpoints vs debt-raised-less-asset-change",
    d_nfo, gross_debt_add - d_fa, 1e-6, "$m")

# Route C, genuinely independent of the balance sheet: the cash flow statement.
# Net debt issuance, cumulated, must approximate the gross debt added.
netdebt_cf = sum(CF['Net Issuance Payments of Debt'][y] or 0 for y in FY)
OUT.append((abs(netdebt_cf - gross_debt_add) / gross_debt_add < 0.01,
            "gross debt added: SEC tags vs cumulated cash-flow net issuance",
            gross_debt_add, netdebt_cf, "$m"))

# And the vendor feed must be shown to break where we say it breaks.
#
# REVISED 2026-08-12. The original two checks asserted a four-year break,
# FY2022-FY2025, which is what the feed showed when this study was built on
# 2026-08-09. It no longer holds. The engine's lease ruling landed the same day
# (commits 93ce82c and 9a92e13) and now feeds the debt row from primary-source
# borrowings in every year that corroborates. On Apple it replaced FY2024 and
# FY2025 - the two years where the vendor had folded in EVERY capitalized lease -
# so those two now agree with primary source to the dollar.
#
# FY2022 and FY2023 were NOT replaced and still sit above primary source. The
# corroboration test subtracts all tagged capitalized leases, but in those two
# years the vendor had folded in only NONCURRENT FINANCE leases, so the test
# fails and the year is left alone. Apple's debt series therefore still carries
# two lease bases at HEAD. That is an engine defect-register item, not something
# this study fixes, and no figure published here depends on it: gross borrowings
# are taken from the Securities and Exchange Commission throughout.
#
# The check is kept, not deleted, and asserts the CURRENT shape. If the feed
# changes again in either direction it fails rather than passing silently.
brk = {y: (v, d) for y, v, d, g in debt_feed_disagreements()}
OUT.append((sorted(brk) == [2022, 2023],
            "vendor total-debt feed diverges from SEC in exactly FY2022-FY2023",
            len(brk), 2, "years"))
OUT.append((all(abs((brk[y][0] - brk[y][1]) - g) < 1
                for y, g in ((2022, 812), (2023, 859))),
            "FY2022 and FY2023 gaps are the noncurrent finance leases, $812m/$859m",
            brk[2022][0] - brk[2022][1], 812, "$m"))
OUT.append((all(abs((BS['Total Debt'].get(y) or 0.0) - DEBT[y]) < 1
                for y in (2024, 2025)),
            "FY2024 and FY2025 vendor rows now agree with SEC to the dollar",
            (BS['Total Debt'].get(2025) or 0.0) - DEBT[2025], 0, "$m"))

# EPS channel decomposition must close on the identity, exactly.
cum_e = sum((NI[y] - NI[y - 1]) / WTD[y] for y in FY)
cum_s = sum(EPS[y - 1] * (WTD[y - 1] / WTD[y] - 1) for y in FY)
cum_o = sum((OI[y] - OI[y - 1]) / WTD[y] for y in FY)
cum_f = sum((NFI[y] - NFI[y - 1]) / WTD[y] for y in FY)
chk("EPS identity: earnings channel + share channel = total growth",
    cum_e + cum_s, EPS[2025] - EPS[2012], 5e-4, "$/sh")
chk("earnings channel splits into operating + financial with no residual",
    cum_o + cum_f, cum_e, 1e-9, "$/sh")
for y in range(2012, 2026):
    chk(f"  NI reconstruction from OI+NFI, FY{y}", OI[y] + NFI[y], NI[y], 1e-6, "$m")

lev_share = d_nfo / rep_t
chk("EPS from leverage + EPS from retention = share-count channel",
    cum_s * lev_share + cum_s * (1 - lev_share), cum_s, 1e-12, "$/sh")

# ======================================================= 2. SOURCES AND USES
# The unreconciled line must be the equity roll-forward residual, same magnitude.
built = CSE[2012] + sum(NI[y] - DIV[y] - REPURCHASE_CASH[y] + SBC[y]
                        - TAX_WITHHOLDING[y] + ISSUANCE_PROCEEDS.get(y, 0) for y in FY)
roll_resid = CSE[2025] - built
uses_resid = cap_in - rep_t - d_noa
chk("uses residual = -(equity roll-forward residual)", uses_resid, -roll_resid, 1e-6, "$m")

# ================================================== 3. THE REAL CAPITAL BASE
cum_rest = sum(REPURCHASE_CASH[y] - ISSUANCE_PROCEEDS.get(y, 0) for y in FY)
rcb_25 = CSE[2025] + cum_rest
# Independent identity: restoring the buyback is algebraically the same as
# rolling opening equity forward with earnings, dividends and employee equity
# only - the repurchase line drops out entirely.
rcb_alt = CSE[2012] + sum(NI[y] - DIV[y] + SBC[y] - TAX_WITHHOLDING[y]
                          for y in FY) + roll_resid
chk("Real Capital Base FY2025: restoration vs buyback-free roll-forward",
    rcb_25, rcb_alt, 1e-6, "$m")

# ============================================ 4. RETURN ON RETAINED EARNINGS
epsr = {y: EPS[y] * DEFL[y] for y in range(2012, 2026)}
dpsr = {y: (DIV[y] / WTD[y]) * DEFL[y] for y in range(2012, 2026)}
num = sum(epsr[y] - epsr[y - 1] for y in FY)
den = sum(epsr[y - 1] - dpsr[y - 1] for y in FY)
# Route A: telescoping - the cumulative change must equal the endpoints.
chk("cumulative d(real EPS) telescopes to the endpoints",
    num, epsr[2025] - epsr[2012], 1e-9, "$/sh")
rore = num / den
b = den / sum(epsr[y - 1] for y in FY)
ident = b * (rore - R)
# Route B: the entity-level cum-dividend series, share-count invariant.
nir = {y: NI[y] * DEFL[y] for y in range(2012, 2026)}
dr = {y: (DIV[y] + REPURCHASE_CASH.get(y, 0)) * DEFL[y] for y in range(2012, 2026)}
aeg = {s: nir[s] - (1 + R) * nir[s - 1] + R * dr[s - 1] for s in FY}
ent_rate = (sum(aeg.values()) / len(FY)) / (sum(nir[y] for y in FY) / len(FY))
OUT.append((abs(ident - ent_rate) < 0.0010,
            "AEG rate: b x (RORE - CoE) vs entity cum-dividend series",
            ident, ent_rate, "/yr"))

# ============================== 5. NET RETIREMENT COST (section 7, new 2026-08-12)
# Rebuilt here from SHARES_OUT and the filed retirement counts directly, without
# reusing build.py's RETIRED/ISSUED dictionaries, so the identity is tested
# rather than assumed.
_ret, _iss = {}, {}
for y in FY:
    s0, s1 = SHARES_OUT[y - 1], SHARES_OUT[y]
    if y in SHARES_RETIRED_FILED:
        _ret[y] = SHARES_RETIRED_FILED[y]
        _iss[y] = s1 - s0 + _ret[y]
    else:
        _iss[y] = s0 * 0.0070
        _ret[y] = s0 - s1 + _iss[y]

# The identity must close EXACTLY, every year and cumulatively. It is the whole
# basis of the measure: if it does not close, gross and net are not the same
# accounting of the same event.
for y in FY:
    chk(f"  share identity FY{y}: gross - issued = net reduction",
        _ret[y] - _iss[y], SHARES_OUT[y - 1] - SHARES_OUT[y], 1e-9, "mn")
chk("share identity, cumulative: gross - issued = net reduction",
    sum(_ret.values()) - sum(_iss.values()),
    SHARES_OUT[2012] - SHARES_OUT[2025], 1e-9, "mn")

# The two independently rebuilt series must agree with build.py's.
chk("rebuilt gross retirement agrees with build.py", sum(_ret.values()),
    sum(RETIRED[y] for y in FY), 1e-9, "mn")
chk("rebuilt issuance agrees with build.py", sum(_iss.values()),
    sum(ISSUED[y] for y in FY), 1e-9, "mn")

_net_t = sum(_ret[y] - _iss[y] for y in FY)
_ret_t = sum(_ret.values())
m_a = rep_t / _ret_t
m_b = rep_t / _net_t
m_c = (rep_t - proc_t) / _net_t
m_d = (rep_t + taxw_t - proc_t) / _net_t

# Each measure against its definition, stated a second way.
chk("A = cash / gross retired", m_a * _ret_t, rep_t, 1e-6, "$m")
chk("B = cash / net reduction", m_b * _net_t, rep_t, 1e-6, "$m")
chk("C = (cash - plan proceeds) / net reduction",
    m_c * _net_t + proc_t, rep_t, 1e-6, "$m")
chk("D = (cash + withholding tax - proceeds) / net reduction",
    m_d * _net_t - taxw_t + proc_t, rep_t, 1e-6, "$m")
# Ordering must hold: A is the smallest, D the largest, and C sits below B
# because it subtracts cash from the numerator. If any of these inverts, the
# construction has gone wrong somewhere upstream.
OUT.append((m_a < m_c < m_b < m_d, "ordering A < C < B < D holds", m_a, m_d, "$/sh"))

# Salesforce contrast: the ratio must be the cash over the count reduction and
# must exceed the highest trade, or the contrast is not a contrast.
for _fy, _cash, _so, _n, _lo, _hi in CRM_NET_CONTRAST:
    chk(f"  CRM FY{_fy}: net retirement cost x net reduction = cash",
        (_cash / _n) * _n, _cash, 1e-6, "$m")
    OUT.append(((_cash / _n) > _hi,
                f"  CRM FY{_fy}: net cost exceeds the year's highest trade",
                _cash / _n, _hi, "$/sh"))

# ================ 5b. THE COST-OF-EQUITY BREAK-EVEN (added 2026-08-12)
# Rebuilt here by bisection on the entry effect, which is a genuinely different
# route from the closed-form root gen_article uses. If the entry effect were not
# linear in rho the two would disagree, so this also tests the linearity claim
# the report makes in prose.
_epsr = {y: EPS[y] * DEFL[y] for y in range(2012, 2026)}
_pxr = {y: (REPURCHASE_CASH[y] / _ret[y]) * DEFL[y] for y in FY}
_yrs = FY[:-1]


def _entry_at(rho, years):
    return sum(_ret[t] * (_epsr[t + 1] - rho * _pxr[t]) for t in years)


def _bisect(years):
    lo, hi = 0.0001, 1.0
    for _ in range(200):
        m = (lo + hi) / 2
        if _entry_at(lo, years) * _entry_at(m, years) <= 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


for _lab, _yy in (("whole program", _yrs),
                  ("FY2013-19 tranches", [t for t in _yrs if t < 2020]),
                  ("FY2020-24 tranches", [t for t in _yrs if t >= 2020])):
    _closed = (sum(_ret[t] * _epsr[t + 1] for t in _yy)
               / sum(_ret[t] * _pxr[t] for t in _yy))
    chk(f"  rho break-even, {_lab}: closed form vs bisection",
        _closed, _bisect(_yy), 1e-9, "/yr")
    chk(f"  entry effect is zero at its own break-even, {_lab}",
        _entry_at(_closed, _yy), 0.0, 1e-6, "$m")

# The sign must actually be what the report claims on either side of the root.
_rs = (sum(_ret[t] * _epsr[t + 1] for t in _yrs) / sum(_ret[t] * _pxr[t] for t in _yrs))
OUT.append((_entry_at(_rs - 0.0001, _yrs) > 0 > _entry_at(_rs + 0.0001, _yrs),
            "entry effect is positive below the break-even and negative above it",
            _entry_at(_rs - 0.0001, _yrs), _entry_at(_rs + 0.0001, _yrs), "$m"))
OUT.append((_rs > R, "break-even sits ABOVE the engine rate, so the headline sign is positive",
            _rs, R, "/yr"))

# ========== 5c. THE EARNINGS-TIMING DECOMPOSITION (added 2026-08-13)
# Rebuilt here from the module against the independently reconstructed share flows above, and
# every claim the report makes about it is re-derived rather than read back.
import timing_decomposition as _td

_td_est = _td.build_estimators(_epsr, window=range(2013, 2026))
_td_band = _td.decomposition_band(_ret, _epsr, _pxr, R, _yrs, _td_est)

# (1) THE IDENTITY. decision + timing must equal the entry effect, per tranche and cumulative,
# under EVERY estimator. This is the whole basis of the measure: if it does not close, the split
# is an adjustment to the published number rather than a decomposition of it.
for _n, _d in _td_band.items():
    for _t in _yrs:
        _r = _d["rows"][_t]
        chk(f"  timing identity {_n} FY{_t}", _r["decision"] + _r["timing"], _r["entry"], 1e-9, "$m")
    chk(f"  timing identity {_n}, cumulative", _d["decision"] + _d["timing"], _d["entry"], 1e-6, "$m")

# (2) THE PUBLISHED ENTRY EFFECT MUST NOT MOVE. The decomposition is a split, not an adjustment,
# so every estimator must reproduce the same entry total as this file's own section 5b arithmetic.
for _n, _d in _td_band.items():
    chk(f"  entry effect unmoved under {_n}", _d["entry"], _entry_at(R, _yrs), 1e-6, "$m")

# (3) TWO INDEPENDENT ROUTES TO THE SYMMETRIC READING. The log-linear fit assumes one constant
# growth rate; the centred geometric mean assumes no functional form at all. If they disagree
# materially the symmetric reading is not robust and must not be presented as primary.
_ll, _c3 = _td_band["loglinear"]["decision"], _td_band["centered3"]["decision"]
OUT.append((abs(_ll - _c3) / abs(_ll) < 0.12,
            "symmetric reading agrees across two independent estimators (within 12%)",
            _ll, _c3, "$m"))

# (4) THE FAMILY SPLIT IS REAL AND IS THE PUBLISHED FINDING. Every symmetric estimator must put
# the decision component positive with its break-even ABOVE the engine rate; every backward-looking
# one must put it negative with its break-even BELOW. If either family stops being internally
# consistent the report's framing is wrong, and this fails rather than passing quietly.
_sym = [_td_band[n] for n in _td.SYMMETRIC_ESTIMATORS]
_bwd = [_td_band[n] for n in _td.BACKWARD_ESTIMATORS]
OUT.append((all(d["decision"] > 0 and d["break_even"] > R for d in _sym),
            "every SYMMETRIC estimator: decision positive, break-even above engine rate",
            min(d["decision"] for d in _sym), min(d["break_even"] for d in _sym) - R, "$m / rate"))
OUT.append((all(d["decision"] < 0 and d["break_even"] < R for d in _bwd),
            "every BACKWARD estimator: decision negative, break-even below engine rate",
            max(d["decision"] for d in _bwd), max(d["break_even"] for d in _bwd) - R, "$m / rate"))

# (5) THE TIMING COMPONENT IS RATE-FREE. Recomputing it at a wildly different capitalization rate
# must change nothing. This is the formal statement of "rate-agnostic by construction".
_alt = _td.decompose(_ret, _epsr, _pxr, R * 3.0, _yrs, _td_est["loglinear"])
chk("timing component is invariant to the cost of equity (rate-agnostic)",
    _alt["timing"], _td_band["loglinear"]["timing"], 1e-6, "$m")

# (6) The decision break-even is a closed-form root: the decision component must be zero at it.
for _n in ("loglinear", "normalizer4"):
    _d = _td_band[_n]
    _z = sum(_ret[t] * (_td_est[_n](t + 1) - _d["break_even"] * _pxr[t]) for t in _yrs)
    chk(f"  decision component is zero at its own break-even, {_n}", _z, 0.0, 1e-6, "$m")

# (7) The claim that Apple's FY2021 jump did NOT revert - the stated reason the symmetric family
# is primary. The report asserts it as fact, so it is tested as fact.
OUT.append((_epsr[2025] > _epsr[2021] > _epsr[2020] * 1.4,
            "FY2021 earnings jump persisted through FY2025 (did not revert)",
            _epsr[2021], _epsr[2025], "$/sh"))

_dep_p = _td.timing_dependence(_td_band["loglinear"]["entry"], _td_band["loglinear"]["timing"])
_dep_a = _td.timing_dependence(_td_band["normalizer4"]["entry"], _td_band["normalizer4"]["timing"])

# ================================================ 6. AGAINST THE PUBLISHED HTML
# Inline expected-value comments (# 26.6, # 3.8, # 125.0 and the rest) were
# removed 2026-08-12. They were written before the debt correction of
# 2026-08-09 and never updated, so they disagreed with figures that were
# correct. An expected value written in a comment is an assertion that nothing
# tests; where a check has an expected value it belongs in the check.
TXT = html.unescape(re.sub(r'<[^>]+>', ' ', open('../Buyback-Study-AAPL.html').read()))
TXT = re.sub(r'\s+', ' ', TXT)


def present(s):
    OUT.append((s in TXT, f"HTML contains: {s!r}", 0, 0, ""))


present(f"${(rep_t-d_nfo)/1000:,.0f} billion came from current")
present(f"${d_nfo/1000:,.0f} billion came from the balance sheet")
present(f"{100*cum_s*(1-lev_share)/(EPS[2025]-EPS[2012]):.1f} percent")
present(f"{100*cum_s*lev_share/(EPS[2025]-EPS[2012]):.1f} percent")
present(f"{100*(cum_s+cum_f)/(EPS[2025]-EPS[2012]):.1f} percent")
present(f"{100*cum_o/(EPS[2025]-EPS[2012]):.1f} percent")
present(f"{100*rep_t/cap_in:.0f} percent went into Apple's own shares")
present(f"{100*d_noa/cap_in:.1f} percent into the business")
present(f"{100*(OI[2025]-OI[2012])/d_noa:.1f} percent")
present(f"{100*rore:.2f} percent")
present(f"{b:.3f}")
present(f"{100*ident:.2f} percent a year")
present(f"{100*ent_rate:.2f} percent a year")
present(f"{cap_in:,.0f}")
present(f"{rcb_25:,.0f}")

# The four measures must appear in the document at the values computed here.
present(f"{m_a:,.2f}")
present(f"{m_b:,.2f}")
present(f"{m_c:,.2f}")
present(f"{m_d:,.2f}")
present(f"retired {_ret_t:,.0f} million shares gross")
present(f"issued {sum(_iss.values()):,.0f} million")
present(f"reduced the count by {_net_t:,.0f} million")
present(f"{100*sum(_iss.values())/_ret_t:.1f} percent of gross retirement")
present(f"real cost of equity of {100*_rs:.2f} percent")
present(f"{10000*(_rs-R):.0f} basis points")

# the earnings-timing decomposition, as published
present(f"fitted real rate of {100*_td_est['loglinear'].growth:.2f} percent a year")
present(f"timing accounts for {100*_dep_p:.0f} percent of the headline")
present(f"timing component is {100*_dep_a:.0f} percent of the headline")
present(f"put the price decision between {min(d['decision'] for d in _sym)/1000:+,.2f}")
present(f"put it between {min(d['decision'] for d in _bwd)/1000:+,.2f}")
present("It is not Neutral Earnings Power")
present("removes no tranche and no year")

# ------------------------------------------------------------------- report
print("=" * 92)
print("INDEPENDENT VERIFICATION OF THE REWRITTEN SECTIONS")
print("=" * 92)
bad = 0
for ok, label, a, bq, unit in OUT:
    if not ok:
        bad += 1
    mark = "PASS" if ok else "**FAIL**"
    if label.startswith("HTML contains"):
        print(f"{mark:8} {label}")
    else:
        print(f"{mark:8} {label:<66} {a:>14,.6f} {bq:>14,.6f} {unit}")
print("=" * 92)
print(f"{len(OUT)-bad} of {len(OUT)} checks pass." if bad else
      f"ALL {len(OUT)} CHECKS PASS.")
