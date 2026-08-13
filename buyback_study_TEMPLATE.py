# -*- coding: utf-8 -*-
"""
buyback_study.py - share repurchase study, any company.

Generalized from the Apple study of 2026-08-09. Companion document:
AEG-Buyback-Study-METHODOLOGY.md, which defines every measure and every guard
implemented here. Read it before changing anything in section 4.

WHAT THIS DOES
    Pulls a company's repurchase record from the SEC's XBRL company-concept
    interface, pairs it with a split-adjusted price series, and computes:
      - the true average price paid (cash divided by shares actually retired)
      - attribution of growth in earnings per share to share count vs earnings,
        and of the earnings part to operating vs financial
      - the forward real earnings yield on each year's repurchases against the
        real cost of equity
      - return on incremental operating capital, with a sign guard
      - internal rate of return on the program at three terminal valuations
      - the timing test, split into within-year execution and across-year
        allocation
      - the dilution offset and the grant-versus-delivery wedge

WHAT YOU MUST SUPPLY PER COMPANY
    A CompanyConfig. Four things are genuinely company-specific and getting any
    of them wrong will produce a study that is quietly wrong rather than one
    that fails loudly:
      cik            the SEC central index key, zero padded to ten digits
      fy_end_month   the fiscal year end month, so calendar months map to
                     fiscal years correctly
      splits         every split since the earliest year studied, so as-filed
                     share counts can be restated onto today's basis
      first_year     the first fiscal year of material repurchase activity

USAGE
    cfg = CompanyConfig(ticker="AAPL", cik="0000320193", fy_end_month=9,
                        splits=[("2014-06-09", 7), ("2020-08-31", 4)],
                        first_year=2013, last_year=2025)
    study = BuybackStudy(cfg, financials, prices, deflator, coe, engine)
    study.run()
    study.to_csv("AAPL_buyback_dataset.csv")
    print(study.report())

2026-08-12 REPAIR (defects 1-9 of Template-Exercise-FINDINGS-2026-08-09.md, closed in two
passes the same day - defects 1-5 first, then 6-9). The rule behind the repair, stated once
so it is not repeated in every docstring below: a missing input must never be silently
treated as zero, and an estimated input must always be announced.

2026-08-12, THIRD pass, prompted by picking McDonald's for the next company study: neither
a direct shares-outstanding tag nor any retirement/acquisition FLOW tag exists for a large
share of large, mature filers (McDonald's, PepsiCo, Procter & Gamble all confirmed on live
SEC data) - only shares issued and the treasury BALANCE. shares_outstanding() and
share_flows() both gained a third fallback tier for this. It is explicitly the weakest
signal of the three - a NET figure derived by differencing a balance, not a gross flow -
and is announced as such, with any year showing net reissuance (a falling balance) left
unresolved rather than approximated.
"""
from dataclasses import dataclass, field
from datetime import date
import csv
import json

SEC_CONCEPT = ("https://data.sec.gov/api/xbrl/companyconcept/"
               "CIK{cik}/us-gaap/{tag}.json")

TAGS = {
    'repurchase_cash': 'PaymentsForRepurchaseOfCommonStock',
    'repurchase_accrual': 'StockRepurchasedAndRetiredDuringPeriodValue',
    'shares_retired': 'StockRepurchasedAndRetiredDuringPeriodShares',
    'issuance_proceeds': 'ProceedsFromIssuanceOfCommonStock',
    'sbc': 'ShareBasedCompensation',
    'tax_withholding': 'PaymentsRelatedToTaxWithholdingForShareBasedCompensation',
    'shares_outstanding': 'CommonStockSharesOutstanding',
    # Companies that hold repurchased stock in treasury rather than retiring it
    # tag these instead. share_flows() tries them as a fallback (defect 1) and
    # says which tag was actually used.
    'treasury_shares_acquired': 'TreasuryStockSharesAcquired',
    'treasury_value_acquired': 'TreasuryStockValueAcquiredCostMethod',
    # 2026-08-12, second pass (McDonald's/PepsiCo/Procter & Gamble exercise):
    # the MOST common pattern among large, mature filers tags NEITHER a
    # direct shares-outstanding figure NOR any retirement/acquisition FLOW
    # at all - only shares issued and the treasury BALANCE. shares_outstanding()
    # and share_flows() both fall back to deriving from these two when the
    # tags above are absent. Some companies rename TreasuryStockShares to
    # TreasuryStockCommonShares partway through their history (McDonald's did,
    # 2024) - fetch both and merge with merge_concept_series() before passing
    # in as 'treasury_shares_balance'.
    'shares_issued': 'CommonStockSharesIssued',
    'treasury_shares_balance': 'TreasuryStockShares',
}


