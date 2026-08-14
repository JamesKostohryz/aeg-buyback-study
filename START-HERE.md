# Start here

Pull this repo from GitHub before doing anything else — `git pull origin main` — even if a
local checkout already exists. The working copy on James's machine is not kept in sync and can
be running code from before today's fixes.

To run a study: `cd code && python3 run_study.py --ticker TICKER --cik CIK --fy-end-month M
--first-year Y1 --last-year Y2 --coe RATE --fetch`. Get the CIK from
`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=TICKER&type=10-K` if it
isn't already known. `--coe` needs an actual real cost-of-equity estimate, or an explicit
placeholder said out loud as one — the template refuses to default it.

This prints console output with every computed, audited number and note - it is NOT finished
prose. `Buyback-Study-AAPL.html` is the finished shape James wants for a new company too, but
getting there for Apple took a separate hand-written narrative pass (`code/build.py` /
`code/gen_article.py`) laid over the computed numbers - the generic driver does not produce
that automatically for a new ticker. Producing an AAPL-length full analysis for a new company
means running the driver for the numbers, then actually writing it up in that same long-form
style (load the `rva-style-guide` and `james-kostohryz-style` skills) before handing it to
James - not just forwarding the console dump.

If the run ends with a "STUDY REFUSED" banner, an audit point failed — stop, report exactly
which one and why, and do not publish or write anything up from that run until James says how
to proceed.
