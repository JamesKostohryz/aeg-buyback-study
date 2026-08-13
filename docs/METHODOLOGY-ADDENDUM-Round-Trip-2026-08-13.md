# Methodology addendum: the round trip

**2026-08-13. Implements item 3 of `00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md`,
which specified it and left it unbuilt. Nothing else from that document is touched.**

## 1. What was missing

Buy heavily near a peak, then issue equity near a trough. It is the case that animates the
entire public argument against share repurchases, and until today this template could not see
it, because Apple — the company it was generalized from — has never raised equity, so nothing
was built. A template that cannot detect a company retiring stock at sixty dollars and issuing
it back at fifteen four years later is missing the finding a reader will most want.

The measure is now built, into `buyback_study_TEMPLATE.py` rather than into a third
per-company driver, and it is proven on a company that did it.

## 2. What it claims, and what it does not

Shares are fungible. No particular share repurchased in 2016 is the share sold in 2020, and
this measure does not pretend otherwise. What it computes is an inventory question with an
exact answer: over a window the company took a quantity of its own equity off the market at
one set of prices and put a quantity back on at another, and the difference in real cash on
the overlapping quantity is a fact about the program.

Three properties govern it. Ordering is respected, so only repurchases that precede a raise
can be matched to it. The matching convention is average cost, which is the one convention
that requires no arbitrary choice of order within the pool, and first-in-first-out is computed
alongside it as an independent route. And the measure is rate-free by construction: it is
shares multiplied by a difference between two transacted prices, it contains no cost of
equity, and it cannot be tuned by any argument about the capitalization rate.

Scope is unchanged and remains ex-post disclosure only. The round trip moves no valuation
number, is not an expense, does not enter the Abnormal Earnings Growth (AEG) account, and
states no estimate of Intrinsic Value or of Neutral Value for any company. Section 8 of the
style guide, which requires every company piece to state Neutral Value, Price to Neutral
Earnings Power and the neutral multiple as figures, does not bind here because this is not a
company piece and no valuation is offered.

## 3. The measure

For each fiscal year the template takes repurchase cash against the shares actually retired,
and equity raised against the shares actually issued in the raise, deflating each end at its
own year so that a round trip spanning a period of inflation is correctly larger in real terms
than in nominal terms. Repurchased shares accumulate in a pool carrying their real cost. When
a raise occurs, the overlapping quantity is drawn from the pool at the pool's running average
real cost, and the round-trip loss is that cost less the real proceeds received. Any part of a
raise exceeding the pool is reported separately as new equity and contributes nothing to the
loss. A company that never raised equity returns a true zero on every total, with
`has_round_trip` false, which is a fact about the company rather than a missing value.

Every central figure is computed three ways before a sentence is written about it. Average
cost is the primary route. First-in-first-out is rebuilt by a separate function that makes a
plainer pass over the same primary inputs, so agreement is evidence rather than restatement.
And the loss is independently reconstructed as matched shares multiplied by the difference
between the two prices. The gap between the average-cost and first-in-first-out readings is
the ordering effect, which is reported rather than suppressed: it says how much of the answer
depends on which repurchase tranche one chooses to call the one that was sold back, and that
is not a knowable fact. This follows the convention the study already uses for the cost of
equity and for the earnings trend, where two readings are published, provenance is stated, and
the study declines to choose.

## 4. Choosing the company, and how it was confirmed

Four candidates were named as unverified leads: Carnival, American Airlines, Boeing and
Occidental. All four were screened against live Securities and Exchange Commission
company-concept data on 2026-08-13.

**Occidental was rejected on sequence.** Its ten billion dollar equity issuance falls in fiscal
2019 and its repurchases of four point nine billion dollars fall in fiscal 2022 and 2023. It
issued and then bought. That is the opposite trade, and it is not a round trip.

**Carnival exhibits the pattern most dramatically of the four and cannot be measured.** It
spent five point seven billion dollars retiring stock through fiscal 2020 while the shares
traded between roughly forty and seventy-three dollars, then raised five point four billion
dollars between fiscal 2020 and 2023 in years whose traded lows were seven dollars eighty and
six dollars eleven. But Carnival tags no period-end shares outstanding in any year of its
history, no share-retirement flow, and a treasury share balance in only two years. The share
counts the measure needs do not exist in the filings as tagged data, and inventing them would
be precisely the failure this template refuses elsewhere. Carnival is recorded as the strongest
known candidate and as blocked on data, not on method.

