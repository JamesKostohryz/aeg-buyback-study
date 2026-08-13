"""
Primary-source data for the Apple share-repurchase study.

SEC figures are taken from the SEC XBRL company-concept API for CIK 0000320193
(Apple Inc.), restricted to form 10-K, full-fiscal-year periods. Dollar figures
are US$ millions. Share counts are in millions.

Prices are EODHD monthly closes for AAPL.US, converted to today's split basis.
"""

# ---------------------------------------------------------------- SEC: dollars
# us-gaap:PaymentsForRepurchaseOfCommonStock  (cash flow statement, financing)
REPURCHASE_CASH = {
    2013: 22860, 2014: 45000, 2015: 35253, 2016: 29722, 2017: 32900,
    2018: 72738, 2019: 66897, 2020: 72358, 2021: 85971, 2022: 89402,
    2023: 77550, 2024: 94949, 2025: 90711,
}

# us-gaap:StockRepurchasedAndRetiredDuringPeriodValue (equity statement, accrual)
REPURCHASE_ACCRUAL = {
    2013: 9000, 2014: 45000, 2015: 36026, 2016: 29000, 2017: 33001,
    2018: 73056, 2019: 67100, 2020: 72500, 2021: 85500, 2022: 90200,
    2023: 76600, 2024: 95000, 2025: 89300,
}

# us-gaap:ProceedsFromIssuanceOfCommonStock. Apple stopped presenting this line
# separately after FY2021; it is folded into "Other" in financing activities.
ISSUANCE_PROCEEDS = {
    2009: 475, 2010: 912, 2011: 831, 2012: 665, 2013: 530, 2014: 730,
    2015: 543, 2016: 495, 2017: 555, 2018: 669, 2019: 781, 2020: 880,
    2021: 1105,
}

# us-gaap:ShareBasedCompensation
SBC = {
    2009: 710, 2010: 879, 2011: 1168, 2012: 1740, 2013: 2253, 2014: 2863,
    2015: 3586, 2016: 4210, 2017: 4840, 2018: 5340, 2019: 6068, 2020: 6829,
    2021: 7906, 2022: 9038, 2023: 10833, 2024: 11688, 2025: 12863,
}

# us-gaap:PaymentsRelatedToTaxWithholdingForShareBasedCompensation
TAX_WITHHOLDING = {
    2010: 406, 2011: 520, 2012: 1226, 2013: 1082, 2014: 1158, 2015: 1499,
    2016: 1570, 2017: 1874, 2018: 2527, 2019: 2817, 2020: 3634, 2021: 6556,
    2022: 6223, 2023: 5431, 2024: 5441, 2025: 5960,
}

# ---------------------------------------------------------------- SEC: shares
# us-gaap:CommonStockSharesOutstanding at each fiscal year end, as filed.
# As-filed values sit on the split basis in force at the filing date, so they
# are restated here onto today's basis. Apple split 7-for-1 on 2014-06-09 and
# 4-for-1 on 2020-08-31, so filings before June 2014 need x28, filings between
# June 2014 and August 2020 need x4, and later filings need no adjustment.
_SHARES_OUT_AS_FILED = {
    2008: 888.325973, 2009: 899.8055, 2010: 915.97005, 2011: 929.277,
    2012: 939.208, 2013: 899.213,                      # filed pre-2014 split
    2014: 5866.161, 2015: 5578.753, 2016: 5336.166,
    2017: 5126.201, 2018: 4754.986,                    # filed pre-2020 split
    2019: 17772.945, 2020: 16976.763, 2021: 16426.786,
    2022: 15943.425, 2023: 15550.061, 2024: 15116.786, 2025: 14773.260,
}
_SPLIT_FACTOR = {y: (28 if y <= 2013 else 4 if y <= 2018 else 1)
                 for y in _SHARES_OUT_AS_FILED}
SHARES_OUT = {y: v * _SPLIT_FACTOR[y] for y, v in _SHARES_OUT_AS_FILED.items()}

