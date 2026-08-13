# Methodology addendum — the excise tax on net repurchases, and the argument for repurchases

**2026-08-13. Item 5 of the generalization addendum of 2026-08-12. Landed with the template, four
continuous-integration gates and a new proving fixture.**

This addendum does two things the study previously did not. It puts a number on the one percent
United States excise on net share repurchases, which has been in force since 2023 and was absent from
the funding account; and it states, in the closing section and without a number attached, the
strongest honest argument in favor of repurchases, which is the deferral of shareholder tax into a
capital gain. Both were listed as open in section 5 of the generalization addendum. Neither moves any
valuation, neither touches the engine, and neither disturbs what the study already found.

---

## 1 · Three things the work order assumed that the filings do not support

The work order said to pull the excise tax per company from `ExciseTaxPayable` or the equivalent
disclosure. Checked live against the Securities and Exchange Commission on 2026-08-13, against both
the rendered filings and every inline extensible business reporting language element name inside
them, all three of its premises fail.

**There is no `ExciseTaxPayable`.** No such element carries this quantity for any company examined.
The only element in the generally accepted accounting principles taxonomy that does is
`ShareRepurchaseProgramExciseTax`. Companies that disclose the figure at all mostly do it through
their own extension elements, and the four checked used four different names for it — Netflix,
O'Reilly Automotive, VeriSign and McKesson each invented their own. An extension element cannot be
reached through the company-concept interface the template uses and does not appear in the
`companyfacts` bulk file either, so on those companies the number has to be read off the filing by a
person and handed to the template explicitly.

**No company in this study discloses a figure, in any year.** Apple's fiscal 2023 note says the
$76.6 billion it quotes is stated "excluding excise tax due under the Inflation Reduction Act of
2022," and then its fiscal 2024 and fiscal 2025 annual reports, and every quarterly report since,
stop using the word altogether. Home Depot states the accounting policy — that excise taxes are a
direct cost of the repurchase and go into the treasury cost basis — and then excludes them from every
table it prints, footnoting each one. Costco and Boeing never use the word. American Airlines uses it
only in risk-factor prose. The premise that a figure exists and merely needs pulling is wrong for
every company on the system.

**Where two disclosures exist they can disagree, and the tagged one is the wrong one.** This is the
finding that matters most for anyone repeating the work, and it is set out in section 3.

---

## 2 · What the measure is

The statute is section 4501 of the Internal Revenue Code, enacted by the Inflation Reduction Act of
2022. One percent of the fair market value of stock repurchased during the taxable year, **reduced by
the fair market value of stock issued during the same year** — the netting rule — on repurchases made
after 2022-12-31.

Three consequences follow, and each one breaks a naive implementation.

**The netting rule is not small.** On O'Reilly Automotive, where both the gross and the net figures
are filed, netting removes between eight and eighteen percent of the gross tax in each of the three
years. On Apple it removes about fifteen percent, because Apple issues roughly thirteen billion
dollars of stock to employees a year against which the repurchases net.

**A fiscal year straddling 2022-12-31 is only partly exposed.** The statute reaches repurchases made
after that date, not fiscal years beginning after it. Apple's fiscal 2023 ran from October 2022 to
September 2023 and is therefore three quarters exposed, not fully. Charging a full year of tax to it
would overstate the tax by a third of that year's charge. The template prorates by months, which is
an approximation, because the filings do not disclose within-year repurchase timing; the
approximation is announced wherever it is used.

**It is accrued in one year and paid in the next.** O'Reilly accrued $28.830 million in 2023 and paid
none of it; paid $28.830 million in 2024 against a 2024 accrual of $17.011 million; and paid $17.012
million in 2025. A sources-and-uses statement is a cash account, so the accrual year and the payment
year are not the same year and must not be quietly merged.

---

## 3 · The O'Reilly finding: the same filing carries two different numbers for the same tax

O'Reilly Automotive's fiscal 2025 annual report says, in the note on the share repurchase program,
that the excise "assessed at one percent of the fair market value of **net** shares repurchased, was
$21.0 million for the year ended December 31, 2025." The statement of stockholders' equity in the same
document charges **$18.720 million**. The two cannot both be right.

The note's figure is one percent of **gross** repurchases to the rounding it presents: one percent of
$2,096.962 million is $20.970 million, which prints as $21.0 million. That is precisely what its own
sentence says it is not. The equity statement's figure is one percent of gross less the netting rule,
which is what the sentence describes. The same pattern holds in fiscal 2024: the note's $20.8 million
is one percent of gross to the presented rounding, and the equity statement charges $17.011 million.

The note's figure is the one carried in `ShareRepurchaseProgramExciseTax`, the single element the
taxonomy provides. **A study that read the obvious tag and believed it would have published a number
twelve percent too high in 2025 and twenty-two percent too high in 2024.** The equity statement is the
charge that reached the accounts, so the template treats it as authoritative and reports a
disagreement rather than resolving one silently.

This is the eighth instance on this project of a number that is internally consistent and externally
wrong. It would have passed every identity check in the study, because it is not inconsistent with
anything — it is simply a different quantity wearing the right label.

---

## 4 · What the template does, and the gate that had to be argued

The rule as written in the work order was to fail loudly on a post-2023 year where the tax cannot be
found rather than treat it as zero. Read literally that refuses the Apple study for fiscal 2023, 2024
and 2025 and takes the only completed document in the series offline over a number Apple chose not to
publish. James ruled on 2026-08-13 that the refusal stays as the default and the study may opt out of
it explicitly.