**Boeing is genuine but weak, and it is blocked on a different addendum item.** It spent
forty-three point four billion dollars acquiring two hundred fifty-eight million shares between
fiscal 2013 and 2019 at an average of one hundred sixty-eight dollars, and raised eighteen
point two billion dollars in fiscal 2024 at around one hundred forty-three dollars for the
common component. The gap is real but modest, the raise was partly in convertible preferred
rather than common, and — decisively — Boeing holds its repurchased shares in treasury and
reissued one hundred forty million of them to settle the 2024 raise. Measuring that correctly
requires item 4 of the generalization addendum, treasury permanence, which is not built. Boeing
should be run after item 4 lands, not before.

**American Airlines was chosen.** It is the only one of the four where the sequence is
unambiguous, the magnitude is large, and every quantity the measure needs is filed at the
strongest available tier: a real share-retirement flow covering every repurchase year rather
than a treasury balance differenced, period-end shares outstanding for every year, the raise
disclosed in the statement of stockholders' equity with the share count and the dollar amount
on the same line, and explicit filed zeros for the equity line in the non-raise years, so that
the absence of a raise is a filed fact rather than a missing tag.

Two independent confirmations were required before the company was accepted. On the buy side,
the price rebuilt from the equity statement was checked against a third tag the measure does
not use — the company's own disclosed average cost per share. It reproduces that disclosure to
within a cent in fiscal 2014 and 2016, three cents in fiscal 2015, and thirty-five cents, or
eight tenths of one percent, in fiscal 2017, which is the worst of the four disclosed years.
On the sell side, the equity statement's share count was checked against the individual
offerings named in the narrative of the fiscal 2020 Form 10-K: eighty-five point two million
shares at thirteen dollars fifty and forty-four point three million at twelve dollars
ninety-seven and a half in two underwritten public offerings, and sixty-eight point six million
at an average of twelve dollars eighty-seven under an at-the-market program. Those add to one
hundred ninety-eight point zero six million shares against the equity statement's one hundred
ninety-eight point zero five million.

## 5. What American Airlines did

Between fiscal 2014 and fiscal 2020 American Airlines spent twelve point six billion dollars,
net of employee tax withholding presented on the same cash-flow line, retiring three hundred
nineteen point four million of its own shares. In fiscal 2020 and 2021 it sold two hundred
twenty-two point two million shares back to the market for three billion sixteen million
dollars in cash of the day.

Netting out four million shares of ordinary employee-plan issuance leaves two hundred eighteen
point two million shares that overlap the repurchase pool. Measured in real terms on those
shares, the company paid fifty-three dollars sixty-nine and received seventeen dollars
thirty-nine: eleven point seven billion dollars of real capital went out and three point eight
billion came back. **The real round-trip loss is seven point
nine billion dollars — thirty-two cents returned on the dollar, on sixty-eight percent of every
share the program ever retired, and equal to forty-five percent of the entire real cost of the
repurchase program.** The first-in-first-out reading is eight point three billion dollars; the
ordering effect is four point nine percent and the two readings are published together.

Every implied price at both ends was validated against that fiscal year's intra-day high and
low, never against period-end closes.

## 6. The finding that matters more than the number

The obvious way to build this measure is to divide the financing-activities line "proceeds from
issuance of equity" by the change in shares outstanding. On American Airlines' fiscal 2020 that
gives fifteen dollars a share. The true figure, from the company's own statement of
stockholders' equity, is twelve dollars ninety-one.

The two thousand nine hundred seventy million dollar financing line contains four hundred
fifteen million dollars that is the equity component of the company's six and a half percent
convertible notes, bifurcated out of debt proceeds under the standard then in force and removed
again on 1 January 2021 when the company adopted the replacement standard. No share was ever
issued for it.

The contaminated price is sixteen percent too high. It errs in the direction that flatters the
repurchase program. And fifteen dollars sits comfortably inside the stock's 2020 traded range
of eight dollars twenty-five to thirty dollars seventy-eight, so the price validator — the guard
that has caught silent estimation failures on two other companies and is never optional — passes
it without a murmur.

**This is the seventh instance of this project's standing hazard: a number that is internally
consistent and externally wrong while every gate reports success.** It also states the limit of
the price validator precisely, which is worth writing down. That validator can only catch a
price outside the range of prices that existed. It cannot catch a contaminated numerator whose
error is small relative to the width of the traded range, and on a volatile stock the traded
range is very wide. A validator that passes anything between eight and thirty-one dollars is not
a strong test of a twelve dollar figure.

