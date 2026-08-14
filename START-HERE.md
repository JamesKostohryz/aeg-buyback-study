# Start here

This is what "do a full share repurchase analysis on TICKER" means by default in this repo. A
short prompt (ticker, fiscal-year window, real cost of equity, "pull latest first") is meant to
be enough — everything below is what a fresh chat should already do without being told again.

## 1. Pull first

`git pull origin main` before doing anything else, even if a local checkout already exists.
James's local checkout is not kept in sync and can be running code from before the latest
fixes.

## 2. Run the driver

`cd code && python3 run_study.py --ticker TICKER --cik CIK --fy-end-month M --first-year Y1
--last-year Y2 --coe RATE --fetch`. Get the CIK from
`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=TICKER&type=10-K` if it
isn't already known. `--coe` needs an actual real cost-of-equity estimate, or an explicit
placeholder said out loud as one — the template refuses to default it.

## 3. The audit-points sweep is not optional

`run_study.py` already runs all fifteen permanent audit points (`code/audit_points.py`) and
prints the result of every one. Read that block. If the run ends with a "STUDY REFUSED"
banner, an audit point failed — stop, report exactly which one and why, and do not write up or
publish anything from that run until James says how to proceed. This is the default behavior
for every study, not a special instruction that has to be asked for.

Company-specific quirks (a share class the SEC interface can't reach, a fiscal year end that
moved, a spinoff masquerading as a split) do not need to be anticipated in a prompt — they are
already documented as comments in `buyback_study_TEMPLATE.py` and `code/run_study.py` near the
code that handles them, and the template's own notes will name the problem when it is hit.

## 4. The deliverable is the full write-up, by default

Console output from step 2 is every computed, audited number and note — it is not finished
prose, and it is not the deliverable on its own. `Buyback-Study-AAPL.html` is the standard: a
full, long-form narrative analysis, the same length and rigor as the Apple piece, built by
actually writing it up (load the `rva-style-guide` and `james-kostohryz-style` skills first),
not by forwarding the console dump. Hand James the whole thing as one HTML file; he picks what
goes into a Seeking Alpha piece from there himself. Producing only the raw numbers, or only a
short summary, is a smaller deliverable than what "a full analysis" means here and should be
treated as a shortfall unless James asked for something narrower.
