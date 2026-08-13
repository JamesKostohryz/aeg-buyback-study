# HANDOFF — Apple share repurchase study

Paste this whole file into a fresh chat in the AEG Valuation System 2 project. Written 2026-08-12,
**replacing** `AEG Buyback Study/00-NEXT-SESSION-PROMPT-Buyback-Study-2026-08-09.md`, which was
written before the engine's canonical-closure work landed and is now wrong in three places.
**Recommended model: Opus for section 2, Sonnet for section 3.**

**First action.** Ask James to grant the folder `C:\Users\james\AEG-Project` and read
`00-START-HERE.md` in it before anything else. That folder is now the single working home of this
project. The session that wrote this handoff could not reach it — the desktop bridge was
disconnected — so everything below was verified against the public repository and project knowledge
instead, and anything in that folder overrides this file.

**A note on the word "template," which is overloaded here.** Section 3 is about
`buyback_study_TEMPLATE.py`, the generalized Python code that applies the study to any company. That
is a different thing from "Template A," the implied-expectations report template, which is separate
work in the `AEG Report Templates And Sample Reports` folder and is not this job.

---

# 1 · STOP — what changed at HEAD, and what it breaks

Repository HEAD is `3937d5e`, 2026-08-11. Between the study being finished and this handoff, the
canonical operating closure landed and the engine's published outputs changed shape. **Three things
in the finished study are now broken or unquotable. Do not rebuild the document until you have read
this whole section.**

**1.1 · The file the generator reads no longer exists.** `gen_article.py` reads
`outputs/AAPL_summary.csv` at build time — a change made deliberately so a stale anchor could not
survive a rebuild. At HEAD that file is now `outputs/AAPL_summary.STALE.csv`. **The build will crash.**

**1.2 · The engine is REFUSING to value Apple.** `outputs/AAPL_REFUSED.csv` reads: *"UNFUNDED
DISTRIBUTION — no valuation produced for AAPL. implied dividend is NEGATIVE in 10 of 10 forecast
years; worst −2.3864/sh in year 10 — the plan implies issuing equity to fund a buyback."* That is the
new two-of-three rule biting on the default Consensus overlay, which carries a three percent buyback
against 2.5 percent asset growth. It is the gate working as designed, not a bug. Until a reviewed
funding decision is recorded in `companies/AAPL.yaml`, there is no current Apple valuation.

**1.3 · The two engine figures the study depends on have not moved, but they are quarantined.** In
the STALE file, `normal_no_growth_value_ps` is still `115.455908754725` and `real_coe_longrun` is
still `0.0548806713262307` — byte-identical to what the study published. That is genuinely
reassuring about the *arithmetic*. It does not license quoting them: the file's own note says the
STALE figures "are not current and must not be published or quoted," and the project instructions
now say any valuation quoted from before 2026-08-11 is stale and that no payload-free number should
be quoted for any company.

**What that means in practice, and it is narrower than it sounds.** The study's own measures — the
price paid, the shares retired, the earnings yields, the entry and continuing effects, the funding
decomposition, the Real Capital Base, the return on retained earnings, the internal rates of return
at market and at the multiple paid — are computed from Securities and Exchange Commission filings
and an external price series. **None of them moves.** The exposure is exactly three things:

- section 11, which quotes Neutral Value, the Neutral P/E and the premium to Neutral Value;
- the "at Neutral Value" column of the internal-rate-of-return table, and the break-even, both of
  which use the real cost of equity and Neutral Value;
- everywhere the real cost of equity of 5.4881 percent appears — which is most of the document.

**Recommended handling, and this is the one judgment call in section 1.** Do not strip those figures
out. Rebuild against the STALE file, and add one visible line to the method footer and the build note
saying the engine anchor is read from a run the engine has since quarantined, that the two figures
used are unchanged from the last published run, and that the document will be re-issued when Apple's
funding review clears the gate. That is honest, it preserves a working document, and it does not
pretend to a currency the engine itself is refusing to claim. **Put that to James before you publish
it — it is his call, not yours.**