So the round trip is struck on the statement of stockholders' equity, where the share count and
the dollar amount sit on the same line and cannot drift apart, and the financing-activities line
is used only to reconcile. Where the two disagree beyond one half of one percent, the difference
must be named explicitly in the company's configuration or the year is refused outright — not
netted, not averaged, not absorbed into the issue price. Refusing with the four hundred fifteen
million dollars unnamed is tested, and it removes fiscal 2020 from the measure entirely rather
than pricing it wrongly.

## 7. Two defects in the existing template, found by pointing it at this company

Neither is caused by the round trip. Both were latent and would have produced a confidently
wrong published figure on the next cyclical company the template was pointed at.

**Defect 10 — a retirement derived for a year with no repurchase.** The share-flow fallback
derives a retirement count from a share-count movement when no count is filed. It did not check
whether the company spent anything repurchasing that year. American Airlines' fiscal 2021 and
2022 each tag a repurchase cash line — eighteen and twenty-one million dollars — and every
dollar of both is employee tax withholding presented on the same line. The company repurchased
nothing in either year; under its payroll support agreements it was contractually barred from
doing so. A template that read that line as a repurchase would have published American Airlines
buying back its own stock in years it was prohibited from buying back its own stock. A year with
no filed retirement count and no repurchase cash net of withholding is now recorded as a year the
company did not repurchase, which is a fact, and the question is settled before the fallback is
consulted at all.

**Defect 11 — a structural share issuance contaminating the issuance-rate fallback.** Defect 5's
fix estimates the ordinary issuance rate from the earliest observable years, which is right when
the only thing moving the share count is employee plan activity. American Airlines' fiscal 2014
prints an issuance rate of thirty-six point eight percent of opening shares, because that is the
year the US Airways merger shares and the bankruptcy claim distributions landed. Averaged into
the fallback it gave thirteen percent, which then manufactured fifty-four point six and
eighty-one point three million shares of retirement in fiscal 2021 and 2022 — years in which the
company retired nothing. No ordinary employee plan issues five percent of a company in a year, so
a rate above five percent is now refused rather than used, the affected years fall through to the
unresolved handling where a share count and a price are not invented for them, and the refusal is
announced. The bound is a named parameter with a stated default, not a hidden constant, and a
company for which a higher rate is genuinely ordinary can raise it explicitly and say so.

It is worth recording how defect 11 surfaced: the intra-day price validator caught it. The
manufactured retirements implied prices of thirty-three and twenty-six cents against traded lows
above eleven dollars. That is the second and third company on which that validator has earned
its place, and the case for never making it optional is now stronger than it was this morning.

## 8. A third change, to remove a standing hazard rather than a defect

`buyback_study.py` at the repository root was a byte-identical hand-maintained copy of
`buyback_study_TEMPLATE.py`, carrying a header instructing each session to copy its changes
across. Holding two copies of an eight-hundred-line module in step by hand is the exact shape of
the duplicate-file problem this repository was bitten by three times on 2026-08-12, and today's
work doubled the exposure. The copy is replaced by a re-export shim containing no code, so the
two names now resolve to one definition in one file and cannot diverge at all.

## 9. Where it lives, and what it does not solve

The measure is `round_trip()`, `round_trip_reconciled()`, `reconcile_raises()`,
`resolved_raises()`, `validate_raise_prices()` and `real_repurchase_price()` on `BuybackStudy`,
with the `EquityRaise` record beside `CompanyConfig`. All of it is in the template and none of it
is duplicated into a company driver. It is exercised by nineteen new checks in `code/verify.py`,
which now reports two hundred and three passing checks against one hundred and eighty-four
before, and by twenty-seven checks in `code/roundtrip_test_AAL.py`. Both are gated in continuous
integration on every push, and both run offline against committed fixtures.

No figure published before this addendum moves. Apple raised no equity inside its window, so
Apple's round trip is a true zero and the Apple document is unchanged. That zero is itself
verified rather than assumed, because a measure that now runs unconditionally on every company
is most likely to fail quietly on the company that did not do the thing.

Three things this does not solve. It says nothing about whether a raise was avoidable, and a
company forced to the market by a pandemic is not thereby proved to have mistimed its
repurchases — the measure reports what the round trip cost, not whether it was culpable, and that
judgment stays with a person. It cannot yet be run on a company that holds its shares in
treasury and reissues them into the raise, which is Boeing and a large fraction of the market,
because that needs item 4. And it is blind to a company whose share counts are not tagged at all,
which is Carnival, and no method fixes a fact that is not filed.
