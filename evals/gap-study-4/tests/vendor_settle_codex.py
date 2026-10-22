#!/usr/bin/env python3
"""Lane vendor-settle: the Codex rows' settlement cases (stage K made this module empty; stage C, the Codex builder, is
its only writer). tests/test_vendor_check.py imports it and merges its three tables with the other harness's module
(tests/vendor_settle_gemini.py); a key here must be a ("codex", <key>) of check_take.VENDOR_PENDING_ROWS, and no key may
appear in both modules.

  SAME_FIRES   ("codex", key) -> fire(fixture_path) -> list of problems: the row's site (or vendor_check) run on a
               planted copy of the row's RECORDED fixture (tests/vendor_plant.planted); VPSameFires requires a line
               carrying the row's reason, for every SAME row of the live map.
  CLEAN_CASES  ("codex", key) -> case() -> (got, want): the reader on the unmodified RECORDED copy against the
               independent value the case's own plain-json parser derives; VPSettleCases requires got == want.
  NC_CASES     ("codex", key) -> case() -> list of problems: a NOT COMPARABLE row's partial check on its non-hollow
               plant; VPSettleCases requires a non-empty list whose every line carries the row's reason.

RECORDED folders for this harness: tests/fixtures/recorded-codex-w-o46 (also w-o47, w-o7).
"""

SAME_FIRES: dict = {}
CLEAN_CASES: dict = {}
NC_CASES: dict = {}
