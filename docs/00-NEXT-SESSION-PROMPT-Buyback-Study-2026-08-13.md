# Next session prompt — AEG buyback study, written 2026-08-13 end of session

Paste everything below the line into a fresh chat.

---

Project: AEG Valuation System 2. Model: Opus. You are continuing the Apple share-repurchase
study. Five sessions ran before you. You are not blocked on any of them.

FIRST ACTION. Ask James to grant `C:\Users\james\AEG-Project` and read `00-START-HERE.md`. Then
clone `github.com/JamesKostohryz/aeg-buyback-study` — that repository, not project knowledge and
not the desktop working copy, is the source of truth for this workstream. If you cannot get the
desktop folder, say so plainly and work against the repository; several past sessions had no
desktop bridge and worked fine.

STATE OF THE WORLD, VERIFIED 2026-08-13. Buyback study repo tip is `9ec5338`, CI green, three
gates. The engine repo `aeg-valuation` moves several times a day via an automated pipeline —
CHECK `git log` rather than trusting any hash. The engine is DECLARED FINISHED; do not touch it,
do not investigate its refusals, do not clear a gate. PepsiCo carries the only real forecast
valuation and nothing in this workstream touches it.

WHAT LANDED 2026-08-13, THREE ITEMS OF THE GENERALIZATION ADDENDUM.

**Item 1, the entry effect (commit `d988d6b`, earlier session).** The proposed suppression rule
was built, measured, found to fire on six of Apple's thirteen years, and WITHDRAWN on James's
ruling that no year and no repurchase may be excluded. Replaced by an exact decomposition,
`entry[t] = decision[t] + timing[t]`. Read
`docs/METHODOLOGY-ADDENDUM-Earnings-Timing-Decomposition-2026-08-13.md` before touching the entry
effect. It also formally departs from the prior work order on which trend estimator is primary.

**Item 3, the round trip (commit `41dfc4b`).** Repurchase cash against equity raised, at the
prices at each end, with a cumulative real loss on the overlapping shares. Built into
`buyback_study_TEMPLATE.py`. Average cost primary, FIFO rebuilt independently, loss reconstructed
a third way; the ordering effect is published as a band, never suppressed. Proven on American
Airlines: $7.9bn real loss on 218.2mn shares, 32 cents back on the dollar, 68% of every share the
program retired. Carnival shows the pattern more dramatically and CANNOT be measured — it tags no
period-end share count in any year. Occidental raised then bought; wrong sequence, not a round
trip. Read `docs/METHODOLOGY-ADDENDUM-Round-Trip-2026-08-13.md`.

**Item 4, treasury permanence (commit `9ec5338`).** Section 7 called measure B the cost of
removing a share PERMANENTLY. That word is a claim about a company's accounting, and the template
now reads it from the filings: cancels → "permanently removed"; treasury balance → "withdrawn
from the float" with the reissuable overhang disclosed; neither tagged → UNDETERMINED, because
silence is not evidence of cancellation. The word was ALREADY WRONG IN PRINT — section 7's
contrast case is Salesforce, which cancels nothing and holds 144mn shares at $32.2bn. That prose
is corrected. Home Depot discloses an 806mn share overhang, 1.18x everything it ever withdrew.
Apple cancels, so all four of its measures stand unchanged — proven by extracting all 1,238
numeric tokens from the regenerated document and diffing. Read
`docs/METHODOLOGY-ADDENDUM-Treasury-Permanence-2026-08-13.md`.

YOUR JOB. Ask James which, and do not start until he answers. In recommended order:

1. **Item 5, the excise tax and the tax-deferral argument.** Opus work, and the only remaining
   item that changes a quantity rather than adding one. The one percent United States excise on
   net repurchases has been in force since 2023, is generally settled separately so it does NOT
   sit inside `PaymentsForRepurchaseOfCommonStock`, and is missing from the sources-and-uses
   table. Pull it per company from `ExciseTaxPayable` or the equivalent disclosure and FAIL LOUDLY
   on a post-2023 year where it cannot be found rather than treating it as zero — that judgment is
   why this is Opus work. The same item also requires the strongest honest argument FOR
   repurchases, the deferral of shareholder tax into a capital gain, stated plainly in the closing
   section and deliberately NOT quantified, because the size depends on the holder.
2. **Boeing's round trip.** Sonnet. Method is settled, item 4 unblocked it, the data is complete.
   Fixture-building plus netting employee-plan settlements out of the 140.1mn treasury shares
   Boeing reissued in fiscal 2024. Note the 2024 raise was partly convertible preferred; only the
   common component belongs in the measure.
3. **Regenerate the Costco document.** Sonnet. `docs/Costco-Buyback-Study-2026-08-12.docx` is now
   THREE addenda stale and is not script-generated.
4. **Pull the entry effect into the template.** It is still duplicated in `code/gen_article.py`
   (Apple) and `code/full_study_COST.py` (Costco). Item 4 removed the same duplication for the
   four net-cost measures and the Apple document regenerated byte-identically, so there is a
   worked pattern to copy.

