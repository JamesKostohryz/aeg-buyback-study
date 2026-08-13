# Next session prompt — AEG buyback study, after item 5

Written 2026-08-13 at the close of the excise-tax session. Supersedes
`00-NEXT-SESSION-PROMPT-Buyback-Study-2026-08-13.md` on everything it repeats.
Paste the block below into a fresh chat.

---

Project: AEG Valuation System 2. Model: Sonnet for items 1 and 2 below; Opus only if you take item 3.
You are continuing the Apple share-repurchase study. Six sessions ran before you. You are not blocked
on any of them.

FIRST ACTION. Ask James to grant `C:\Users\james\AEG-Project` and read `00-START-HERE.md`. Then clone
`github.com/JamesKostohryz/aeg-buyback-study` — that repository, not project knowledge and not the
desktop working copy, is the source of truth for this workstream. You CANNOT `git clone` into a
mounted host folder; clone to `/tmp`, work there, push from there. If a stale clone from an earlier
session is sitting in `/tmp` it will be owned by another user and unwritable — clone to a new
directory name rather than fighting it. The sandbox can also be recycled mid-session, taking `/tmp`
with it; if a path vanishes, re-clone rather than assuming you imagined the work. If you cannot get
the desktop folder, say so plainly and work against the repository; several past sessions had no
desktop bridge and worked fine.

STATE OF THE WORLD, VERIFIED 2026-08-13. Buyback study repo tip is `2a264de`, CI green, FOUR gates.
The engine repo `aeg-valuation` moves several times a day via an automated pipeline — CHECK `git log`
rather than trusting any hash. The engine is DECLARED FINISHED; do not touch it, do not investigate
its refusals, do not clear a gate. PepsiCo carries the only real forecast valuation and nothing in
this workstream touches it.

THE GENERALIZATION ADDENDUM IS NOW COMPLETE. All four items landed on 2026-08-13. Read the addendum
for any item you are about to touch; do not work from this summary alone.

Item 1, the entry effect (`d988d6b`). Suppression rule built, measured, found to fire on six of
Apple's thirteen years, WITHDRAWN on James's ruling that no year and no repurchase may be excluded.
Replaced by an exact decomposition, `entry[t] = decision[t] + timing[t]`. Departs formally from the
prior work order on which trend estimator is primary.
`docs/METHODOLOGY-ADDENDUM-Earnings-Timing-Decomposition-2026-08-13.md`.

Item 3, the round trip (`41dfc4b`). Repurchase cash against equity raised, at the prices at each end,
cumulative real loss on the overlapping shares. Average cost primary, FIFO rebuilt independently, loss
reconstructed a third way; the ordering effect is published as a band, never suppressed. Proven on
American Airlines: $7.9bn real loss on 218.2mn shares, 32 cents back on the dollar, 68% of every share
the program retired. Carnival shows the pattern more dramatically and CANNOT be measured — it tags no
period-end share count in any year. Occidental raised then bought; wrong sequence.
`docs/METHODOLOGY-ADDENDUM-Round-Trip-2026-08-13.md`.

Item 4, treasury permanence (`9ec5338`). "Permanently removed" is now read from the filings: cancels →
"permanently removed"; treasury balance → "withdrawn from the float" with the reissuable overhang
disclosed; neither tagged → UNDETERMINED, because silence is not evidence of cancellation. Section 7's
contrast case, Salesforce, cancels nothing and holds 144mn shares at $32.2bn; that prose is corrected.
Home Depot discloses an 806mn share overhang, 1.18x everything it ever withdrew. Apple cancels, so its
four measures stand unchanged. `docs/METHODOLOGY-ADDENDUM-Treasury-Permanence-2026-08-13.md`.

Item 5, the excise tax and the tax-deferral argument (`2a264de`). Read
`docs/METHODOLOGY-ADDENDUM-Excise-Tax-2026-08-13.md` before touching anything tax-related. Three
premises of the work order did not survive the filings and are corrected there: there is no
`ExciseTaxPayable` (the only us-gaap element is `ShareRepurchaseProgramExciseTax`, and companies that
disclose mostly use their own extension elements — four different names on the four checked, none
reachable through the company-concept interface); NO company in this study discloses a figure in any
year, Apple included; and where two disclosures exist they can DISAGREE, with the tagged one wrong.
`excise_tax()` refuses by default (`ExciseTaxUndisclosed`) on any exposed year with no filed figure and
only produces a number when a driver opts in explicitly with `allow_statutory_estimate=True`. The
reconstruction publishes as a band — gross end a true upper bound, netted end an ESTIMATE that misses
in both directions and is never described as a bracket. Fiscal years straddling 2022-12-31 are
prorated by month; Apple's FY2023 is 75% exposed, not 100%. Apple: $2.08bn netted across FY2023-25,
$2.44bn gross bound, 0.79% of those years' repurchase cash and 0.25% of the thirteen-year program,
published as a MEMORANDUM line outside the reconciled sources-and-uses account. The tax-deferral
argument is in section 12, at full strength and deliberately unquantified.