@dataclass
class CompanyConfig:
    ticker: str
    cik: str
    fy_end_month: int
    splits: list                  # [(iso date, ratio), ...] oldest first
    first_year: int
    last_year: int
    # The rate used for the earnings-yield comparison and the Neutral P/E. Pass
    # both if the engine carries both; the report shows the spread on each.
    coe_longrun: float = None
    inflation_for_breakeven: float = 0.025

    def split_factor(self, filed_or_priced_on):
        """Cumulative factor to put an as-filed count or quoted price on today's
        basis. Multiply share counts by it; divide prices by it."""
        d = (filed_or_priced_on if isinstance(filed_or_priced_on, str)
             else filed_or_priced_on.isoformat())
        f = 1.0
        for when, ratio in self.splits:
            if d < when:
                f *= ratio
        return f

    def fiscal_year_of(self, y, m):
        """Calendar (year, month) -> fiscal year."""
        return y + 1 if m > self.fy_end_month else y

    def fiscal_months(self, fy):
        out = []
        for m in range(self.fy_end_month + 1, 13):
            out.append((fy - 1, m))
        for m in range(1, self.fy_end_month + 1):
            out.append((fy, m))
        return out


# --------------------------------------------------------------------- SEC
def parse_concept(payload, form='10-K', full_year_only=True):
    """SEC company-concept JSON -> {fiscal_year: value}, latest filing wins.

    Deliberately keeps the FILED date alongside the value, because as-filed
    share counts sit on the split basis in force at that date and must be
    restated before use.

    DEFECT 2 FIX (2026-08-12): the unit buckets scanned used to be just
    ('USD', 'shares'). Diluted earnings per share - and any other per-share
    quantity - is filed by every registrant under 'USD/shares', which was
    never scanned, so the template returned an EMPTY series for diluted
    earnings per share on every company in existence. That silently disabled
    the earnings-per-share attribution, the multiple paid, the market
    multiple and the whole timing test. 'pure' is added alongside it because
    it is the other unitless/ratio bucket XBRL uses (e.g. dilution and
    percentage-of-class concepts) and costs nothing to include.
    """
    out = {}
    units = payload.get('units', {})
    for unit_key in ('USD', 'shares', 'USD/shares', 'pure'):
        for e in units.get(unit_key, []):
            if e.get('form') != form:
                continue
            if 'start' in e and full_year_only:
                s, d = date.fromisoformat(e['start']), date.fromisoformat(e['end'])
                if not (330 <= (d - s).days <= 400):
                    continue
            fy = e.get('fy')
            if fy is None:
                continue
            key = date.fromisoformat(e['end']).year
            prev = out.get(key)
            if prev is None or e['filed'] > prev['filed']:
                out[key] = {'val': e['val'], 'filed': e['filed'],
                            'end': e['end'], 'unit': unit_key}
    return out


def fetch_concept(cik, tag, get):
    """`get` is a callable taking a URL and returning parsed JSON. Injected so
    this module has no network dependency of its own and can be tested offline.
    The SEC requires a descriptive User-Agent header on every request."""
    return parse_concept(get(SEC_CONCEPT.format(cik=cik, tag=tag)))