**1.4 · The engine already acted on the debt finding, and went further than we did.**
`pipeline/debt_feed.py` now exists. It states our finding in its own docstring, credits
`debt_feed_disagreements()` from the study's `build.py` as the shape it generalized, and adds the
thing we could not establish from outside: **substituting primary source for the vendor row moved
Apple's tied engine equity from 87.1659 to 89.8409 per share — with the four-method tie green at
1.3e-14 in BOTH runs.** So the answer to the question the old engine prompt posed is: it is GATED,
it does move a valuation number, and the tie is structurally blind to it. `in_debt` still comes from
the vendor row; the module reports rather than prefers. **The old engine prompt at
`claude/00-NEXT-SESSION-PROMPT-Engine-Vendor-Debt-2026-08-09.md` is superseded and should not be
pasted into a new chat.**

It also refined our finding, correctly. We said the vendor started folding leases in at fiscal 2024.
It is two shifts, not one: the fiscal 2022 and 2023 gaps of $812 million and $859 million are
Apple's **noncurrent finance leases to the dollar**, and the fiscal 2024 and 2025 gaps of $12,430
million and $13,720 million are **every capitalized lease it carries** — operating plus finance,
current plus noncurrent, exact in both years. Verified independently this session against
`FinanceLeaseLiabilityNoncurrent`, `FinanceLeaseLiabilityCurrent`,
`OperatingLeaseLiabilityCurrent` and `OperatingLeaseLiabilityNoncurrent`.

**1.5 · One contradiction to hand back, with the arithmetic that settles it.** `debt_feed.py`'s
docstring asserts a clean break for Apple. The committed `outputs/AAPL_debt_feed.csv` returns
`UNVERIFIED` for Apple on the grounds that *"the two feeds agree and disagree in alternating years
(disagreements begin 2022 but agreement continues to 2025); that is the signature of an incomplete
reconstruction on our side."* Both artifacts are in the same commit and they cannot both be right.

For Apple the break is clean, and here is the reconstruction that shows it. Using
`LongTermDebtNoncurrent` + `LongTermDebtCurrent` + `CommercialPaper`, falling back to `LongTermDebt`
+ `CommercialPaper` where the components are untagged: fiscal 2012 through 2021 agree with the vendor
**to the dollar, ten consecutive years**, and fiscal 2022, 2023, 2024 and 2025 all disagree, by
812, 859, 12,430 and 13,720. There is no alternation. Apple tags neither
`LongTermDebtAndCapitalLeaseObligations` nor `DebtLongtermAndShorttermCombinedAmount`, so a fallback
to either cannot be the cause; the likeliest explanation is a tag-coverage gap in the runtime for
2015 through 2021, where Apple tags the components but not `LongTermDebt`. **This is a note for the
engine chat, not work for this one.**

---

# 2 · NEW WORK JAMES ASKED FOR — the net share-count analysis

Two requests, made 2026-08-12. The first is arithmetic and is already done; the numbers are below,
recomputed this session, and need only to be dropped into the document. The second is a
methodological question that has been answered with a recommendation, and the recommendation needs
building.

## 2.1 · The table James asked for. Publish it.

Gross repurchases in dollars and as a percentage of shares, annually, less issuance, giving the net
share-count change. Computed 2026-08-12 from the study's own committed inputs.

| FY | Cash $m | Gross retired mn | % of shares | Issued mn | % of shares | NET change mn | % of shares | Gross price | NET cost/share |
|---|---|---|---|---|---|---|---|---|---|
| 2013 | 22,860 | 1,304 | 4.96% | 184 | 0.70% | 1,120 | 4.26% | 17.53 | 20.41 |
| 2014 | 45,000 | 1,890 | 7.50% | 176 | 0.70% | 1,713 | 6.80% | 23.81 | 26.26 |
| 2015 | 35,253 | 1,314 | 5.60% | 164 | 0.70% | 1,150 | 4.90% | 26.83 | 30.66 |
| 2016 | 29,722 | 1,127 | 5.05% | 156 | 0.70% | 970 | 4.35% | 26.38 | 30.63 |
| 2017 | 32,900 | 989 | 4.63% | 149 | 0.70% | 840 | 3.93% | 33.26 | 39.17 |
| 2018 | 72,738 | 1,622 | 7.91% | 137 | 0.67% | 1,485 | 7.24% | 44.84 | 48.99 |
| 2019 | 66,897 | 1,381 | 7.26% | 134 | 0.70% | 1,247 | 6.56% | 48.45 | 53.65 |
| 2020 | 72,358 | 917 | 5.16% | 121 | 0.68% | 796 | 4.48% | 78.91 | 90.88 |
| 2021 | 85,971 | 656 | 3.86% | 106 | 0.62% | 550 | 3.24% | 131.05 | 156.32 |
| 2022 | 89,402 | 569 | 3.46% | 86 | 0.52% | 483 | 2.94% | 157.12 | 184.96 |
| 2023 | 77,550 | 471 | 2.95% | 78 | 0.49% | 393 | 2.47% | 164.65 | 197.15 |
| 2024 | 94,949 | 499 | 3.21% | 66 | 0.42% | 433 | 2.79% | 190.28 | 219.14 |
| 2025 | 90,711 | 402 | 2.66% | 58 | 0.39% | 344 | 2.27% | 225.65 | 264.06 |
| **Total** | **816,311** | **13,140** | — | **1,615** | — | **11,525** | — | **62.12** | **70.83** |

