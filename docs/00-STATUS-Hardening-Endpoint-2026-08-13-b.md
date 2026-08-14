# Status update: criterion three now passes, 2026-08-13 (second pass)

Supersedes the criterion-3 section of `00-STATUS-Hardening-Endpoint-2026-08-13.md`, written
earlier the same day. That document is otherwise still current. Repo tip after this commit:
`51324a6`.

## THREE. Injection suite - now PASSES, 10 of 10

James authorized fixing the four gaps found in the first pass rather than deferring them. Four
new methods landed on `BuybackStudy`, called at the top of `run()`: `validate_deflator()`,
`validate_dividend_series()`, `validate_eps_consistency()`, `validate_no_duplicated_years()`. Each
is purely additive - a new note, never a changed value - which is what made it possible to land
all four in one pass without re-deriving any published figure.

Proof standard met before landing, not after: the regenerated Apple document is
**BYTE-IDENTICAL** to the pre-change version - 96,116 bytes, 1,268 numeric tokens, zero moved,
and `diff -q` reports the two files identical, not merely token-equivalent. All five
pre-existing gates and the new fleet gate re-ran unchanged and green:
`verify.py` (333), `template_test_HD.py`, `excise_test_ORLY.py` (37), `roundtrip_test_AAL.py`
(27), `coe_invariance_test.py` (104), `fleet_test.py` (10/10, 0 crashes).
`code/injection_test.py` re-run: 10 of 10 corruptions caught by a named guard, 0 walk through
silently.

One finding worth carrying forward rather than hiding: `validate_eps_consistency()` fires on
Meta Platforms, FY2010-2012, in the fleet gate - filed diluted EPS disagrees with net income
divided by weighted shares by up to 50% in FY2012. This is judged a real, plausible divergence
from Facebook's 2012 IPO-year accounting (a mid-year share count discontinuity and probable
income allocated to pre-IPO preferred stock), not a defect - and it changes nothing published,
because Meta's study is already fully refused for an unrelated reason (no share count reachable
through the structured interface at all). Recorded here so it is not mistaken for a fresh defect
if it is seen again.

## Net, updated

TWO of four criteria now solidly hold: THREE (injection suite) and FOUR (fleet gate). ONE (shape
coverage, 8 of 16) and TWO (convergence, not attempted) remain open. The green light is still not
declared - shape coverage and convergence are both real, unfinished work, not paperwork - but the
criterion the task named as mattering most is now closed and proven, not merely built.