def merge_concept_series(series_list, mode='update', expected_years=None,
                          label=None):
    """Combine several already-parsed concept series into one.

    DEFECT 3 FIX (2026-08-12): one tag name per quantity is not enough.
    Companies change the us-gaap tag they file a quantity under partway
    through their history (Home Depot's pretax income needed two different
    tags to cover an eighteen-year window), and some quantities are
    genuinely the sum of several tags rather than one (Home Depot's gross
    debt is LongTermDebtAndCapitalLeaseObligations plus its Current variant
    plus CommercialPaper - the single-tag version returned two years out of
    eighteen). This is the ordered-alternates mechanism the findings file
    asked for, plus the loud failure it asked for in place of a silent zero.

    series_list : ordered list of {fiscal_year: {'val':..., 'filed':...}},
        each one the output of parse_concept()/fetch_concept() for one tag.
    mode='update' : later entries in the list win on any year both cover.
        Use this when the series are ALTERNATE NAMES for the same quantity
        (a company retired one tag and adopted another). Put the tag that
        should be preferred on a year both cover LAST in the list - normally
        the newer tag, since it is the one the company is currently using.
    mode='sum'    : every series that has a given year is added together for
        that year. Use this when the quantity actually IS the sum of several
        components (e.g. total debt). A year absent from every component
        series stays absent in the sum - it is never treated as a zero
        component.
    expected_years : the fiscal years the caller actually needs. If given
        and the merged result is missing any of them, this raises ValueError
        naming exactly which years are short, rather than letting a
        thin series pass silently into a downstream ratio. Leave it None
        only for genuinely exploratory use; every production call should
        supply it.
    label : name used in the error message, so a raised failure says what
        quantity is short, not just that something is.
    """
    if mode == 'update':
        out = {}
        for s in series_list:
            out.update(s)
    elif mode == 'sum':
        years = set()
        for s in series_list:
            years |= set(s)
        out = {}
        for y in years:
            have = [s[y] for s in series_list if y in s]
            if not have:
                continue
            out[y] = {'val': sum(e['val'] for e in have),
                       'filed': max(e['filed'] for e in have)}
    else:
        raise ValueError(f"merge_concept_series: unknown mode {mode!r}")

    if expected_years is not None:
        missing = sorted(set(expected_years) - set(out))
        if missing:
            raise ValueError(
                f"{label or 'concept'}: coverage short by {len(missing)} "
                f"year(s) after merging {len(series_list)} tag(s) - missing "
                f"{', '.join('FY%d' % y for y in missing)}. A missing year "
                "must not be silently treated as zero; supply another "
                "alternate tag, or narrow the requested year range and say "
                "so in the report.")
    return out


def fetch_concept_alternates(cik, tags, get, mode='update',
                              expected_years=None, label=None):
    """fetch_concept() + merge_concept_series() in one call, for the common
    case of pulling several alternate/component tags for one quantity live."""
    series_list = [fetch_concept(cik, tag, get) for tag in tags]
    return merge_concept_series(series_list, mode=mode,
                                 expected_years=expected_years, label=label)


# --------------------------------------------------------------------- math
def irr(flows, lo=-0.95, hi=3.0, tol_iter=200):
    """flows: [(t_years, amount)]. Bisection; returns None if no sign change."""
    def npv(r):
        return sum(a / (1 + r) ** t for t, a in flows)
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(tol_iter):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def solve(f, target, lo, hi, iters=200):
    """Monotone bisection for a break-even level."""
    for _ in range(iters):
        mid = (lo + hi) / 2
        v = f(mid)
        if v is None or v < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass
