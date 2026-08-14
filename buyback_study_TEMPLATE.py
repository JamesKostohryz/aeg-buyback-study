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

import timing_decomposition

SEC_CONCEPT = ("https://data.sec.gov/api/xbrl/companyconcept/"
               "CIK{cik}/us-gaap/{tag}.json")

TAGS = {
    'repurchase_cash': 'PaymentsForRepurchaseOfCommonStock',
    'repurchase_accrual': 'StockRepurchasedAndRetiredDuringPeriodValue',
    'shares_retired': 'StockRepurchasedAndRetiredDuringPeriodShares',
    # DEFECT 20 (2026-08-13, found on Microsoft). A company that repurchases and
    # retires in one motion may tag the flow WITHOUT the word "Retired".
    # Microsoft files StockRepurchasedDuringPeriodShares for every year of its
    # history and nothing else, so the template saw no retirement flow at all,
    # fell through every fallback, and left all thirteen years unresolved on the
    # largest repurchase program in the sample.
    'shares_repurchased': 'StockRepurchasedDuringPeriodShares',
    'shares_repurchased_value': 'StockRepurchasedDuringPeriodValue',
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
    # 2026-08-13, the round trip (addendum item 3). The financing-activities
    # equity line, under whichever of these names the company uses. It is the
    # RECONCILIATION target for the round trip, NOT its numerator - see
    # EquityRaise below for why that distinction is the whole guard.
    'equity_raise_cash_flow': 'ProceedsFromIssuanceOrSaleOfEquity',
    'equity_raise_cash_flow_alt': 'ProceedsFromIssuanceOfCommonStock',
    'equity_raise_cash_flow_warrants': 'ProceedsFromIssuanceOfCommonStockAndWarrants',
    # Ordinary employee-plan share issuance, netted out of the round trip so a
    # routine compensation flow cannot masquerade as a distress raise.
    'plan_shares_issued': 'StockIssuedDuringPeriodSharesShareBasedCompensation',
    # 2026-08-13, treasury permanence (addendum item 4). A company that RETIRES
    # its repurchased shares has removed them permanently; a company that holds
    # them in TREASURY has not, and the same arithmetic needs a different word.
    # Companies rename the balance partway through their history - Home Depot
    # and Boeing both moved from TreasuryStockShares to TreasuryStockCommonShares
    # - so both names are carried and merged.
    'treasury_shares_balance_alt': 'TreasuryStockCommonShares',
    'treasury_value_balance': 'TreasuryStockValue',
    'treasury_value_balance_alt': 'TreasuryStockCommonValue',
    'treasury_shares_reissued': 'StockIssuedDuringPeriodSharesTreasuryStockReissued',
    'shares_retired_value': 'StockRepurchasedAndRetiredDuringPeriodValue',
    # 2026-08-13, the excise tax (addendum item 5). This is the ONLY element in
    # the us-gaap taxonomy carrying the Inflation Reduction Act excise on net
    # repurchases, and on the one company found filing it, it is NOT the figure
    # that agrees with that company's own statement of stockholders' equity -
    # see excise_tax() for the O'Reilly finding and for why the equity statement
    # wins where the two disagree. Most companies that disclose the quantity at
    # all use a company EXTENSION element under their own namespace (nflx:,
    # orly:, vrsn: and mck: were each found using a different name for it),
    # which cannot be reached through the us-gaap company-concept URL at all;
    # those have to be read off the filing and passed in through `disclosed`.
    'excise_tax': 'ShareRepurchaseProgramExciseTax',
}

# Internal Revenue Code section 4501, enacted by the Inflation Reduction Act of
# 2022. One percent of the fair market value of stock repurchased during the
# taxable year, REDUCED by the fair market value of stock ISSUED during the same
# year - the netting rule, which is not optional and is not small: on O'Reilly
# Automotive it removes between eleven and eighteen percent of the gross tax in
# each of the three years measured. Applies to repurchases made AFTER
# 2022-12-31, so a fiscal year straddling that date is only partly exposed.
EXCISE_RATE = 0.01
EXCISE_EFFECTIVE_AFTER = (2022, 12)


class ExciseTaxUndisclosed(RuntimeError):
    """Raised when a fiscal year is exposed to the excise tax and no filed
    figure can be found for it. It exists so that the tax cannot become zero by
    default in a table that reconciles to the dollar elsewhere."""

# Any one of these carrying a non-zero balance is positive evidence that the
# company holds repurchased stock rather than cancelling it.
TREASURY_BALANCE_KEYS = ('treasury_shares_balance', 'treasury_shares_balance_alt',
                         'treasury_value_balance', 'treasury_value_balance_alt')
# Weaker but still positive evidence of treasury accounting: a company that
# tags shares or value ACQUIRED INTO treasury is using the treasury method, even
# where the balance itself is not in the fixture. It is weaker because a company
# can acquire into treasury and cancel later, so it never overrides a balance
# and it is reported as the weaker basis it is.
TREASURY_FLOW_KEYS = ('treasury_shares_acquired', 'treasury_value_acquired')
# Any one of these is positive evidence that it cancels.
RETIREMENT_KEYS = ('shares_retired', 'shares_retired_value')

ROUND_TRIP_RAISE_TAGS = ('ProceedsFromIssuanceOrSaleOfEquity',
                         'ProceedsFromIssuanceOfCommonStock',
                         'ProceedsFromIssuanceOfCommonStockAndWarrants')


