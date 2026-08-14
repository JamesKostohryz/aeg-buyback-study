# Methodology addendum: the fifteen audit points

**2026-08-14. Implements the audit-points section of `docs/00-PASTE-THIS-Hardening-Endpoint.md`,
which specified all fifteen checks and left them unbuilt. Built as `code/audit_points.py`,
wired into `run_study.py`'s `run()`, and run on every study from here forward, not only during
hardening.**

## 1. What was missing

The four hardening-endpoint criteria (shape coverage, convergence, the injection suite, the
fleet gate — all satisfied, see `docs/00-GREEN-LIGHT-2026-08-13.md`) established that the
template and its generic driver are trustworthy enough to stop hardening and start publishing.
They say nothing about any one study. A study can run cleanly, print a number, and still be
wrong in a way none of the four criteria would ever see, because all four are about the
*engine's* behavior across many companies, not about whether *this* company's numbers agree
with themselves or with the world. The hardening-endpoint document specified fifteen standing
checks for exactly that gap and left them unbuilt. This addendum is that build.

## 2. What "refuse" means in this codebase

The specification says a failing audit point "refuses the study rather than annotating it,
unless James overrides in writing and the override is recorded in the output." This driver
already has an idiom for that — `note('REFUSAL', ...)`, the module-level `REF` log, and the
"REFUSALS, FALLBACKS AND SUPPRESSIONS" block printed at the end of every run — and a refusal in
that idiom has never meant a program abort. It means a guard saw something it could not
honestly measure, named it, and excluded the tainted quantity from every downstream figure,
while the run itself completes. A crash on an unfamiliar company is a defect, which is exactly
what the fleet gate exists to catch; a refusal is the opposite of a defect. `audit_points.py`
follows the same idiom. It never raises and never exits. Each check returns PASS, FAIL, FLAG or
UNAVAILABLE with a plain-language reason; `run_study.py` turns any FAIL into a loud, unmissable
"STUDY REFUSED" banner naming which point failed, on top of the existing refusal note, and
that banner is the instruction not to publish until either the finding is resolved or James
overrides it in writing.

E3 is the one point the specification itself carves out: forward real earnings yield outside
a plausible band is a judgment about a business cycle, not a data error, so it is scored FLAG
and never triggers the refusal banner — published as a finding, exactly as it already was when
this check first caught Booking Holdings printing 87, 143 and 151 percent.

A check that this driver cannot compute from what it has plumbed in is scored UNAVAILABLE, not
skipped and not quietly passed. Three of the nine external checks — E6, E7 and E8 — are
UNAVAILABLE today on every company, and section 4 below says exactly what each would need.

## 3. Why this could not move Apple

`code/audit_points.py` imports nothing from `buyback_study_TEMPLATE.py`. It is called by
`run_study.py`'s own `run()` function, once, after `study.run()` and `entry_effect()` have both
already finished, and it reads their results without mutating either. `code/gen_article.py`,
which builds the published Apple study, never calls `run_study.run()` at all — it constructs
`BuybackStudy` directly through `build.py`, a separate path that predates this driver. Nothing
in this addendum's change can therefore move a byte of `Buyback-Study-AAPL.html`, and this was
checked rather than assumed: `diff -q` against a pre-change copy, and
`code/numeric_token_diff.py` against the same copy, both confirm zero movement across the
file's 96,116 bytes and 1,268 numeric tokens.

## 4. Internal coherence — does the study agree with itself?

**I1 — the share-count identity.** Opening shares, less retired, plus issued, must equal
closing shares to floating-point exactness, for every year both a retirement and an issuance
figure exist. This should hold by construction: `share_flows()` always computes one of the two
as the residual of the other, never both independently, so a break here would mean a future
edit stopped doing that. The check exists as a tripwire on that invariant, not because it is
expected to fail. It passed on every fleet company this session.

**I2 — decision plus timing equals entry.** The earnings-timing decomposition splits the
published entry effect into a decision term and a timing term under six estimators, three
symmetric and three backward-looking, and the two terms must sum back to the entry effect
exactly, per tranche and cumulatively, under all six. This is checked independently of the
`identity_residual` value the decomposition already publishes — recomputed here from the raw
per-tranche rows — as a second look at the same claim. Passed on every fleet company with a
decomposition computed; scored UNAVAILABLE, correctly, on companies with fewer than three
positive real-earnings observations, where the decomposition itself declines to run.

**I3 — the break-even is a genuine root.** The entry effect must equal zero when struck at its
own published break-even rate, and the closed-form break-even (an exact algebraic root, since
the entry effect is linear in the discount rate) must agree with a break-even found by an
independently coded bisection search that shares no code with the closed form. Both held to
machine precision everywhere this ran — the two routes agreed to roughly 1e-14, the same order
the existing `coe_invariance_test.py` gate already reports.

**I4 — sources and uses reconcile on filed facts.** This reuses `reconcile_raises()`, which was
already built for the round trip: it compares the equity statement's raise total against the
financing-activities cash-flow line for the same year, refuses any unexplained gap rather than
netting it, and — the specification's own phrase — keeps the excise tax outside the account,
published only as a memorandum line. I4 checks that the exclusion actually holds downstream:
that every year `raise_reconciliation` marks unclean is also excluded from `raise_refusals` and
from `resolved_raises()`. On a company that never raised equity this passes vacuously, a true
zero rather than a missing check.

**I5 — every dual-route measure agrees with its second route.** This template currently has two
genuinely independent second routes — the timing-decomposition band (I2) and the break-even
root (I3) — and I5 is the composite verdict across both, plus an honest statement of which
measures in a given run have only one route: an entry effect struck at a single cost of equity
with no `coe_by_year` alternate supplied is a point, not a band, and that fact is stated rather
than presented as more certain than it is.

