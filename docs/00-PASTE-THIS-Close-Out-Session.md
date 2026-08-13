# Paste this into a fresh chat

Everything below the line. It is short on purpose; it points at the long prompt rather than repeating it.

---

Project: AEG Valuation System 2, buyback study. Model: Sonnet.

FIRST ACTION, before anything else. Ask James to grant `C:\Users\james\AEG-Project`, then clone
`github.com/JamesKostohryz/aeg-buyback-study` to `/tmp` (you cannot clone into a mounted folder) and
read `docs/00-NEXT-SESSION-PROMPT-Buyback-Study-2026-08-13b.md` in full. That is your real briefing:
state of the world, four completed addendum items, four CI gates, twelve defects, the standing rules,
and where the tokens live. Do not start work until you have read it. Repo tip was `04859d6` on
2026-08-13; check `git log`.

THIS IS THE CLOSE-OUT SESSION FOR THE TEMPLATE. James's ruling, 2026-08-13: the revision cycle stops
here. The goal is a template he can point at any ticker, not a template that is perfect. General
defects get fixed now; anything peculiar to one company gets handled when that company comes up, not
pre-emptively. Do not open new methodology questions. Do not propose a fifth addendum item. If you
find something that looks like a new general problem, say so in one paragraph and let James decide
whether it is in scope — do not just start building it.

DO THESE THREE THINGS, IN ORDER, AND THEN STOP.

1. Pull the entry effect into `buyback_study_TEMPLATE.py`. It is the last measure still duplicated
   per company, living in `code/gen_article.py` (Apple) and `code/full_study_COST.py` (Costco).
   Items 4 and 5 both removed exactly this kind of duplication and the Apple document regenerated
   with zero existing numeric tokens changed. Meet that standard: diff the numeric tokens of the
   regenerated Apple document against the prior version and show that none moved.

2. Build ONE generic driver — `code/run_study.py` — that takes a ticker plus a small per-company
   configuration block and produces a full study with no company-specific code in it. Today there is
   none: `gen_article.py` carries 93 Apple-specific references and `run_COST.py` is a Costco script,
   so "the template works on any company" is true of the measurements and false of everything around
   them. What legitimately stays per-company is the CompanyConfig (central index key, fiscal year
   end, splits, window), the price series, the deflator, the cost of equity, and any excise-tax
   figure read off a filing by hand. Everything else must come from the template.

3. Run that driver COLD on one company nobody in this project has touched, and publish what happened
   — which fallbacks fired, which guards refused, which years were suppressed and why. A refusal is
   a pass, not a failure; the point is to prove the guards speak up rather than to get a clean sheet.
   Pick the company yourself and say why.

Then write a short close-out note in `docs/`, update `docs/00-WHERE-THINGS-LIVE.md`, keep all four CI
gates green with your new checks added, commit and push. Do not start a fourth thing.

EXPLICITLY OUT OF SCOPE, AND RECLASSIFIED. Boeing's round trip and the Costco document regeneration
were on the old list. Neither is a template defect — Boeing is a second proving fixture for a measure
already proven on American Airlines, and Costco is a deliverable refresh. They are APPLICATIONS of a
finished template and James will ask for them when he wants them. Do not do them in this session even
if you finish early.
