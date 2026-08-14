# Start here

Pull this repo from GitHub before doing anything else — `git pull origin main` — even if a
local checkout already exists. The working copy on James's machine is not kept in sync and can
be running code from before today's fixes.

To run a study: `cd code && python3 run_study.py --ticker TICKER --cik CIK --fy-end-month M
--first-year Y1 --last-year Y2 --coe RATE --fetch`. Get the CIK from
`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=TICKER&type=10-K` if it
isn't already known. `--coe` needs an actual real cost-of-equity estimate, or an explicit
placeholder said out loud as one — the template refuses to default it. This prints the full
analysis, the same shape as `Buyback-Study-AAPL.html` — the raw output, not an article; James
picks what goes into Seeking Alpha from there.

If the run ends with a "STUDY REFUSED" banner, an audit point failed — stop, report exactly
which one and why, and do not publish or write anything up from that run until James says how
to proceed.