Shares outstanding went from 26,298 million to 14,773 million. Issuance was 12.3 percent of gross
retirement. Employee-plan proceeds received over the period were $6,288 million and cash withholding
tax paid on employee awards was $45,772 million.

## 2.2 · The four measures, and why all four belong in one table

    A  cash / GROSS shares retired                              $62.12    the market price paid
    B  cash / NET share-count reduction                         $70.83    +14.0%   cost per share removed
    C  (cash - employee proceeds) / NET reduction               $70.29    +13.1%
    D  (cash + withholding tax - employee proceeds) / NET        $74.26    +19.5%   total cash spent
                                                                                    managing the count

**D is the fullest expression of what James is after, and C on its own would flatter the company.**
Adjusting for the cash employees paid in ($6.3 billion) while ignoring the cash Apple paid out to the
tax authority on their behalf ($45.8 billion) is a one-sided adjustment. Under net share settlement
the company pays that tax *instead of* issuing more shares, so it is money spent holding the count
down and it belongs on the same side of the ledger as the repurchase. It is seven times larger than
the proceeds.

## 2.3 · The methodological ruling, with the reasoning, so it is not reopened

**Yes, build it — as a disclosed measure with its own name. No, it is not a price, and it must never
be substituted for one.** Three conditions, and they are not optional.

**It cannot enter the abnormal-earnings account.** The entry effect is `E − ρP`, and it is an
identity only when `P` is the price actually transacted: the capital charge is on the cash actually
spent and the earnings acquired are those the shares actually retired carried. Substituting a
synthetic higher price would break the identity, move the pivot away from Neutral Value, and corrupt
every figure in section 3 of the study. The new measure sits beside the existing ones, not inside
them.

**It cannot be turned into an expense.** Share-based compensation is already charged to earnings at
grant-date fair value. Computing the net cost per share *and* treating the excess over the gross
price as an additional cost of the buyback charges the same compensation twice. This is the same
double count that had to be declined once already, in section 5 of the capital-decomposition
addendum. The measure is a descriptive ratio — dollars per unit of permanent count reduction — not a
value adjustment and not an addition to expense.

**It needs the same denominator guard as everything else.** Suppress and report the fact where the
net reduction is small or negative rather than printing a ratio. For Apple every year is safe. For a
company that issued more than it bought in a given year the ratio is negative and meaningless.

**Subject to those three, it is a good measure and it answers a question the gross price cannot.**
What did it cost to permanently remove one share? From a continuing shareholder's standpoint the
count reduction is the only thing they actually received, so that is arguably the more relevant
number. Call it the **net retirement cost**, or **cost per share of net count reduction** — anything
but "price paid."

## 2.4 · Where James is right, where the Apple case is weaker than he thinks, and a bonus

**Push back on Apple as the crazy case, because it is not one.** Apple's dilution offset is 12.3
percent of shares retired and 13.5 percent of dollars spent. The reframing raises the effective cost
from $62.12 to between $70.29 and $74.26 — fourteen to twenty percent. That is real, it is worth
publishing, and it is not scandalous. The honest Apple sentence is that roughly one dollar in seven
of the repurchase program was buying back stock the company had just issued to its own employees,
and that correcting for it raises the cost of permanently removing a share by about a fifth. Do not
let this get written up as an exposé; the numbers will not carry it and the study's credibility
rests on not overreaching.