**I6 — no quantity prints where a guard declined to compute one.** For every year excluded as
unresolved, no-share-count, negative-retirement or no-repurchase, this checks directly that the
year does not leak into `retired`, `issued`, or the entry-effect tables — that "unavailable"
stayed unavailable all the way to the numbers a reader would see, rather than becoming a zero
somewhere downstream. Passed everywhere this ran.

## 5. External coherence — does the study agree with the world?

**E1 — every implied price sits inside its own fiscal year's traded range.** This is
`study.price_failures`, already computed by `validate_prices()` at `run()` time; the audit
point's contribution is publishing it at refusal strength instead of a note. It has already
caught Texas Instruments and Booking Holdings during hardening. Its stated limit is real: a
contaminated numerator whose error is small relative to the range — the American Airlines
withholding-in-the-cash-line defect — can still pass.

**E2 — real growth stays below nominal growth under positive inflation.** This is the check
that caught the Costco deflator inversion during hardening (a fitted real trend of 17.73
percent a year against lower nominal growth, arithmetically impossible), and it is cheap
because it follows directly from this template's stated convention that real equals nominal
times the deflator: whenever the deflator shows genuine inflation across the window, real
growth cannot exceed nominal growth, and if it does, the deflator was applied backwards.

**E3 — forward real earnings yield inside a plausible band.** Flagged, never refused, per the
specification. Booking Holdings remains the standing example (87, 143 and 151 percent on three
tranches) of a real finding this check exists to surface, not to hide behind a refusal.

**E4 — shares retired are a plausible fraction of opening shares.** Under 25 percent, never
negative. Negative retirement is already refused at source by `share_flows()` (defect 23); this
is a second, independent look at the same failure mode at the level of the published fraction.

**E5 — the dollar-weighted price sits inside the window's overall traded range.** The same
class of error E1 catches, at the level of the whole program rather than one year — a level
shift or unit error that moves every year's price a little in the same direction could pass E1
year by year and still miss here.

**E6, E7, E8 — honestly unavailable, not silently skipped.** E6 (the multiple paid against a
market multiple) has no market-multiple series plumbed into this driver at all; building it
means adding a supplied series the way `coe_by_year` already works. E7 (an independently
retrieved price quote) cannot be built from what exists today: `fetch_prices()` builds both the
monthly-close series and the intra-period traded range from one EODHD call, so E1 and E5 are
not really cross-vendor checks, they are the same vendor's own OHLC bars checked against its
own closes — a real limit worth stating plainly rather than implying a rigor that is not there.
A genuine E7 would need a second, live, single-date call to a different endpoint, made optional
so the fleet gate and injection suite keep running offline. E8 (the company's own cumulative
repurchase-program disclosure) has no reachable XBRL element — the taxonomy's
`StockRepurchaseProgramAuthorizedAmount1` reports authorization, not execution, and this driver
sums filed cash instead, which is a different fact.

**E9 — the closing count against a second source.** `shares_outstanding()` already has a
splice check against the Form 10-K cover-page count (`EntityCommonStockSharesOutstanding`) for
years its primary tag does not reach, allowing a splice only when the two agree within two
percent. E9 runs the same comparison every year both sources exist, not only the gap years —
and on Boeing it found something the existing splice logic never had a reason to look for. See
section 6.

## 6. What this run already caught

Running the full committed fleet (eleven fixtures, offline) through the new checks produced
three findings, one of them new. Booking Holdings and Jefferies both refused at E1, E4 and (for
Jefferies) E5 — but these are not new discoveries. Both companies' fixtures already carried
`price_failures` from the existing `validate_prices()` guard, visible in the header line of
every prior run of these fixtures; the audit points did not find new bad years, they escalated
years that were already flagged from a buried note to a study-level refusal, exactly the
behavior the specification calls for.

The new finding is Boeing. E9 failed with a 44 percent gap between the two sources, and
inspection of the raw filed facts explains why: Boeing's `CommonStockSharesOutstanding` tag
reports the identical value, 1,012,261,159, in every one of eighteen filed years from 2008
through 2025, while the cover-page count moves normally year to year (563 million in fiscal
2019, 583 million in fiscal 2020). A company that has repurchased tens of billions of dollars
of stock every year cannot have a constant outstanding count; the far more plausible reading is
that Boeing's filer has tagged shares *issued* — a figure that genuinely would not move, since
Boeing has not issued new common shares in decades — under the *outstanding* element name.
`shares_outstanding()`'s existing cover-page fallback never had a reason to catch this, because
it only activates when the primary tag has a gap, and Boeing's primary tag has no gap; it is
simply, consistently wrong for the entire window. This means every per-share measure this
template has published for Boeing under this driver has been computed against a share count
roughly 1.7 to 1.8 times too large. This is reported to James separately and is not corrected
here: fixing the share-count derivation for a real company moves a real valuation-adjacent
quantity, which is a GATED change under this project's own standing rule, not a SAFE one to
make inside an addendum about adding a check.

## 7. Verification

All seven existing gates were re-run after this change and pass unchanged: `verify.py`
(333/333), `template_test_HD.py`, `excise_test_ORLY.py` (37/37), `roundtrip_test_AAL.py`
(27/27), `code/coe_invariance_test.py` (104/104), `code/fleet_test.py` (eleven fixtures, zero
unhandled crashes), `code/injection_test.py` (ten of ten corruptions caught). The Apple article
is confirmed byte-identical per section 3. None of these gates call `run_study.run()` except
`coe_invariance_test.py` and `fleet_test.py`'s tier-1 fixtures, and both ran the audit points
without incident, confirming the new block does not destabilize a path that already worked.
