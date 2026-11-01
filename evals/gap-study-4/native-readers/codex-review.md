VERDICT: PASS
Reviewer: a fresh Opus 5.5 reviewer agent of glitch-45, adversarial, under Javier's standing delegation; review only.

# Codex native-session reader re-review: lane fold6/kill-leftovers

Candidate head: ec62dec8b402375b2f27e8831dab25b9642b5765 on branch fold6/kill-leftovers, the head `git -C /Users/javrodher/aegis-builds/fold3-20261030 rev-parse HEAD` showed (clone clean).
Accepted line: 961e232db150bd3ed55dbd50138e7d2da2e720c5, where the Codex record binds sources 48540c455e1a6b387f23eb263def5a221501fe1c4263f5148282acf05d494e9e.
Clock: started Sun Nov  1 08:33:23 EST 2026, evidence closed Sun Nov  1 09:04:39 EST 2026 (both from `date`).
Where: the Mac only, in the reviewer's scratch folder; two `git clone --no-local` copies checked out at 961e232d and ec62dec8, and one dry clone of the lane branch in a folder named `accept-readers-both-dry.rv01`.
Nothing was written into /Users/javrodher/aegis-builds/fold3-20261030, nothing touched gap4-walk-records-20261019 or athena, nothing was sent to any remote, ACCEPT was never typed and the kit was never run.
Disk was 56 GiB free at the start (`df -h /System/Volumes/Data`).
Every test run, walk survey and build batch ran after `mac_slot.py light-ok --tests --work gap-study-r4` printed `light ok`; none was held.
Scripts that read walk bytes ran as `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV /usr/local/bin/python3.12 -I -B` with TMPDIR in the scratch folder.

## In plain words, for Javier

What changed: among the files your Codex acceptance hashes, only drive.py, and only one line of it.
That line is in TakeDriver._postflight, the check of a take's config folder after the take ends: it now also hands that check the take's session id and run tree.
The Codex reader never runs that code: reading a rollout, joining it to the exec streams and the snapshot-history check do not call _postflight, and codex_native.py, native_reader_registration.py, vendor_provenance.py and native_snapshot.py are byte-identical to the accepted line.
The other file the lane changed, box/preflight.py, is not hashed; its new code only admits a killed Claude Code take's own sessions/ pair, and it is not on the reader's road.
What you would be accepting: the same walk as before, w-o46, with the same 3 interactions, the same native snapshot and the same three streams; only the sources hash (48540c45 to b7018ec5) and the review fields change.
Every one of the 74 committed arm-O walks in the register reads to the same facts, the same join, the same check and the same snapshot history through the reader at the accepted line and at the candidate head, and all 74 join PASS; the 38 that carry a regrade.json re-derive to their committed bytes at both heads.
What stays unverified: the new postflight branch on a real killed Claude Code take, and the checker-digest recheck the lane's copy record says follows (both outside this reader); and the kit's real commit step, which only you run.

## Evidence

### 1. Which hashed sources differ

Per-file sha256 (first 16 hex) of every file in CODEX_SOURCES (native_reader_registration.py:191-192), from each clone:

```
                               961e232d           ec62dec8
codex_native.py                27280c8eac4a06bc   27280c8eac4a06bc
native_reader_registration.py  c9100df76a5b6db0   c9100df76a5b6db0
drive.py                       a68b269e190f48f8   1a907aac2c5e4749
vendor_provenance.py           067758fb8124f5fc   067758fb8124f5fc
native_snapshot.py             a96a6bf081eeb7c0   a96a6bf081eeb7c0
```

`reader_sources_sha256(sources=CODEX_SOURCES)` computed by each head's own module, both from the working files and from HEAD's committed bytes:

```
961e232d  codex  48540c455e1a6b387f23eb263def5a221501fe1c4263f5148282acf05d494e9e   (disk = HEAD)
ec62dec8  codex  b7018ec53b040adcc5427c43e4eae50c4026330381eba085530352641c786851   (disk = HEAD)
```