YOUR JOB. Ask James which, and do not start until he answers. In recommended order:

1. Boeing's round trip. Sonnet. Method settled, item 4 unblocked it, data complete. Fixture-building
   plus netting employee-plan settlements out of the 140.1mn treasury shares Boeing reissued in fiscal
   2024. The 2024 raise was partly convertible preferred; only the common component belongs in the
   measure. Boeing discloses no excise tax and repurchased nothing in the exposed years, so item 5
   does not complicate it. Build the fixture the way `code/excise_test_ORLY.py` and
   `code/roundtrip_test_AAL.py` do: committed raw SEC JSON plus a monthly price CSV, offline, gated.

2. Regenerate the Costco document. Sonnet. `docs/Costco-Buyback-Study-2026-08-12.docx` is now FOUR
   addenda stale and is not script-generated. Costco discloses no excise tax in any year — verified
   2026-08-13 — so a regenerated document must either carry the announced reconstruction or say
   plainly that it carries none. Do not let it default to silence.

3. Pull the entry effect into the template. Sonnet, or Opus if you want the duplication argued rather
   than executed. Still duplicated in `code/gen_article.py` (Apple) and `code/full_study_COST.py`
   (Costco). Items 4 and 5 both removed duplication this way and the Apple document regenerated with
   zero existing numeric tokens changed, so there is a worked pattern to copy and a proof standard to
   meet.

STRUCTURAL FACTS YOU NEED BEFORE YOU START.
- `buyback_study_TEMPLATE.py` is the ONLY copy of the template. `buyback_study.py` at the root is a
  re-export shim with no code in it. Never reintroduce a hand-synced copy. One file, one location.
- `gen_article.py` CONSUMES `net_retirement_cost()` and `excise_tax()` from the template, and asserts
  at build time both that Apple still reads as a cancelling company and that Apple still discloses no
  excise tax. If Apple ever starts disclosing, the build FAILS rather than publishing an estimate
  beside a filed fact. That is deliberate.
- FOUR CI gates, all offline against committed fixtures, all run from `code/`:
  `verify.py` (237 checks, must print `ALL <n> CHECKS PASS.`), `template_test_HD.py` (11 defect + 7
  item-4 checks, must print `ALL DEFECT-1-THROUGH-9 CHECKS PASS`), `roundtrip_test_AAL.py` (27 checks,
  `ALL ROUND-TRIP CHECKS PASS`), `excise_test_ORLY.py` (37 checks, `ALL <n> EXCISE CHECKS PASS`).
- Only Apple is a full study. Costco runs on a placeholder 5.5% real cost of equity because no engine
  run exists for that ticker. Home Depot is a test fixture whose price validator fails two years.
  American Airlines proves ONE measure and O'Reilly Automotive proves ONE measure; NEITHER is a study
  and neither may be described as one.
- Deflator convention: calendar-year CPI-U (BLS series CUUR0000SA0), base 335.123, INHERITED from the
  Apple study's committed row rather than chosen. The Apple deflator is labelled by fiscal year but is
  in fact calendar-year — proven, implied base constant to three parts per million. There is no
  published October 2025 index; 2025 is an eleven-month average and says so.

DEFECTS 10, 11 AND 12, BECAUSE THEY WILL BITE AGAIN.
10. A retirement must never be derived for a year with no repurchase cash net of any employee
    withholding on the same line. American Airlines FY2021-22 tag $18m/$21m that is entirely
    withholding; the template would have published AAL repurchasing in years it was barred from it.
11. The earliest-years issuance-rate fallback is contaminated by structural issuance — mergers,
    bankruptcy emergence, stock-funded acquisitions. AAL FY2014 printed 36.8% of opening shares. Rates
    above a stated 5% bound are refused, not used.
