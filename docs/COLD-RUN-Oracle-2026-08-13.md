# The cold run: Oracle, fiscal 2013 to fiscal 2025

Written 2026-08-13, close-out session. The full machine transcript is
`COLD-RUN-Oracle-transcript-2026-08-13.txt` alongside this file and every figure quoted
here is read out of it.

## Why Oracle

The instruction was to point the new generic driver at one company nobody in this project
has touched and publish what happened, on the understanding that a refusal is a pass. The
companies already touched are Apple, Costco, Home Depot, American Airlines, O'Reilly
Automotive, Salesforce, Boeing, Coca-Cola, Walmart, PepsiCo, McDonald's, Procter and
Gamble, Netflix, Carnival, Occidental, VeriSign, McKesson and Constellation Brands. Oracle
is none of them, and it was chosen for four reasons rather than at random.

It has one of the largest and longest repurchase programs in the market, so there is
enough of a record to break something. Its fiscal year ends on the thirty-first of May,
which means the year that straddles the thirty-first of December 2022 is partly exposed to
the repurchase excise tax and partly not — the proration built for item 5 had to work or
produce a wrong number. It funded much of the program with debt, which is the case where
the cost-of-equity break-even matters most, because a company that levers up to buy its own
stock raises the required return on the equity that remains. And it is a cancelling
company with a clean filed retirement flow, so nothing in the run would be excused by bad
data.

## What broke

The driver crashed on the first attempt, and finding that is the main return on the
exercise.

The earnings-per-share attribution splits the earnings channel into an operating part and
a financial part by striking an effective tax rate off pretax income. Oracle tags
`IncomeLossFromContinuingOperationsBeforeIncomeTaxes...` for fiscal 2011 through fiscal
2018 and then stops, under either of the two element names the template knows. The code
built the tax rate only for the years it could and then read the result unconditionally,
dying with a bare `KeyError: 2019`.

The crash is the good outcome and it is worth saying why. The dangerous version of this bug
is not the one that stops; it is the one that quietly skips the years it cannot split and
publishes an attribution over a shorter window than the one named in its own heading. That
would have closed every identity it has and been wrong about the company — the failure mode
this project has now met nine times. This is recorded as **defect 13** and it is fixed: the
two channels that need no tax rate are computed for every year, the operating and financial
split is filled in only where it is determinable and set to `None` where it is not, and the
years without a split are named in the notes. A `None` is visible in every table it reaches;
a silently shorter window is not. Four checks in `code/template_test_HD.py` hold it there.

## Which guards spoke, and what they said

Thirty guard messages. In summary:

**Eleven elements are not filed by Oracle in any year**, including every treasury element of
every name. That absence is what tells the template Oracle cancels its repurchased shares
rather than parking them, so the phrase "permanently removed" is earned from the filings
rather than assumed. It also means Oracle files no long-term debt element under either of the
two names in the template's list, so the net-operating-asset lines that need a debt figure
report the line as missing rather than treating an untagged debt stack as no debt.

**The excise tax refused outright.** Oracle's fiscal 2023 runs from June 2022 to May 2023, so
five of its twelve months fall after the thirty-first of December 2022 and the year is
forty-two percent exposed. Oracle discloses no figure. The template therefore produced no
number at all, which is the default and is correct: a driver has to opt in explicitly before
a statutory reconstruction appears, and this one did not.

**Four years of the net retirement cost are suppressed** — fiscal 2017, 2023, 2024 and 2025 —
because Oracle's net reduction in those years falls below a quarter of one percent of opening
shares. A ratio on a small denominator is meaningless and, worse, is far more likely to be
believed than a missing one.

**The earliest-years issuance fallback fired**, holding the unobserved years at 1.84 percent of
opening shares, the rate observed in the three earliest observable years rather than the mean
of the whole window. That is defect 11's guard doing its job; the rate is well inside the five
percent bound above which a rate is refused rather than used.

**Every implied average price paid sits inside its own fiscal year's traded range**, checked
against intra-month extremes rather than period-end closes. No price failures.

## The two findings a person should read

**Oracle's entry effect must not be read as a verdict on the price paid.** The
earnings-timing decomposition built for item 1 puts the timing component at 336 percent of
the headline: the accident of which accounting year happened to follow each purchase is more
than three times the size of the result it sits inside. The cause is visible in the tranche
table. Fiscal 2018 real earnings per share come in at $1.13 against a trend near $3, because
the Tax Cuts and Jobs Act transition charge landed in a May year end; fiscal 2022 comes in at
$2.76 for acquisition reasons. Two accounting years carry the whole verdict. The symmetric and
backward-looking estimator families disagree on the sign of the price decision, so the trend
level is not point-identified here either, and the band is the only honest publication. This
is the first company on which the diagnostic has exceeded one hundred percent, and it is the
clearest vindication the item 1 addendum has had: without the split, the study would have
reported a positive entry effect on Oracle and been reporting the corporate tax code.

**The sign of Oracle's headline is decided by a rate nobody has sourced.** The cumulative
entry effect is $+0.33 billion at the 5.50 percent placeholder real cost of equity. The
break-even — the retirement-weighted forward real earnings yield on the program, which is an
exact root and not a search — is 5.67 percent. There are seventeen basis points of headroom.
Any engine-sourced rate for Oracle above 5.67 percent inverts the conclusion, and for a
company that funded its repurchases with debt, a real cost of equity below that is not the way
to bet. **No sign should be quoted for Oracle until a real cost of equity is run for it.**
The early tranches break even at 6.00 percent and the late ones at 5.11 percent, so the
program bought well before 2020 and badly after it, which is the same shape the Apple study
found and is not a coincidence about either company.

## What this is not

This is not a study of Oracle. It is a proving run of the driver, on a placeholder rate, with
no forecast, no Neutral Value and no valuation attached. Nothing here moves an engine number
and no figure in it should be quoted for Oracle outside the context above.

## Reproducing it

The fixtures are committed, so it repeats offline with no network:

    cd code
    python3 run_study.py --ticker ORCL --cik 0001341439 --fy-end-month 5 \
        --first-year 2013 --last-year 2025 --coe 0.055 \
        --prices orcl_monthly.csv --traded-range orcl_traded_range.csv --split-year 2020

Add `--fetch` to pull fresh structured data from the Securities and Exchange Commission and
overwrite `orcl_sec_raw.json`. Eight of the checks in `code/template_test_HD.py` re-run the
whole thing offline and assert the findings above, so a change that silently alters them
fails the build.