class BuybackStudy:
    cfg: CompanyConfig
    fin: dict          # net_income, diluted_eps, wtd_diluted_shares, dividends,
                       # operating_income, pretax_income, tax_provision,
                       # common_equity, total_debt, financial_assets, capex, ocf
                       # each {fiscal_year: value}, dollars in millions
    sec: dict          # output of fetch_concept per key in TAGS
    prices: dict       # {(cal_year, cal_month): split-adjusted close}
    deflator: dict     # {fiscal_year: multiplier to base-year dollars}
    coe: dict          # {fiscal_year: real cost of equity, decimal}
    engine: dict = field(default_factory=dict)   # neutral_value_ps, price_real
    notes: list = field(default_factory=list)

    # ---------------------------------------------------------------- setup
    def years(self):
        return list(range(self.cfg.first_year, self.cfg.last_year + 1))

    def fy_mean_price(self, fy):
        v = [self.prices[k] for k in self.cfg.fiscal_months(fy) if k in self.prices]
        return sum(v) / len(v) if v else None

    def fy_end_price(self, fy):
        """DEFECT 8 FIX (2026-08-12): this used to assemble its own lookup
        key, (fy, self.cfg.fy_end_month), independently of fiscal_months().
        For a fiscal year end that is not squarely mid-calendar-year (Home
        Depot's real closing dates wander between late January and early
        February; September, Apple's, never straddles anything), a second,
        independently-written formula for "which calendar month is the
        fiscal year end" is a standing invitation for the two to disagree
        without anyone noticing - and it returned nothing on Home Depot's
        actual test data. There must be exactly one definition of the
        fiscal-year-end calendar month; fiscal_months() already owns it, so
        borrow its last entry instead of recomputing it here.
        """
        return self.prices.get(self.cfg.fiscal_months(fy)[-1])

    def shares_outstanding(self):
        """As-filed counts restated onto today's split basis.

        DEFECT-10-STYLE FIX (2026-08-12, second pass): falls back to
        CommonStockSharesIssued minus the treasury share balance when no
        direct CommonStockSharesOutstanding tag exists. This is not an edge
        case - McDonald's, PepsiCo and Procter & Gamble all tag it this way;
        Apple's direct tag turned out to be the less common pattern, not the
        norm.
        """
        raw = self.sec.get('shares_outstanding', {})
        if raw:
            return {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                    for y, e in raw.items()}
        issued = self.sec.get('shares_issued', {})
        treasury = self.sec.get('treasury_shares_balance', {})
        out = {}
        for y in sorted(set(issued) & set(treasury)):
            iss = issued[y]['val'] * self.cfg.split_factor(issued[y]['filed'])
            tre = treasury[y]['val'] * self.cfg.split_factor(treasury[y]['filed'])
            out[y] = (iss - tre) / 1e6
        if out and not getattr(self, '_noted_shares_outstanding_source', False):
            self.notes.append(
                "no CommonStockSharesOutstanding tagged; shares outstanding "
                "derived as CommonStockSharesIssued minus the treasury share "
                "balance instead")
            self._noted_shares_outstanding_source = True
        return out

    # ------------------------------------------------- shares retired/issued
    def share_flows(self, issue_rate_fallback=None, issue_scale=1.0,
                     early_years_for_fallback=3):
        """Shares retired and net shares issued, both in millions.

        Where the company tagged shares retired, it is used directly and net
        issuance falls out of the identity. Where it did not, DEFECT 1 FIX:
        the treasury-accounting fallback documented in TAGS is now actually
        applied here, not just commented. Where neither exists for a year,
        net issuance is estimated from the years we CAN see and shares
        retired is the residual (defect 5's fix governs how); where it
        cannot even be estimated, DEFECT 4 FIX: the year is left unresolved
        rather than defaulted to zero. See methodology section 3.
        """
        S = self.shares_outstanding()
        filed = {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                 for y, e in self.sec.get('shares_retired', {}).items()}
        retired_tag = 'StockRepurchasedAndRetiredDuringPeriodShares'

        # --------------------------------------------------------- defect 1
        if not filed:
            treas = {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                      for y, e in self.sec.get('treasury_shares_acquired', {}).items()}
            if treas:
                filed = treas
                retired_tag = 'TreasuryStockSharesAcquired'
                self.notes.append(
                    "no StockRepurchasedAndRetiredDuringPeriodShares tagged; "
                    "used the TreasuryStockSharesAcquired fallback instead "
                    "(this company holds repurchased stock in treasury "
                    "rather than retiring it)")

        # --------------------------------- second-pass fix, 2026-08-12
        # Neither a retirement flow nor an "acquired during period" flow
        # exists for a large share of large, mature filers (McDonald's,
        # PepsiCo, Procter & Gamble) - only the treasury BALANCE at each
        # period end. The year-over-year INCREASE in that balance is usable
        # as a last-resort estimate of shares retired, but it is a NET
        # figure: it equals gross shares retired only in years the company
        # did not also reissue treasury shares (for compensation, an
        # acquisition, etc.) in the same year. Where the balance DECREASES
        # year over year, net reissuance happened and the assumption breaks
        # down entirely - that year is left out here (not reported as a
        # negative retirement, not clipped to zero) and falls through to the
        # unresolved-year handling below like any other year with no usable
        # data.
        if not filed:
            treas_bal = {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                          for y, e in self.sec.get('treasury_shares_balance', {}).items()}
            if treas_bal:
                from_balance, net_reissuance_years = {}, set()
                for y in sorted(treas_bal):
                    if (y - 1) not in treas_bal:
                        continue
                    d = treas_bal[y] - treas_bal[y - 1]
                    if d >= 0:
                        from_balance[y] = d
                    else:
                        net_reissuance_years.add(y)
                if from_balance:
                    filed = from_balance
                    retired_tag = ('TreasuryStockShares (year-over-year '
                                   'change - NET, not gross)')
                    msg = ("no shares-retired or treasury-acquired FLOW "
                           "tagged; derived shares retired as the "
                           "year-over-year INCREASE in the treasury share "
                           "BALANCE instead. This is a NET figure, not a "
                           "gross repurchase count - it understates gross "
                           "repurchases in any year the company also "
                           "reissued treasury shares.")
                    if net_reissuance_years:
                        msg += (" NET REISSUANCE detected (treasury balance "
                                "fell) in " +
                                ", ".join(f"FY{y}" for y in sorted(net_reissuance_years)) +
                                " - those year(s) are left unresolved rather "
                                "than reported as a negative or zero "
                                "retirement.")
                    self.notes.append(msg)
        self.retired_tag = retired_tag

        # observed issuance rates, from the years we can see both sides
        obs = {}
        for y in self.years():
            if y in filed and y in S and (y - 1) in S:
                obs[y] = (S[y] - S[y - 1] + filed[y]) / S[y - 1]

        if issue_rate_fallback is None:
            if obs:
                # ----------------------------------------------- defect 5
                # Do not average across the whole observed window - if the
                # observed years are all recent and the rate trends (option
                # exercise activity commonly falls away over time), a plain
                # mean pulled backward has been shown to overshoot the
                # implied price by more than twenty percent. Use the rate
                # observed in the EARLIEST observable years instead, and say
                # exactly which years and how many were used, so the choice
                # is visible rather than assumed.
                n = min(early_years_for_fallback, len(obs))
                early_years = sorted(obs)[:n]
                issue_rate_fallback = sum(obs[y] for y in early_years) / n
                self.notes.append(
                    f"net issuance observable in {len(obs)} year(s); years "
                    "without a filed retirement count are held at the rate "
                    f"observed in the earliest {n} observable year(s) "
                    f"({', '.join('FY%d' % y for y in early_years)}), "
                    f"{100*issue_rate_fallback:.3f}% of opening shares - "
                    "NOT the mean of the whole observed window, which would "
                    "extrapolate a later trend backward")
            else:
                # ------------------------------------------------- defect 4
                # No year anywhere in the window has both a filed retirement
                # count and a visible share-count movement, so there is
                # nothing to estimate an issuance rate FROM. The old
                # behavior defaulted this to 0.0, which silently invents a
                # share count and, from it, a fictitious gross price for
                # every unresolved year. Refuse instead: leave
                # issue_rate_fallback unset and let the per-year loop below
                # decline to report those years rather than fabricate them.
                issue_rate_fallback = None

        retired, issued, derived, unresolved = {}, {}, set(), set()
        for y in self.years():
            if y not in S or (y - 1) not in S:
                continue
            if y in filed:
                retired[y], issued[y] = filed[y], S[y] - S[y - 1] + filed[y]
            elif issue_rate_fallback is not None:
                issued[y] = S[y - 1] * issue_rate_fallback * issue_scale
                retired[y] = S[y - 1] - S[y] + issued[y]
                derived.add(y)
            else:
                unresolved.add(y)

        self.derived_years = derived
        self.unresolved_years = unresolved
        if unresolved:
            cash_excluded = sum(
                self.sec.get('repurchase_cash', {}).get(y, {}).get('val', 0) / 1e6
                for y in unresolved)
            self.notes.append(
                "NO GROSS PRICE for " +
                ", ".join(f"FY{y}" for y in sorted(unresolved)) +
                f" (${cash_excluded:,.0f}m of repurchase cash spent in "
                "these years) - no filed retirement count and no "
                "observable issuance rate anywhere in the window to "
                "estimate one. A share count and a price were not "
                "invented for them. Excluded from the average price paid, "
                "the multiple paid, the timing test and the compensation "
                "wedge; the cash itself is still a fact and is reported "
                "separately above.")
        return retired, issued

    def validate_prices(self, retired, traded_range=None):
        """Every implied average price paid must be a price that existed.

        traded_range: {fy: (intra-period low, high)} on today's split basis. Use
        intra-period extremes, NOT the range of period-end closes - month-end
        closes alone produce false failures.
        """
        fails = []
        for y, q in retired.items():
            cash = self.sec['repurchase_cash'].get(y, {}).get('val')
            if not cash or not q:
                continue
            px = cash / 1e6 / q
            if traded_range and y in traded_range:
                lo, hi = traded_range[y]
            else:
                v = [self.prices[k] for k in self.cfg.fiscal_months(y)
                     if k in self.prices]
                lo, hi = min(v), max(v)
                self.notes.append(f"FY{y} validated against period-end closes "
                                  f"only; intra-period extremes are stricter")
            if not (lo <= px <= hi):
                fails.append((y, px, lo, hi))
        return fails

    # ---------------------------------------------------------- attribution
    def eps_attribution(self):
        f, S = self.fin, self.fin['wtd_diluted_shares']
        NI, EPS = f['net_income'], f['diluted_eps']
        oi, nfi = {}, {}
        for y in list(S):
            if y in f['pretax_income'] and f['pretax_income'][y]:
                t = f['tax_provision'][y] / f['pretax_income'][y]
                oi[y] = f['operating_income'][y] * (1 - t)
                nfi[y] = (f['pretax_income'][y] - f['operating_income'][y]) * (1 - t)
        rows = {}
        for y in self.years():
            if (y - 1) not in S:
                continue
            rows[y] = {
                'from_earnings': (NI[y] - NI[y - 1]) / S[y],
                'from_share_count': EPS[y - 1] * (S[y - 1] / S[y] - 1),
                'operating': (oi[y] - oi[y - 1]) / S[y],
                'financial': (nfi[y] - nfi[y - 1]) / S[y],
            }
        self._oi = oi
        return rows

    def return_on_incremental_capital(self, windows, min_relative_change=0.05):
        """Sign-and-magnitude-guarded. A negative change in net operating
        assets makes the ratio meaningless, so the fact is reported instead
        of a number.

        DEFECT 6 FIX (2026-08-12): the guard used to test only the SIGN of
        the change in net operating assets. A change that is positive but
        trivially small relative to the opening capital base produces a
        ratio just as meaningless as a negative one - more so, because
        nothing about a positive-but-tiny denominator looks wrong at a
        glance. Home Depot's fiscal 2013-2019 window moved net operating
        assets by -2.0% of the opening base and was (correctly) suppressed
        on sign; had the same window drifted +2.0% instead, the unguarded
        code printed a return on the order of two thousand percent with no
        warning at all. `min_relative_change` (default 5% of the opening
        base) is the threshold below which the ratio is suppressed
        regardless of sign; state a different value explicitly if 5% is not
        the right materiality bar for a given company's capital base.
        """
        f = self.fin
        noa = {y: f['common_equity'][y] + (f['total_debt'].get(y) or 0)
               - f['financial_assets'][y]
               for y in f['common_equity'] if y in f['financial_assets']}
        out = {}
        for a, b in windows:
            if a not in noa or b not in noa or a not in self._oi:
                continue
            d_noa, d_oi = noa[b] - noa[a], self._oi[b] - self._oi[a]
            base = abs(noa[a])
            rel = (d_noa / base) if base else None
            too_small = rel is None or abs(rel) < min_relative_change
            if d_noa <= 0 or too_small:
                if d_noa <= 0:
                    why = ('net operating assets did not increase; the '
                           'ratio has no meaning')
                else:
                    why = (f'net operating assets moved by only '
                           f'{100*rel:.1f}% of the opening capital base '
                           f'({base:,.0f}) - a ratio computed on a '
                           'denominator this small relative to the base is '
                           'not meaningful even though its sign is positive')
                out[(a, b)] = {'suppressed': True, 'd_noa': d_noa, 'd_oi': d_oi,
                               'why': why}
            else:
                t0 = f['tax_provision'][a] / f['pretax_income'][a]
                d_oi_ct = (f['operating_income'][b] - f['operating_income'][a]) * (1 - t0)
                out[(a, b)] = {'suppressed': False, 'd_noa': d_noa, 'd_oi': d_oi,
                               'ratio': d_oi / d_noa,
                               'ratio_constant_tax': d_oi_ct / d_noa}
        self._noa = noa
        return out

    # ----------------------------------------------------------------- IRR
    def program_flows(self, y0, retired, terminal_ps, deflate=False):
        f, flows, held = self.fin, [], 0.0
        for y in range(y0, self.cfg.last_year + 1):
            k = self.deflator[y] if deflate else 1.0
            cash = self.sec['repurchase_cash'].get(y, {}).get('val', 0) / 1e6
            flows.append((y - y0 + 0.5, -cash * k))
            if held > 0:
                dps = f['dividends'][y] / f['wtd_diluted_shares'][y]
                flows.append((y - y0 + 0.5, held * dps * k))
            held += retired.get(y, 0.0)
        kt = self.deflator[self.cfg.last_year] if deflate else 1.0
        flows.append((self.cfg.last_year - y0 + 1.0, held * terminal_ps * kt))
        return flows, held

    def irrs(self, y0, retired, terminals):
        return {name: irr(self.program_flows(y0, retired, tv, d)[0])
                for name, (tv, d) in terminals.items()}

    def break_even(self, y0, retired, hurdle):
        return solve(lambda p: irr(self.program_flows(y0, retired, p)[0]),
                     hurdle, 0.01, 10000.0)

    # -------------------------------------------------------------- timing
    def timing(self, retired):
        ys = [y for y in self.years() if y in retired and retired[y]]
        cash = {y: self.sec['repurchase_cash'][y]['val'] / 1e6 for y in ys}
        eps = self.fin['diluted_eps']
        pe_paid = {y: (cash[y] / retired[y]) / eps[y] for y in ys}
        pe_mkt = {y: self.fy_mean_price(y) / eps[y] for y in ys}
        tot = sum(cash.values())
        dw = sum(cash[y] * pe_paid[y] for y in ys) / tot
        ew = sum(pe_paid.values()) / len(ys)
        mk = sum(pe_mkt.values()) / len(ys)
        return {'dollar_weighted_pe_paid': dw, 'equal_weighted_pe_paid': ew,
                'market_pe': mk,
                'execution_within_year': ew / mk - 1,
                'allocation_across_years': dw / ew - 1,
                'combined': dw / mk - 1,
                'pe_paid': pe_paid, 'pe_market': pe_mkt}

    # ------------------------------------------------- compensation wedge
    def comp_wedge(self, issued):
        # Years with no resolved issuance (defect 4) must not fall back to
        # a silent zero here either - the market value of shares delivered
        # in those years is genuinely unknown, not nil.
        unresolved = getattr(self, 'unresolved_years', set())
        ys = [y for y in self.years() if y not in unresolved]
        g = lambda k, y: self.sec.get(k, {}).get(y, {}).get('val', 0) / 1e6

        # DEFECT 7 FIX (2026-08-12): `g()` substitutes 0 for any year/tag
        # combination that is absent, which is correct when a company files
        # a genuine zero for a year and wrong when the company does not tag
        # the concept AT ALL - those are different facts and the old code
        # could not tell them apart. Home Depot does not tag
        # PaymentsRelatedToTaxWithholdingForShareBasedCompensation in any
        # year; the wedge came out at -$178m against a $4,622m accounting
        # charge with nothing to say a whole component was missing (on
        # Apple, which does tag it, that line was $45.8bn - a study can be
        # understated by tens of billions with no visible warning). Detect
        # "tag absent entirely" per component and report it explicitly.
        component_tags = (('tax_withholding',
                            'PaymentsRelatedToTaxWithholdingForShareBasedCompensation'),
                           ('issuance_proceeds', 'ProceedsFromIssuanceOfCommonStock'),
                           ('sbc', 'ShareBasedCompensation'))
        missing_components = [label for key, label in component_tags
                               if not self.sec.get(key)]

        delivered = sum(issued.get(y, 0) * self.fy_mean_price(y) for y in ys)
        tax = sum(g('tax_withholding', y) for y in ys)
        proceeds = sum(g('issuance_proceeds', y) for y in ys)
        sbc = sum(g('sbc', y) for y in ys)
        econ = delivered + tax - proceeds
        caveat = ('cumulative only; single years compare unrelated award '
                  'cohorts')
        if unresolved:
            caveat += (f'; excludes {len(unresolved)} unresolved year(s) '
                       'with no determinable issuance')
        if missing_components:
            caveat += ('; MISSING COMPONENT(S) treated as $0 because this '
                       'company does not tag them at all (not because the '
                       'amount is genuinely zero): ' +
                       ', '.join(missing_components))
        return {'market_value_delivered': delivered, 'withholding_tax': tax,
                'employee_proceeds': proceeds, 'economic_cost': econ,
                'accounting_charge': sbc, 'wedge': econ - sbc,
                'multiple': (econ / sbc) if sbc else None,
                'missing_components': missing_components,
                'caveat': caveat}

    # ----------------------------------------------------------------- run
    def run(self, traded_range=None):
        self.retired, self.issued = self.share_flows()
        self.price_failures = self.validate_prices(self.retired, traded_range)
        if self.price_failures:
            self.notes.append(
                "IMPLIED PRICE OUTSIDE TRADED RANGE in " +
                ", ".join(f"FY{y}" for y, *_ in self.price_failures) +
                " - do not publish until resolved")
        self.attribution = self.eps_attribution()
        self.timing_result = self.timing(self.retired)
        self.wedge = self.comp_wedge(self.issued)
        if self.wedge.get('missing_components'):
            self.notes.append(
                "COMPENSATION WEDGE MISSING COMPONENT(S): " +
                ", ".join(self.wedge['missing_components']) +
                " - this company does not tag them at all, they are NOT "
                "genuinely zero, and the wedge above is understated by an "
                "unknown amount")
        return self

    def to_csv(self, path):
        S = self.shares_outstanding()
        rows = []
        for y in self.years():
            if y not in self.retired:
                continue
            cash = self.sec['repurchase_cash'][y]['val'] / 1e6
            px = cash / self.retired[y]
            rows.append({
                'fiscal_year': y,
                'shares_retired_source': 'derived' if y in self.derived_years else 'filed',
                'shares_retired_tag': getattr(self, 'retired_tag', ''),
                'repurchase_cash_usdm': round(cash, 1),
                'shares_retired_mn': round(self.retired[y], 1),
                'shares_issued_mn': round(self.issued[y], 1),
                'shares_outstanding_fye_mn': round(S[y], 1),
                'pct_shares_retired': round(100 * self.retired[y] / S[y - 1], 3),
                'net_share_change_pct': round(100 * (S[y] / S[y - 1] - 1), 3),
                'avg_price_paid': round(px, 2),
                'fy_mean_market_price': round(self.fy_mean_price(y), 2),
                'pe_paid': round(self.timing_result['pe_paid'][y], 2),
                'market_pe': round(self.timing_result['pe_market'][y], 2),
                'real_cost_of_equity_pct': round(100 * self.coe[y], 2)
                if y in self.coe else '',
            })
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        return path

    def report(self, dilution_absorption_threshold=0.80):
        t, w = self.timing_result, self.wedge
        L = [f"{self.cfg.ticker}  FY{self.cfg.first_year}-FY{self.cfg.last_year}",
             "-" * 64]
        # Cash and shares must share the same basis (defect 4): years with
        # no resolved shares-retired count are excluded from BOTH sides of
        # the average price paid, not just the share side.
        tot_cash = sum(self.sec['repurchase_cash'][y]['val'] / 1e6
                       for y in self.retired if y in self.sec['repurchase_cash'])
        tot_q = sum(self.retired.values())

        # DEFECT 9 FIX (2026-08-12): the offset used to print as a bare
        # percentage no matter how large. The methodology is explicit that
        # once issuance is running close to or above the pace of
        # repurchases, describing the program as a "repurchase program" at
        # all is the wrong description - it is dilution absorption, or (at
        # or above 100%) net issuance dressed up as a buyback. State that in
        # words, not just leave the reader to interpret a number.
        offset = sum(self.issued.values()) / tot_q
        if offset >= 1.0:
            offset_desc = ("NOT A REPURCHASE PROGRAM - issuance meets or "
                           "exceeds shares retired; this is net dilution "
                           "absorption, not a return of capital")
        elif offset >= dilution_absorption_threshold:
            offset_desc = ("primarily dilution absorption, not a return of "
                           "capital")
        else:
            offset_desc = "of shares retired"

        L += [f"cash spent            {tot_cash:14,.0f}",
              f"shares retired        {tot_q:14,.0f} mn",
              f"dollar-wtd price paid {tot_cash/tot_q:14,.2f}",
              f"dollar-wtd P/E paid   {t['dollar_weighted_pe_paid']:14.2f}",
              "",
              f"execution within year {100*t['execution_within_year']:+13.1f}%",
              f"allocation across yrs {100*t['allocation_across_years']:+13.1f}%",
              "",
              f"dilution offset       {100*offset:13.1f}%  {offset_desc}",
              f"comp economic cost    {w['economic_cost']:14,.0f}",
              f"comp accounting chg   {w['accounting_charge']:14,.0f}",
              f"wedge                 {w['wedge']:14,.0f}  ({w['multiple']:.2f}x)"]
        if offset >= dilution_absorption_threshold:
            L += ["", f"*** DILUTION OFFSET {100*offset:.1f}% >= "
                      f"{100*dilution_absorption_threshold:.0f}% - {offset_desc.upper()} ***"]
        if self.notes:
            L += ["", "NOTES"] + [f"  - {n}" for n in self.notes]
        if self.price_failures:
            L += ["", "*** VALIDATION FAILED - see notes ***"]
        return "\n".join(L)


if __name__ == '__main__':
    print(__doc__)