12. NEW, 2026-08-13. The one standard XBRL element for the repurchase excise tax carries, at O'Reilly,
    a figure that contradicts the same filing's statement of stockholders' equity — the note reports
    one percent of GROSS while calling it net, 12% high in 2025 and 22% high in 2024. Where a face
    statement and a note disagree, the face statement is the charge that reached the accounts. Report
    the disagreement; never resolve one silently by preferring the tagged value.

STANDING RULES. Every figure computed, never typed. `verify.py` must still print ALL CHECKS PASS with
your new checks added. Every central measure computed two independent ways, reconciling, before you
write a sentence about what it means — and if the second route shares intermediate quantities with the
first it is not a second route. Where a second route genuinely does not exist, say so and publish a
band with both ends rather than manufacturing a fake one. Validate any implied price against
intra-period highs and lows, never period-end closes; that validator has caught silent failures on
three companies. But know its limit: it CANNOT catch a contaminated numerator whose error is small
relative to the traded range, which is how the American Airlines convertible nearly got through. A
missing input is never silently zero; an estimated input is always announced. READ YOUR OWN EDITS BACK
from the rendered output before calling anything done, and diff the numeric tokens of any regenerated
document against the prior version — items 4 and 5 both did, and both proved zero existing figures
moved. Do not publish a number about the engine you have not traced to the engine at its current tip.
Load the `rva-style-guide` skill before writing a word of published copy.

OPERATIONAL. The GitHub token is at `C:\Users\james\Documents\GitHub\.claude-github-token` (classic
PAT, repo + workflow scope) and the EODHD token at `C:\Users\james\AEG-Project\.eodhd-token`. Find them
there rather than asking; never print or commit either. Granting the GitHub folder is a SEPARATE
`request_cowork_directory` call from granting AEG-Project. The sandbox reaches `data.sec.gov`,
`www.sec.gov`, `efts.sec.gov` (full-text search, confirmed working and genuinely useful), `eodhd.com`
and `api.bls.gov` directly. `companyfacts` does NOT contain company extension elements — if a quantity
is filed under a company's own namespace you must read it out of the filing's inline XBRL, which is
the primary document itself.

TWO THINGS THAT KEEP BITING THIS ENGINE, AND SHOULD BE A STANDING SUSPICION.
1. A number silently wrong or silently inert while every gate reports success. EIGHT instances now;
   the newest is defect 12 above, a correctly-tagged element carrying the wrong quantity, which would
   have passed every identity check because it is not inconsistent with anything.
2. A single anchor year's rate driving a permanent line. It has twice determined the SIGN of the
   abnormal-earnings stream.

HOW JAMES WORKS. Financial markets analyst, not a programmer. Plain language. Prose rather than bullet
lists in published copy, American spelling, acronyms written out. When he must act, give the exact
page, exactly what to click, and what success looks like. ONE clear question with a recommendation,
never a menu. Do everything you can yourself first and never stall silently; treat "I didn't find it"
as "I haven't looked hard enough." Recommend which model to use, and flag a good handoff point before
a long chat degrades. Tell him plainly when he, the consensus, or you are wrong — and correct yourself
in writing when you find you were, as the treasury and excise addenda both do.

SETTLED. DO NOT REOPEN. The pivot for a repurchase's contribution to abnormal earnings growth is
Neutral Value, not Intrinsic Value. Scope is ex-post disclosure only; nothing here moves an engine
valuation number. The study states no estimate of Apple's Intrinsic Value. The net retirement cost is
not a price, does not enter the abnormal earnings growth account, and is not an expense. Neutral
Earnings Power is not substituted into the entry effect. No year and no repurchase is ever excluded
from the study. Do not build a bespoke re-levered cost of equity inside this study. The excise tax is a
memorandum line and does not enter the reconciled sources-and-uses account while it remains an
estimate. The tax-deferral argument stays unquantified.

ONE OPEN QUESTION THE NEXT COMPANY STUDY MUST SETTLE, NOT ASSUME. Section 5 of the generalization
addendum said the excise "does not sit inside `PaymentsForRepurchaseOfCommonStock`." That is now
checked and true of O'Reilly, but it is NOT safe as a general claim: Home Depot's own accounting policy
puts the excise inside the treasury cost basis, and Netflix files an element named
`PaymentsForRepurchaseOfCommonStockNetOfExciseTax`. Settle it from the filing for any new company
before adding an excise figure to anything, because adding it to a line that already contains it would
double count.
