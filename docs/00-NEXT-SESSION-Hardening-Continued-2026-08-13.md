# Next session: finish the hardening, then build the filing reader

Written 2026-08-13 at the end of the hardening pass. Repo tip `4ff5d77`, five CI gates green.
Read `00-CLOSE-OUT-Template-2026-08-13.md` first for what the template is, then this.

## Where the hardening got to

Twenty-one untouched companies were run cold. Nine crashed or published nonsense. Eleven
defects, numbered 15 to 25, were found and fixed; the commit message for `4ff5d77` lists all
of them and defect 25 is the one to internalize, because it produced a number that was
internally consistent, closed every identity the template checks, and was wrong by a factor
of twenty-five.

The crash rate fell as the pass went on, from roughly one in two companies to roughly one in
five, and the remaining failures changed character: the early ones were "an input was assumed
present", the later ones were "an element name we did not know" and "a company shape we had
not met". That second kind does not converge to zero by running more companies of the same
sort. It converges by reading filings, which is the next build.

## Three things to do, in order

### One. Finish the sweep, and gate a fleet run

Run at least twenty more companies cold, chosen to break things rather than to succeed. The
shapes not yet exercised: a company with a reverse split inside the window; a foreign private
issuer filing 20-F rather than 10-K; a company that emerged from bankruptcy inside the window;
a real-estate investment trust; a bank holding company with preferred stock in the equity
statement; and any company that changed fiscal year end mid-window. Each is a shape, not a
name, and one of each is worth twenty more large-cap technology companies.

Then commit a **fleet gate**: a script that runs every committed fixture and asserts that each
either completes or refuses with a named reason, and that none of them crashes. Today the
cold-run coverage is one company inside `template_test_HD.py`. That was right when there was
one; it is not right now.

### Two. Build the filing reader, and make the study multi-pass

This is the answer to James's question of 2026-08-13 — what can a human find that the machine
cannot — and the answer is nothing, so the machine should find it.

Three separate problems all reduce to the same missing capability, which is why it is one
build rather than three:

The **excise tax** cannot be read from structured data because most companies that disclose it
use an extension element under their own namespace. Four different names were found on four
companies checked. The company-concept interface cannot reach any of them.

**Multi-class share counts** cannot be read from structured data either, for a different
reason: Meta Platforms and Alphabet report every share count dimensioned by share class, and
the company-concept and companyfacts interfaces both serve only undimensioned facts. Meta
Platforms currently has no share count at all and therefore no study.

**Equity raises for the round trip** are still hand-built from the statement of stockholders'
equity, which is the last genuinely manual input in the whole system.

All three live in the primary document. The sandbox reaches `www.sec.gov`, `data.sec.gov` and
`efts.sec.gov`, and full-text search is confirmed working. The build is: resolve a company's
Form 10-K accessions for the window from the submissions interface, fetch each primary
document, and extract from the inline XBRL — which carries extension elements, dimensions and
all — the quantities the structured interface drops. Cache the extracted facts to a committed
fixture so the run repeats offline like every other gate.

**Design the study as multi-pass and say so in the methodology.** Pass one is structured data
and produces a study with named holes. Pass two is the filing reader, which fills the holes it
can and reports what it could not. Pass three is a person, who sees only what survived two
passes and adjudicates genuine ambiguity — the case defect 12 describes, where a company's face
statement and its own note disagree and the tagged value is the wrong one. Nothing about a
study of this kind requires it to be completed in one run, and pretending otherwise is what put
manual inputs in the configuration block in the first place.

### Three. The remaining known limits, to be closed or documented

The `pretax_income` element list has two names and Oracle files neither after 2018, so the
operating/financial split is unavailable on a company with a full income statement. Either find
the elements or state the limit in the methodology.

`total_debt` has two names and Oracle files neither, so the net-operating-asset lines silently
lose a company with fifty billion dollars of debt. Same choice.

Timing dependence is a ratio whose denominator vanishes at the break-even, so it must always be
quoted with its rate. Decide whether the published form should be the ratio, the numerator in
dollars, or both.

## What must not be reopened

The cost of equity is an INPUT. `code/coe_invariance_test.py` proves, in 104 gated checks, that
swapping it moves only what it is supposed to move: every rate-free quantity is bit-identical
across a nine-hundred-basis-point swing, the break-even is unmoved, the entry effect is exactly
linear with slope equal to minus the real cash outlay to machine precision, and the
decomposition identity closes under all six estimators at every rate. A year-by-year series
substitutes for a scalar without ceremony. When the engine series arrives it is a substitution
and nothing more. Do not treat its absence as a blocker and do not rebuild anything to
accommodate it.

The Apple document must regenerate byte-identical. It has done so through every change in this
and the preceding session — 96,116 bytes, 1,268 numeric tokens, zero moved — and
`code/numeric_token_diff.py` is the tool that proves it. Any change that moves a token is
wrong until argued otherwise.

## Model

Sonnet. The design decisions above are made; what remains is running companies, reading
failures and writing principled fixes. Escalate to Opus only if the filing reader turns out to
need a judgment about what counts as a disclosure.