So `excise_tax()` raises `ExciseTaxUndisclosed` on any exposed year with no filed figure. That is the
default and nothing overrides it implicitly. A driver that has checked the absence, and found the
absence to be itself the finding, sets `allow_statutory_estimate=True`; only then does a number
appear, and everything it produces is labelled in the document as the study's own arithmetic rather
than the company's disclosure.

**The reconstruction is published as a band and both ends are printed.** The upper end is one percent
of gross repurchases and is a true upper bound, because the netting rule can only reduce the base and
stock issued is never negative. The lower end applies the netting rule, valuing shares issued at the
fiscal year's mean price. The gross end is computed twice, from the cash-flow repurchase line and from
the equity-statement repurchase line, which are independently filed and which the study already
reconciles elsewhere.

**The lower end is an estimate and not a bound, and the proving fixture is what establishes that.** On
O'Reilly the netted end lands 0.25 percent *above* the filed charge in 2023 and 0.38 and 0.25 percent
*below* it in 2024 and 2025. It misses in both directions, because the netting term values a year's
issued shares at that year's mean price and the shares were not issued at the mean. The measure is
therefore never described as bracketing the truth, and `excise_test_ORLY.py` asserts the two-sided
miss explicitly so that a future change which made the lower end look like a bound would fail the
build.

None of it enters the reconciled sources-and-uses account. That account closes on filed facts against
Apple's own equity roll-forward to a checkable residual, and folding an estimate into it would destroy
the check that makes it worth printing. The excise appears as a memorandum line, set apart and
labelled.

---

## 5 · The numbers

**O'Reilly Automotive, the proving fixture.** Filed charges against equity of $28.830 million,
$17.011 million and $18.720 million for 2023, 2024 and 2025. The study's reconstruction reproduces
them to within four tenths of one percent in each year and six hundredths of one percent in total —
$64.522 million against $64.561 million.

**Apple.** Nothing disclosed in any year. The reconstruction gives **$2.08 billion** netted across
fiscal 2023, 2024 and 2025, against a gross upper bound of $2.44 billion. That is 0.79 percent of what
Apple spent on repurchases in those three years and 0.25 percent of the thirteen-year program. It is
real money and it changes no conclusion in the study.

**Everyone else.** Costco, Home Depot, Boeing and American Airlines disclose nothing, and none of them
is a full study. Home Depot paused repurchases in March 2024 and American Airlines was contractually
barred from repurchasing in the relevant years, so exposure is small or nil in both.

---

## 6 · The argument for repurchases, stated and deliberately not quantified

A shareholder who receives a dividend pays tax on it in the year it arrives. A shareholder of a
company that repurchases instead receives nothing, owns a marginally larger share of the same
business, and pays nothing until the shares are sold, and then only on the gain net of what the shares
cost.

It is worth being accurate about where the advantage lies, because the loose version of this argument
overstates it. For a qualified dividend the tax rate is the same either way, so this is not a rate
advantage. It is the deferral itself, the recovery of basis, and the real possibility that the tax is
never paid at all, because the shares are given to charity or held until death. That is a transfer of
value to the continuing holder, it comes at the expense of the public purse rather than of the
company, and it attaches to every dollar of repurchase.

It is not quantified, and the reason is that its size depends on facts about the holder that neither
Apple nor this study knows: the rate that would have applied to the dividend, the holding period, the
cost basis, and whether the account is taxable at all. A pension fund, an individual retirement
account and many foreign holders capture none of it; a taxable individual who never sells captures a
great deal. Any single number would be a number about an assumed shareholder rather than about the
company.

**What it does not do is disturb the study's finding, and the reason is worth stating because it is
the whole point.** The deferral is worth the same proportion of every dollar whether that dollar buys
a share at eleven times earnings or at thirty-five. So it makes repurchasing a better way to return
cash than paying a dividend, without making an expensive repurchase any better than a cheap one. The
excise tax runs the other way and is far smaller. Neither changes which half of Apple's program was
the good half.

---

## 7 · What landed

- `buyback_study_TEMPLATE.py`: `EXCISE_RATE`, `EXCISE_EFFECTIVE_AFTER`, `ExciseTaxUndisclosed`,
  `excise_exposure()` and `excise_tax()`. The `excise_tax` key is added to `TAGS` with a comment
  recording that the element it names is not to be trusted over the equity statement.
- `code/excise_test_ORLY.py`, new: 37 checks, offline against committed fixtures
  `code/orly_sec_raw.json` and `code/orly_monthly.csv`. Prints `ALL 37 EXCISE CHECKS PASS`.
- `.github/workflows/verify.yml`: a fourth gate, which fails the build if that line is absent.
- `code/verify.py`: eight new checks and twelve new text assertions, rebuilding the exposure
  proration and both ends of the band from the primary-source dictionaries without reference to the
  template. Now prints `ALL 237 CHECKS PASS`.
- `code/gen_article.py`: the memorandum line in Exhibit 8, two paragraphs in section 9, and two
  paragraphs in section 12. It asserts at build time that Apple still discloses nothing, so that if
  Apple ever starts disclosing, the build fails rather than continuing to publish an estimate
  alongside a filed fact.

**Correcting the generalization addendum in writing, as this project's convention requires.** Section
5 of `00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md` says the excise "is generally accrued and
settled separately, so it does not sit inside `PaymentsForRepurchaseOfCommonStock`." That is true of
O'Reilly, which is now checked rather than assumed, but it is not safe as a general claim: Home
Depot's own accounting policy puts the excise inside the treasury cost basis, and Netflix files an
element named `PaymentsForRepurchaseOfCommonStockNetOfExciseTax`, whose existence implies the
question is live for that company. Any new company study must settle this from the filing before
adding an excise figure to anything, because adding it to a repurchase line that already contains it
would double count.