The candidate value equals the claimed b7018ec5…6851, and the accepted value equals the committed codex-acceptance.json.
(The Gemini hash moves too, f58cfd1d to 267ac0e2, because drive.py is also in READER_SOURCES; the Gemini reviewer covers it.)

The whole diff, `git diff --stat 961e232d ec62dec8`: COPIED.d/fold6-kill-leftovers.json, box/preflight.py, drive.py (`--numstat`: 1 added, 1 removed), and five files under tests/.
The rehearsals tree is 63738925 at both heads, and native-readers/ is unchanged.
The drive.py hunk, in full:

```
-            post = _preflight.postflight(take.config_dir, row["agent"]["harness"])
+            post = _preflight.postflight(take.config_dir, row["agent"]["harness"], session_id=(take.identity or {}).get("session_id"), run_tree=take.spec.run_tree if take.spec else None)  # noqa: E501  lane fold6/kill-leftovers
```

Can it reach the reader or its join?
- `_postflight` has one caller, drive.py:2894, inside the live take loop; `grep` finds no call from native_reader_registration.py, codex_native.py, vendor_provenance.py, native_snapshot.py or walk_regrade.py.
- What the Codex road uses from drive.py is drive.WALK_SUBJECT, LEDGER_FILE, WALK_GRADE, walk_files, codex_cross_check, neutral_name and take_checker; none touches the changed line.
- box/preflight.py is imported by drive.py at module load (drive.py:1519); its new module-level code is four constants and one function, with no side effect; `stat` was already imported.
- The new postflight output key `admitted_session_pair` is written only when session_id or run_tree is passed; no reader, join, regrade or acceptance code reads postflight.json's `recorded` content.
- `take.identity` and `take.spec` both default to None in `_Take.__init__` (drive.py:2028, 2042), so the new line cannot raise on a take that never got them; with either missing, postflight admits nothing new.

The kit's own `line-check` agreed on the dry clone: `line holds: 961e232d is under HEAD; only drive.py moved among the readers' hashed sources, by exactly the fold6 keyword line; native-readers/ and rehearsals/ are the accepted line's; both records refuse only for their stale sources (codex b7018ec53b04, gemini 267ac0e2bc56)`.

### 2. Every committed arm-O walk, accepted line against candidate head

The register at the candidate head holds 387 entries, 74 of them arm O, and all 74 folders are committed.
One script of mine ran once against each clone's study folder, through that head's own modules, and hashed each output with `json.dumps(sort_keys=True)`:
`codex_native.project` on every retained snapshot, `codex_native.read_rollout` on the last snapshot, `native_reader_registration.codex_join_session` and `codex_check` on the last snapshot with the walk's streams and ledger, `vendor_provenance.session_history_facts("codex", ...)` over every snapshot with `readers={"codex": codex_reader}`, and, where the walk carries one, regrade.json re-derived as `_regrade_problems` does it and compared to its committed bytes.
Every snapshot was first checked against its ledger sha256.

```
walks 74 differing keys []
check status new Counter({'PASS': 74})
regrade present 38 equal old Counter({'True': 38, 'None': 36}) equal new Counter({'True': 38, 'None': 36})
snap sha ok True
n_snaps Counter({1: 29, 2: 23, 4: 10, 3: 6, 5: 3, 6: 2, 7: 1})
```

A second pass at the candidate head confirmed the equal hashes are not equal errors:

```
errors []
history n Counter({1: 29, 2: 23, 4: 10, 3: 6, 5: 3, 6: 2, 7: 1})
late after_complete Counter({0: 74})
```

So: 74 of 74 read the same on every output (project, read_rollout, join, check, snapshot history, regrade); none differs; all 74 join PASS; the snapshot history has one entry per retained snapshot on every walk; no walk holds a late command.

### 3. w-o46, the anchor walk, at the candidate head