**But the instinct behind the request is right, and it is stronger than James put it.** Salesforce,
computed this session from primary source:

| FY | Repurchase cash $m | Shares outstanding mn | NET reduction mn | NET cost per share | Traded range that year |
|---|---|---|---|---|---|
| 2024 | 7,620 | 971 | 10.0 | **$762.00** | 176–318 |
| 2025 | 7,829 | 962 | 9.0 | **$869.89** | 212–369 |
| 2026 | 12,596 | 929 | 33.0 | **$381.70** | 230–370 |

Two to three times the highest price the stock traded. **That** is the crazy case, and it is not
rare — it is the normal shape of a large-capitalization software company.

**And the bonus, which was not expected.** The net measure needs only two inputs — repurchase cash
and the change in shares outstanding — and both are available for every company that files. The
gross measure needs a share-retirement count, and Salesforce tags neither
`StockRepurchasedAndRetiredDuringPeriodShares` nor `TreasuryStockSharesAcquired`, so **no gross price
can be computed for it at all.** James's measure is therefore *more* general than the one the study
currently leads with, not less. That is a genuine argument for promoting it rather than appending it.

## 2.5 · What to build

Add a section to `gen_article.py` — provisionally section 7, pushing the funding decomposition and
everything after it down one, with exhibits renumbered — carrying the table in 2.1, the four
measures in 2.2, the ruling in 2.3 compressed to a short signal box, and the Salesforce contrast as
a single sentence with the three figures. Every figure computed, none typed. Extend `verify.py` with
checks that A, B, C and D reconcile to their definitions and that the published values match. The
identity `gross retired − issued = net reduction` must close exactly, every year and cumulatively;
it does.

---

# 3 · Repair the generalized study code

Nine defects, specified in full with the code that found them in
`AEG Buyback Study/Template-Exercise-FINDINGS-2026-08-09.md`. That document is unaffected by
anything in section 1 and is still accurate. Close the first five, re-run `template_test_HD.py`
against the fixed code, and regenerate the findings file. Do not generate a company report from it
until that passes.

The first two matter most. `parse_concept()` scans only the `USD` and `shares` unit buckets, and
diluted earnings per share is filed under `USD/shares`, so it returns an **empty** series for every
company and silently disables the attribution, the multiple paid and the whole timing test. And when
no year has an observable issuance rate the fallback is silently set to zero, collapsing shares
retired into the net share reduction and reporting a dilution offset of zero for exactly the
companies where dilution is the story.

**Note the connection to section 2, which is new.** That second defect makes the code compute
James's net measure *by accident* while labelling it the gross one. Once the net retirement cost is
a named measure in its own right, the fix is cleaner: when no retirement count is available, report
the net measure honestly and decline to report a gross price, rather than deriving a fictitious one.
Methodology section 3 already says this in words; the code should now say it too.

The rule behind six of the nine: **a missing input must never be silently treated as zero, and an
estimated input must always be announced.**

Still unexercised: the dilution offset at or above one hundred percent has never fired on real data.
Home Depot's is 7.5 percent and Salesforce tags nothing to compute it from. Find a company that tags
a retirement or treasury count *and* issues nearly as fast as it buys.

---

# 4 · Read these, in this order

1. `C:\Users\james\AEG-Project\00-START-HERE.md` — if you can get the folder. It overrides this file.
2. `AEG Buyback Study/00-Buyback-Study-METHODOLOGY-2026-08-09.md` — **version 2**, governing.
3. `AEG Buyback Study/Template-Exercise-FINDINGS-2026-08-09.md` — the work order for section 3.
4. `AEG Buyback Study/AAPL-Capital-Decomposition-ADDENDUM-2026-08-09.md` — version 2, reissued.
5. `AEG Buyback Study/AAPL-Buyback-FINDINGS-2026-08-09.md` — version 2, corrected.
6. `LANDING-INSTRUCTIONS-2026-08-10.md` and `AEG-Equity-Enterprise-RESOLUTION-2026-08-10.md` — what
   changed in the engine and why. Read these before you touch anything that reads engine output.
