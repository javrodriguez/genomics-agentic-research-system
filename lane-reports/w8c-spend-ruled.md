status: built, awaiting review
head: see RESUME HERE. Base 98424794, branch gap4/w8c-spend-ruled, worktree /Users/javrodher/aegis-builds/gap4-w8c.

# Lane w8c-spend-ruled: Gap Study round 4, Javier's spend-marker ruling

_Written Mon 12 Oct 2026 08:59 EDT (`date`) by the lane's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b to implement Javier's own decision, ruling W8C-gap4-1._
_Spec: Javier typed "spend markers: 1A 2A 3A" (Mon 12 Oct 2026 08:52 EDT, glitch-1b's window) on plans/gap-study-round-4/spend-markers-proposal-2026-10-11.md; section 5 of that proposal and the "Javier's decision: spend markers 1A 2A 3A" block of next-slices-2026-10-11.md._

No model was run; no API, vendor, network, Docker or credential was used; no `.env`, brief, saved output, sealed grader part or holdout was read.
Nothing was pushed.

## What changed

- **routing.json.** `spend_cap_markers_status` is now the proposal's section-5 line, `<date>` = 2026-10-12, naming Javier's words:
  `RULED 2026-10-12 by Javier ("spend markers: 1A 2A 3A", typed Mon 12 Oct 2026 08:52 EDT in glitch-1b's window, on plans/gap-study-round-4/spend-markers-proposal-2026-10-11.md): claude-code's spend-cap list is empty on purpose; arm A runs on his subscription login (D4 A), which bills no money per call, and a usage or weekly limit pauses under rate_limit_markers. The OpenAI and Google entries are added with their adapters, each with a non-empty list (OpenAI: project_spend_limit_exceeded, organization_spend_limit_exceeded, credit_balance_exhausted, insufficient_quota; Google: status 402 and its spend-cap error read at a walk), and this status is ruled again then.`
  claude-code's list stays empty (1A).
  No OpenAI or Google entry was added.
  `pin_profiles_status` and every other PENDING value are byte-unchanged (a scripted check refused any other key change).
- **2A** is Javier's own hands (prepay, auto-reload off); he answered "prepaid" at 08:53:38 EDT. No code; the amounts are not verified here.
- **3A needs no code.** The month-turn hold is already as decided: `costs.month_turn_allowed` refuses arms O and G from 23:30 UTC Sat 31 Oct until his "caps trimmed", and w7c's `Batch._money_gate` calls it (and `costs.walk_gate`) before each paid block; October spend is not blocked. Neither file was touched.
- **prereg-draft.json** regenerated through `build_draft.py`'s writer: `routing_markers` carries the RULED status, so that path leaves the pending inputs (79 to 78); the freeze stays closed.

## Tests (red first by assertion, then green; Python 3.13, each behind `mac_slot.py light-ok` and `timeout -s INT 120`)

- Red on the PENDING table (tests written first): test_routing exit 1 (276 ran, 1 failure: the status is not the RULED line); test_spend_wiring exit 1 (25 ran, 4 failures, 0 errors: P3-ruled, R1-nonempty's "not ruled" guard, and the two witnesses whose bound check was not green on the tree).
- test_routing: `test_claude_code_spend_list_is_empty_and_pending` became `..._and_ruled`; it holds the status equal to the RULED line (`SPEND_STATUS_RULED`), starting "RULED 2026-10-12 by Javier", naming "spend markers: 1A 2A 3A", no PENDING, claude-code's list empty, no other spend-cap harness.
- test_spend_wiring: R1-nonempty also proves, on routing.json as ruled, that a codex or gemini entry with an empty spend-cap list is refused (and with one marker is sound); P3-pending became P3-ruled: the status is Javier's, `pin_profiles_status` stays PENDING, `start_problems` and `batch.py --check` give exactly the two pin-profile lines with exit 1, `Batch` refuses with them, and the same table with the base's PENDING spend status still gives the base's three lines.
- test_batch: `spend_gate_problems` read the real table's status as PENDING (it failed after the ruling); it now holds the real table ruled (no spend line) and, set back to PENDING, refused naming it; the ignore-the-spend-cap mutant fails that line too.
- Green: test_routing 0 (276), test_spend_wiring 0 (25), test_batch 0 (118), test_build_draft 0 (45, run after the code commit, since test_committed_writer reads HEAD).
- Script checks: `routing.py --check` 0 (22 rows, 3 annotations, sound); `batch.py --check` 1 with two lines (`pin_profiles is empty ...`, `pin_profiles_status is not ruled ...`); `build_draft.py --check` 0; `copy_manifest.py --check` 0 (275 files, 43 fragments); `freeze.py --check` 0 (275 owned paths); the new checks.d line 0.

## Witnesses (rule B; no new guard code, so no new witness)

All 14 of test_spend_wiring's witnesses red by their own check, 0 collateral, 0 errors; `spend-status-ungated` now binds P3-ruled (2 own), `empty-paid-list-admitted` R1-nonempty (11 own, up from 9 with the two after-the-ruling lines).

## Ownership (ruling W8C-gap4-1)

routing.json and tests/test_routing.py move from w1b-cp1-routing-batch to COPIED.d/w8c-spend-ruled.json; w1b's own fragment entry names the transfer.
Edits without transfer, recorded in their owners' entries: tests/test_batch.py (w1b), tests/test_spend_wiring.py (w7c), prereg-draft.json (w7a).
New: COPIED.d/w8c-spend-ruled.json, checks.d/w8c-spend-ruled.txt.

## Left as found, for the reviewer

- claude-code's `spend_cap_markers.claude-code.source` still opens "Open, and empty by glitch-f3's ruling 4 ... with a PENDING status"; the brief said to replace the status only, so the ruling lives in the status. A one-line source note is a candidate fold.
- The comments in checks.d/w7c-spend-wiring.txt and w1b-cp1-routing-batch.txt say their batch line "goes red on purpose" when a status is ruled; their grep only forbids other lines, so they stay green. Not edited (not this lane's files); the exact two-line check is in checks.d/w8c-spend-ruled.txt.