# us-gaap:StockRepurchasedAndRetiredDuringPeriodShares, form 10-K, full year,
# restated onto today's split basis. Apple did not tag this element for
# FY2014-FY2017 (and the FY2013 tagged value covers only part of the year), so
# those years are derived in build.py from the share-count identity.
SHARES_RETIRED_FILED = {
    2018: 405.5 * 4, 2019: 345.2 * 4,
    2020: 917.0, 2021: 656.0, 2022: 569.0,
    2023: 471.0, 2024: 499.0, 2025: 402.0,
}

# ---------------------------------------------------------------- prices
# EODHD AAPL.US monthly closes, first month = 2005-10. Raw closes sit on the
# split basis in force at the time; the divisor below restates them.
_MONTHLY_CLOSE_FROM_2005_10 = [
    57.5904, 67.8188, 71.89,
    75.5104, 68.4908, 62.72, 70.3892, 59.7688, 57.2712, 67.9588, 67.8496,
    76.9804, 81.0796, 91.6608, 84.84,
    85.7304, 84.6104, 92.9096, 99.8004, 121.1896, 122.0408, 131.7596,
    138.4796, 153.4708, 189.9492, 182.2212, 198.0804,
    135.3604, 125.02, 143.5, 173.95, 188.7508, 167.44, 158.9504, 169.5288,
    113.6604, 107.59, 92.6688, 85.3496,
    90.1292, 89.3088, 105.1204, 125.8292, 135.8112, 142.4304, 163.3912,
    168.21, 185.3488, 188.4988, 199.9088, 210.7308,
    192.0604, 204.6212, 235.0012, 261.0888, 256.8804, 251.5296, 257.25,
    243.0988, 283.7492, 300.9804, 311.15, 322.56,
    339.3208, 353.2088, 348.5104, 350.1288, 347.83, 335.6696, 390.4796,
    384.8292, 381.3208, 404.7792, 382.2, 405.0004,
    456.4812, 542.4412, 599.55, 583.9792, 577.7296, 583.9988, 610.7612,
    665.2408, 667.1, 595.3192, 585.2812, 532.1708,
    455.49, 441.4004, 442.6604, 442.7808, 449.7304, 396.5304, 452.5304,
    487.2196, 476.7504, 522.7012, 556.0688, 561.0192,
    500.6008, 526.2404, 536.7404, 590.0888, 632.9988, 92.93, 95.6, 102.5,
    100.75, 108.0, 118.93, 110.38,
    117.16, 128.46, 124.43, 125.15, 130.28, 125.43, 121.3, 112.76, 110.3,
    119.5, 118.3, 105.26,
    97.34, 96.69, 108.99, 93.74, 99.86, 95.6, 104.21, 106.1, 113.05, 113.54,
    110.52, 115.82,
    121.35, 136.99, 143.66, 143.65, 152.76, 144.02, 148.73, 164.0, 154.12,
    169.04, 171.85, 169.23,
    167.43, 178.12, 167.78, 165.26, 186.87, 185.11, 190.29, 227.63, 225.74,
    218.86, 178.58, 157.74,
    166.44, 173.15, 189.95, 200.67, 175.07, 197.92, 213.04, 208.74, 223.97,
    248.76, 267.25, 293.65,
    309.51, 273.36, 254.29, 293.8, 317.94, 364.8, 425.04, 129.04, 115.81,
    108.86, 119.05, 132.69,
    131.96, 121.26, 122.15, 131.46, 124.61, 136.96, 145.86, 151.83, 141.5,
    149.8, 165.3, 177.57,
    174.78, 165.12, 174.61, 157.65, 148.84, 136.72, 162.51, 157.22, 138.2,
    153.34, 148.03, 129.93,
    144.29, 147.41, 164.9, 169.68, 177.25, 193.97, 196.45, 187.87, 171.21,
    170.77, 189.95, 192.53,
    184.4, 180.75, 171.48, 170.33, 192.25, 210.62, 222.08, 229.0, 233.0,
    225.91, 237.33, 250.42,
    236.0, 241.84, 222.13, 212.5, 200.85, 205.17, 207.57, 232.14, 254.63,
    270.37, 278.85, 271.86,
    259.48, 264.18, 253.79, 271.35, 312.06, 289.36, 308.91, 313.33,
]