@dataclass
class EquityRaise:
    """One share-issuing equity raise, taken from the statement of stockholders'
    equity, where the share count and the dollar amount sit on the SAME LINE.

    WHY THIS IS NOT READ FROM A TAG, AND THE FINDING THAT FORCED IT
    (2026-08-13, American Airlines). The obvious construction is to divide the
    financing-activities equity line by the change in shares outstanding. On
    American Airlines' fiscal 2020 that gives $15.00 a share. The true figure,
    from the company's own equity statement, is $12.91: the $2,970m financing
    line contains $415m that is the EQUITY COMPONENT OF A CONVERTIBLE BOND,
    bifurcated out of debt proceeds under the then-current standard. No share
    was issued for it.

    The contaminated price is sixteen percent too high, it is wrong in the
    direction that FLATTERS the repurchase program, and - this is the part that
    matters - $15.00 sits comfortably inside the stock's 2020 traded range of
    $8.25 to $30.78, so validate_prices() passes it without a murmur. The price
    validator cannot see a contaminated numerator whose error is small relative
    to the traded range. Nothing else in this template could have caught it.

    So the round trip is struck on the equity statement, where shares and
    dollars are disclosed together and cannot drift apart, and the
    financing-activities line is used only to RECONCILE. Where the two
    disagree by more than the tolerance, the difference must be named in
    `reconciling_items` or the year is refused outright.

    shares    millions, as disclosed on that line
    proceeds  $ millions, as disclosed on that line (net of offering costs)
    source    provenance: the filing and the statement line it came from
    """
    fiscal_year: int
    shares: float
    proceeds: float
    label: str
    source: str

    @property
    def price(self):
        return self.proceeds / self.shares


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
    # ------------------------------------------------ the round trip (2026-08-13)
    raises: list = field(default_factory=list)
    # [EquityRaise], from the statement of stockholders' equity. Empty means
    # "this company raised no equity in the window", which is a FACT about the
    # company and is reported as such - it is not a missing input.
    plan_shares: dict = field(default_factory=dict)
    # {fy: millions} ordinary employee-plan share issuance, netted out so a
    # routine compensation flow cannot be read as a distress raise.
    raise_reconciling_items: dict = field(default_factory=dict)
    # {fy: {name: $m}} named differences between the equity statement and the
    # financing-activities line. Anything unnamed refuses the year.
    shares_out: dict = None
    # {fy: millions} already restated onto today's split basis. Supply this only
    # where the caller already owns a verified share-count series - Apple's
    # build chain does - so that one definition of the share count is used
    # rather than two. Left None, shares_outstanding() reads the tags as usual.
    withholding_in_repurchase_cash: dict = field(default_factory=dict)
    # {fy: $m} where the company presents share repurchases and shares withheld
    # for employee taxes on ONE cash-flow line (American Airlines does), the
    # withholding portion is not a repurchase and is removed from the price
    # paid. Absent means the two are presented separately.

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
        # Memoized: this is called from several places and each call used to
        # append its notes again, so a single splice was reported three times.
        # A reader who sees the same warning three times learns to skim
        # warnings, which is the opposite of what they are for.
        if getattr(self, '_shares_out_cache', None) is not None:
            return self._shares_out_cache
        if self.shares_out is not None:
            return self.shares_out
        raw = self.sec.get('shares_outstanding', {})
        out = {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
               for y, e in raw.items()} if raw else {}

        # DEFECT 17 (2026-08-13, found on AutoZone). A large number of filers
        # stop tagging CommonStockSharesOutstanding at some point and report the
        # count only on the cover page of the Form 10-K, as the Document and
        # Entity Information element EntityCommonStockSharesOutstanding.
        # AutoZone stops in fiscal 2018 and files seven more years of heavy
        # repurchases with no us-gaap share count at all, which under defect 16
        # silently halved the study window.
        #
        # The cover-page count is a DIFFERENT MEASUREMENT, not a synonym: it is
        # struck as of the filing date, typically a few weeks after the fiscal
        # year end, so it includes any share movement in between. It is used
        # only to fill years the us-gaap series does not reach, it is announced,
        # and where the two series overlap they must AGREE - a level shift
        # between two sources spliced into one line would move every derived
        # retirement in the window and close every identity while doing it.
        dei = self.sec.get('shares_outstanding_dei', {})
        if dei:
            cover = {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                     for y, e in dei.items()}
            overlap = sorted(set(out) & set(cover))
            gap = [y for y in cover if y not in out]
            if overlap:
                worst = max(abs(cover[y] / out[y] - 1) for y in overlap if out[y])
            else:
                worst = None
            if not out:
                self.notes.append(
                    "SHARE COUNT FROM THE COVER PAGE: no CommonStockSharesOutstanding "
                    "is tagged in any year, so the count is taken from the Form 10-K "
                    "cover page (EntityCommonStockSharesOutstanding). That figure is "
                    "struck as of the FILING date, not the fiscal year end, so every "
                    "derived retirement carries a few weeks of share movement it "
                    "should not. Treat derived years as approximate and lean on the "
                    "price validator.")
                out = cover
            elif gap and worst is not None and worst <= 0.02:
                self.notes.append(
                    f"SHARE COUNT EXTENDED FROM THE COVER PAGE for FY{sorted(gap)}: "
                    "CommonStockSharesOutstanding stops before the end of the window "
                    "and the cover-page count fills the rest. The two agree to within "
                    f"{100*worst:.2f}% in the {len(overlap)} overlapping year(s), which "
                    "is why the splice is allowed. The cover-page figure is as of the "
                    "FILING date, so the filled years carry a few weeks of share "
                    "movement the others do not.")
                _merged = dict(cover)
                _merged.update(out)      # the us-gaap series wins wherever it exists
                out = _merged
            elif gap:
                self.notes.append(
                    "COVER-PAGE SHARE COUNT REFUSED: CommonStockSharesOutstanding stops "
                    f"before the end of the window and the cover-page count disagrees "
                    f"with it by up to {100*(worst or 0):.1f}% in the overlapping "
                    f"year(s) ({overlap or 'none at all'}). Splicing two series that do "
                    "not agree would move every derived retirement in the window while "
                    "closing every identity. The later years are left without a share "
                    "count instead.")
        if out:
            self._shares_out_cache = out
            return out
        issued = self.sec.get('shares_issued', {})
        treasury = self.sec.get('treasury_shares_balance', {})
        if not issued and not treasury and not raw and not dei:
            # DEFECT 22 (2026-08-13, found on Meta Platforms and Alphabet). A
            # company with more than one class of common stock reports every
            # share count DIMENSIONED by class, and the Securities and Exchange
            # Commission's company-concept interface serves only undimensioned
            # facts. So the structured data carries no share count at all - not
            # a short one, none - and no amount of fallback inside this file can
            # produce one. Meta Platforms is the pure case: not one of the five
            # share-count elements this template knows returns anything.
            #
            # This is a limit of the INTERFACE, not of the company or of the
            # study, and it is named as such so nobody spends another session
            # looking for a tag that is not reachable. Reading it requires the
            # filing itself.
            self.notes.append(
                "NO SHARE COUNT IS REACHABLE THROUGH THE STRUCTURED INTERFACE: none "
                "of CommonStockSharesOutstanding, CommonStockSharesIssued, the "
                "treasury balance or the cover-page count returns anything. The usual "
                "cause is MORE THAN ONE CLASS OF COMMON STOCK, which makes every "
                "share-count fact dimensioned by class, and the company-concept "
                "interface serves only undimensioned facts. No study of this company "
                "is possible from structured data alone; the counts must be read out "
                "of the filing.")
        out = {}
        for y in sorted(set(issued) & set(treasury)):
            iss = issued[y]['val'] * self.cfg.split_factor(issued[y]['filed'])
            tre = treasury[y]['val'] * self.cfg.split_factor(treasury[y]['filed'])
            out[y] = (iss - tre) / 1e6
        self._shares_out_cache = out or None
        if out and not getattr(self, '_noted_shares_outstanding_source', False):
            self.notes.append(
                "no CommonStockSharesOutstanding tagged; shares outstanding "
                "derived as CommonStockSharesIssued minus the treasury share "
                "balance instead")
            self._noted_shares_outstanding_source = True
        return out

    # ------------------------------------------------- shares retired/issued
    def share_flows(self, issue_rate_fallback=None, issue_scale=1.0,
                     early_years_for_fallback=3, max_plausible_issue_rate=0.05,
                     require_cash_for_derived=True):
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

        # --------------------------------------------------------- defect 20
        if not filed:
            alt = {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                   for y, e in self.sec.get('shares_repurchased', {}).items()}
            if alt:
                filed = alt
                retired_tag = 'StockRepurchasedDuringPeriodShares'
                self.notes.append(
                    "no StockRepurchasedAndRetiredDuringPeriodShares tagged; used "
                    "StockRepurchasedDuringPeriodShares instead. The element does not "
                    "say whether the shares were cancelled or parked, so permanence is "
                    "decided separately from the treasury balance, not inferred from "
                    "this tag.")

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
        # DEFECT 21 (2026-08-13). retired_tag was initialized to the name of the
        # PREFERRED element and then only overwritten when a fallback fired, so
        # a company that tags no retirement flow at all reported
        # "retired tag = StockRepurchasedAndRetiredDuringPeriodShares" at the
        # top of its study while resolving nothing. The header said the data was
        # there. A label that lies about its own source is worse than no label.
        if not filed:
            retired_tag = 'NONE FOUND - no retirement or treasury flow tagged'
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
                # ------------------------------------------------ defect 11
                # 2026-08-13, found on American Airlines while building the
                # round trip. Defect 5's fix estimates the issuance rate from
                # the EARLIEST observable years, which is right when the only
                # thing moving the share count is employee plan activity, and
                # badly wrong when an early year contains a STRUCTURAL share
                # issuance - a merger, an emergence from bankruptcy, a large
                # stock-funded acquisition. American Airlines' fiscal 2014
                # prints an "issuance rate" of 36.8 percent of opening shares,
                # because that is the year the US Airways merger shares and
                # the bankruptcy claim distributions landed. Averaged into the
                # fallback it gave 13 percent, which then manufactured 54.6
                # and 81.3 million shares of retirement in fiscal 2021 and
                # 2022 - years in which the company repurchased nothing and
                # was in fact contractually barred from doing so.
                #
                # No ordinary employee plan issues five percent of the company
                # in a year. A rate above `max_plausible_issue_rate` is not an
                # employee plan and is refused rather than used; the affected
                # years fall through to the unresolved handling below, where a
                # share count and a price are not invented for them. Raise the
                # bound explicitly for a company where a higher rate is
                # genuinely ordinary, and say so in the report.
                if (max_plausible_issue_rate is not None
                        and issue_rate_fallback > max_plausible_issue_rate):
                    self.notes.append(
                        "ISSUANCE-RATE FALLBACK REFUSED: the rate estimated "
                        f"from the earliest {n} observable year(s) "
                        f"({', '.join('FY%d' % y for y in early_years)}) is "
                        f"{100*issue_rate_fallback:.2f}% of opening shares, "
                        f"above the {100*max_plausible_issue_rate:.0f}% bound "
                        "for an ordinary employee plan. A rate that size is a "
                        "structural issuance - a merger, an emergence from "
                        "bankruptcy, a stock-funded acquisition - not "
                        "compensation, and extrapolating it would manufacture "
                        "retirements in years the company retired nothing. "
                        "Years without a filed retirement count are left "
                        "unresolved instead.")
                    issue_rate_fallback = None
                else:
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

        # ------------------------------------------------------- defect 10
        # 2026-08-13, found on American Airlines. A year in which the company
        # spent nothing repurchasing stock cannot have had a retirement, and
        # deriving one from a share-count movement is how a share issuance gets
        # reported as a buyback. Two of American Airlines' years look like
        # repurchase years on the cash line alone and are not: fiscal 2021 and
        # 2022 tag $18m and $21m of PaymentsForRepurchaseOfCommonStock, and
        # every dollar of it is employee tax withholding presented on the same
        # line. The company repurchased nothing in either year - under the
        # payroll support agreements it was barred from doing so - and a
        # template that read that line as a repurchase would have published
        # American Airlines buying back its own stock in years it was
        # contractually prohibited from buying back its own stock.
        def _repurchase_cash(y):
            v = self.sec.get('repurchase_cash', {}).get(y, {}).get('val')
            if v is None:
                return None
            return v / 1e6 - self.withholding_in_repurchase_cash.get(y, 0.0)

        retired, issued, derived, unresolved, no_cash = {}, {}, set(), set(), set()
        no_count, negative = set(), set()
        for y in self.years():
            if y not in S or (y - 1) not in S:
                # DEFECT 16 (2026-08-13, found on AutoZone, and the dangerous
                # kind). A year with no share-count observation used to be
                # skipped here with a bare `continue` - not recorded as
                # unresolved, not counted, not mentioned. AutoZone stops
                # tagging CommonStockSharesOutstanding after fiscal 2018 and
                # files the count on the cover page instead, so seven of its
                # thirteen years fell through this line. The study then
                # reported `unresolved = []` and published a six-year program
                # as though the window it named in its own heading were
                # complete. Nothing failed. Nothing looked wrong.
                #
                # A year that cannot be measured is now named, and a year in
                # which cash was demonstrably spent is named louder.
                no_count.add(y)
                continue
            if y in filed:
                # DEFECT 23 (2026-08-13, found on Booking Holdings). A NEGATIVE
                # shares-retired figure is not a small retirement, it is not a
                # net issuance, and it is not a number this study can use: it
                # divides repurchase cash into a negative price per share, which
                # then flows into the entry effect as a positive contribution.
                # Booking Holdings' fiscal 2014 printed -45.8mn shares and a
                # real price of MINUS $23.20, and the entry effect was struck on
                # it anyway. A negative quantity is refused at source.
                if filed[y] < 0:
                    negative.add(y)
                    continue
                retired[y], issued[y] = filed[y], S[y] - S[y - 1] + filed[y]
                continue
            c = _repurchase_cash(y)
            if require_cash_for_derived and not (c and c > 0):
                # No filed retirement and no repurchase cash. The company did
                # not repurchase. This is settled before the fallback is even
                # consulted, because no estimate of an issuance rate can turn a
                # year with no repurchase into a year with one.
                no_cash.add(y)
                continue
            if issue_rate_fallback is not None:
                issued[y] = S[y - 1] * issue_rate_fallback * issue_scale
                retired[y] = S[y - 1] - S[y] + issued[y]
                derived.add(y)
            else:
                unresolved.add(y)

        self.negative_retirement_years = negative
        if negative:
            self.notes.append(
                "NEGATIVE RETIREMENT REFUSED in " +
                ", ".join(f"FY{y}" for y in sorted(negative)) +
                ": the filed shares-retired figure is negative, which divides "
                "repurchase cash into a negative price per share. The year is "
                "excluded from every measure rather than carried with a sign "
                "nobody intended. The usual cause is a reissuance netted into "
                "the same element; read the filing before assuming otherwise.")
            unresolved |= negative

        self.no_share_count_years = no_count
        if no_count:
            spent = {y: _repurchase_cash(y) for y in no_count}
            spent = {y: v for y, v in spent.items() if v and v > 0}
            msg = ("NO SHARE COUNT for " +
                   ", ".join(f"FY{y}" for y in sorted(no_count)) +
                   ": the shares-outstanding series does not cover the year or "
                   "the year before it, so no retirement, price or issuance "
                   "can be computed. These years are NOT in any figure below.")
            if spent:
                msg += (" THIS MATTERS: ${:,.0f}m of repurchase cash was spent "
                        "in ".format(sum(spent.values())) +
                        ", ".join(f"FY{y}" for y in sorted(spent)) +
                        ", so the window actually measured is shorter than the "
                        "window named. Either extend the share-count series or "
                        "narrow the study window and say so.")
            self.notes.append(msg)
            unresolved |= set(spent)

        self.no_repurchase_years = no_cash
        if no_cash:
            self.notes.append(
                "no repurchase in " + ", ".join(f"FY{y}" for y in sorted(no_cash)) +
                " - no filed retirement count and no repurchase cash net of any "
                "employee withholding presented on the same line. These years "
                "are recorded as years the company did not repurchase, which is "
                "a fact, rather than having a retirement derived for them from a "
                "share-count movement.")

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
        """Growth in earnings per share split into its earnings and share-count
        channels, and the earnings channel split again into operating and
        financial.

        DEFECT 13 FIX (2026-08-13, close-out session, found by running the
        generic driver cold on Oracle). The operating/financial split needs a
        pretax income figure to strike the effective tax rate on. Oracle tags
        IncomeLossFromContinuingOperationsBeforeIncomeTaxes... for fiscal 2011
        to 2018 and then stops, under either of its two element names. The old
        code built `oi` and `nfi` only for the years it could, then read
        `oi[y]` and `oi[y - 1]` unconditionally, and died with a bare KeyError
        on the first year it could not.

        The crash was the good outcome. The bad one is the shape of this bug in
        general: a study that quietly dropped the years it could not split would
        publish an attribution over a shorter window than the one named in its
        own heading. So the FIRST TWO CHANNELS - which need no tax rate and are
        the ones the study actually leans on - are computed for every year, and
        the operating/financial split is filled in only where it is determinable
        and set to None where it is not, with the years named in the notes. A
        None is visible in every table it reaches; a silently shorter window is
        not.
        """
        f = self.fin
        # DEFECT (2026-08-13, found on Alibaba and Visa during the
        # convergence sweep). Every per-YEAR read in this method was already
        # guarded (see the two defect-13 notes above) but the top-level KEYS
        # were not: a company with no weighted-average diluted share count
        # tagged under any name this template knows - Alibaba files a 20-F,
        # not a 10-K, and this driver reads only 10-K facts; Visa's element
        # coverage gap turned out to be a fetch-window artifact, not absence,
        # but the crash is identical either way - died with a bare KeyError
        # before any of the careful per-year handling below ever ran. The
        # method's own docstring already says the lesson: EVERY series this
        # method touches has to be treated as possibly short, and that has to
        # include the series being entirely absent, not just gappy.
        S = self.fin.get('wtd_diluted_shares')
        if not S:
            self.notes.append(
                "EARNINGS ATTRIBUTION NOT COMPUTED AT ALL: no weighted-average "
                "diluted share count is tagged under any known name in any "
                "year. Every channel of this attribution needs it in the "
                "denominator and none of them can be struck without it.")
            self._oi = {}
            return {}
        NI, EPS = f.get('net_income', {}), f.get('diluted_eps', {})
        if not NI or not EPS:
            missing = [n for n, v in (('net income', NI), ('diluted EPS', EPS)) if not v]
            self.notes.append(
                "EARNINGS ATTRIBUTION NOT COMPUTED AT ALL: " + " and ".join(missing) +
                " not tagged under any known name in any year.")
            self._oi = {}
            return {}
        pre = f.get('pretax_income', {})
        tax = f.get('tax_provision', {})
        op = f.get('operating_income', {})
        oi, nfi = {}, {}
        for y in list(S):
            if pre.get(y) and tax.get(y) is not None and op.get(y) is not None:
                t = tax[y] / pre[y]
                oi[y] = op[y] * (1 - t)
                nfi[y] = (pre[y] - op[y]) * (1 - t)
        rows, unsplit, unattributed = {}, [], []
        for y in self.years():
            if (y - 1) not in S or y not in S:
                continue
            # DEFECT 13, SECOND PASS (2026-08-13, found by running IBM cold
            # immediately after Oracle). The first pass guarded the tax-rate
            # inputs and left the earnings and share-count channels reading
            # NI[y] and NI[y-1] unconditionally. International Business
            # Machines files NetIncomeLoss only from 2015 - before that the
            # figure sits under a different element - so the very next company
            # died on the very next line. The lesson is not "add another
            # guard": it is that EVERY series this method touches has to be
            # treated as possibly short, because on a wide enough sample of
            # filers every one of them is.
            have_ni = NI.get(y) is not None and NI.get(y - 1) is not None
            have_eps = EPS.get(y - 1) is not None
            if not (have_ni and have_eps):
                unattributed.append(y)
                continue
            splittable = y in oi and (y - 1) in oi
            if not splittable:
                unsplit.append(y)
            rows[y] = {
                'from_earnings': (NI[y] - NI[y - 1]) / S[y],
                'from_share_count': EPS[y - 1] * (S[y - 1] / S[y] - 1),
                'operating': ((oi[y] - oi[y - 1]) / S[y]) if splittable else None,
                'financial': ((nfi[y] - nfi[y - 1]) / S[y]) if splittable else None,
            }
        if unattributed:
            self.notes.append(
                f"EARNINGS ATTRIBUTION NOT COMPUTED AT ALL for FY{unattributed}: "
                "net income or diluted earnings per share is untagged in that "
                "year or the one before it. The years are named rather than the "
                "window being quietly shortened.")
        if unsplit:
            self.notes.append(
                "EARNINGS ATTRIBUTION NOT SPLIT into operating and financial for "
                f"FY{unsplit}: pretax income, the tax provision or operating "
                "income is untagged in that year or the one before it, so there "
                "is no effective tax rate to strike the split on. The earnings "
                "and share-count channels are unaffected and are computed for "
                "every year; the split is reported as unavailable rather than "
                "the years being dropped from the window.")
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
        """The multiple paid against the multiple on offer, split into
        within-year execution and across-year allocation.

        DEFECT 14 (2026-08-13, found by running Union Pacific cold). Every
        quantity here is a ratio, and the old code assumed each denominator was
        non-empty: a fiscal year with no diluted earnings per share, or a window
        whose resolved repurchase cash sums to zero, divided by zero and killed
        the run. Union Pacific reaches the second case. The measure is a
        weighted average of years, so the honest response is to drop the years
        it cannot price - naming them - and to REFUSE the whole measure rather
        than return a shaped zero if nothing priceable is left.
        """
        eps = self.fin.get('diluted_eps', {})
        ys, skipped = [], []
        for y in self.years():
            if y not in retired or not retired[y]:
                continue
            c = self.sec.get('repurchase_cash', {}).get(y, {}).get('val')
            e = eps.get(y)
            p = self.fy_mean_price(y)
            if c is None or not e or p is None:
                skipped.append(y)
                continue
            ys.append(y)
        if skipped:
            self.notes.append(
                f"TIMING TEST EXCLUDES FY{skipped}: repurchase cash, diluted "
                "earnings per share or a price for the year is missing, and a "
                "multiple cannot be struck without all three. The years are "
                "named rather than the window being quietly shortened.")
        cash = {y: self.sec['repurchase_cash'][y]['val'] / 1e6 for y in ys}
        tot = sum(cash.values())
        if not ys or not tot:
            self.notes.append(
                "TIMING TEST NOT COMPUTED: no fiscal year in the window has a "
                "retirement count, repurchase cash and an earnings figure "
                "together. This is reported as unavailable; it is NOT a zero, "
                "and nothing downstream may read it as one.")
            return {'dollar_weighted_pe_paid': None, 'equal_weighted_pe_paid': None,
                    'market_pe': None, 'execution_within_year': None,
                    'allocation_across_years': None, 'combined': None,
                    'pe_paid': {}, 'pe_market': {}, 'excluded_years': skipped,
                    'available': False}
        pe_paid = {y: (cash[y] / retired[y]) / eps[y] for y in ys}
        pe_mkt = {y: self.fy_mean_price(y) / eps[y] for y in ys}
        dw = sum(cash[y] * pe_paid[y] for y in ys) / tot
        ew = sum(pe_paid.values()) / len(ys)
        mk = sum(pe_mkt.values()) / len(ys)
        return {'dollar_weighted_pe_paid': dw, 'equal_weighted_pe_paid': ew,
                'market_pe': mk,
                'execution_within_year': ew / mk - 1,
                'allocation_across_years': dw / ew - 1,
                'combined': dw / mk - 1,
                'pe_paid': pe_paid, 'pe_market': pe_mkt,
                'excluded_years': skipped, 'available': True}

    # ============================================================ entry effect
    # ADDENDUM ITEM 1, PULLED INTO THE TEMPLATE 2026-08-13 (close-out session).
    #
    # The entry effect was the last measure in this study still written out once
    # per company. It lived twice: in code/gen_article.py for Apple and in
    # code/full_study_COST.py for Costco. Two definitions of one quantity is the
    # exact shape of the defect this repository has been bitten by repeatedly -
    # a number that is internally consistent, passes every gate, and is wrong in
    # one of its two homes. Items 4 and 5 removed the same duplication for the
    # net retirement cost and the excise tax; this closes the set.
    #
    # WHAT THE MEASURE IS. For a repurchase tranche struck in fiscal year t,
    #
    #     entry[t] = shares_retired[t] * (real_eps[t+1] - rho * real_price[t])
    #
    # the earnings the retired shares carried in the year that followed, less
    # the capital charge on the cash actually spent. The pivot is Neutral Value,
    # not Intrinsic Value, and the study states no estimate of the latter. It is
    # ex-post disclosure: it moves no valuation number, it is not a price, it is
    # not an expense, and the net retirement cost is never substituted into it.
    #
    # WHAT IS NEW HERE IS NOTHING ARITHMETIC. Every formula below is the one
    # already published. What is new is that there is now one copy of it, that
    # the guards are the template's rather than each driver's, and that a driver
    # which forgets a guard cannot silently do without it.

    def earnings_span(self):
        """The years the real earnings series is defined over: the study window
        and the single year before it.

        The span is NOT "every year the statements happen to reach back to",
        and the difference is not cosmetic. Two of the three trend estimators
        behind the earnings-timing decomposition read neighbouring years out of
        this series - the centred geometric mean takes a window either side of
        the year it is evaluating, and the engine normalizer walks back from the
        earliest year present. Feeding one company forty years of history and
        another twelve would make their decompositions incomparable, and would
        silently change a published number the day somebody extended a source
        file backwards. The span is a stated convention: `first_year - 1`
        through `last_year`, the same years the abnormal earnings growth
        recursion needs, and nothing else.

        Override `span` on the instance where a company genuinely warrants a
        different one, and say so in the study.
        """
        sp = getattr(self, 'span', None)
        if sp is not None:
            return list(sp)
        return list(range(self.cfg.first_year - 1, self.cfg.last_year + 1))

    def real_eps(self):
        """Diluted earnings per share in base-year dollars.

        The deflator is a MULTIPLIER - nominal times deflator equals base-year
        dollars. It is stated that way on the committed deflator row and it is
        used that way everywhere else in this file. A driver that divides by it
        instead produces a real series that leans the wrong way with time, and
        because the error is smooth and small in any single year it will not
        trip a range check. Reading the series from here removes the choice.
        """
        e = self.fin['diluted_eps']
        return {y: e[y] * self.deflator[y] for y in self.earnings_span()
                if e.get(y) is not None and y in self.deflator}

    def real_net_income(self):
        ni = self.fin['net_income']
        return {y: ni[y] * self.deflator[y] for y in self.earnings_span()
                if ni.get(y) is not None and y in self.deflator}

    def real_distributions(self):
        """Dividends plus repurchase cash, real. The cum-dividend term in the
        entity-level abnormal earnings growth recursion."""
        rep = {y: e['val'] / 1e6
               for y, e in self.sec.get('repurchase_cash', {}).items()}
        d = self.fin.get('dividends')
        if d is None:
            # DEFECT 15 (2026-08-13, found on AutoZone). A company that pays no
            # dividend files no dividend element, and the old code took
            # self.fin['dividends'] straight, so the whole entry effect died
            # with KeyError: 'dividends'. AutoZone is the archetype: it returns
            # everything through repurchases and has never paid a dividend.
            #
            # A missing input is never silently zero - but an absent dividend
            # element is not always a missing input, and treating the two the
            # same is its own error. The distinction is made on EVIDENCE and
            # announced either way; `dividends_are_zero` is set by the driver
            # only when no dividend element of ANY known name is filed.
            if getattr(self, 'dividends_are_zero', False):
                self.notes.append(
                    "NO DIVIDEND: this company files no dividend element under "
                    "any known name in any year of the window, so the dividend "
                    "stream is taken as a genuine zero rather than as missing "
                    "data. That is a claim about the company and it is stated "
                    "here so it can be checked, not buried in an arithmetic "
                    "default.")
                d = {}
            else:
                raise ValueError(
                    "no dividend series was supplied and the driver did not "
                    "assert that this company pays none. A dividend stream "
                    "that is absent because nobody fetched it and one that is "
                    "absent because the company pays nothing are different "
                    "facts and this will not guess between them. Set "
                    "`dividends_are_zero = True` on the study only on the "
                    "evidence that no dividend element of any name is filed.")
        return {y: (d.get(y, 0.0) + rep.get(y, 0.0)) * self.deflator[y]
                for y in self.earnings_span()
                if y in self.deflator}

    def aeg_entity(self, rho, years=None):
        """Entity-level abnormal earnings growth, real, cum-dividend form:

            AEG(s) = NI_r(s) - (1 + rho) * NI_r(s-1) + rho * D_r(s-1)

        A year whose predecessor is missing is skipped rather than given a
        substitute predecessor, and the skip is reported by its absence from
        the returned keys - the caller can see which years are there.
        """
        ni, dr = self.real_net_income(), self.real_distributions()
        ys = self.years() if years is None else years
        return {s: ni[s] - (1 + rho) * ni[s - 1] + rho * dr[s - 1]
                for s in ys
                if s in ni and (s - 1) in ni and (s - 1) in dr}

    def entry_tranches(self):
        """The repurchase years on which an entry effect can honestly be struck,
        and a reason for every year excluded.

        Four things must hold. The company must have retired shares that year;
        there must be repurchase cash net of any employee tax withholding
        folded into the same line (DEFECT 10 - American Airlines tags $18m and
        $21m in fiscal 2021 and 2022 that is entirely withholding, and without
        this guard the study would publish American Airlines repurchasing in
        years it was contractually barred from doing so); the deflator must
        cover the year; and the FOLLOWING year's earnings must actually have
        been reported, because the measure is struck on them. The last is why
        the final year of every study is absent from the entry-effect table.

        Returns (tranches, excluded) where excluded is {year: reason}.
        """
        eps = self.real_eps()
        # DEFECT 24 (2026-08-13, found on Booking Holdings). The price validator
        # is the guard that catches a derived share count whose implied price
        # never existed. It was REPORTING failures at the top of the study and
        # nothing was acting on them: Booking Holdings failed validation in
        # fiscal 2013 and 2014 - an implied $96.19 against a traded range of
        # $25.11 to $47.95, and an implied MINUS $16.39 - and the entry effect
        # was struck on both years regardless. A guard whose finding does not
        # reach the measure is not a guard.
        failed = {y for y, *_ in (getattr(self, 'price_failures', None) or [])}
        tranches, excluded = [], {}
        for y in self.years():
            if y in failed:
                excluded[y] = ('the implied average price paid failed validation '
                               'against the year\'s own traded range, so the share '
                               'count behind it cannot be right')
                continue
            q = self.retired.get(y)
            if not q:
                excluded[y] = 'no shares retired'
                continue
            cash = self.sec.get('repurchase_cash', {}).get(y, {}).get('val')
            if cash is None:
                excluded[y] = 'no repurchase cash tagged'
                continue
            cash = cash / 1e6 - self.withholding_in_repurchase_cash.get(y, 0.0)
            if cash <= 0:
                excluded[y] = ('repurchase cash is nil net of employee tax '
                               'withholding on the same line (defect 10)')
                continue
            if y not in self.deflator:
                excluded[y] = 'no deflator for the year'
                continue
            if eps.get(y + 1) is None:
                excluded[y] = (f'fiscal {y + 1} earnings not reported, so there '
                               'is no year following the purchase to strike the '
                               'measure on')
                continue
            tranches.append(y)
        return tranches, excluded

    def entry_effect(self, rho=None, tranches=None, split_year=None,
                     coe_by_year=None, estimator_window=None,
                     per_share_base=None, decompose=True):
        """The entry effect, its break-even rate, the entity-level abnormal
        earnings growth account behind the continuing effect, and the
        earnings-timing decomposition, in one place.

        `rho` is the flat long-run real cost of equity the headline is struck
        at. It is NOT defaulted: a capitalization rate silently supplied is
        precisely the failure mode this project keeps meeting, so an absent rate
        refuses rather than guesses.

        `coe_by_year` optionally supplies the company's own year-by-year real
        cost of equity, which produces the alternative reading published
        alongside the headline. Absent, that reading is None rather than a copy
        of the headline wearing a different name.

        `split_year` asks for the break-even rate on the tranches before and
        from that year as well as on all of them. Which year to split at is an
        editorial judgment about the company and stays with the driver; the
        arithmetic does not.

        `per_share_base` is the share count the continuing effect divides by.
        Default is shares outstanding, which is what the published Apple study
        uses. A driver with only a weighted diluted count may pass it, and the
        choice is recorded in the returned dictionary so it cannot be lost.
        """
        if rho is None:
            raise ValueError(
                "entry_effect() needs an explicit real cost of equity. It will "
                "not default one: the capitalization rate sets the SIGN of this "
                "measure, and a rate that arrived by default rather than by "
                "decision has twice been the defect in this project.")
        eps, px = self.real_eps(), {}
        auto, excluded = self.entry_tranches()
        if tranches is None:
            tranches = auto
        else:
            excluded = {y: r for y, r in excluded.items() if y not in tranches}
        for t in tranches:
            p = self.real_repurchase_price(t)
            if p is None:
                raise ValueError(f"tranche {t} has no real repurchase price; it "
                                 "should have been excluded, not priced")
            px[t] = p

        per_year = {t: self.retired[t] * (eps[t + 1] - rho * px[t])
                    for t in tranches}
        total = sum(per_year.values())
        negative = [t for t in tranches if per_year[t] < 0]

        alt_per_year = alt_total = alt_negative = None
        if coe_by_year:
            alt_per_year = {t: self.retired[t] * (eps[t + 1] - coe_by_year[t] * px[t])
                            for t in tranches if t in coe_by_year}
            alt_total = sum(alt_per_year.values())
            alt_negative = [t for t in alt_per_year if alt_per_year[t] < 0]

        # The break-even rate. The entry effect is LINEAR in rho, so it has
        # exactly one root and that root is the retirement-weighted forward real
        # earnings yield on the tranches. No search, no tolerance, no iteration
        # - it is an identity, and it is the only sensitivity in this study that
        # moves a SIGN rather than a magnitude.
        def _root(ys):
            den = sum(self.retired[t] * px[t] for t in ys)
            if not den:
                return None
            return sum(self.retired[t] * eps[t + 1] for t in ys) / den

        break_even = _root(tranches)
        windows = {'all': break_even}
        if split_year is not None:
            early = [t for t in tranches if t < split_year]
            late = [t for t in tranches if t >= split_year]
            windows['early'] = _root(early) if early else None
            windows['late'] = _root(late) if late else None

        # The continuing effect: what the retired shares would have earned in
        # every year after the one the entry effect is struck on.
        base = per_share_base if per_share_base is not None else self.shares_outstanding()
        aeg = self.aeg_entity(rho)
        continuing = {}
        for t in tranches:
            continuing[t] = sum(
                self.retired[t] * aeg[s] / base[s]
                for s in range(t + 2, self.cfg.last_year + 1)
                if s in aeg and base.get(s))
        aeg_ps = {s: aeg[s] / base[s] for s in self.years()
                  if s in aeg and base.get(s)}
        # Summed in sorted order so the result does not depend on dictionary
        # insertion order. Floating-point addition is not associative and a mean
        # that moves when a driver reorders its inputs is not reproducible.
        _v = sorted(aeg_ps.values())
        mean_aeg_ps = (sum(_v) / len(_v)) if _v else None

        out = {
            'rho': rho,
            'tranches': tranches,
            'excluded_years': excluded,
            'real_eps': eps,
            'real_price_paid': px,
            'per_year': per_year,
            'total': total,
            'negative_years': negative,
            'alt_per_year': alt_per_year,
            'alt_total': alt_total,
            'alt_negative_years': alt_negative,
            'break_even': break_even,
            'break_even_windows': windows,
            'headroom': (break_even - rho) if break_even is not None else None,
            'aeg_entity': aeg,
            'aeg_per_share': aeg_ps,
            'mean_aeg_per_share': mean_aeg_ps,
            'per_share_base': ('shares outstanding' if per_share_base is None
                               else 'supplied by the driver'),
            'continuing': continuing,
            'continuing_total': sum(continuing.values()),
            'band': None, 'primary': None, 'timing_dependence': None,
            'identity_residual': None, 'decomposition_note': None,
        }
        for y, why in sorted(excluded.items()):
            self.notes.append(f"entry effect, fiscal {y} not struck: {why}")

        if decompose:
            self._decompose_entry(out, estimator_window)
        return out

    # The earnings-timing decomposition, entry[t] = decision[t] + timing[t].
    # It splits the published figure and corrects nothing: no tranche is
    # dropped, no year is excluded, and the two parts sum to the entry effect
    # exactly. The timing term contains no rate at all, so the diagnostic is
    # rate-agnostic by construction. The trend level is not point-identified and
    # the disagreement between the symmetric and backward-looking estimator
    # families is itself the published result - see
    # docs/METHODOLOGY-ADDENDUM-Earnings-Timing-Decomposition-2026-08-13.md.
    def _decompose_entry(self, out, estimator_window=None):
        eps, tranches = out['real_eps'], out['tranches']
        window = (estimator_window if estimator_window is not None
                  else [y for y in self.years() if eps.get(y) is not None])
        positive = [y for y in window if eps.get(y) is not None and eps[y] > 0]
        if len(positive) < 3 or not tranches:
            out['decomposition_note'] = (
                "the earnings-timing decomposition is not computed: it needs at "
                f"least three positive real earnings observations and at least "
                f"one tranche, and this company offers {len(positive)} and "
                f"{len(tranches)}. This is reported, not worked around.")
            self.notes.append("ENTRY EFFECT: " + out['decomposition_note'])
            return out
        shares = {t: self.retired[t] for t in tranches}
        est = timing_decomposition.build_estimators(eps, window=window)
        band = timing_decomposition.decomposition_band(
            shares, eps, out['real_price_paid'], out['rho'], tranches, est)
        out['estimators'] = est
        out['band'] = band
        out['primary'] = band['loglinear']
        out['trend_growth'] = est['loglinear'].growth
        out['identity_residual'] = max(
            abs(d['decision'] + d['timing'] - d['entry']) for d in band.values())
        out['timing_dependence'] = timing_decomposition.timing_dependence(
            out['primary']['entry'], out['primary']['timing'])
        sym = [band[n] for n in timing_decomposition.SYMMETRIC_ESTIMATORS]
        bwd = [band[n] for n in timing_decomposition.BACKWARD_ESTIMATORS]
        out['symmetric_decision'] = (min(d['decision'] for d in sym),
                                     max(d['decision'] for d in sym))
        out['backward_decision'] = (min(d['decision'] for d in bwd),
                                    max(d['decision'] for d in bwd))
        out['symmetric_break_even'] = (min(d['break_even'] for d in sym),
                                       max(d['break_even'] for d in sym))
        out['backward_break_even'] = (min(d['break_even'] for d in bwd),
                                      max(d['break_even'] for d in bwd))
        out['families_disagree_on_sign'] = (
            min(d['decision'] for d in sym) * max(d['decision'] for d in bwd) < 0)
        if out['timing_dependence'] >= 1.0:
            self.notes.append(
                "ENTRY EFFECT, TIMING DEPENDENCE AT OR ABOVE 100 PERCENT: the "
                "accident of which earnings year followed each purchase is "
                "larger than the headline it sits inside. The entry effect must "
                "not be read as a verdict on the price paid for this company; "
                "publish the decomposition beside it, never the headline alone.")
        elif out['timing_dependence'] >= 0.5:
            self.notes.append(
                "ENTRY EFFECT, TIMING DEPENDENCE ELEVATED: earnings timing "
                "carries a large share of the verdict. Publish the "
                "decomposition alongside the entry effect.")
        if out['families_disagree_on_sign']:
            self.notes.append(
                "ENTRY EFFECT: the symmetric and backward-looking trend "
                "estimator families disagree on the SIGN of the price-decision "
                "component. The trend level is not point-identified on this "
                "company; publish the band rather than a point.")
        return out

    # ------------------------------------------------- treasury permanence
    # ADDENDUM ITEM 4, built 2026-08-13. Section 7's measure divides cash by the
    # reduction in shares outstanding and calls it the cost of removing a share
    # PERMANENTLY. For a company that cancels its repurchased shares, as Apple
    # does, that is exactly right. For a company that parks them in treasury -
    # Home Depot, Boeing, Salesforce, and a large fraction of the market - the
    # shares still exist, can be reissued tomorrow, and the reduction is a
    # decision rather than a fact.
    #
    # The arithmetic does not change and no figure moves. The WORD changes, from
    # "permanently removed" to "withdrawn from the float", and the treasury
    # balance is disclosed alongside it as the reissuable overhang. An honest
    # label on the same number.

    def treasury_status(self):
        """Does this company cancel its repurchased shares or hold them?

        Decided from the filings, never assumed, and never inferred from the
        absence of something. A company that tags a treasury balance holds; a
        company that tags a retirement and no treasury balance cancels; a
        company that tags neither is UNDETERMINED, and an undetermined company
        gets a label that claims neither permanence nor impermanence rather
        than a default. Silence in the filings is not evidence of cancellation.
        """
        bal_shares = {}
        for key in ('treasury_shares_balance', 'treasury_shares_balance_alt'):
            for y, e in self.sec.get(key, {}).items():
                v = e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                prev = bal_shares.get(y)
                if prev is None or e['filed'] > prev[1]:
                    bal_shares[y] = (v, e['filed'])
        bal_shares = {y: v for y, (v, _) in bal_shares.items()}

        bal_value = {}
        for key in ('treasury_value_balance', 'treasury_value_balance_alt'):
            for y, e in self.sec.get(key, {}).items():
                prev = bal_value.get(y)
                if prev is None or e['filed'] > prev[1]:
                    bal_value[y] = (abs(e['val']) / 1e6, e['filed'])
        bal_value = {y: v for y, (v, _) in bal_value.items()}

        has_balance = any(v for v in bal_shares.values()) or any(
            v for v in bal_value.values())
        has_retirement = any(self.sec.get(k) for k in RETIREMENT_KEYS)

        # Where the share count in treasury is not tagged but both the issued
        # and outstanding counts are, the overhang is their difference. That is
        # arithmetic on two filed facts, not an estimate, and it is the only
        # route available on a company like Salesforce, which tags the treasury
        # VALUE and never the share count.
        derived_from = None
        if not bal_shares:
            issued = self.sec.get('shares_issued', {})
            out = self.sec.get('shares_outstanding', {})
            for y in sorted(set(issued) & set(out)):
                i = issued[y]['val'] * self.cfg.split_factor(issued[y]['filed'])
                o = out[y]['val'] * self.cfg.split_factor(out[y]['filed'])
                if i - o > 0:
                    bal_shares[y] = (i - o) / 1e6
            if bal_shares:
                derived_from = ('CommonStockSharesIssued less '
                                'CommonStockSharesOutstanding')

        reissued = {y: e['val'] * self.cfg.split_factor(e['filed']) / 1e6
                    for y, e in self.sec.get('treasury_shares_reissued', {}).items()}

        has_treasury_flow = any(self.sec.get(k) for k in TREASURY_FLOW_KEYS)

        if has_balance or bal_shares:
            holds, basis = True, 'treasury'
            ev = []
            for key in TREASURY_BALANCE_KEYS:
                if self.sec.get(key):
                    ev.append(TAGS[key])
            evidence = ("holds repurchased shares in treasury; " +
                        ("tagged " + ", ".join(ev) if ev else
                         "shares issued exceed shares outstanding") +
                        (f"; overhang share count derived as {derived_from}"
                         if derived_from else ""))
            if has_retirement:
                # Acquires into treasury AND cancels. Boeing and American
                # Airlines both do this at different times. The balance is what
                # governs: whatever is still sitting there has not been
                # cancelled, whatever else the company also did.
                evidence += ("; NOTE this company ALSO tags a retirement, so it "
                             "both parks and cancels - the label follows the "
                             "balance that remains, which has not been cancelled")
        elif has_treasury_flow:
            holds, basis = True, 'treasury'
            evidence = ("acquires shares into treasury; tagged " +
                        ", ".join(TAGS[k] for k in TREASURY_FLOW_KEYS
                                  if self.sec.get(k)) +
                        ", and tags no retirement in any year. No treasury "
                        "BALANCE is available, so the size of the reissuable "
                        "overhang is not known from these inputs - only that "
                        "there is one")
        elif has_retirement:
            holds, basis = False, 'retired'
            evidence = ("cancels its repurchased shares; tagged " +
                        ", ".join(TAGS[k] for k in RETIREMENT_KEYS
                                  if self.sec.get(k)) +
                        " and no treasury balance in any year")
        else:
            holds, basis = None, 'undetermined'
            evidence = ("neither a retirement nor a treasury balance is tagged "
                        "in any year, so whether repurchased shares were "
                        "cancelled or parked cannot be read off the filings")

        last = max(bal_shares) if bal_shares else None
        status = {
            'holds_treasury': holds,
            'basis': basis,
            'evidence': evidence,
            'overhang_shares': bal_shares,
            'overhang_value': bal_value,
            'overhang_shares_latest': bal_shares.get(last),
            'overhang_value_latest': bal_value.get(max(bal_value)) if bal_value else None,
            'overhang_derived_from': derived_from,
            'reissued': reissued,
            'reissued_total': sum(reissued.values()) if reissued else 0.0,
        }
        self.treasury = status
        return status

    # The three readings of what one share cost, and the word that goes with
    # each. Only the middle one changes; A is the transacted price under every
    # regime and needs no qualifier.
    PERMANENCE_LABEL = {
        'retired': 'permanently removed',
        'treasury': 'withdrawn from the float',
        'undetermined': 'removed from the count',
    }
    PERMANENCE_NOTE = {
        'retired': ('These shares were cancelled. The reduction is permanent '
                    'and cannot be reversed without a new issuance.'),
        'treasury': ('These shares were NOT cancelled. They sit in treasury, '
                     'they can be reissued at the board\'s discretion, and the '
                     'reduction in the float is a decision rather than a fact. '
                     'The reissuable overhang is disclosed alongside.'),
        'undetermined': ('Whether these shares were cancelled or parked in '
                         'treasury is not determinable from the filings, so no '
                         'claim about permanence is made in either direction.'),
    }

    def net_retirement_cost(self, min_net_frac=0.0025):
        """The four readings of what a share cost, with the permanence label
        the company's own accounting actually supports.

        A  cash / GROSS shares retired ............. the transacted price
        B  cash / NET count reduction .............. cost per share {label}
        C  (cash - plan proceeds) / NET
        D  (cash + withholding - proceeds) / NET ... total cash spent on the count

        The arithmetic is identical for every company and identical to what it
        was before this method existed. What varies is the word attached to B,
        C and D, and whether a reissuable overhang has to be disclosed with
        them.

        `min_net_frac` is the two-sided denominator guard: a year whose net
        reduction is below this fraction of opening shares reports the fact
        instead of a ratio, because a ratio on a small or negative denominator
        is meaningless and far more likely to be believed than a missing one.
        """
        st = getattr(self, 'treasury', None) or self.treasury_status()
        S = self.shares_outstanding()
        g = lambda k, y: self.sec.get(k, {}).get(y, {}).get('val', 0) / 1e6

        years = [y for y in self.years()
                 if y in self.retired and y in self.issued]
        net = {y: self.retired[y] - self.issued[y] for y in years}
        ok = {y: (y - 1) in S and net[y] > min_net_frac * S[y - 1]
              for y in years}
        suppressed = [y for y in years if not ok[y]]

        cash = sum(self.sec.get('repurchase_cash', {}).get(y, {}).get('val', 0) / 1e6
                   - self.withholding_in_repurchase_cash.get(y, 0.0)
                   for y in years)
        gross = sum(self.retired[y] for y in years)
        net_t = sum(net.values())
        proc = sum(g('issuance_proceeds', y) for y in years)
        tax = sum(g('tax_withholding', y) for y in years)

        out = {
            'basis': st['basis'],
            'label': self.PERMANENCE_LABEL[st['basis']],
            'permanence_note': self.PERMANENCE_NOTE[st['basis']],
            'A_gross_price': (cash / gross) if gross else None,
            'B_per_share': (cash / net_t) if net_t else None,
            'C_per_share': ((cash - proc) / net_t) if net_t else None,
            'D_per_share': ((cash + tax - proc) / net_t) if net_t else None,
            'gross_retired': gross, 'net_reduction': net_t,
            'cash': cash, 'plan_proceeds': proc, 'withholding': tax,
            'per_year': {y: ((self.sec.get('repurchase_cash', {})
                              .get(y, {}).get('val', 0) / 1e6
                              - self.withholding_in_repurchase_cash.get(y, 0.0))
                             / net[y]) if ok[y] else None for y in years},
            'suppressed_years': suppressed,
            'min_net_frac': min_net_frac,
            'treasury': st,
        }
        if st['basis'] == 'treasury':
            oh = st['overhang_shares_latest']
            ohv = st['overhang_value_latest']
            bits = []
            if oh is not None:
                bits.append(f"{oh:,.0f}mn shares")
                if gross:
                    bits.append(f"{oh / gross:.2f}x the gross retirement of the window")
            if ohv is not None:
                bits.append(f"${ohv:,.0f}m at cost")
            self.notes.append(
                "TREASURY, NOT RETIREMENT: " + st['evidence'] + ". The cost per "
                "share is therefore the cost per share WITHDRAWN FROM THE FLOAT, "
                "not the cost of removing one permanently. Reissuable overhang: "
                + (", ".join(bits) if bits else "share count not tagged") +
                (f". {st['reissued_total']:,.0f}mn treasury shares were in fact "
                 "reissued inside the window."
                 if st['reissued_total'] else "."))
        elif st['basis'] == 'undetermined':
            self.notes.append(
                "PERMANENCE UNDETERMINED: " + st['evidence'] + ". The cost per "
                "share is reported as cost per share removed from the count, "
                "and no claim is made that the removal is permanent.")
        self.net_cost = out
        return out

    # --------------------------------------------------------- round trip
    # ADDENDUM ITEM 3, built 2026-08-13. Buy heavily near a peak, then issue
    # equity near a trough. It is the case that animates the entire public
    # argument against repurchases, and until now this template could not see
    # it, because Apple - the company it was generalized from - has never
    # raised equity, so nothing was built.
    #
    # WHAT IS AND IS NOT CLAIMED. Shares are fungible; no particular share
    # repurchased in 2016 is the share sold in 2020, and this measure does not
    # pretend otherwise. What it computes is an inventory question with an
    # exact answer: over this window the company took a quantity of its own
    # equity off the market at one set of prices and put a quantity back on at
    # another, and the difference in real cash on the overlapping quantity is a
    # fact about the program. Ordering is respected - only repurchases that
    # PRECEDE a raise can be matched to it - and the matching convention is
    # average cost, which is the one convention that does not require choosing
    # an arbitrary order within the pool. FIFO is computed alongside it as an
    # independent route and the two are required to agree.
    #
    # This is ex-post disclosure. It moves no valuation number, it is not an
    # expense, it does not enter the abnormal earnings growth account, and it
    # states no view about Intrinsic Value.

    # ------------------------------------------- excise tax (addendum item 5)
    def excise_exposure(self, y):
        """Fraction of fiscal year `y` that falls after 2022-12-31, by month.

        The excise applies to repurchases made after that date, not to fiscal
        years beginning after it. A September year end therefore has a first
        exposed year that is only three quarters exposed, and a January year end
        one that is eleven twelfths exposed. Charging a full year of tax to a
        partly exposed year would overstate it, and doing so silently is exactly
        the failure this study keeps finding.

        This is a proration by MONTHS, not by repurchase activity, because the
        study cannot see within-year repurchase timing. It is an approximation
        and is announced as one wherever it is used.
        """
        months = self.cfg.fiscal_months(y)
        if not months:
            return 0.0
        return sum(1 for m in months if m > EXCISE_EFFECTIVE_AFTER) / len(months)

    def excise_tax(self, disclosed=None, allow_statutory_estimate=False,
                   rate=EXCISE_RATE):
        """The Inflation Reduction Act excise on net repurchases, per year.

        WHY THIS METHOD IS NOT A ONE-LINE TAG READ, WHICH IS WHAT THE WORK ORDER
        ASSUMED. Three things were established against live filings on
        2026-08-13 and each of them breaks the obvious implementation:

        1. There is no `ExciseTaxPayable`. The only us-gaap element for this is
           `ShareRepurchaseProgramExciseTax`. Companies that disclose the figure
           mostly do it through their own extension elements, under four
           different names on the four companies checked, and an extension
           element is not reachable through the us-gaap concept interface and
           does not appear in `companyfacts` at all. So a driver may have to
           read the number off the filing and hand it in through `disclosed`.

        2. Where BOTH disclosures exist they can disagree, and the tagged one is
           the wrong one. O'Reilly Automotive's fiscal 2025 note says the excise
           "assessed at one percent of the fair market value of NET shares
           repurchased, was $21.0 million"; the statement of stockholders'
           equity in the same filing charges $18.720 million. The note's figure
           is one percent of GROSS repurchases to the rounding presented
           ($2,096.962m x 1% = $20.970m, which prints as $21.0m); the equity
           statement's is not, and the difference is the netting rule the note's
           own sentence claims to have applied. The equity statement is the
           charge that actually hit the accounts, so it wins, and a disagreement
           is reported rather than resolved by preference.

        3. It is accrued in one year and PAID in the next. O'Reilly accrued
           $28.830m in 2023 and paid nothing; paid $28.830m in 2024 against a
           2024 accrual of $17.011m; paid $17.012m in 2025. A sources-and-uses
           table is a cash account, so the accrual year and the payment year are
           not the same year and must not be quietly merged.

        `disclosed` is {fiscal_year: $m}, or {fiscal_year: (accrual $m, source)}.
        Pass what the filing says. Anything passed here is treated as filed fact.

        `allow_statutory_estimate` is the gate. Left False - the default - a
        fiscal year with any exposure and no disclosed figure raises
        ExciseTaxUndisclosed, because a company that does not publish the number
        must not be silently credited with a zero. Set True only when the
        absence has been checked and is itself the finding, and the study is
        prepared to publish a reconstruction that is labelled, in the document,
        as the study's own arithmetic rather than the company's disclosure.

        THE RECONSTRUCTION IS A BAND, NEVER A POINT, and both ends are printed.
        The upper end is one percent of gross repurchases: an upper bound,
        because the netting rule can only reduce the base and stock issued is
        never negative. The lower end nets the fair market value of shares
        issued during the year, valued at the fiscal year's mean price. The
        gross end is computed twice from two independently filed lines - the
        cash-flow repurchase line and the equity-statement repurchase line -
        which is the same pair the study already carries and reconciles
        elsewhere, so the cash-versus-accrual spread is visible here too.
        """
        disclosed = dict(disclosed or {})
        for y, e in (self.sec.get('excise_tax') or {}).items():
            if y not in disclosed:
                disclosed[y] = (e['val'] / 1e6,
                                'us-gaap:' + TAGS['excise_tax'] + ' (tagged)')

        g = lambda k, y: self.sec.get(k, {}).get(y, {}).get('val', 0) / 1e6
        years, undisclosed, notes = {}, [], []
        for y in self.years():
            exposure = self.excise_exposure(y)
            if exposure <= 0:
                years[y] = {'exposure': 0.0, 'status': 'pre-statute',
                            'disclosed': None, 'value': 0.0, 'low': 0.0,
                            'high': 0.0, 'source': 'statute not yet in force'}
                continue

            gross_cash = (g('repurchase_cash', y)
                          - self.withholding_in_repurchase_cash.get(y, 0.0))
            gross_accrual = g('repurchase_accrual', y)
            px = self.fy_mean_price(y)
            iss = getattr(self, 'issued', {}).get(y)
            issued_fmv = (iss * px) if (iss is not None and px) else None

            high = rate * gross_cash * exposure
            high_accrual = (rate * gross_accrual * exposure
                            if gross_accrual else None)
            low = (rate * max(gross_cash - issued_fmv, 0.0) * exposure
                   if issued_fmv is not None else None)

            d = disclosed.get(y)
            if d is not None:
                val, src = d if isinstance(d, tuple) else (d, 'filed')
                years[y] = {'exposure': exposure, 'status': 'disclosed',
                            'disclosed': val, 'value': val, 'low': val,
                            'high': val, 'source': src,
                            'statutory_high': high, 'statutory_low': low,
                            'statutory_high_accrual': high_accrual,
                            'issued_fmv': issued_fmv}
                continue

            undisclosed.append(y)
            if not allow_statutory_estimate:
                raise ExciseTaxUndisclosed(
                    f"{self.cfg.ticker} FY{y} is {100*exposure:.0f}% exposed to "
                    "the section 4501 excise on net repurchases and no filed "
                    "figure for it was found, in the us-gaap tag or in anything "
                    "handed in through `disclosed`. It is NOT zero. Either "
                    "supply the filed figure or set allow_statutory_estimate="
                    "True and publish the reconstruction as an announced "
                    "estimate.")
            years[y] = {
                'exposure': exposure, 'status': 'estimated', 'disclosed': None,
                'value': low if low is not None else high,
                'low': low if low is not None else high, 'high': high,
                'statutory_high': high, 'statutory_low': low,
                'statutory_high_accrual': high_accrual,
                'issued_fmv': issued_fmv,
                'source': ('statutory reconstruction - the company discloses no '
                           'figure for this year'),
            }

        if undisclosed:
            notes.append(
                "EXCISE TAX NOT DISCLOSED in " +
                ", ".join(f"FY{y}" for y in undisclosed) +
                ". The one percent excise under section 4501 applied to these "
                "years and the company publishes no figure for it, so every "
                "excise number shown for them is this study's own arithmetic "
                "and not a filed fact. It is presented as a band whose upper "
                "end is one percent of gross repurchases and whose lower end "
                "applies the netting rule at the fiscal year's mean price.")
        straddle = [y for y, r in years.items() if 0 < r['exposure'] < 1]
        if straddle:
            notes.append(
                "excise exposure is PARTIAL in " +
                ", ".join(f"FY{y} ({100*years[y]['exposure']:.0f}%)"
                          for y in sorted(straddle)) +
                ", because the statute reaches repurchases made after "
                "2022-12-31 and that fiscal year straddles the date. The "
                "proration is by months, not by repurchase activity, which the "
                "filings do not show.")
        if any(r['status'] == 'estimated' for r in years.values()):
            notes.append(
                "the excise is assessed on a TAXABLE year; this study prorates "
                "onto FISCAL years, and where the two differ the annual split "
                "is approximate even though the total is not.")

        live = [r for r in years.values() if r['exposure'] > 0]
        out = {
            'rate': rate, 'years': years, 'notes': notes,
            'undisclosed_years': undisclosed,
            'any_exposure': bool(live),
            'all_disclosed': bool(live) and not undisclosed,
            'total_low': sum(r['low'] for r in live) if live else 0.0,
            'total_high': sum(r['high'] for r in live) if live else 0.0,
            'total': sum(r['value'] for r in live) if live else 0.0,
        }
        self.excise = out
        self.notes.extend(notes)
        return out

    def real_repurchase_price(self, y):
        """Real price paid per share retired in fiscal year y, in base-year
        dollars, or None where the year is unresolved.

        Removes any employee tax withholding folded into the same cash-flow
        line. That withholding is not a repurchase; leaving it in overstates
        the price paid, and on the year it matters most it is a large share of
        a small line (American Airlines fiscal 2020: $15m of $173m, nine
        percent of the line).
        """
        q = self.retired.get(y)
        if not q:
            return None
        cash = self.sec.get('repurchase_cash', {}).get(y, {}).get('val')
        if cash is None:
            return None
        cash = cash / 1e6 - self.withholding_in_repurchase_cash.get(y, 0.0)
        return (cash / q) * self.deflator[y]

    def reconcile_raises(self, tolerance=0.005, _quiet=False):
        """The equity statement against the financing-activities line.

        This is the guard the price validator cannot be. It compares the sum of
        the disclosed issuance lines for a year against the cash-flow equity
        line for the same year, and requires any difference beyond `tolerance`
        of the line to be NAMED in `raise_reconciling_items`. An unnamed
        difference refuses that year's raise rather than absorbing it into the
        price. Returns {fy: dict} and appends a note per year that does not
        reconcile cleanly.
        """
        if getattr(self, '_reconciled', False):
            return self.raise_reconciliation
        self._reconciled = True
        cf = {}
        for key in ('equity_raise_cash_flow', 'equity_raise_cash_flow_alt',
                    'equity_raise_cash_flow_warrants'):
            for y, e in self.sec.get(key, {}).items():
                cf.setdefault(y, {})[key] = e['val'] / 1e6

        out, refused = {}, set()
        by_year = {}
        for r in self.raises:
            by_year.setdefault(r.fiscal_year, []).append(r)

        for y, rs in sorted(by_year.items()):
            stmt = sum(r.proceeds for r in rs)
            line = max(cf.get(y, {}).values()) if cf.get(y) else None
            named = self.raise_reconciling_items.get(y, {})
            named_total = sum(named.values())
            if line is None:
                out[y] = {'statement': stmt, 'cash_flow_line': None,
                          'gap': None, 'named': named, 'clean': None}
                self.notes.append(
                    f"FY{y} equity raise: no financing-activities equity line "
                    "tagged, so the equity-statement figure could not be "
                    "cross-checked against the cash flow statement. The raise "
                    "is used as disclosed and this is stated rather than "
                    "assumed away.")
                continue
            gap = line - stmt
            resid = gap - named_total
            clean = abs(resid) <= tolerance * abs(line)
            out[y] = {'statement': stmt, 'cash_flow_line': line, 'gap': gap,
                      'named': named, 'residual': resid, 'clean': clean}
            if named:
                self.notes.append(
                    f"FY{y} equity raise reconciles: equity statement "
                    f"${stmt:,.0f}m against a financing-activities line of "
                    f"${line:,.0f}m, a gap of ${gap:,.0f}m accounted for by " +
                    ", ".join(f"{k} ${v:,.0f}m" for k, v in named.items()) +
                    ". The cash-flow line is NOT the numerator; the equity "
                    "statement is.")
            if not clean:
                refused.add(y)
                self.notes.append(
                    f"FY{y} EQUITY RAISE REFUSED: the financing-activities "
                    f"line (${line:,.0f}m) and the equity statement "
                    f"(${stmt:,.0f}m) differ by ${gap:,.0f}m, of which "
                    f"${resid:,.0f}m is unexplained. An unexplained difference "
                    "is not netted, averaged or absorbed into the issue price "
                    "- the year is left out of the round trip and said so.")
        self.raise_refusals = refused
        self.raise_reconciliation = out
        return out

    def resolved_raises(self):
        """Raises that survived reconciliation, with ordinary employee-plan
        share issuance netted out of the share count.

        Netting matters because the plan flow is continuous and small while a
        distress raise is lumpy and large; without netting, every year of
        routine option and restricted-stock settlement would enter the measure
        as if the company had gone to the market for capital.
        """
        if not hasattr(self, 'raise_refusals'):
            self.reconcile_raises()
        out = []
        for r in sorted(self.raises, key=lambda r: r.fiscal_year):
            if r.fiscal_year in self.raise_refusals:
                continue
            out.append(r)
        plan_total = sum(self.plan_shares.get(y, 0.0)
                         for y in {r.fiscal_year for r in out})
        if plan_total and out and not getattr(self, '_noted_plan_netting', False):
            self._noted_plan_netting = True
            self.notes.append(
                f"round trip: {plan_total:,.1f}mn shares of ordinary "
                "employee-plan issuance in the raise years are excluded from "
                "the issued side, so a routine compensation flow cannot be "
                "read as a distress raise. Plan issuance is measured on its "
                "own tagged share count, not inferred from a residual.")
        return out

    def _plan_netted_shares(self, raises):
        """Net each year's ordinary employee-plan issuance out of that year's
        raises exactly once.

        Subtracting the year's plan figure from EVERY raise line in that year
        double-counts it. American Airlines' fiscal 2020 has two lines - the
        underwritten offerings and the at-the-market programme - so the naive
        version removed 1.6 million shares of plan issuance twice and
        understated the round trip by that much. Returns {id(raise): net
        shares}, drawing the year's plan flow down across its raises in order.
        """
        remaining = {}
        for r in raises:
            remaining.setdefault(r.fiscal_year,
                                 self.plan_shares.get(r.fiscal_year, 0.0))
        out = {}
        for r in sorted(raises, key=lambda r: (r.fiscal_year, -r.shares)):
            take = min(remaining[r.fiscal_year], r.shares)
            remaining[r.fiscal_year] -= take
            out[id(r)] = r.shares - take
        return out

    def round_trip(self, match='average_cost'):
        """Repurchase cash per year against equity raised per year, at the
        prices at each end, and the cumulative round-trip loss where both
        occurred inside the window.

        Everything is in base-year (real) dollars. `match` is 'average_cost'
        (primary) or 'fifo' (the independent cross-check); the two are required
        to agree on matched shares exactly and on the loss to within a stated
        tolerance, and round_trip_reconciled() below performs that test.

        Returns a dict. `has_round_trip` False means the company issued no
        equity inside the window - a fact about the company, reported as such,
        with every total at a true zero rather than a missing value.
        """
        raises = self.resolved_raises()
        buy_years = [y for y in self.years()
                     if self.retired.get(y) and self.real_repurchase_price(y)]

        rows, pool, fifo_pool = [], [], []
        cost_matched = proceeds_matched = shares_matched = 0.0
        unmatched_raise_shares = unmatched_raise_proceeds = 0.0
        fifo_cost_matched = 0.0

        raises_by_year = {}
        for r in raises:
            raises_by_year.setdefault(r.fiscal_year, []).append(r)
        net_shares = self._plan_netted_shares(raises)

        for y in self.years():
            if y in buy_years:
                q, px = self.retired[y], self.real_repurchase_price(y)
                pool.append([q, px])
                fifo_pool.append([q, px])
            for r in raises_by_year.get(y, []):
                q_raise = net_shares[id(r)]
                px_sell = r.price * self.deflator[y]
                if q_raise <= 0:
                    self.notes.append(
                        f"FY{y} raise '{r.label}': net of employee-plan "
                        "issuance the share count is not positive, so it is "
                        "not treated as a raise.")
                    continue
                avail = sum(t[0] for t in pool)
                take = min(avail, q_raise)
                # ---- average cost (primary)
                cost = 0.0
                if take > 0:
                    avg = sum(t[0] * t[1] for t in pool) / avail
                    cost = take * avg
                    left = take
                    for t in pool:
                        d = min(t[0], left)
                        t[0] -= d
                        left -= d
                        if left <= 1e-12:
                            break
                    pool[:] = [t for t in pool if t[0] > 1e-12]
                # ---- FIFO (independent route)
                fifo_cost, left = 0.0, take
                for t in fifo_pool:
                    d = min(t[0], left)
                    fifo_cost += d * t[1]
                    t[0] -= d
                    left -= d
                    if left <= 1e-12:
                        break
                fifo_pool[:] = [t for t in fifo_pool if t[0] > 1e-12]

                proceeds = take * px_sell
                rows.append({
                    'fiscal_year': y, 'label': r.label,
                    'raise_shares_gross': r.shares,
                    'plan_shares_netted': r.shares - q_raise,
                    'raise_shares_net': q_raise,
                    'matched_shares': take,
                    'unmatched_shares': q_raise - take,
                    'real_price_received': px_sell,
                    'nominal_price_received': r.price,
                    'real_avg_price_paid': (cost / take) if take else None,
                    'real_cost_matched': cost,
                    'real_proceeds_matched': proceeds,
                    'real_loss': cost - proceeds,
                    'fifo_real_cost_matched': fifo_cost,
                    'source': r.source,
                })
                shares_matched += take
                cost_matched += cost
                fifo_cost_matched += fifo_cost
                proceeds_matched += proceeds
                unmatched_raise_shares += q_raise - take
                unmatched_raise_proceeds += (q_raise - take) * px_sell

        total_buy_cost = sum(self.retired[y] * self.real_repurchase_price(y)
                             for y in buy_years)
        total_buy_shares = sum(self.retired[y] for y in buy_years)
        loss = cost_matched - proceeds_matched
        return {
            'has_round_trip': bool(rows),
            'episodes': rows,
            'matched_shares': shares_matched,
            'real_cost_matched': cost_matched,
            'real_proceeds_matched': proceeds_matched,
            'real_loss': loss,
            'fifo_real_cost_matched': fifo_cost_matched,
            'fifo_real_loss': fifo_cost_matched - proceeds_matched,
            'recovery_ratio': (proceeds_matched / cost_matched)
                              if cost_matched else None,
            'real_avg_price_paid_matched': (cost_matched / shares_matched)
                                           if shares_matched else None,
            'real_avg_price_received': (proceeds_matched / shares_matched)
                                       if shares_matched else None,
            'unmatched_raise_shares': unmatched_raise_shares,
            'unmatched_raise_proceeds': unmatched_raise_proceeds,
            'total_real_repurchase_cost': total_buy_cost,
            'total_shares_retired': total_buy_shares,
            'share_of_program_round_tripped':
                (shares_matched / total_buy_shares) if total_buy_shares else 0.0,
            'loss_share_of_program':
                (loss / total_buy_cost) if total_buy_cost else 0.0,
        }

    def round_trip_reconciled(self, share_tol=1e-9, loss_tol=1e-6):
        """The round trip computed two independent ways, as the house
        convention requires before a sentence is written about what it means.

        Route A, average cost, draws every match from a single pooled average.
        Route B, FIFO, matches tranche by tranche in the order the shares were
        bought. They are genuinely different arithmetic on genuinely different
        intermediate quantities, and they must agree on the matched share count
        exactly. Where they disagree on the loss, the difference is the
        ordering effect and is reported rather than suppressed - it is real
        information about how concentrated the round trip is in a few tranches.
        """
        rt = self.round_trip()

        # Route B, rebuilt from the inputs by a separate function rather than
        # read off the same loop, so the agreement below is a test and not a
        # tautology. round_trip() also carries a FIFO figure computed inline;
        # that one shares the loop's matched quantity by construction and is
        # therefore NOT independent evidence. This one is.
        fifo = self._fifo_round_trip()
        rt['fifo_rebuilt'] = fifo
        rt['fifo_agrees_on_shares'] = (
            abs(fifo['matched_shares'] - rt['matched_shares']) <= share_tol)
        rt['fifo_agrees_on_proceeds'] = (
            abs(fifo['real_proceeds_matched'] - rt['real_proceeds_matched'])
            <= max(loss_tol, 1e-9 * abs(rt['real_proceeds_matched'])))
        rt['fifo_inline_agrees'] = (
            abs(fifo['real_cost_matched'] - rt['fifo_real_cost_matched'])
            <= max(loss_tol, 1e-9 * abs(rt['fifo_real_cost_matched'] or 1.0)))

        # Route C, independent of both matching conventions: the loss must also
        # equal the sum over episodes of matched shares times the difference
        # between the two prices. This is the definition restated, and it
        # closes only if the pool drawdown and the cost accumulation agree.
        route_c = sum(r['matched_shares'] *
                      ((r['real_avg_price_paid'] or 0.0) - r['real_price_received'])
                      for r in rt['episodes'])
        rt['route_c_real_loss'] = route_c
        rt['route_c_agrees'] = abs(route_c - rt['real_loss']) <= max(
            loss_tol, 1e-9 * abs(rt['real_loss']))

        # The ordering effect is the gap between average cost and FIFO. It is
        # not an error and is not suppressed: it says how much of the answer
        # depends on which repurchase tranche one calls the one that was sold
        # back, which is not a knowable fact. A large ordering effect is a
        # reason to publish the band, exactly as the study already does for the
        # cost of equity and the earnings-timing trend.
        rt['ordering_effect'] = fifo['real_loss'] - rt['real_loss']
        rt['ordering_effect_share'] = (
            abs(rt['ordering_effect']) / abs(rt['real_loss'])
            if rt['real_loss'] else 0.0)
        return rt

    def _fifo_round_trip(self):
        """Route B. Deliberately written as a separate, plainer pass over the
        same primary inputs - oldest tranche first, no pooled average anywhere -
        so that agreement with round_trip() is evidence rather than restatement.
        """
        raises = self.resolved_raises()
        by_year = {}
        for r in raises:
            by_year.setdefault(r.fiscal_year, []).append(r)
        net_shares = self._plan_netted_shares(raises)
        tranches = []          # [shares remaining, real price paid], oldest first
        matched = cost = proceeds = 0.0
        for y in self.years():
            px_buy = self.real_repurchase_price(y)
            if self.retired.get(y) and px_buy:
                tranches.append([self.retired[y], px_buy])
            for r in by_year.get(y, []):
                want = net_shares[id(r)]
                if want <= 0:
                    continue
                px_sell = r.price * self.deflator[y]
                for t in tranches:
                    if want <= 1e-12:
                        break
                    if t[0] <= 1e-12:
                        continue
                    d = min(t[0], want)
                    t[0] -= d
                    want -= d
                    matched += d
                    cost += d * t[1]
                    proceeds += d * px_sell
        return {'matched_shares': matched, 'real_cost_matched': cost,
                'real_proceeds_matched': proceeds, 'real_loss': cost - proceeds}

    def validate_raise_prices(self, traded_range=None):
        """Every implied issue price must be a price that existed, tested
        against intra-period highs and lows and never against period-end
        closes. The same guard the repurchase side has carried since the
        template was generalized; a raise struck at an impossible price is the
        same failure as a repurchase struck at one.
        """
        fails = []
        for r in self.resolved_raises():
            y, px = r.fiscal_year, r.price
            if traded_range and y in traded_range:
                lo, hi = traded_range[y]
            else:
                v = [self.prices[k] for k in self.cfg.fiscal_months(y)
                     if k in self.prices]
                if not v:
                    continue
                lo, hi = min(v), max(v)
                self.notes.append(
                    f"FY{y} raise price validated against period-end closes "
                    "only; intra-period extremes are stricter")
            if not (lo <= px <= hi):
                fails.append((y, r.label, px, lo, hi))
        return fails

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

        # DEFECT (2026-08-13, found on Hertz Global Holdings during the
        # convergence sweep). `fy_mean_price()` is documented to return None
        # for a fiscal year with no priced calendar month in the series - a
        # real gap (a trading halt, a bankruptcy reorganization, a ticker
        # that did not exist yet) rather than a bug in the price fetch - and
        # this line multiplied it into the market value delivered
        # unconditionally, which is a TypeError on any company that has one.
        # Those years are excluded from THIS measure exactly the way
        # unresolved-issuance years already are, and named the same way.
        price_missing = [y for y in ys if self.fy_mean_price(y) is None]
        ys_priced = [y for y in ys if y not in price_missing]
        delivered = sum(issued.get(y, 0) * self.fy_mean_price(y) for y in ys_priced)
        tax = sum(g('tax_withholding', y) for y in ys)
        proceeds = sum(g('issuance_proceeds', y) for y in ys)
        sbc = sum(g('sbc', y) for y in ys)
        econ = delivered + tax - proceeds
        caveat = ('cumulative only; single years compare unrelated award '
                  'cohorts')
        if unresolved:
            caveat += (f'; excludes {len(unresolved)} unresolved year(s) '
                       'with no determinable issuance')
        if price_missing:
            caveat += (f'; excludes {len(price_missing)} year(s) with no '
                       'priced calendar month in the fiscal year (a trading '
                       'gap, a halt, or a reorganization) - '
                       f'FY{sorted(price_missing)}')
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

    # ------------------------------------------- injection-suite hardening
    # Four checks added 2026-08-13 (hardening-endpoint session, second pass)
    # after code/injection_test.py found the corruption it deliberately
    # applies walks through with no guard at all. Each is additive - a new
    # note, never a changed VALUE - so none of them can move a number in an
    # existing study; that is what lets them land without re-proving the
    # Apple byte-identical regeneration touches anything but its own text.
    def validate_deflator(self):
        """The deflator is a MULTIPLIER: nominal times this equals base-year
        dollars, and it must get SMALLER as the fiscal year approaches today
        - the earlier a dollar was earned, the more it must be scaled up to
        reach today's price level. Nothing before this checked the
        deflator's own plausibility; it was applied and trusted. A series
        divided instead of multiplied downstream, or handed in already
        inverted, still contains superficially plausible numbers - all
        positive, all in a similar range - and closes every identity the
        template checks while being wrong in every real-dollar figure it
        touches.

        Checked at the whole-window level, first year against last, rather
        than year over year: a single year CAN legitimately rise on the
        CPI's own disinflation (the committed engine series does, fiscal
        2009 over fiscal 2008, 1.55652 to 1.56208) and a strict step-by-step
        monotonicity requirement would misfire on that real data. A 2%
        tolerance on the endpoint comparison absorbs it; the corruption this
        guards against is not a 2% effect, it inverts the whole series.
        """
        ys = sorted(self.deflator)
        bad_values = [y for y in ys if self.deflator[y] is None or self.deflator[y] <= 0]
        if bad_values:
            self.notes.append(
                "DEFLATOR IMPLAUSIBLE: FY" +
                ", FY".join(str(y) for y in bad_values) +
                " carries a non-positive or missing multiplier, which cannot "
                "be a base-year price-level ratio.")
            return
        if len(ys) >= 2:
            first, last = ys[0], ys[-1]
            if self.deflator[first] < self.deflator[last] * 0.98:
                self.notes.append(
                    f"DEFLATOR IMPLAUSIBLE: the multiplier for FY{first} "
                    f"({self.deflator[first]:.4f}) is SMALLER than for FY{last} "
                    f"({self.deflator[last]:.4f}). The convention is nominal "
                    "times this equals base-year dollars, so the EARLIER year "
                    "must carry the LARGER multiplier under any sustained "
                    "inflation, and every window this template has studied has "
                    "had one. This is the signature of a deflator applied "
                    "backwards - divided instead of multiplied, or supplied "
                    "already inverted - and every real-dollar figure in this "
                    "report inherits it.")

    def validate_dividend_series(self):
        """DEFECT 15 (found on AutoZone) distinguishes a company that files
        no dividend element at all (asserted a genuine zero, on evidence)
        from a dividend series that was never fetched (refused). It does not
        distinguish a THIRD case: a dividend element that IS filed, present
        in `self.fin['dividends']`, where every value across the window
        happens to be exactly zero. That looks identical to the genuine
        no-dividend case to every method that reads it, but it was never
        asserted as one - it is either a real, unusual fact about the
        company (a program that pays nothing while still tagging the
        element) or a data problem, and it is not this template's place to
        assume which."""
        d = self.fin.get('dividends')
        if d and not getattr(self, 'dividends_are_zero', False):
            vals = [d[y] for y in self.years() if y in d]
            if vals and all(v == 0 for v in vals):
                self.notes.append(
                    "DIVIDEND SERIES PRESENT BUT EVERY VALUE IS ZERO: a "
                    "dividend element IS filed - unlike the genuine "
                    "no-dividend case, which files no element at all and is "
                    "asserted as a fact, not inferred - yet every value across "
                    "the window is exactly zero. Check this against the filing "
                    "before anything downstream (the entity-level abnormal "
                    "earnings growth recursion sums dividends and repurchase "
                    "cash together) trusts it.")

    def validate_eps_consistency(self, tolerance=0.03):
        """Diluted earnings per share has a second, independent route: net
        income divided by the weighted-average diluted share count, both of
        which reach this template already restated onto today's split basis
        (share counts are, everywhere else in this file). The two are not
        expected to match exactly - preferred dividends, discontinued
        operations and rounding all open small, real gaps - but a mismatch
        of more than a few percent is not a rounding difference.

        DEFECT 25 (found on Booking Holdings) fixed this for run_study.py's
        own ingestion path: `split_factor()` is now applied to diluted EPS
        there, from each fact's own filed date, the same way it already was
        for share counts and prices. But `split_factor()` is applied to EPS
        NOWHERE inside this file, and any driver that constructs a
        BuybackStudy directly - as several already do - carries no defense
        of its own if it hands in an EPS series that was never restated.
        That is exactly what an as-filed EPS fact, read before a company's
        own split, looks like: off from net income divided by weighted
        shares by close to the split ratio. This is the second, independent
        route this project's own audit-point philosophy calls for (I5):
        it is computed here from net income and the share count, never by
        calling `real_eps()` or trusting `diluted_eps` itself.
        """
        ni = self.fin.get('net_income', {})
        eps = self.fin.get('diluted_eps', {})
        wtd = self.fin.get('wtd_diluted_shares', {})
        bad = []
        for y in sorted(set(ni) & set(eps) & set(wtd)):
            if not wtd.get(y) or eps.get(y) is None or ni.get(y) is None:
                continue
            implied = ni[y] / wtd[y]
            if implied == 0:
                continue
            if abs(eps[y] / implied - 1.0) > tolerance:
                bad.append((y, eps[y], implied))
        if bad:
            self.notes.append(
                "EPS INCONSISTENT WITH NET INCOME / WEIGHTED SHARES: FY" +
                ", FY".join(f"{y} (filed {e:.3f} vs implied {i:.3f})"
                           for y, e, i in bad) +
                f" - filed diluted EPS disagrees with net income divided by the "
                f"weighted-average diluted share count by more than "
                f"{100*tolerance:.0f}% in the year(s) named. Both are supposed "
                "to be on today's split basis by the time they reach here; a "
                "gap this size is the signature of an EPS series that was "
                "never restated for a split and should not be trusted until "
                "resolved.")

    def validate_no_duplicated_years(self,
            keys=('net_income', 'diluted_eps', 'operating_income',
                  'wtd_diluted_shares')):
        """A fiscal year's value copied exactly into the year beside it -
        the signature of a copy-paste or a re-indexing error - reads as a
        genuinely flat business to every identity this template checks, and
        nothing before this looked for it. Exact equality between two
        CONSECUTIVE fiscal years, to the precision these figures are filed
        at, essentially never happens by coincidence in a real company's
        reported net income, EPS, operating income or share count; when it
        does, it is worth a person's look before anything downstream trusts
        it. This is a NOTE, not a refusal - a truly flat year is possible
        and only the filing can settle it, this template cannot.
        """
        hits = []
        for key in keys:
            s = self.fin.get(key) or {}
            ys = sorted(s)
            for a, b in zip(ys, ys[1:]):
                if b == a + 1 and s[a] is not None and s[b] is not None \
                        and s[a] == s[b] != 0:
                    hits.append((key, a, b, s[a]))
        if hits:
            self.notes.append(
                "SUSPICIOUSLY IDENTICAL ADJACENT YEARS: " +
                "; ".join(f"{key} FY{a} and FY{b} are EXACTLY equal ({v:,.4f})"
                         for key, a, b, v in hits) +
                " - exact equality between consecutive fiscal years in a filed "
                "dollar or per-share figure essentially never happens by "
                "coincidence. This is the signature of a copy-paste or "
                "re-indexing error, not asserted as one; check it against the "
                "filing before trusting anything downstream.")

    # ----------------------------------------------------------------- run
    def run(self, traded_range=None):
        self.validate_deflator()
        self.validate_dividend_series()
        self.validate_eps_consistency()
        self.validate_no_duplicated_years()
        self.retired, self.issued = self.share_flows()
        self.price_failures = self.validate_prices(self.retired, traded_range)
        if self.price_failures:
            self.notes.append(
                "IMPLIED PRICE OUTSIDE TRADED RANGE in " +
                ", ".join(f"FY{y}" for y, *_ in self.price_failures) +
                " - do not publish until resolved")
        self.attribution = self.eps_attribution()
        self.timing_result = self.timing(self.retired)
        # Treasury permanence runs before anything is labelled, so that no
        # measure in this study claims a share was removed permanently on a
        # company whose own balance sheet says otherwise.
        self.treasury_status()
        self.net_cost = self.net_retirement_cost()
        # The round trip runs on every company, including those that never
        # raised equity. On those it returns a true zero and says so; a company
        # that did not do the thing is a finding, not a missing input.
        self.reconcile_raises()
        self.raise_price_failures = self.validate_raise_prices(traded_range)
        if self.raise_price_failures:
            self.notes.append(
                "IMPLIED ISSUE PRICE OUTSIDE TRADED RANGE in " +
                ", ".join(f"FY{y}" for y, *_ in self.raise_price_failures) +
                " - do not publish until resolved")
        self.round_trip_result = self.round_trip_reconciled()
        if not self.round_trip_result['has_round_trip']:
            self.notes.append(
                "round trip: this company issued no equity inside the window, "
                "so there is no round trip to measure. Every round-trip total "
                "is a true zero, not a missing value.")
        self.wedge = self.comp_wedge(self.issued)
        if self.wedge.get('missing_components'):
            self.notes.append(
                "COMPENSATION WEDGE MISSING COMPONENT(S): " +
                ", ".join(self.wedge['missing_components']) +
                " - this company does not tag them at all, they are NOT "
                "genuinely zero, and the wedge above is understated by an "
                "unknown amount")
        return self

    def round_trip_report(self):
        """The round-trip block, on its own so a company that is being used to
        prove this one measure need not run the whole study to print it."""
        rt = getattr(self, 'round_trip_result', None)
        if rt is None:
            return []
        L = ["", "ROUND TRIP (real, base-year dollars)"]
        if not rt['has_round_trip']:
            return L + ["  no equity raised inside the window - nothing to match"]
        L += [f"  shares round-tripped   {rt['matched_shares']:12,.1f} mn"
              f"   ({100*rt['share_of_program_round_tripped']:.1f}% of shares retired)",
              f"  real price paid        {rt['real_avg_price_paid_matched']:12,.2f}",
              f"  real price received    {rt['real_avg_price_received']:12,.2f}",
              f"  real cost              {rt['real_cost_matched']:12,.0f}",
              f"  real proceeds          {rt['real_proceeds_matched']:12,.0f}",
              f"  REAL ROUND-TRIP LOSS   {rt['real_loss']:12,.0f}"
              f"   ({100*rt['recovery_ratio']:.1f} cents back on the dollar)",
              f"  FIFO cross-check       {rt['fifo_rebuilt']['real_loss']:12,.0f}"
              f"   (ordering effect {100*rt['ordering_effect_share']:.1f}%)",
              f"  loss / program cost    {100*rt['loss_share_of_program']:11,.1f}%"]
        if rt['unmatched_raise_shares'] > 1e-9:
            L += [f"  raised beyond the pool {rt['unmatched_raise_shares']:12,.1f} mn"
                  "   - new equity, not a round trip; excluded from the loss"]
        return L

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

        # A quantity an earlier guard declined to compute prints as the word
        # "unavailable". It must never print as a zero, an em dash or a blank,
        # each of which a reader can mistake for a measurement (defects 14, 18).
        def _f(v, fmt):
            return format(v, fmt) if v is not None else "unavailable"

        L = [f"{self.cfg.ticker}  FY{self.cfg.first_year}-FY{self.cfg.last_year}",
             "-" * 64]
        # Cash and shares must share the same basis (defect 4): years with
        # no resolved shares-retired count are excluded from BOTH sides of
        # the average price paid, not just the share side.
        tot_cash = sum(self.sec['repurchase_cash'][y]['val'] / 1e6
                       for y in self.retired if y in self.sec['repurchase_cash'])
        tot_q = sum(self.retired.values())

        # DEFECT 14, THIRD INSTANCE (2026-08-13). A window in which NOTHING is
        # resolved - Union Pacific tags a retirement element but files no
        # annual figure this template can pair with repurchase cash in any year
        # of the window - leaves tot_q at zero and every ratio below undefined.
        # The honest output is a refusal that says which window was asked for
        # and why nothing could be measured in it, not a crash and certainly
        # not a page of zeros.
        if not tot_q:
            return "\n".join(L + [
                "",
                "NO MEASURABLE REPURCHASE IN THIS WINDOW.",
                f"  Not one fiscal year from FY{self.cfg.first_year} to "
                f"FY{self.cfg.last_year} has a resolved shares-retired count "
                "paired with repurchase cash.",
                f"  Unresolved years: {sorted(self.unresolved_years)}",
                "  This is a statement about what the filings support, not "
                "about the company: it may have repurchased heavily and tagged "
                "it in a way this template cannot read. Re-probe the elements "
                "and choose a window the data supports before running again.",
                "", "NOTES"] + [f"  - {n}" for n in self.notes])

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

        # A timing test that could not be struck prints as unavailable. It must
        # never print as a zero or an em dash the reader can mistake for one
        # (defect 14).
        L += [f"cash spent            {tot_cash:14,.0f}",
              f"shares retired        {tot_q:14,.0f} mn",
              f"dollar-wtd price paid {tot_cash/tot_q:14,.2f}" if tot_q
              else "dollar-wtd price paid    unavailable - no shares retired",
              f"dollar-wtd P/E paid   {_f(t['dollar_weighted_pe_paid'], '14.2f')}",
              "",
              f"execution within year {_f(t['execution_within_year'] and 100*t['execution_within_year'], '+13.1f')}"
              + ("%" if t['execution_within_year'] is not None else ""),
              f"allocation across yrs {_f(t['allocation_across_years'] and 100*t['allocation_across_years'], '+13.1f')}"
              + ("%" if t['allocation_across_years'] is not None else ""),
              "",
              f"dilution offset       {100*offset:13.1f}%  {offset_desc}",
              # DEFECT 18 (2026-08-13, found on General Electric and Exxon
              # Mobil). Every line in this block formats a number that an
              # earlier guard is entitled to return as None, and a format
              # string does not survive one. A company that tags no share-based
              # compensation has no wedge MULTIPLE - the denominator is zero -
              # and the honest print is the word, not a crash and not a zero
              # that reads as "no wedge".
              f"comp economic cost    {_f(w['economic_cost'], '14,.0f')}",
              f"comp accounting chg   {_f(w['accounting_charge'], '14,.0f')}",
              f"wedge                 {_f(w['wedge'], '14,.0f')}"
              + (f"  ({w['multiple']:.2f}x)" if w.get('multiple') is not None
                 else "  (multiple unavailable - no accounting charge tagged)")]
        if offset >= dilution_absorption_threshold:
            L += ["", f"*** DILUTION OFFSET {100*offset:.1f}% >= "
                      f"{100*dilution_absorption_threshold:.0f}% - {offset_desc.upper()} ***"]
        nc = getattr(self, 'net_cost', None)
        if nc is not None:
            lab = nc['label'].upper()
            # Every one of these four is None when its denominator is
            # unusable - a company that issued more shares than it retired over
            # the window has no positive net reduction to divide by, and Boeing
            # is exactly that company (defect 18, second instance).
            L += ["", f"WHAT A SHARE COST  ({nc['basis']})",
                  f"  A gross price paid    {_f(nc['A_gross_price'], '14,.2f')}",
                  f"  B cash / net          {_f(nc['B_per_share'], '14,.2f')}"
                  f"   per share {nc['label']}",
                  f"  C less plan proceeds  {_f(nc['C_per_share'], '14,.2f')}",
                  f"  D plus withholding    {_f(nc['D_per_share'], '14,.2f')}"]
            if nc['net_reduction'] is not None and nc['net_reduction'] <= 0:
                L += [f"  NET REDUCTION IS {nc['net_reduction']:,.1f} MN - the company ended "
                      "the window with MORE shares outstanding than it started with.",
                      "  Measures B, C and D are undefined and are not reported. The "
                      "program did not reduce the count; it absorbed issuance."]
            t = nc['treasury']
            if t['basis'] == 'treasury':
                oh = t['overhang_shares_latest']
                L += [f"  reissuable overhang   "
                      + (f"{oh:14,.0f} mn - these shares were NOT cancelled"
                         if oh is not None else
                         "     not tagged - value only")]
                if t['reissued_total']:
                    L += [f"  reissued in window    {t['reissued_total']:14,.1f} mn"]
            if nc['suppressed_years']:
                L += ["  suppressed years: " +
                      ", ".join(f"FY{y}" for y in nc['suppressed_years'])]
        L += self.round_trip_report()
        if self.notes:
            L += ["", "NOTES"] + [f"  - {n}" for n in self.notes]
        if self.price_failures or getattr(self, 'raise_price_failures', None):
            L += ["", "*** VALIDATION FAILED - see notes ***"]
        return "\n".join(L)


if __name__ == '__main__':
    print(__doc__)
