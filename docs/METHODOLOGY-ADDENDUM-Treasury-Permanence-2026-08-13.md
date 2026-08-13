# Methodology addendum: treasury permanence

**2026-08-13. Implements item 4 of `00-METHODOLOGY-ADDENDUM-Generalization-2026-08-12.md`.
Companion to `METHODOLOGY-ADDENDUM-Round-Trip-2026-08-13.md`, built the same day. Nothing else
from the work order is touched.**

## 1. The defect, and it was already in print

Section 7 of the Apple study divides repurchase cash by the reduction in shares outstanding and
calls the result the cost of removing a share **permanently**. For a company that cancels the
shares it buys, as Apple does, that is exactly right. For a company that parks them in treasury,
the shares still exist, can be reissued at the board's discretion tomorrow, and the reduction in
the float is a decision rather than a fact.

The work order rated this as a risk to future companies. It was not. **The published Apple
document was already using the word on a company that has never cancelled a share.** Its
contrast case — the company section 7 leans on hardest, under the heading "the same measure on a
company where it bites" — is Salesforce, and the closing line read: *at its worst Salesforce paid
2.4 times the highest price its own stock traded that year to remove one share permanently.*

Salesforce's balance sheet at 31 January 2026 shows one thousand and seventy-three million shares
issued against nine hundred and twenty-nine million outstanding. One hundred and forty-four
million shares sit in treasury at a cost of thirty-two billion two hundred and twenty-eight
million dollars, up from nineteen billion five hundred and seven million a year earlier, and the
accounting policy note states that the company carries treasury stock at cost. The balance is
growing, not shrinking. Nothing has been cancelled. The removal the study called permanent is
reversible at a board meeting.

The arithmetic was never wrong. The word was.

## 2. What changed

The template now reads which kind of company it is looking at out of the filings, and the word
follows the reading rather than the assumption.

| Basis | What the filings show | The label on measures B, C and D |
|---|---|---|
| Cancels | a retirement is tagged and no treasury balance exists in any year | cost per share **permanently removed** |
| Treasury | a treasury balance is tagged, or shares issued exceed shares outstanding | cost per share **withdrawn from the float** |
| Undetermined | neither is tagged anywhere | cost per share **removed from the count**, with no claim either way |

Measure A is unaffected under every regime. It is the price actually transacted, and a price
needs no qualifier.

Three rules govern the reading. Evidence must be positive: silence in the filings is never taken
as evidence of cancellation, which is why the undetermined case exists rather than a default.
A treasury *balance* outranks a treasury *flow*, because a company can acquire into treasury and
cancel later, and a company that does both is labelled by whatever balance remains, since that
is the part that has not been cancelled. And where a treasury balance is tagged, the reissuable
overhang is disclosed beside the cost per share rather than left for the reader to find.

## 3. Home Depot, where the disclosure earns its place

Home Depot is the treasury case already in continuous integration. It is detected correctly from
three tags, and the overhang it discloses is not a footnote.

Home Depot holds **eight hundred and six million shares** in treasury at a cost of ninety-five
billion nine hundred and seventy-one million dollars. It retired six hundred and eighty million
shares across the fifteen years of the study window. **The reissuable overhang is one point one
eight times everything the company withdrew from the float in the entire period covered.** A
reader told that Home Depot paid one hundred and forty-seven dollars eighty-five to remove a
share permanently would have been told something false about a share count that could be restored
in full, and then some, without the company issuing a single new share.

Detecting it required one thing the template already knew how to do and had not been asked to.
Home Depot renamed its treasury balance tag from `TreasuryStockShares` to
`TreasuryStockCommonShares` in 2024. A single-tag read stops in fiscal 2023 and reports no
current overhang at all. Both names are carried and merged, which is the ordered-alternates
mechanism defect 3 built, applied to a new quantity.

## 4. What did not move, and how that is known