def _split_divisor(year, month):
    """Cumulative split divisor to put a month-end close on today's basis."""
    ym = year * 100 + month
    if ym <= 201405:            # before the 7-for-1 on 2014-06-09
        return 28.0
    if ym <= 202007:            # before the 4-for-1 on 2020-08-31
        return 4.0
    return 1.0


def monthly_prices():
    """{(year, month): split-adjusted close} from 2005-10 onward."""
    out, y, m = {}, 2005, 10
    for close in _MONTHLY_CLOSE_FROM_2005_10:
        out[(y, m)] = close / _split_divisor(y, m)
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


# Apple's fiscal year ends on the last Saturday of September, so fiscal year t
# runs from October of t-1 through September of t.
def fiscal_months(fy):
    return [(fy - 1, m) for m in range(10, 13)] + [(fy, m) for m in range(1, 10)]


# ------------------------------------------------------- SEC: gross borrowings
# us-gaap:LongTermDebtNoncurrent + us-gaap:LongTermDebtCurrent +
# us-gaap:CommercialPaper, form 10-K, fiscal year end, US$ millions. For FY2013
# Apple tagged only us-gaap:LongTermDebt and carried no commercial paper.
#
# WHY THIS IS HERE. The engine's vendor balance-sheet feed carries a "Total Debt"
# line that agrees with these figures to the dollar for FY2012 through FY2021,
# then diverges: +$812mn in FY2022, +$859mn in FY2023, +$12,430mn in FY2024 and
# +$13,720mn in FY2025. The FY2024-25 gaps are Apple's operating lease
# liabilities ($11,534mn and $12,490mn) plus its finance leases. The vendor
# began folding capitalized leases into "Total Debt" in FY2024 and did not
# restate the earlier years, so the series changes definition mid-stream. A
# series that changes definition cannot be differenced across the break, and
# FY2025 is an endpoint of this study. Whatever one concludes about whether a
# lease liability is financing or operating, it has to be the same answer in
# every year. These figures are used instead. Verified against
# data.sec.gov 2026-08-09.
# ------------------------------------------- Salesforce, contrast case only
# CRM is in this study for ONE purpose: to show that Apple is not the extreme
# case on the net-retirement-cost measure, and that the measure is more general
# than the gross one. No figure here enters any Apple calculation.
#
# Salesforce tags NEITHER us-gaap:StockRepurchasedAndRetiredDuringPeriodShares
# NOR us-gaap:TreasuryStockSharesAcquired, so NO gross price per share retired
# can be computed for it at all. The net measure needs only repurchase cash and
# the change in shares outstanding, both of which every filer reports. That is
# the argument for the net measure being the more portable of the two.
#
# (fiscal year as CRM labels it, us-gaap:PaymentsForRepurchaseOfCommonStock $m,
#  period-end us-gaap:CommonStockSharesOutstanding mn, net reduction in shares
#  outstanding over the year mn, lowest and highest trade in the fiscal year $)
#
# PROVENANCE, and it is weaker than the Apple figures. These were computed from
# primary source by the handoff session of 2026-08-12. The fiscal 2025 row is
# independently corroborated: Template-Exercise-FINDINGS-2026-08-09 section 2,
# defect 4, reports the same $7,829mn over 9mn shares, an implied $869.89
# against a highest trade of $369.00, reached by a different route. Fiscal 2024
# and fiscal 2026 have NOT been re-derived from filings in this session and are
# flagged as such in the build note.
CRM_NET_CONTRAST = [
    (2024,  7620, 971, 10.0, 176.0, 318.0),
    (2025,  7829, 962,  9.0, 212.0, 369.0),
    (2026, 12596, 929, 33.0, 230.0, 370.0),
]


BORROWINGS = {
    2012: 0, 2013: 16960, 2014: 35295, 2015: 64462, 2016: 87032,
    2017: 115680, 2018: 114483, 2019: 108047, 2020: 112436, 2021: 124719,
    2022: 120069, 2023: 111088, 2024: 106629, 2025: 98657,
}