- codex_check: `{'interactions': 3, 'served_models': [None, None, None], 'shapes': {'command_round_trips': 9, 'interactions': 3, 'marker_texts': 0, 'reroutes': 0}, 'status': 'PASS'}`, the same at the accepted line.
- The join `{"status": "PASS", "interactions": 3}` equals the committed codex-acceptance.json.
- CODEX_FLOOR (2 interactions, 1 command round trip) is met, so floor_problem is None; `acceptance_problems` (which calls floor_problem) holds on the dry clone (section 4); 3 retained snapshots.
- The record built from it binds native session/native-turn-3.jsonl sha256 568705600a468810a42d12ee0665c796053c353a624eea9024655604f73aba2b and the same three stream hashes as the committed record (ac849ba7…, b8fe52b5…, 2156c7be…).

### 4. The record the kit would build, on a dry clone

Dry clone: `git clone --no-local --no-hardlinks --branch fold6/kill-leftovers` of the lane clone into `<scratch>/cxrv/accept-readers-both-dry.rv01/clone`, at ec62dec8; scratch identities only through `git -c`.
Two test-made stand-in reviews (line 1 `VERDICT: PASS`, a `Reviewer: stand-in reviewer for a dry run of the acceptance road, rv01` line) stood in for the two reviews.

Before anything, at ec62dec8: `native_reader_registration.py verify` prints `REFUSED: the reader's sources changed since the record: a new acceptance is needed`, exit 1; at 961e232d it prints `registered: ['codex', 'gemini']; ...`, exit 0.

`accept_readers_both_build.py build`, codex:

```
placeholder acceptor, --out outside any repository   built codex-acceptance.json: walk w-o46, 3 stream(s), join PASS 3, ..., sources b7018ec53b04
placeholder acceptor, --out inside a clone           STOP: a placeholder record is written only outside every git repository
javier, a study outside a dry-prefixed folder        STOP: with acceptor javier the study must be the kit's mktemp dry clone
javier, the dry clone                                built codex-acceptance.json: walk w-o46, 3 stream(s), join PASS 3, ..., sources b7018ec53b04
```

The placeholder record and the dry-clone record are equal except accepted_by.
Against the committed record, the built one differs in exactly reader_sources_sha256 (48540c45 to b7018ec5), review.sha256 and review.reviewer.

Does verify print `registered: ['codex', 'gemini'];` only once both records are rebuilt?

```
codex only committed:    codex acceptance_problems: holds | gemini REFUSED: the reader's sources changed ... | verify: REFUSED: the reader's sources changed ..., exit 1
gemini only committed:   codex REFUSED: the reader's sources changed ... | gemini acceptance_problems: holds | verify: REFUSED: ..., exit 1
all four in one commit:  codex holds | gemini holds | verify: registered: ['codex', 'gemini']; acceptance commit c196a6bf... exit 0
```

After the four-file commit: `git diff --cached --name-status` was exactly the four reader files, all M; the dry clone stayed clean after commit and after verify; `after --after ec62dec8` printed `the commit changes exactly the four reader files`.
Bad variants, each committed on top of the four-file commit and verified, then reset:

```
review bytes edited after the record   REFUSED: the review hash in the record does not match the committed bytes of codex-review.md
reviewer set to Javier                 REFUSED: the reviewer and the acceptor must be different principals
walk swapped to w-o72                  REFUSED: commit 3020d46d... touches the walk folder and is not a regrade commit of its regrade.json alone
```

The kit and its helper were edited on disk at 08:45 during this review (kit sha256 f2b94c80…, helper cea3e79d…); I re-read both whole.
The helper now requires line 1 to be exactly `VERDICT: PASS`; I rebuilt both records with the edited helper in a second dry clone (`accept-readers-both-dry.rv02`, since removed) and they are byte-identical to the first build; a review with `VERDICT: PASS` on line 2 now stops (`STOP: the codex reader review's line 1 is not exactly 'VERDICT: PASS'`).
This file's own final bytes are checked by the same road after it is written; the result is in the reviewer's handback, since recording it here would change the bytes.

