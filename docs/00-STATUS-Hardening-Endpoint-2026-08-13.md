# Status against the hardening stopping criteria, 2026-08-13

Written at the end of the session that read `00-PASTE-THIS-Hardening-Endpoint.md`. This is a
progress report, not a green light. Two of four criteria are open, one closed, one closed but
FAILING its own bar. Repo tip after this session: `aea0093`.

## ONE. Shape coverage - PARTIAL, 8 of 16

Verified rather than assumed, per instruction: the close-out doc's claim that AutoZone, Boeing
and Meta were "already done" was true of the interactive run but FALSE of the repository - none
of the three had a committed price fixture, so none was reproducible offline and none was gated.
Closed this session, along with the same gap on Booking Holdings and IBM (raw fixtures existed,
prices did not). All five are now committed and wired into `code/fleet_test.py`.

Covered and gated: (c) Booking Holdings, (d) Oracle, (e) IBM/Booking/AutoZone/Boeing all show
treasury behavior, (g) AutoZone, (h) Boeing, (i) American Airlines (its FY2020 equity raise,
already exercised by `roundtrip_test_AAL.py`), (o) Meta Platforms, (p) IBM.

Still open, no company run for any of them this session: (a) forward split inside the window on
the generic driver (Apple's splits are inside its own window but Apple runs on a separate code
path, not `run_study.py`), (b) reverse split, (f) a treasury BALANCE with no flow tag at all,
(j) emerged from bankruptcy, (k) bank holding company with preferred, (l) REIT, (m) 20-F foreign
filer, (n) mid-window fiscal year end change.

## TWO. Convergence - NOT ATTEMPTED

Zero fresh companies run this session toward the two-consecutive-batches-of-ten bar. This needs
its own session; it cannot be done honestly in the tail of one that already ran nine companies
for shape coverage.

## THREE. Injection suite - BUILT, and it FAILS its own bar

`code/injection_test.py` corrupts a known-good run ten ways. 6 of 10 are caught by a named
guard. 4 are NOT:

  - inverting the deflator (dividing instead of multiplying) - no sanity check on the deflator's
    own value exists anywhere
  - zeroing a real dividend series - the guard only fires when the dividend KEY is absent, not
    when it is present and zero
  - feeding as-filed EPS across an in-window split - `split_factor()` is applied to share counts
    and prices everywhere in the template and to earnings per share NOWHERE. Predicted by the
    task brief before the test was even run; confirmed.
  - duplicating a fiscal year - nothing checks for suspiciously identical adjacent years

None of these four were fixed this session. Fixing any of them changes numbers and is GATED -
it needs James's sign-off and the Apple byte-identical proof before it lands, and that is a
separate, focused session, not an addendum to this one.

## FOUR. Fleet gate - DONE

`code/fleet_test.py` runs all 10 non-Apple committed fixtures in-process and asserts each
completes or refuses by name. All 10 pass; zero unhandled crashes. Apple is excluded by design
(separate code path, checked by `numeric_token_diff.py` instead).

## Net

Criteria ONE and TWO are open, and criterion THREE - the one the task said mattered most - is
built and currently FAILING. The green light is not declared. All five pre-existing gates
(`verify.py` 333, `template_test_HD.py`, `excise_test_ORLY.py` 37, `roundtrip_test_AAL.py` 27,
`coe_invariance_test.py` 104) were re-run unchanged and are still green; nothing outside new
files was touched this session.

## For the next session

In order of what closes the most: (1) decide with James whether to fix the four injection gaps
now (each is small and none touches the four-method tie directly, but each moves a number and
needs the gated process) or defer them to when they bite a real study; (2) run the eight
remaining shapes, choosing real companies without regard to whether they are expected to work;
(3) two convergence batches; (4) `code/audit_points.py`, not started.