Apple cancels its shares. It tags a retirement and carries no treasury stock at any date in the
study, so its label is unchanged and every figure in section 7 stands exactly as published: the
gross price of sixty-two dollars twelve, and the three net readings of seventy dollars
eighty-three, seventy dollars twenty-nine and seventy-four dollars twenty-six.

That is not asserted, it is demonstrated. The published document was regenerated and every number
in it extracted and compared against the version in the repository. **One thousand two hundred
and thirty-eight numeric tokens, and not one of them changed.** The eight additions are the
Salesforce treasury facts newly disclosed in section 7, and the single deletion is a full stop
that became a comma. Beyond that, four checks in `verify.py` now compare the template's four
measures against that file's own independent rebuild of them, and the generator asserts at build
time that Apple still reads as a cancelling company — if that ever stops being true the build
fails rather than publishing the wrong word.

## 5. A duplication removed along the way

The four measures used to be computed inside `gen_article.py` for Apple and would have had to be
computed again inside the template for every other company. That is two definitions of one
quantity, which is the failure mode this repository has been bitten by repeatedly. They are now
computed once, in `net_retirement_cost()` on the template, and the Apple build chain consumes it.
The Apple document regenerates byte for byte identically through the rewire, which is the
strongest available evidence that the two definitions really were the same before they were
merged into one.

## 6. Boeing is unblocked, and a correction to what was said this morning

The round-trip addendum published earlier today said Boeing should wait for this item. That
stands, and Boeing is now ready. But it also implied Boeing's treasury share balance was missing
for fiscal 2023 to 2025, and **that was wrong.** Boeing made the same tag rename Home Depot made;
the balance is filed in every year of the window under one name or the other, and the merge
handles it. Boeing's shares issued are constant at one thousand and twelve point three million,
its treasury balance runs unbroken from 2012 to 2025, and its acquisition and reissuance flows are
both tagged in every year. The data was never the obstacle.

The real obstacle was conceptual, and this item removes it. On a company that cancels, a
repurchase and a later equity raise are two different transactions in the same security. On a
company that holds, they are the same shares: Boeing put one hundred and forty point one million
treasury shares back out in fiscal 2024 to settle a raise, out of a balance it had accumulated by
buying at an average of one hundred sixty-eight dollars. Until the template could tell the two
regimes apart, it could not know which pool a reissuance should be matched against.

One consequence is worth recording because it strengthens the round trip rather than
complicating it. On a treasury company, average-cost matching is not a convention chosen for
tidiness — **it is how treasury stock is actually carried**, at cost, under the company's own
accounting. The ordering effect that has to be published as a band on a cancelling company is,
on a treasury company, closer to a fact.

## 7. What this does not do

It does not change any ratio, and it is not a correction to any number.

It does not judge a company for holding shares in treasury. Treasury accounting is ordinary and
often driven by state law rather than intent, and a company that holds is not thereby shown to be
planning a reissuance.

It does not tell you how likely reissuance is. The overhang is disclosed as a quantity that could
be reissued, not as a forecast that it will be, and that judgment stays with a person.

And it says nothing about the treatment of treasury shares inside the Abnormal Earnings Growth
(AEG) account, which is untouched. Scope remains ex-post disclosure only. No valuation number
moves, no estimate of Intrinsic Value or Neutral Value is stated, and the pivot for a
repurchase's contribution remains Neutral Value.

## 8. Where it lives

`treasury_status()` and `net_retirement_cost()` on `BuybackStudy`, with the label tables
`PERMANENCE_LABEL` and `PERMANENCE_NOTE` beside them, all in `buyback_study_TEMPLATE.py` and
duplicated nowhere. Salesforce's treasury facts are in `code/source_data.py` with the filing they
came from. Exercised by sixteen new checks in `code/verify.py`, which now reports two hundred and
nineteen passing checks against two hundred and three this morning and one hundred and
eighty-four yesterday, and by seven new checks in `code/template_test_HD.py`. Both are gated in
continuous integration.