### 5. The kit, read whole (the version at 08:45)

- Commits only the four reader files: it stages the four by name and refuses unless `git diff --cached --name-status` is exactly those four as M (kit lines 227-229), then `after` re-checks the commit (242). The lane clone has no hooks outside the samples and no core.hooksPath, so nothing can add to the commit.
- No commit without ACCEPT: the read word must equal `ACCEPT` (205); EOF reads as empty; a rehearsal (KIT_ENV_FILE or KIT_REVIEW_DIR set) stops before the clone whatever is typed (204); Ctrl-C at the prompt exits with REAL=0, before any write.
- No git identity set: the real commit uses the clone's configured identity and refuses if none (133-135); the dry clone uses `git -c` only (187).
- Nothing leaves the Mac: no push, fetch or network call; the only clone is `--no-local` of a local path; commit_msg.py and verify make no network call; the verify transcript goes to the kit folder, outside the clone.
- A failure after the first write: REAL=1 is set before the first copy (222), and any `no` from there runs `undo`, which un-commits a kit commit on the expected branch and parent, resets and checks out the four files from the base, and prints whether the clone is back at the base and clean.
- Before REAL=1 nothing is written into the clone: line-check and verify run with `-B`, and the clone is checked clean after them (132) and again before the commit (210).

### 6. Tests

```
tests/test_fold6_kill_leftovers.py         at ec62dec8: Ran 8 tests OK
tests/test_native_reader_registration.py   at ec62dec8: Ran 7 tests, FAILED (errors=2); the tail I kept shows `RegistrationRefused: the reader's sources changed since the record: a new acceptance is needed`, the expected hold until a new acceptance is committed (I kept only the last 6 lines, so I saw one of the two tracebacks)
tests/test_native_reader_registration.py   at 961e232d: Ran 7 tests OK
tests/test_native_reader_registration.py   on the dry clone after the four-file commit: Ran 7, FAILED (failures=2), both the ACCEPTED_AT pin: codex `'c196a6bf…' != '46132ace…'` and gemini `'c196a6bf…' != '5292df49…'` (finding 1); no other failure
```

## Findings

1. MINOR, owner-step follow-up: tests/test_native_reader_registration.py pins ACCEPTED_AT (line 189; codex 46132ace…) and asserts the last commit touching each acceptance record equals it, so after Javier's commit that module is red until a later lane commit moves both pins (his commit must stay the four files, as `after` checks). On the dry clone after the stand-in four-file commit it fails for both harnesses (section 6).
2. MINOR, outside this diff: `native_reader_registration.py verify` prints `acceptance_provenance()` with its default harness, Gemini, so its "walk commit" is the Gemini walk's (e2c30e0c on the dry clone) and its acceptance commit is whichever commit last touched gemini-acceptance.json; in a one-commit acceptance of both that is the same commit, but the line never names the Codex walk.
3. NIT, kit: an interrupt that lands after `git commit` returns and before `NEW=` is assigned (kit lines 230-231) would run `undo` with NEW empty, so it would check the four base files out over the new commit and leave the clone dirty; `undo` reports that state plainly rather than claim a clean clone, and the kit's own text now names this window. Not reachable without a Ctrl-C at that instant.
4. NIT, scope: the lane's copy record says drive.py is a CHECKER_CODE_FILES member, so check_take's checker digests move (codex 0fce8586 to 9189f309) and a recheck wave of the committed walks follows; that recheck is not the reader and is not covered here (the 38 regrade.json files re-derive unchanged, so the regrade document does not carry that digest).
5. NIT, coverage: the new postflight branch runs only on a live claude-code take; no committed arm-O walk exercises it, and it is tested only by tests/test_fold6_kill_leftovers.py.

No finding is load-bearing for the Codex reader: no reader file changed, the one drive.py line is off the reader's road, and every committed arm-O walk reads the same, with w-o46 still joining PASS on 3 interactions above the floor.