7. `AEG Definition & Explanation Articles/00-HOUSE-CONVENTIONS-2026-08-08.md`.
8. Load the `rva-style-guide` skill before writing a word of copy.

Code is in project knowledge under `AEG Buyback Study/code/`. To reproduce: clone
`JamesKostohryz/aeg-valuation`, copy `AAPL_reported_is.csv`, `AAPL_reported_bs.csv`,
`AAPL_reported_cf.csv`, `AAPL_dupont.csv`, `coe_history_AAPL_annual.csv` and `AAPL_restated.csv`
from `outputs/` alongside the code — **and `AAPL_summary.STALE.csv`, renamed, with the caveat in
section 1.3 attached** — then `python3 gen_article.py && python3 verify.py`. Before the new work,
verify must print ALL 40 CHECKS PASS.

---

# 5 · Settled. Do not reopen.

**The AEG pivot is Neutral Value, not Intrinsic Value.** Settled by James, 2026-08-09. A repurchase's
contribution to measured abnormal earnings growth is the earnings acquired less the real cost of
equity applied to the price paid, so it is positive precisely when the earnings yield at the price
paid exceeds the real cost of equity — that is, when the price paid sits below Neutral Value. No
estimate of Intrinsic Value enters it and none may be substituted. A previous session got this wrong
and it had to be corrected twice.

**Scope is ex-post disclosure only.** Nothing in this study moves a valuation number and it must stay
that way. The ex-ante benchmark that charges every capital source is separate gated work; see
`claude/AEG-Capital-Attribution-SPEC-2026-08-08.md`.

**The study states no estimate of Apple's Intrinsic Value.** It reports Neutral Value, the price, the
break-even, and what the price paid implies. The reader judges.

**The implied-expectations companion piece already exists** at `AEG Report Templates And Sample
Reports/Sample Reports/AAPL-Implied-Expectations-Report.html`. Revising it is Template A work in its
own chat, not this one. It carries a known error of its own: the line reading "Inflation adjustments,
net +$2.64 (debt capital gain +$2.87, depreciation penalty −$0.23)," in which all three parts are
wrong.

---

# 6 · Traps

The vendor cash-flow feed cannot be used for repurchases or issuance. The vendor balance-sheet
total-debt line cannot be differenced across fiscal 2022 or fiscal 2024. Use the Securities and
Exchange Commission XBRL company-concept interface; tags are in methodology section 2.

`Ordinary Shares Number` in the repository balance sheet is the weighted average diluted count, not
period-end shares. Period-end comes from `CommonStockSharesOutstanding`.

As-filed share counts sit on the split basis in force at the filing date. Derive the factor per
company; Apple needs ×28, ×4, ×1 and Home Depot needs 1.0 throughout.

Validate implied prices against intra-period highs and lows, never period-end closes. **This
validator is the most valuable guard in the study — it caught two separate silent estimation failures
on two different companies. Never make it optional.**

Suppress rather than print a ratio with a small or negative denominator, and make the guard
two-sided rather than sign-only.

Two averages exist for the price paid and they are nearly a factor of two apart — $62.12 weighted by
shares, $114.08 weighted by dollars. Say which weighting you are on, every time. Section 2 now adds
a third and a fourth quantity that are neither; name them carefully.

---

# 7 · Working rules

James is a financial markets analyst, not a programmer. Plain language, prose rather than bullet
lists in published copy, American spelling, acronyms written out on first use. When he must act, the
exact page, exactly what to click and where it is on screen, and what success looks like. One clear
question with a recommendation when a decision is needed, never a menu.

Every central measure is computed two independent ways and must reconcile before a sentence is
written about what it means. It caught the return-on-retained-earnings figure, it proved the derived
share counts, and it is the only reason the vendor total-debt break was found at all.

Do not publish a number about the engine that you have not traced to the engine at HEAD, and check
whether HEAD has moved before you trust anything in this file. It moved twice in the three days
between the study being finished and this handoff being written.

He wants precise pushback, not agreement. Three things in this study came from him challenging or
overruling a session: the Neutral Value pivot, the second reading of leverage, and the $62 labelling
error. One calculation he requested had to be declined as a double count and delivered a different
way instead. Section 2.4 of this file pushes back on his framing of the Apple case, and that
pushback is part of the deliverable, not a hedge.
