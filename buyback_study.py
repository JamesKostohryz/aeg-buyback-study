# -*- coding: utf-8 -*-
"""
buyback_study.py - import shim. THERE IS NO CODE IN THIS FILE.

`buyback_study_TEMPLATE.py`, in this same folder, is the template and its only
location. This file exists so that `import buyback_study` resolves for
`code/template_test_HD.py`, `code/run_COST.py`, `code/roundtrip_test_AAL.py`
and any future company driver.

CHANGED 2026-08-13, and the reason matters. Until today this file was a
BYTE-IDENTICAL COPY of the template, kept in step by hand, with a header
instructing the next session to "copy changes here after". That is the exact
shape of the duplicate-file problem this repository has already been bitten by
three times in one day, and holding two copies of an eight-hundred-line module
in sync by hand is a defect waiting for whichever session forgets. The copy is
replaced by this re-export so that the two names cannot diverge at all: there
is now one definition, in one file, reachable under both names.

If a driver needs something this shim does not expose, add it to the template
and it will appear here automatically. Do not add code below.
"""
from buyback_study_TEMPLATE import *          # noqa: F401,F403
from buyback_study_TEMPLATE import (           # noqa: F401  explicit, for readers
    SEC_CONCEPT, TAGS, ROUND_TRIP_RAISE_TAGS,
    CompanyConfig, EquityRaise, BuybackStudy,
    parse_concept, fetch_concept, merge_concept_series, fetch_concept_alternates,
    irr, solve,
)
