# Paste this into a fresh chat

Everything below the line.

---

Project: AEG Valuation System 2, buyback study. Model: Sonnet.

FIRST ACTION, before anything else. Ask James to grant `C:\Users\james\AEG-Project`, then clone
`github.com/JamesKostohryz/aeg-buyback-study` to `/tmp` (you cannot clone into a mounted folder)
and read, in this order, `docs/00-CLOSE-OUT-Template-2026-08-13.md`,
`docs/00-NEXT-SESSION-Hardening-Continued-2026-08-13.md` and the commit message of `4ff5d77`,
which lists defects 15 to 25 and is the most compressed statement of what has gone wrong on this
system. Repo tip was `84db5ca` on 2026-08-13; check `git log`. Do not start work until you have
read all three.

WHAT THIS SESSION IS FOR. Hardening the template so it can be pointed at any ticker. But
hardening has to END, or it goes on forever and no study is ever run. Your job is to execute
the stopping criteria below, report honestly against them, and either declare the green light or
say plainly what is still missing. You are not being asked to make the template perfect. You are
being asked to make it TRUSTWORTHY and then stop.

STATE OF THE WORLD, VERIFIED 2026-08-13. Twenty-two untouched companies have been run cold; nine
crashed or published something wrong; eleven defects were found and fixed. Five CI gates, all
offline against committed fixtures, all run from `code/`: `verify.py` (333 checks),
`template_test_HD.py`, `excise_test_ORLY.py` (37), `roundtrip_test_AAL.py` (27) and
`coe_invariance_test.py` (104). The Apple document must regenerate BYTE-IDENTICAL — 96,116
bytes, 1,268 numeric tokens, zero moved — and `code/numeric_token_diff.py` proves it. Any change
that moves a token is wrong until argued otherwise. There is ONE driver, `code/run_study.py`;
do not write a per-company driver.

THE COST OF EQUITY IS SETTLED. It is an INPUT, not a mechanic. `code/coe_invariance_test.py`
proves in 104 gated checks that swapping it moves only what it should. Use 6% real as a
placeholder, or several rates, or a year-by-year series — it changes nothing about whether the
study is performed correctly. Do NOT treat its absence as a blocker and do not rebuild anything
to accommodate the real series when it arrives. It will be a substitution and nothing more.

===========================================================================
THE HARDENING STOPS WHEN ALL FOUR OF THESE HOLD. NOT BEFORE, AND NOT AFTER.
===========================================================================

ONE. SHAPE COVERAGE. At least one company of each shape below has been run cold and has either
completed or refused with a named reason a non-programmer could act on. Shapes, not names: one
of each is worth twenty more large-capitalization technology companies.

  a. a forward split inside the window          b. a REVERSE split inside the window
  c. a split AFTER the window closes            d. a company that cancels its repurchases
  e. a company that holds them in treasury      f. a company with only a treasury BALANCE
  g. a company that pays no dividend            h. a company that suspended its dividend
  i. a company that raised equity in the window j. a company that emerged from bankruptcy
  k. a bank holding company with preferred      l. a real estate investment trust
  m. a foreign private issuer filing 20-F       n. a mid-window fiscal year end change
  o. more than one class of common stock        p. a company that stopped repurchasing entirely

Several are already done — (c) Booking Holdings, (d) Oracle, (e) International Business Machines,
(g) AutoZone, (h) Boeing, (o) Meta Platforms, (p) IBM. Verify rather than assume; check the
committed fixtures.

TWO. CONVERGENCE. TWO CONSECUTIVE batches of ten fresh companies produce ZERO NEW GENERAL
DEFECTS. Pick each batch WITHOUT regard to whether you expect it to work — picking easy companies
to end the process is the one way to get this wrong. A general defect is one that would affect
some other company: a missing element name, an unguarded read, a wrong convention. A quirk in one
company's data that the guards correctly refuse is NOT a defect and does not reset the count.
Report the count honestly; if batch two finds something, batch three starts over.

THREE. THE INJECTION SUITE PASSES, and this is the criterion that matters most. Crashes converge
quickly — this project has already watched the rate fall from one in two companies to one in
five. SILENT errors do not converge, because nothing surfaces them. Defect 25 never crashed: it
reported a break-even real cost of equity of 92.72 percent, closed every identity the template
checks, and was wrong by a factor of twenty-five. The standing failure mode of this whole system,
now met nine times, is a number that is internally consistent and externally wrong.

So build `code/injection_test.py`: deliberately corrupt a known-good run, one corruption at a
time, and require a NAMED guard to catch each one. At minimum:

  1. delete a split from the split list
  2. multiply one year's filed share count by 1,000 (a unit error)
  3. invert the deflator — divide where the convention multiplies
  4. shift the price series by one year (a stale series)
  5. substitute another company's price series entirely
  6. truncate the share-count series before the end of the window
  7. make one year's shares retired negative
  8. zero a dividend series that genuinely exists
  9. feed AS-FILED earnings per share to a company with a split in or after its window
 10. duplicate a fiscal year in one input series

Expect some of these to FAIL on first run, and say so rather than weakening the test. Number 9
in particular was fixed by doing the arithmetic right, not by adding a guard that would catch a
regression — so it will probably walk straight through. That is the finding, and closing it is
the work.

FOUR. NO CRASHES ANYWHERE, GATED. A sixth CI gate — a fleet test — runs every committed fixture
and asserts that each either completes or refuses with a named reason, and that not one of them
raises an unhandled exception. Today the cold-run coverage is one company inside
`template_test_HD.py`. That was right when there was one.

