# Close-out note: the buyback study template is done

Written 2026-08-13 at the end of the close-out session. This is the last revision session on
the template itself. What follows are applications of it, not further work on it.

James's ruling of 2026-08-13 was that the revision cycle stops here, that the goal is a
template he can point at any ticker rather than a template that is perfect, and that general
defects get fixed now while anything peculiar to one company waits until that company comes
up. Three things were asked for. All three are done and nothing else was started.

## One: the entry effect now lives in the template

It was the last measure in this study still written out once per company, in
`code/gen_article.py` for Apple and again in `code/full_study_COST.py` for Costco. Two
definitions of one quantity is the exact shape of the defect this repository keeps meeting —
a number that is internally consistent, passes every gate, and is wrong in one of its two
homes.

The entity-level abnormal earnings growth recursion, the entry effect on each tranche, the
continuing effect, the cost-of-equity break-even and the earnings-timing decomposition are now
`BuybackStudy.entry_effect()` and both drivers read them from there. Items 4 and 5 removed the
same duplication for the net retirement cost and the excise tax; this closes the set.

**The proof standard was met and then some.** The regenerated Apple document is not merely
free of moved numeric tokens — it is byte-for-byte identical to the version generated before
the change, 96,116 bytes, 1,268 numeric tokens, none of them different. The comparison is no
longer done by eye: `code/numeric_token_diff.py` is committed and is the tool for it.

Ninety-six new checks in `code/verify.py` prove the template reproduces that file's own
independent arithmetic — every tranche, both totals, the break-even on all three windows, the
whole six-estimator decomposition band, the entity-level account and the continuing effect —
to floating-point exactness. The share flows handed to the template in those checks are
`verify.py`'s own reconstruction, not the ones the Apple driver uses, so this is not the
template checking itself against itself.

**One thing about the template's new methods is worth knowing.** The real earnings series is
defined over the study window plus the single year before it, and not over every year the
source statements happen to reach back to. That matters because two of the three trend
estimators read neighbouring years out of the series: the centred geometric mean takes a
window either side of the year it is evaluating, and the engine normalizer walks back from the
earliest year present. Apple's income statement carries every year from 1985. Had the template
taken all of it, the decomposition would have changed while every identity check still closed.
The span is a stated convention and `verify.py` proves it binds.

## Two: one generic driver

`code/run_study.py` takes a ticker and a small configuration block and produces a full study
with no company-specific code in it. Before this, "the template works on any company" was true
of the measurements and false of everything around them: `gen_article.py` carried
ninety-three references to Apple and `run_COST.py` was a Costco script.

What legitimately stays per company is the CompanyConfig — central index key, fiscal year end,
splits, window — plus the price series, the deflator, the real cost of equity, and any figure
that has to be read off a filing by a person. The excise tax is the standing example of the
last, because most companies that disclose it at all use their own extension element, which
cannot be reached through the structured company-concept interface.

The driver collects every refusal, fallback and suppression it meets and prints them at the
end under one heading. A run that reports none on an unfamiliar company should be read with
suspicion rather than satisfaction.

## Three: the cold run, and defect 13

Oracle, fiscal 2013 to fiscal 2025, never touched by this project. Read
`COLD-RUN-Oracle-2026-08-13.md`; the summary is that the driver crashed on the first attempt
and that finding it was the return on the exercise.

**Defect 13.** `eps_attribution()` split the earnings channel into operating and financial by
striking an effective tax rate off pretax income, built that rate only for the years it could,
and then read the result unconditionally. Oracle stops tagging pretax income after fiscal 2018
under either element name, so it died with a bare `KeyError`. Fixed: the two channels that
need no tax rate are computed for every year, the split is `None` where it is not
determinable, and the years without one are named. The dangerous version of this bug is not
the one that stops but the one that quietly publishes an attribution over a shorter window
than its own heading claims.

Thirty guard messages on the cold run. Two of them deserve a person's attention. Oracle's
timing dependence is 336 percent — the accident of which accounting year followed each
purchase is more than three times the headline it sits inside, driven by the Tax Cuts and Jobs
Act transition charge landing in a May year end — so Oracle's entry effect must never be
quoted as a verdict on the price paid. And the cumulative entry effect is positive by
seventeen basis points of headroom over its own break-even, on a placeholder rate, which means
no sign should be quoted for Oracle until a real cost of equity is run for it.

## A defect found in passing, and corrected

`code/full_study_COST.py` was dividing by the consumer price index deflator instead of
multiplying by it, and lagging it a year. The committed deflator row says, in its own label,
"MULTIPLIER: nominal x this = base-year 2026$. Do NOT divide." The same script's `study`
object was meanwhile using the same dictionary the right way round through the template's own
`real_repurchase_price()`, so one file held two conventions for one quantity and they
disagreed by roughly a factor of two at the start of the window.

Nothing published moves. `docs/Costco-Buyback-Study-2026-08-12.docx` was written by hand
rather than generated by that script, and regenerating it is explicitly out of scope for this
session. But every real figure that script prints does move, and the tell that the old numbers
were wrong is plain: the fitted real earnings-per-share trend came out at 17.73 percent a
year, which is higher than Costco's nominal earnings growth over the same window and is
therefore impossible with positive inflation. Corrected, it is 10.62 percent. **When the
Costco document is regenerated, it must be regenerated against these figures and not the old
ones.**

This is the argument for removing duplication, made by the duplication itself.

## Gates

Four, as before, all offline against committed fixtures, all green:

| Gate | Before | After |
|---|---|---|
| `code/verify.py` | 237 checks | **333 checks** |
| `code/template_test_HD.py` | 18 checks | **+19 checks** (defect 13, the entry effect's guards, the Oracle cold run reproduced offline) |
| `code/excise_test_ORLY.py` | 37 checks | 37 checks |
| `code/roundtrip_test_AAL.py` | 27 checks | 27 checks |

No fifth job was added. The cold run is gated inside the template regression test because it
is a fact about the template, not about a company.

## What is deliberately not here

Boeing's round trip and the Costco document regeneration were both explicitly out of scope and
were not touched. They are applications of a finished template and James will ask for them. No
fifth addendum item was proposed and no methodology question was reopened.

## What the next session should know

The template is closed. Point `code/run_study.py` at a ticker. If it refuses, the refusal is
the output — read it, decide whether the company can be measured, and say so in the study
rather than clearing the guard. Two things still need a person before any company study can
state a sign: a real cost of equity from the valuation engine for that ticker, and a reading
of the filings for whether the excise tax sits inside `PaymentsForRepurchaseOfCommonStock`,
which is true of some companies and not others and would double count if assumed.
