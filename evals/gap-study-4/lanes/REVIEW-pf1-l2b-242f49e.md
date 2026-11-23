VERDICT: PASS

# Closure check of lane pf1-l2b-labelling-stats at 242f49e (after the CHANGES review at 9241942)

Fresh reviewer, closure pass, Sat 24 Oct 2026, 23:08 EDT (from `date`).
Read: `git diff 9241942..242f49ef` in full, the two capture commits (9f888052 and 65984366), and four athena records.
No code was run on the Mac. This pass is code reading and athena records only.
Every finding from 9241942 is closed or ruled.
The three MINORs below are a wording fix and two cheap tightenings, and none breaks a threat-model property.
They can fold here, or at L4 on the freeze line.

## The coordinator's checks

- **Can the flagged sheet be rendered before the blind labels are committed?**
  No, for a missing or uncommitted labels.json.
  `sheet.write_flagged` refuses while `blind_labels_problems()` is non-empty, which means no labels.json, more than one commit touching it, a shallow clone, or a disk copy that is not the one commit's (`agreement.history_problems`).
  FL2 and the lane's tests cover the refusal through `main` and through the default agreement module.
  The gate reads only the history, not whether the labels are complete (finding 2).
- **Does the flagged sheet ever unblind a blind item?**
  A take in both lists is shown with its arm, harness and model on the flagged sheet, so it unblinds that item by design.
  The order rule handles this, and it holds: the sheet opens only after labels.json is committed once, and `history_problems` then refuses any second version.
  So nothing seen on the flagged sheet can move a blind label.
  The blind sheet's own road (`write_sheet`, `blind_items`) is unchanged.
- **Is the beyond-cap count right, and the seeded cap draw?**
  Yes. `flagged_list` is unchanged since 9241942: the cap draw uses `random.Random(f"{seed}|flagged")` and never the blind generator, and `beyond_cap = flagged - listed`.
  FL1 covers caps 1, 3, n-1, n and n+5.
  RESULT.md prints flagged, listed and beyond-the-cap from `sample.derive`, and `test_result_counts_beyond_the_cap...` binds the numbers.
- **Does OFF stay byte-identical?**
  Yes. With `flagged_list` null the draw has no `flagged` key and the same items, and `render` adds no line (`*([...] if rec.get("flagged") is not None else [])`).
  `test_off_is_byte_identical` checks the sample, its rendered bytes and RESULT.md.
  `design_sha256` differs between OFF and ON, as it must, because the design differs.
- **Is the :621 qualification honest?**
  It is honest about the mechanism, but its wording overstates the cap (finding 1).
  The sha-bound R29 text stays verbatim, and `labelling_rules.qualifies` points at it and at the W-3b clause, which is now generated from the switch.
- **The probes capture approach:** sound.
  The same 21-line throwaway script sits on two capture branches (`capture/pf1-l2b-probes-base` on 96c1d959, `capture/pf1-l2b-probes-head3` on 242f49ef); the script's diff between them is empty, and neither branch is an ancestor of the lane.
  It exits 1 on purpose, so `run_checks` prints its lines into the athena log.
  The two logs match on every line: rc 0, 198 lines, full sha256 bd61eded…, rows sha256 59e12980…, tail sha256 a571b622…, and "169 rows, 1690 cells graded, 0 defects, 0 problems".
  It ran probes4 itself, not a golden, and only the VENDOR SHAPE lines were dropped. That closes finding 6's byte claim.

## Earlier findings, closure

| 9241942 | Closed by | Status |
|---|---|---|
| 1 flagged list had no road | `sheet.py --flagged`, the order gate, counts in RESULT.md | closed (see 2 below) |
| 2 "so it is seen" while off | `flagged_seen()`, `W3B_SEEN`, `labelling_rules.qualifies` | closed; wording overstates the cap (1 below) |
| 3 public page not read by lint_language | `lint_language --section-of docs/EVALS.md` in CI, bound in test_ci_job | closed |
| 4 readers rule unregistered | `frame.READERS_RULE` and `labelling_rules.readers` | closed |
| 5 record shape collides with L2a | merge step (coordinator) | open by design, at the merge |
| 6 red run, 169-row bytes | red 52ae6bb (0/3, real assertions), capture runs | closed |
| 7 vendor pins | not taken | accepted as a NIT |
| 8-11 nits | `grader_flag`, non-bool refusal, gone-file refusal, per-arm release, strict `read_deferred_arms`, committed and clean `committed_evidence`, docstring | closed |

The six new allowlist entries excuse only my quotations in the committed 9241942 review, each bound to its exact line. That is sound.
This file avoids those words, so it needs none.

## Findings

1. **MINOR: the registered "seen" sentences ignore the cap of 40.**
   `labelling_rules.flagged_seen` and every `routed_residuals[*].text` say "Every take its grader flags for the human sample goes to the flagged check list".
   With `{"cap": 40}`, takes beyond 40 are a seeded draw away from the list, and RESULT.md itself says they are "published and not read".
   The rule also covers the original part's cells only, since a deferred arm's list lives in sample-followup.json.
   Many takes are flagged on the right move (every explained or flagged trap, every count-check), so the cap will likely bind, and a routed residual's "only safeguard" is then a draw of 40.
   The R29 qualifier inherits the same overstatement.
   Fix: generate the sentence with the cap: "up to forty, a seeded draw when more are flagged, with the count beyond the cap published".

2. **MINOR: the order gate reads labels.json's history, not that it is complete.**
   `blind_labels_problems` opens the sheet once labels.json is committed once, even with sheet ids unlabelled (`agreement.validate_labels` is not called).
   Nothing silent follows, because the labels cannot be re-committed and the agreement check then fails.
   But the registered order ("no flagged item's arm, harness or model is seen before the blind label of the same take is written") holds only vacuously for the unlabelled takes.
   Fix: add `validate_labels` against the sample to the gate.

3. **MINOR: a missing frame raises an exception the callers do not catch.**
   With records committed and no frame.json, `result.flagged_counts` raises `SampleError` (`sample.py:368`), which subclasses `Exception`, not `ValueError`.
   `result.main` (`except ValueError`) and `check_results.main` (`except (ValueError, KeyError, OSError)`) both show it as a traceback.
   It fails closed, but the "No flagged list is drawn yet: there is no frame." branch is then reachable only with no takes.
   Fix: catch `SampleError` and print it as a FAIL line.

4. **NIT: `flagged_counts` reads the study's prereg.json through `sample.derive`, not the `pre` that `from_records` was given.**
   The two are the same file in production.

5. **NIT: a deferred arm's follow-up flagged list has no sheet and no count.**
   `sheet.py --flagged` reads `sample.json` only, and RESULT.md counts only the original part. Name this in the follow-up road before any G go.

6. **NIT: the two `capture/pf1-l2b-probes-*` branches should be deleted once this record stands**, so that no push carries them.

Stopped at nits.