STRUCTURAL FACTS YOU NEED BEFORE YOU START.

- `buyback_study_TEMPLATE.py` is the ONLY copy of the template. `buyback_study.py` at the root is
  now a re-export shim with no code in it — it used to be a hand-synced byte-identical copy.
  Never reintroduce that. Each file has exactly one location.
- `gen_article.py` now CONSUMES `net_retirement_cost()` from the template. It also asserts at
  build time that Apple still reads as a cancelling company.
- Three CI gates, all offline against committed fixtures: `code/verify.py` (219 checks, must
  print `ALL <n> CHECKS PASS.`), `code/template_test_HD.py` (11 defect + 7 item-4 checks, must
  print `ALL DEFECT-1-THROUGH-9 CHECKS PASS`), `code/roundtrip_test_AAL.py` (27 checks, must print
  `ALL ROUND-TRIP CHECKS PASS`).
- Only Apple is a full study. Costco runs on a placeholder 5.5% real cost of equity because no
  engine run exists for that ticker. Home Depot is a test fixture whose price validator fails two
  years. American Airlines is a proving fixture for ONE measure and is explicitly NOT a study —
  do not describe any of the three as a completed study.
- Deflator convention: calendar-year CPI-U (BLS series CUUR0000SA0), base 335.123, INHERITED from
  the Apple study's committed row rather than chosen. The Apple deflator is labelled by fiscal
  year but is in fact calendar-year — proven, the implied base is constant to three parts per
  million. There is no published October 2025 index; 2025 is an eleven-month average and says so.

DEFECTS 10 AND 11, LANDED TODAY, BECAUSE THEY WILL BITE AGAIN.
10. A retirement must never be derived for a year with no repurchase cash net of any employee
    withholding on the same line. American Airlines FY2021-22 tag $18m/$21m that is entirely
    withholding; the template would have published AAL repurchasing in years it was contractually
    barred from doing so.
11. The earliest-years issuance-rate fallback is contaminated by structural issuance — mergers,
    bankruptcy emergence, stock-funded acquisitions. AAL FY2014 printed 36.8% of opening shares.
    Rates above a stated 5% bound are refused, not used.

STANDING RULES. Every figure computed, never typed. `verify.py` must still print ALL CHECKS PASS
with your new checks added. Every central measure computed two independent ways, reconciling,
before you write a sentence about what it means — and if the second route shares intermediate
quantities with the first it is not a second route. Validate any implied price against
intra-period highs and lows, never period-end closes; that validator has now caught silent
failures on three companies. But know its limit: it CANNOT catch a contaminated numerator whose
error is small relative to the traded range, which is how the American Airlines convertible
nearly got through. A missing input is never silently zero; an estimated input is always
announced. READ YOUR OWN EDITS BACK from the rendered output before calling anything done. Do not
publish a number about the engine you have not traced to the engine at its current tip. Load the
`rva-style-guide` skill before writing a word of published copy.

OPERATIONAL. The GitHub token is at `C:\Users\james\Documents\GitHub\.claude-github-token`
(classic PAT, repo + workflow scope) and the EODHD token at
`C:\Users\james\AEG-Project\.eodhd-token`. Find them there rather than asking; never print or
commit either. The sandbox reaches `data.sec.gov`, `www.sec.gov`, `eodhd.com` and
`api.bls.gov` directly. You CANNOT `git clone` into a mounted host folder — the config lock fails
on permissions. Clone to `/tmp`, work there, and push from there.

TWO THINGS THAT KEEP BITING THIS ENGINE, AND SHOULD BE A STANDING SUSPICION.
1. A number silently wrong or silently inert while every gate reports success. Seven instances
   now; the newest is the American Airlines convertible equity component, which put an issue price
   16% too high in the direction that flattered the buyback and passed every check.
2. A single anchor year's rate driving a permanent line. It has twice determined the SIGN of the
   abnormal earnings stream.

HOW JAMES WORKS. He is a financial markets analyst, not a programmer. Plain language. Prose rather
than bullet lists in published copy, American spelling, acronyms written out. When he must act,
give the exact page, exactly what to click, and what success looks like. One clear question with a
recommendation, never a menu. Do everything you can yourself first and never stall silently.
Recommend which model to use. Tell him plainly when he, the consensus, or you are wrong — and
correct yourself in writing when you find you were, as the treasury addendum does about Boeing.

SETTLED. DO NOT REOPEN. The pivot for a repurchase's contribution to abnormal earnings growth is
Neutral Value, not Intrinsic Value. Scope is ex-post disclosure only; nothing here moves an engine
valuation number. The study states no estimate of Apple's Intrinsic Value. The net retirement cost
is not a price, does not enter the abnormal earnings growth account, and is not an expense.
Neutral Earnings Power is not substituted into the entry effect. No year and no repurchase is ever
excluded from the study. Do not build a bespoke re-levered cost of equity inside this study —
item 2 inherits the engine's V2 hook when it lands.
