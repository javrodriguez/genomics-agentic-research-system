VERDICT: CHANGES

# Review of lane pf1-l2b-labelling-stats at 9241942 (base freeze/r4-20261021 = 96c1d959)

Fresh, independent review, Sat 24 Oct 2026, 17:42 EDT (from `date`).
Scope: pre-freeze review 1's MAJOR 6, MAJOR 10, m13, m14 and m16, against the approved fold plan.
Method: the diff `96c1d959..9241942` read in full, the athena records read, break attempts done by reading code and the lane's tests.
No code was run on the Mac: `mac_slot.py light-ok --tests --work gap-study-r4` refused twice (17:36 and 17:41, "CPU speed limit 68 is below 80").

No finding breaks a threat-model property.
The verdict is CHANGES because findings 3, 4 and 6 are cheap and within the lane's scope, and findings 1, 2 and 5 need an owner or a merge step named before the freeze line.

## Verified

- Record fields are appended only: `TAKE_FIELDS[:8]` is unchanged (`stats.py:136-137`), and `drive.LAUNCH_FIELDS` (`drive.py:4235`) and `takes.py:357` still read the first eight.
- No READER_SOURCES file changed: none of the nine names in `native_reader_registration.py:85-87` is in `git diff 96c1d959..HEAD --stat`.
- No grader file changed, and `run.dispatch` is a pure move of `regrade`'s body: I compared the old and new text line by line. `human_why` is never written into the grade, so no walk's `grade.json` can move.
- A flag on an ungraded record: `record_for` drops it (`run.py:223`), and `stats._check_human` refuses one (`stats.py:451`). H1 tests both.
- A human_why value outside the vocabulary is refused loudly (`stats.py:447`), and so is an unknown `human_check`, never dropped.
- FLAGGED_LIST ON with fewer takes than the cap, equal and more: FL1 covers caps 1, 3, n-1, n and n+5. The blind draw is the same either way, and `beyond_cap` is counted.
- A G record never reaches the original report: `stats.original_records` filters by arm, `from_records` refuses G records without a go and without published values, and G1 reproduces the reviewer's probe (values with G deferred are equal before and after G records exist; the full-family values differ).
- A values file edited in a second commit, even one later reverted, is refused (G2). `check_results.main` refuses a shallow clone, so the history read is not hollow.
- A stopped take with no end state, or one that cannot be read, counts as unread, never clean (`run.py:360-368`, S1).
- "outperforms" next to a family label is still a finding: the excuse holds only if the match lies inside the label's span (`inside_label`; L1 tests "| <label> | and the stronger model held |").
- The `assign-empty` EQUIVALENT is correct: that mutation sets the value to `ast.Constant(None)` (`tests/test_labelling.py:2344-2346`), which is the line as written. Any other value of the switch is killed by FL1's first check.
- The allowlist entry for `coverage_today.md:16` is sound: "the stronger guards" is about GARS guard reach, not about models, and the excuse binds the exact line text.
- Athena: red b1d6ab2 had 0 of 4 commands passing, green 675b1bf had 25 of 27, fix 9241942 had 4 of 4. The fix changed only `tests/test_probes4.py` and one EQUIVALENT line, so the other 23 greens carry over to 9241942.

## Findings

1. **MINOR: the flagged list has no road to the labeller once it is ON.**
   ON writes F-items into `sample.json` (`labelling/sample.py:197-214`).
   But `sheet.py` renders `doc["items"]` only (`sheet.py:238`), `agreement.py` ignores the list, and `sheet.py:39-41` says the labeller never opens `sample.json`.
   An F-item carries its take's stratum (arm, harness, model), and a take may sit in both lists, so seeing it unblinds the matching L-item.
   No rule says the blind sheet is labelled first.
   The "count beyond the cap" is published only in `sample.json`; RESULT.md prints nothing about it.
   Fix: before Q2's yes can take effect, add a non-blind check-list sheet and a rule that the blind sheet is labelled first, and print the flagged and beyond-cap counts in RESULT.md. The Q2 card should say this.

2. **MINOR: the draft still promises that flagged takes are seen while the switch is off.**
   The promise is at `build_draft.py:621` ("sends the take to the human sample, so it is seen") and `:986` ("a nonzero count sends a claude-code take to the human sample").
   With `flagged_list` null, a flagged take is seen only if the blind draw of about 80 happens to pick it.
   The new `routed_residuals` text is honest, but these two claims, the ones MAJOR 6 names, are unchanged, and no gate stops a freeze with them.
   Owner: Q2's answer (ON), or L4 rewords them. Track it on the freeze line.

