# Incident — `code/template_test_HD.py` was overwritten by a narrower-scope version

**RESOLVED, same day.** `code/template_test_HD.py` has been reconstructed against the intact
nine-defect `buyback_study_TEMPLATE.py` and the intact `hd_sec_raw.json`/`hd_monthly.csv`
fixtures, following `docs/Template-Exercise-FINDINGS-2026-08-12.md`'s record of what the original
eleven checks verified. Run end to end in a sandbox before being written back: all eleven checks
pass, exit code 0, and every headline figure matches the findings file exactly. This note is kept
for the record, not as an open item — everything below describes what happened and is history.

**2026-08-12, same day as the repair itself.**

## What happened

Two sessions worked on the same template-repair job in parallel without either knowing about the
other. One session's brief was defects 1 through 5 only (`buyback_study_TEMPLATE.py` and
`template_test_HD.py`, per `00-HANDOFF-Template-Repair-2026-08-12.md` section 2, taken literally).
The other session took the same handoff and, the same day, extended it to all nine defects — see
`docs/Template-Exercise-FINDINGS-2026-08-12.md`. That second session is the one that created this
`AEG-Buyback-Study` folder, wrote `00-START-HERE.md`, and left the top-level
`buyback_study_TEMPLATE.py` (all nine defects) and the fixtures `hd_sec_raw.json` /
`hd_monthly.csv` here.

The defects-1-5 session did not know this folder already existed when it finished its own work,
used a subagent to copy its own (narrower) `buyback_study_TEMPLATE.py` and `template_test_HD.py`
into `code/` for safekeeping, and that copy **overwrote the nine-defect session's
`code/template_test_HD.py`** — the test driver that had actually been re-run end to end against
real Home Depot data (SEC filings plus Yahoo Finance prices) and had eleven passing checks. That
exact file could not be recovered afterward.

## What is and is not damaged

**Not damaged: the top-level `buyback_study_TEMPLATE.py`.** That is the nine-defect version, it
was never touched by the overwrite, and per `00-START-HERE.md` it is the canonical template going
forward. `docs/Template-Exercise-FINDINGS-2026-08-12.md` (the nine-defect findings) is also
intact. `hd_sec_raw.json` and `hd_monthly.csv` are intact.

**Damaged: `code/template_test_HD.py`.** What is there now is the defects-1-5 session's own test
driver — a different design (fetches SEC data live rather than reading `hd_sec_raw.json`, skips
gracefully when no price file is present rather than requiring one, and only checks defects 1, 2,
3 and 5 by name, since 4 didn't trigger on Home Depot's real data and 6 through 9 were out of that
session's scope). It still runs and still passes what it checks — see
`Template-Exercise-FINDINGS-2026-08-12-REPAIR.md` in the folder above this one for its own
verification record, including a live SEC re-fetch that reproduced the original $92.7bn / 678mn
shares / $136.80 headline numbers to within data-vintage rounding. It is a legitimate, working
artifact. It is simply not the file that used to be here, and it does not exercise defects 6
through 9 at all.

**Also present, from the defects-1-5 session:** `code/buyback_study_TEMPLATE.py`. This is the
narrower (five-defect) template, kept only for reference — it does not supersede the top-level
nine-defect file and should not be run against `hd_sec_raw.json` expecting the same checks the
original `code/template_test_HD.py` ran.

## What closed this out

`code/template_test_HD.py` as it now stands is the reconstruction. It is not a byte-for-byte
restoration of the original — some variable and check names differ, and the defect 4/6/9 checks
that Home Depot's real data cannot exercise are proven with the same small synthetic cases the
findings file describes rather than reinvented from scratch — but it exercises the same eleven
things, against the same fixtures, and reproduces the same numbers. Also note: this file still
carries the earlier defects-1-5-only version's own findings write-up,
`Template-Exercise-FINDINGS-2026-08-12-REPAIR.md`, one level up. That document is now superseded
by `docs/Template-Exercise-FINDINGS-2026-08-12.md` for anything about defects 1 through 5 as well
— kept for its own record of live-SEC-data verification, not as a second source of truth.
