status: handed back for review; athena owed
head: 2f512340 (code commit; this report's own commit follows it). Base ddebb57e (S5's folded head, on S1 4dd1e8e6, on 89b54db4), branch gap4/w6h-drive-lifecycle, worktree /Users/javrodher/aegis-builds/gap4-w6h.

# Lane w6h-drive-lifecycle: CP2 drive lifecycle, part 2

_Gap Study round 4, slice S6 of next-slices-2026-10-11. Written Sun 11 Oct 2026 18:30 EDT (`date`) by the slice's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b under Javier's standing delegation._

No image or container was built or run.
No model was run.
No network was used by any test.
No login, `.env`, sealed, holdout, brief, grader-source or saved-output path was read.
Nothing was pushed, merged or dispatched.

## Scope

The plan's UPDATE check_take.py task, and the fake-runtime half of tests/test_box_integration.py: launch, preflight through S1's entry point, the drive step wiring S5's commit_records into the real take path (scan, mask, route, commit: ruling S6-Q3), a refused commit restoring the ledger (ruling S6-Q2), and the finally-path cleanup on every refusal.
The real-Docker half of test_box_integration.py is not here (it needs athena's box).

## What changed

`drive.py` (moved w6e to w6h under ruling S6-gap4-1).
Part 2 is appended above `if __name__`, so no line other files cite moves, and w6e's checks.d prefix line still passes.
Its named changes R4-7 to R4-12 sit in its own banner.

- R4-7: `commit_records` now wraps the commit step (renamed `_commit_step`).
  On any refusal, outcomes.json goes back to HEAD's bytes (removed when HEAD has none), and every name the call staged is unstaged; then the refusal is raised as it was.
  The take's own masked files stay masked.
  Once the commit has landed, `on_published(row, attempt)` runs; its failure is recorded in `publish_problems`, never raised.
- R4-8: `TakeDriver(runtime, take_folder, config_parent, spec_for, sidecar_for, proxy, lock_path, hosts, adapter_for, script_for, pin_for, checker, secrets, rules_scanner, uid_map, budget_s, finalize_wait_s, poll_s, clock, sleep, ...)` is batch.Batch's driver: `launch`, `drive`, `remove`, plus the repo's `record_files` and `published` hooks.
  Nothing a walk or the box must tell is defaulted.
- R4-9: drive() begins the sidecar (the reply read by `sidecar.parse_completed`), then calls `preflight_take` with the Launched record launch returned, the sidecar's own launch record, the take's evidence folder and the parsed begin reply.
  It writes the record beside the evidence (`preflight.write`).
  A failed check, or a ValueError or RuntimeError inside begin or preflight, is a pre-turn refusal: it goes to refusal.json, no turn runs, and preflight_ok is False, so the take rehearses.
- R4-10: before drive() returns, every file in the take folder (a closed name-to-kind map; an unknown file refuses) is scanned by `scan_record.scan`, which masks on disk.
  The masked hits plus the checker's events become `events.outside_reach`.
  batch.py then routes and annotates, and the commit scans again and binds the bytes.
  A scan refusal raises, so the take is `failed`.
- R4-11, the turns: after each turn the driver polls the agent's processes up to `finalize_wait_s`.
  At the cap it kills them by an exec as the agent's uid, polls again to none, and only then signals `post-n` (and `pre-n+1` before the next turn).
  A timed-out turn is killed at once.
  The survivors are counted (`quiescence_cap_survivors`), and `quiescence_kill` is set only for a cap kill.
- R4-11, cleanup: in `finally`, on every road, the adapter is ended, the agent's leftovers are killed and polled, and `run_take.teardown` removes every container and the network by its recorded id.
  Problems go to teardown.json.
- R4-11, removal: `remove(id)` removes the take container by that id only while the full listing holds it, and raises LeakedContainer if it is still listed after.
  A failed launch whose partial teardown left the take container carries its id (`container_id`).
- R4-11, the config folder: it is deleted (`run_take.remove_config_dir`) only from `published`, after the commit; never after a refused one.
- R4-12: the restart listing stays per register (S6-Q4); nothing changed.
- The sidecar's `sidecar` record comes from health.jsonl after finish (`sidecar_health`): a missing file reads as no start and no stop, never healthy.

`check_take.py` (moved w1a to w6h under ruling S6-gap4-1).
Three lines changed in place, and a round-4 section is appended after `main()` (R4C-1 to R4C-5):
- 902: `want_mode = mode_for_arm(pre, ledger.get("arm"))`, read from `driver_constants.permission_mode_by_arm`; an unpinned arm equals no mode.
- 1567 and 1604: `check(..., *, wording_script=None)`; the wording's script replaces the half's when given.
- `check4(..., wording_script, arm, table=None)`, round 4's road:
  - it requires a wording script;
  - it lifts routing.json's `checker_reasons_become_events` (study-materials-reached, account-email, read-outside-the-checkout) out of the reasons;
  - it counts each instance with check()'s own readers;
  - it refuses a refusal with no id, or a checker and reader that disagree;
  - for takes, it adds `recorded_mode_problems`: the transcript's record-level permissionMode must be exactly the arm's pin.
- A checks.d line binds every other line of round 3's file, in order.

COPIED.d: `w6h-drive-lifecycle.json` (new) claims drive.py and check_take.py as edited, naming S6-gap4-1 (drive.py's w6e reason carried), plus the two tests, the fragment and the checks file.
w6e's and w1a's fragments drop the entries, and their self-entries record the transfer.
`copy_manifest.py --check`: ok, 225 files, 29 fragments.

## Guards, checks and witnesses (whole-file anchor edits compiled in memory, registry pattern)

| guard | bound check | witness | result |
|---|---|---|---|
| R4-7 rollback | B1-rollback: an unmaskable value refuses the commit; the ledger equals HEAD's bytes, nothing is staged, and the take then commits | omit-restore | red by B1-rollback (3 own, 0 collateral, 0 errors) |
| R4-9 preflight road | B2-preflight: one call before any turn, with the Launched record (spec on the real network), the sidecar record, the evidence folder, the lock, the harness and the parsed begin; the record written | skip-preflight | red by B2-preflight (1 own, 0, 0) |
| R4-9 pre-turn refusal | B3-preturn: a failed record or a typed refusal starts no adapter and routes rehearsal with preflight.ok False and 0 turns; refusal.json written | failed-preflight-read-as-passed | red by B3-preturn (2 own, 0, 0) |
| R4-10 scan before route | B4-scan: through batch.Batch, the stream is masked when routing.route runs; outside_reach = 1 masked + 2 checker events; mask and outside-reach event set; committed bytes masked | no-drive-scan | red by B4-scan (2 own, 0, 0) |
| R4-11 cleanup | B5-cleanup: six roads (passed, failed check, typed refusal, adapter raises, timed out, scan refuses) leave no container, network or agent process; every recorded id removed; kill as the agent's uid; teardown.json | no-finally-cleanup | red by B5-cleanup (18 own, 0, 0) |
| R4-11 quiescence | B6-quiesce: post-1 and post-2 signalled with 0 processes alive, labels post-1, pre-2, post-2, cap kill recorded (1 survivor), the cap waited out; a timeout killed at once with no wait | no-cap-kill | red by B6-quiesce (4 own, 0, 0) |
| R4-11 removal | B7-remove: a take container left by teardown is removed by its id (twice in total); still listed raises; a gone one is not removed again; a failed launch carries the left id | remove-never-removes | red by B7-remove (3 own, 0, 0) |
| R4-11 config folder | B8-config: the folder outlives drive(), is gone after the commit, and stays after a refused commit | no-on-published | red by B8-config (1 own, 0, 0) |
| R4C-1 mode by arm | K1-arm: A or C with their pins pass; C with A's mode, an unpinned arm, no arm and A with `default` carry constant-binding | one-mode-constant | red by K1-arm (4 own, 0, 0) |
| R4C-2 wording script | K2-wording: the wording's line passes; the half's line fails operator-lines; check4 refuses None and [] | the-halfs-script | red by K2-wording (2 own, 0, 0) |
| R4C-3/4 events | K3-events: the three ids never reach the reasons; one study read, one email, the outside reads counted; the sum is outside_reach; a clean transcript counts 0 | nothing-lifted (both layers off: the lift and the agreement refusal; neither credited alone) | red by K3-events (1 own, 0, 0) |
| R4C-5 recorded mode | K4-mode: bypass under arm A passes, and a clean take grades; `default` and `plan` carry constant-binding and route rehearsal before and harness-error after the first turn; no mode, an unpinned arm, or two modes refuse | recorded-mode-unchecked | red by K4-mode (5 own, 0, 0) |

Unwitnessed tests cover:
- the take path end to end: two slots;
- a watcher gap, which routes harness-error and still cleans up;
- a malformed begin, which is a pre-turn refusal (refusal.json: ReplyError);
- a refused begin, which reaches preflight unaltered;
- an adapter that raises (failed, clean box, adapter ended);
- a leaked take container, which stops the loop and refuses the restart;
- an unknown file in the take folder;
- an unrecorded or second drive;
- sidecar_health on a gap;
- the checker-and-reader disagreement refusal;
- the event ids, which are read from routing.json;
- an unpinned mode, which equals nothing;
- the three in-place lines.

## Red, then green (Mac, `mac_slot.py light-ok &&`, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`, `timeout -s INT 60`, Python 3.13, `-B -W ignore`)

Red on ddebb57e's drive.py and check_take.py (byte backup, restored, `shasum -c` OK):
- test_box_integration (by class): `Ran 30`, `FAILED (failures=26)`, 0 errors, rc 1.
- test_check_take: `Ran 14`, `FAILED (failures=12)`, 0 errors, rc 1.
- The six that are green on base are infrastructure: the guard tests, the witness-registry naming tests, and the real-box stub test.

Green at 2f512340, all rc 0, each ending in a bare `OK`:
- test_box_integration, by class and by witness, because the whole module takes about 130 s, past the 60 s bound:
  - TestGuardArmed 2;
  - TestTheTakePath 10 (32 s);
  - TestBoundChecks 8 (31 s);
  - TestRealBoxStub 1;
  - the registry test;
  - the eight witnesses, each alone (1-23 s).
- test_check_take: `Ran 14 ... OK`; through test_round4's main over a folder holding only it: `test_round4: 14 run, 0 skipped, 0 expected failures`.
- test_round4.module_problems over test_box_integration: none; 30 cases, no skip.
- test_drive_commit (w6e's), by class (2, 8, 4, 4, 2), plus its ten witnesses one at a time: every one still red by its own check with 0 errors, and its registry test passes.
- test_preflight `Ran 43 ... OK`; test_run_take `Ran 44 ... OK`.
- `copy_manifest.py --check`: ok.
- test_scaffold, single cases only:
  - test_check_passes_on_the_folder (15 s);
  - test_a_copy_that_differs_without_an_edited_entry_is_refused (51 s);
  - test_every_copied_module_imports_from_inside_this_folder (8 s);
  - test_the_named_imports_resolve_here.
- checks.d: w6h line 3 (check_take.py's in-place rule; also shown red on a touched line, a reverted 902 and an inserted line) and w6e's drive.py prefix line, both rc 0.

Not run on the Mac: the whole test_scaffold, run_checks and the battery (athena's).

## Departures and questions for glitch-1b

- **Departure w6h-1 (needs ratification; the shape of the ratified w6e-1).** Moving check_take.py out of w1a's fragment turns two tests in w1a's tests/test_scaffold.py red, so two edits were made:
  - the identical-copy case uses allowlist.py in check_take.py's place;
  - copied_modules reads w6h's fragment in place of w6e's (w6e no longer claims a .py), so drive.py and check_take.py are still import-probed.

  Both are recorded in w1a's entry for that file.
- **Departure w6h-2.** check_take.py's three in-place edits are above the banner rather than appended, because the plan names those lines and no line may move.
  The checks.d rule binds every other line.
- **Departure w6h-3.** B2-B8 use a spy for `preflight.collect_and_evaluate`.
  The eighteen probes are S1's, tested in test_preflight; a fake for every probe was out of scope.
  What is proved here is the road and its arguments.
- **Q-w6h-1 (the real-box stub).** test_round4's SKIP_ALLOWED is empty, so a collected skip fails the battery.
  The stub is `RealBoxHalf`, deliberately not a TestCase: its method raises `SkipTest(REAL_BOX_STEP)` naming CP2's real-box step (J1).
  A bound test checks the reason.
  Making it a collected skip needs that reason in SKIP_ALLOWED (w1a's file, a reviewed entry).
- **Q-w6h-2.** `driver_constants.permission_mode_by_arm` is this lane's reading of "keyed by arm"; the frozen pre-registration must carry it.
  mode_binding.py's per-arm-and-model expectations (plan 17-19) are outside S6's file list and remain a carry.
- **Q-w6h-3.** The `checker` callable is injected.
  Its real body is check4, the operator-diff count and round 3's finalize abort, and it waits on several things not yet built: the Claude Code adapter, the transcript copied out of the config folder and cross-checked with the stream, and the operator writes.
  The driver's evidence ledger.jsonl (endstate's) is not written yet either.
- **Q-w6h-4.** Only ValueError and RuntimeError count as pre-turn refusals.
  A TimeoutError from the begin exec propagates, so the take is `failed` and needs a ruling, not a rehearsal.
- **Q-w6h-5.** One instance can be counted twice: a masked email in the transcript and the checker's account-email event.
  routing's events doc counts both, and rows never read events, so only the reported counts move.
- **Q-w6h-6.** A failure in `on_published` is recorded in TakeRepo.publish_problems, which nothing reads yet.
- **Merge note (W6-merge-1).** This branch sits on ddebb57e, not on 28e1be3e.
  The w5c line also edits w1a's fragment and tests/test_scaffold.py (BLOCKED emptied; copied_modules reading w5c's fragment), so merging into gap4/wave6-merge conflicts mechanically in those two files.
  The resolution: copied_modules reads w1a's, w5c's and w6h's fragments, and both transfer notes are kept.

## Writer release

The sole writer releases the worktree at this report's commit.
The tree is clean, and no `__pycache__` was written (`-B` throughout).
Scratch outputs are in the session scratchpad under `w6h/`, outside the repository.

RESUME HERE: hand-back at 2f512340