3. **MINOR: the new comparative patterns never read the public page.**
   `docs/EVALS.md` is read by `lint_pooling --section-of` only (`ci.yml:486`), and `lint_language` has no `--section-of`.
   The port matches round 3 (`ci.yml:287`), but m14's words ("outperform", "stronger", "beats") are therefore checked in the study folder, RESULT.md and commit bodies, and not in the one public section.
   Fix: add a section-of scan for `lint_language` (or call its `scan_text` on the section), and bind it in `test_ci_job`.

4. **MINOR: the frame's `readers` rule shapes the oversampling but is registered nowhere.**
   `frame.py:23-26` sets "agree" for every take whose grader does not compare the access log with the tool-call reader, which is every take outside scope_read.
   `sample.py:11-12` says `readers` tells whether the two readers "saw the same actions", which is not measured for those takes.
   The rule sets the `disagree` factor (3), and it lives only in the frame's docstring.
   Fix: register it in `labelling_design` (or in its draft text), and reword `readers` as "disagree when scope_read's readers disagree, else not-compared-or-agree".

5. **MINOR: the record shape collides with L2a.**
   L2a (`pf1-l2a-20261024`, head e5f7ea44) also appends to `TAKE_FIELDS` (`"agent_events", "ruled"`) and also edits `record_for`, `validate_ledger`'s identity record and the test record helpers.
   The fold plan said to build MAJOR 6 with MAJOR 8 as one record shape.
   H1 asserts `TAKE_FIELDS[-2:] == ("human_sample", "human_why")`, and the COPIED reason says the fields come "after its twelve fields".
   At the L2a-then-L2b merge, the field order must be settled, both lanes' helpers must carry all four fields, and L2b's checks and the battery must be re-run on the merged head.

6. **MINOR: the red-first run and the 169-row claim are weaker than stated.**
   At b1d6ab2, `test_pf1_l2b.py` failed with an ImportError (`labelling.frame` missing), so none of H1-D1, including G1's 0.020 probe, was shown red on its own.
   D1 checks the counts (169 rows, 1690 cells) and `evaluate() == []`, not that the rows are the same bytes as at the base.
   I could not run probes4 at both commits (the Mac was held). My reading of the dispatch says the rows cannot move.
   Fix: one athena run of `probes4.py --check` at 96c1d959 and at 9241942, diffed with the VENDOR lines removed, recorded in the lane.

7. **NIT: the vendor labels are pinned from walks that are not graded.**
   The committed `grade.json` of w-o46 and w-g21 both say "not graded, because its native cross-check is pending".
   `vendor_rows` grades them through `grade_walk_folder`, which admits nothing, so the pinned labels "unrestated" and "held" are whatever today's graders say.
   The docstring says so, but the message "update VENDOR_SHAPES" invites following the pin. Say instead that a change is a reading change to raise.

8. **NIT: human_why can drop the grader's own reason.**
   The `<grader>-flag` id is added only when no other reason exists (`run.py:199-201`).
   So a template_adherence flag together with a nested CLI records only `nested-agent-cli`. The flag itself stands.

9. **NIT: a truthy non-bool flag is dropped silently.**
   `human_why` tests `human_sample is not True` (`run.py:184`), so a grade with `human_sample: 1` would be recorded as unflagged instead of refused.
   Every grader emits a bool today. Refusing a non-bool is cheap.

10. **NIT: edge cases in the original-values check and the follow-up.**
    `original_values_problems` returns `[]` when the file is absent, even after it was committed and then deleted. This fails closed, because the follow-up then refuses, but "published once" is not checked in that state.
    `from_records` compares `released` with `held`, which would refuse in error with two deferred arms of which one has records (only G exists today).
    `stats.read_deferred_arms` returns an empty set on an unreadable pre-registration, where `prereg.deferred_arms` raises; it is caught by the page compare.

11. **NIT: three small wording and binding gaps.**
    The design shape in `sample.py`'s docstring still lists five fields.
    The `routed_residuals` text could say plainly that with `flagged_list` null the take is seen only if the blind draw picks it.
    `committed_evidence` (m13) does not require the take folder to be committed and clean, as `grade_committed` does. The CI page compare catches a drift.

Stopped at nits.