WHEN ALL FOUR HOLD: write `docs/00-GREEN-LIGHT-<date>.md` stating which criterion was satisfied
by what evidence, and stop. From that point hardening is OVER. Defects found later are fixed when
they appear in a real study; they are not hunted. If you cannot satisfy all four, say exactly
which one failed and why, and do not declare the green light to be tidy.

===========================================================================
THE AUDIT POINTS. THESE ARE PERMANENT AND ARE PART OF THE METHODOLOGY.
===========================================================================

A green light does not mean a study is trusted because it ran. EVERY live study, forever, runs
the checks below and publishes the result of each one. Write them up as a numbered section of the
methodology document and implement them as `code/audit_points.py`, called by `run_study.py` at
the end of every run. Any audit point that FAILS refuses the study rather than annotating it,
unless James overrides in writing and the override is recorded in the output.

INTERNAL COHERENCE — does the study agree with itself?

  I1  The share-count identity closes every year: opening shares, less retired, plus issued,
      equals closing shares, to floating-point exactness.
  I2  decision + timing == entry, per tranche and cumulatively, under all six estimators.
  I3  The entry effect is zero at its own break-even, and the break-even from the closed form
      equals the break-even from bisection.
  I4  Sources and uses reconcile on filed facts alone, with the excise tax outside the account.
  I5  Every measure with a second independent route agrees with it; where no second route
      exists, that fact is stated and a band published rather than a point.
  I6  No quantity prints as a number that an earlier guard declined to compute. "Unavailable"
      is a permitted output; a zero standing in for one is not.

EXTERNAL COHERENCE — does the study agree with the world? This is the class that catches the
errors that matter, and each of these has already caught a real one.

  E1  Every implied average price paid sits inside its own fiscal year's INTRA-PERIOD traded
      range. Caught Texas Instruments and Booking Holdings. Its limit is real and must be
      stated: it cannot catch a contaminated numerator whose error is small relative to the
      range, which is how the American Airlines convertible nearly got through.
  E2  Real earnings growth is BELOW nominal earnings growth whenever inflation was positive
      over the window. This is the check that exposed the Costco deflator inversion — a fitted
      real trend of 17.73 percent a year against lower nominal growth, which is arithmetically
      impossible. Cheap, and it catches an entire class of deflator error.
  E3  The forward real earnings yield on every tranche sits inside a plausible band, say 0.5 to
      25 percent. Booking Holdings printed 87, 143 and 151 percent. Flag loudly rather than
      refuse: judgment about a business cycle stays with a person.
  E4  Shares retired in any year are a plausible fraction of opening shares, say under 25
      percent, and never negative.
  E5  The dollar-weighted price paid across the whole window sits inside the window's overall
      traded range.
  E6  The multiple paid in each year is within a stated factor of the market multiple in the
      same year. A large divergence is either a real execution finding or a data error, and the
      study must say which it thinks it is.
  E7  The price series endpoints are checked against an independently retrieved quote for the
      same dates, from a different call than the one that built the series.
  E8  Total repurchase cash over the window is checked against an independent statement of the
      program's size — the company's own cumulative disclosure where it exists.
  E9  The closing share count is checked against a third-party count for the same date.

For each audit point record, in the methodology, WHAT IT WOULD HAVE CAUGHT. An audit point with
no history of catching anything is either new or useless, and the difference should be visible.

STANDING RULES, UNCHANGED. Every figure computed, never typed. Every central measure computed two
independent ways, reconciling, before you write a sentence about what it means — and if the
second route shares intermediate quantities with the first it is not a second route. A missing
input is never silently zero; an estimated input is always announced. Read your own edits back
from the rendered output. Do not publish a number about the engine you have not traced to the
engine at its current tip. Load the `rva-style-guide` skill before writing published copy. Prose
rather than bullet lists in published copy, American spelling, acronyms written out.

OPERATIONAL. GitHub token at `C:\Users\james\Documents\GitHub\.claude-github-token` (classic
personal access token, repo and workflow scope) — granting that folder is a SEPARATE
`request_cowork_directory` call. EODHD token at `C:\Users\james\AEG-Project\.eodhd-token`;
`run_study.py` finds it automatically. Never print or commit either. The sandbox reaches
`data.sec.gov`, `www.sec.gov`, `efts.sec.gov` and `eodhd.com` directly. Long batches die when a
shell call ends — run them inside a single call under the timeout, in groups of five or so, not
detached.

HOW JAMES WORKS. Financial markets analyst, not a programmer. Plain language. When he must act,
give the exact page, exactly what to click, and what success looks like. ONE clear question with
a recommendation, never a menu. Do everything you can yourself first and never stall silently.
Tell him plainly when he, the consensus, or you are wrong, and correct yourself in writing when
you find you were. Recommend which model to use and flag a good handoff point before a long chat
degrades.

DO NOT REOPEN. The pivot for a repurchase's contribution to abnormal earnings growth is Neutral
Value, not Intrinsic Value. Scope is ex-post disclosure only; nothing here moves an engine
valuation number. The net retirement cost is not a price and is not an expense. No year and no
repurchase is ever excluded from a study on grounds of taste — only on grounds of a named guard.
The cost of equity is an input. The Apple document regenerates byte-identical.

IF YOU FINISH THE FOUR CRITERIA AND HAVE ROOM: the next build is the filing reader described in
`docs/00-NEXT-SESSION-Hardening-Continued-2026-08-13.md` — it closes the excise tax, multi-class
share counts and the round trip's equity raises in one piece of work, and it makes the study
multi-pass by design. Propose it to James before building it.
