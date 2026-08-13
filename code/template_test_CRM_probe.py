# -*- coding: utf-8 -*-
"""Targeted probe: the dilution-offset path, on a company that neither retires
shares nor tags treasury acquisitions.

Home Depot exercised the treasury fallback but its dilution offset is only 7.5
percent, so the near-or-above-100-percent path stayed unexercised. Salesforce
was chosen because equity compensation is the dominant share flow there. What it
actually exposed is worse than a missing report line.
"""
import json
import urllib.request
from datetime import date

H = {'User-Agent': 'JK Investment Consulting research james@jameskostohryz.com'}
CIK = '0001108524'          # salesforce, inc.


def concept(tag):
    u = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK}/us-gaap/{tag}.json"
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H)))
    except Exception:
        return {}
    out = {}
    for arr in d.get('units', {}).values():
        for e in arr:
            if e.get('form') != '10-K':
                continue
            if 'start' in e:
                s, t = date.fromisoformat(e['start']), date.fromisoformat(e['end'])
                if not (330 <= (t - s).days <= 400):
                    continue
            k = int(e['end'][:4])
            if k not in out or e['filed'] > out[k][1]:
                out[k] = (e['val'], e['filed'])
    return {k: v[0] for k, v in out.items()}


SO = concept('CommonStockSharesOutstanding')
CASH = concept('PaymentsForRepurchaseOfCommonStock')
RET = concept('StockRepurchasedAndRetiredDuringPeriodShares')
TRE = concept('TreasuryStockSharesAcquired')

# Fiscal 2025 = February 2024 to January 2025. EODHD monthly bars over exactly
# that window: high 369.00 (December 2024), low 212.00 (May 2024).
FY25_HIGH, FY25_LOW = 369.00, 212.00

print("SALESFORCE PROBE - the zero-issuance fallback")
print("-" * 72)
print(f"StockRepurchasedAndRetiredDuringPeriodShares tagged: {bool(RET)}")
print(f"TreasuryStockSharesAcquired tagged:                  {bool(TRE)}")
print("Neither. Shares retired must be derived from the share-count identity,")
print("and net issuance is observable in ZERO years.")
print()
print("What buyback_study.share_flows() does when obs is empty:")
print("    issue_rate_fallback = (sum(obs)/len(obs)) if obs else 0.0")
print("    ...and the explanatory note is only appended `if obs:`")
print("So issuance is silently set to zero, shares retired collapses to the net")
print("reduction in shares outstanding, and the dilution offset is reported as")
print("0.0% for the company where dilution is the entire story.")
print()
print(f"{'FY':>5}{'sh.out mn':>12}{'d(sh.out)':>12}{'cash $m':>11}"
      f"{'implied px':>13}{'verdict':>28}")
for y in (2024, 2025, 2026):
    if y not in SO or (y - 1) not in SO or y not in CASH:
        continue
    d = (SO[y - 1] - SO[y]) / 1e6
    cash = CASH[y] / 1e6
    px = cash / d if d else float('nan')
    v = ""
    if y == 2025:
        v = f"traded {FY25_LOW:.0f}-{FY25_HIGH:.0f}: IMPOSSIBLE"
    print(f"{y:>5}{SO[y]/1e6:>12,.0f}{d:>12,.1f}{cash:>11,.0f}{px:>13,.2f}{v:>28}")
print()
print("The fiscal 2025 implied average price of about $870 is 2.4 times the")
print("highest price Salesforce traded in that fiscal year. The price validator")
print("catches it, which is the system working. The zero-issuance default that")
print("caused it is silent, which is the system failing.")
