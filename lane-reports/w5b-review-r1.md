VERDICT: CHANGES

Review round 1 of w5b-cp5-pipeline at 0304c56d (base be1286f7). The reviewer was a fresh opus-medium agent, read-only. The clock read 15:57 EDT on Fri 9 Oct 2026 at the finish. glitch-f3 saved this text from the reviewer's final message, because the reviewer's own write of this file was refused.

Section 12 (git identity) is known and not re-reported.

**Counts:** 3 MAJOR, 4 MINOR, 1 NIT. 7 of the reviewer's 14 whole-file mutants stayed GREEN.

**Reproduced:**
- test_pipeline: 52 run, 0 failures. The report lists 52 mutants.
- Copy gate: 40 identical, 13 edited, 165 new.

## Findings

### W5B1-1 · MAJOR · check_results.py:93-139 (`pause_event`) and takes.py:137-142 (`registration_outcomes`)
- **Scenario:** a block holds 1 to 3 outcomes, so the committed history cannot show where one block ends and the next begins.
  - `pause_event` refuses almost every ruled pause as ambiguous. The lane's own test treats the core W1B4-3 case, [pause s1, failed s2] plus `route pause`, as ambiguous.
  - Probe P1: [graded s1, graded s2, failed s3 drive_started] plus `route pause` on s3, with no window event anywhere. `cr.publication` raises "the ruled pause's block cannot be derived uniquely from committed history", while `batch.history_problems` accepts it.
  - `guard_registration` goes through `publication` whenever any ruling exists, so it raises for every row, including a brand-new slot s4. One legal ruling stops the run, and publication can never succeed after it.
- **Fix:** when no admissible candidate block holds a window event, return the take's own event, and refuse only when the candidates would give different counts. Keep the registration guard on batch's strict own-event count, not on the PL-3 derivation.

### W5B1-2 · MAJOR · takes.py:104 (`commit_ruling`), RulingDoor tests
- **Scenario:** R24 says the door takes `by` from its caller and never defaults it. A mutant `by=by or "synthetic-person"` inside the door leaves the whole file GREEN (52 run, 0 failures). The lane's ruling-by mutant only patches `validate_ruling`.
- **Fix:** a scratch-repo test calling `commit_ruling` with by=None and by="" that asserts a refusal and no commit, plus a committed door-level mutant.

### W5B1-3 · MAJOR · costs.py:166-185 (`month_turn_allowed`)
- **Scenario:** R29's hold runs only from 23:30 UTC on the month's last day until a "caps trimmed" record exists. The predicate instead demands a trim record for the current month at every moment.
  - Probe P8, arm O with no record: refused at 12:00 UTC on 15 Oct and refused at 23:29 UTC on 31 Oct.
  - No test covers 23:29.
- **Fix:** refuse only from 23:30 on the last day until a next-month record exists; allow otherwise. Add the 23:29 and mid-month cases.

### W5B1-4 · MINOR · refusals with no test
- **Scenario:** each refusal below can be deleted and the whole file stays GREEN:
  - takes.py:202-207 `RegistrationGuard.check` mid-block ("finishing block");
  - takes.py:79 `read_history` "one commit introduces exactly one outcome or ruling";
  - takes.py:107 the door's clean-tree check;
  - takes.py:238 `load_rows` uncommitted-ledger refusal;
  - check_results.py:368 run outputs inside the freeze commit itself (claimed by the report, bound by no test);
  - costs.py:181 a future-dated trim record.
- **Fix:** one test and one committed mutant for each.

### W5B1-5 · MINOR · check_results.py:150-211 (`publication`)
- **Scenario:** `publication` never calls `batch.Batch.cell_history_problems` and never checks the fate fields. It accepts histories batch refuses:
  - a forged `cell_state` on a graded take below the cap is published as "incomplete — mechanical";
  - three rehearsals at the cap with no cell state are accepted, and the guard then allows attempt 4;
  - a graded outcome with `final=False` is silently dropped from the records.
- **Fix:** call `cell_history_problems` with the table, and refuse a non-final graded or aborted outcome.

### W5B1-6 · MINOR · check_results.py:39-56 (`validate_ledger`)
- **Scenario:** it refuses one half_cell id naming two identities, but not one identity carrying two ids. Probe P9 shows this splits batch's cap counting, and `completeness` (reading only the first id) published `no takes` for a half-cell closed under the second id.
- **Fix:** a one-to-one mapping in both directions.

### W5B1-7 · MINOR · freeze.py:371,381 and check_results.py:377-442
- **Scenario:** with `--rehearsal` in any clone without remotes, `--write` freezes with the placeholder "rehearsal or preview". `check_results` never re-checks `rehearsal_record` against the frozen file:
  - first line equals `draft_sha256_at_freeze`;
  - tree line equals `rehearsed_study_tree_sha256`;
  - last line "all green".
  It also accepts the placeholder.
- **Fix:** `check_frozen_content` re-checks all three and refuses the placeholder.

### W5B1-8 · NIT
- **Scenario:**
  - Several in-test mutants patch the very function they assert on, so they cannot fail; only the whole-file runs are red.
  - Registration and human-ruling commits made at runtime carry a Codex co-author trailer.
  - `admitted_rehearsal` and `rehearsal_problems` are dead code.
  - Arms "O" and "G" are typed in costs.py instead of read from study.
  - `wall_seconds` is the first-to-last span, not a per-call sum.
  - The report's line 1 still says `status: blocked`.
- **Fix:** optional.

## The 7 whole-file mutants that stayed GREEN (52 run, 0 failures each)
1. `commit_ruling` fills `by` with `by or "synthetic-person"`.
2. `runtime_timing_problems` with `commit != frozen` dropped (outputs in the freeze commit allowed).
3. `RegistrationGuard.check` with `elif self.live & done: raise` removed.
4. `read_history` with `len(added) != 1` changed to `< 1`.
5. `commit_ruling` without its clean-tree check.
6. `month_turn_allowed` without `utc(trimmed["at"]) > now`.
7. `load_rows` without its uncommitted-ledger check.

Probe scripts: review-r1/probes.py, probes2.py and mymutants.py.
