VERDICT: PASS
Reviewer: a fresh Opus 5.5 reviewer agent of glitch-45, adversarial, under Javier's standing delegation; review only.

# Gemini native-session reader: re-review after lane fold6/kill-leftovers

- Candidate head: `ec62dec8b402375b2f27e8831dab25b9642b5765` on `fold6/kill-leftovers` (what `git -C /Users/javrodher/aegis-builds/fold3-20261030 rev-parse HEAD` printed; the brief's head, so no stop).
- Accepted line: `961e232db150bd3ed55dbd50138e7d2da2e720c5` (Gemini sources `f58cfd1dee65…`, Javier's record holds there).
- Clock: Sun Nov 1 08:33:23 EST 2026 (start) to about 08:45 EST (from `date`).
- Disk: 56 GiB free at start, 52 GiB at the end (`df -h /System/Volumes/Data`); every test batch ran after `mac_slot.py light-ok --tests --work gap-study-r4` printed `light ok`.
- Where I worked: my own scratch folder `/private/tmp/claude-501/-Users-javrodher-glitch/e81989c6-0378-4e91-8b73-fd844ef7d40f/scratchpad/gemrv/`: `git archive` copies of `evals/gap-study-4` at both heads (`acc/`, `cand/`), and three `git clone --no-local --no-hardlinks` copies with their `origin` remote removed (`accept-readers-both-dry.rv01/clone` at the candidate, `acc-clone-dir/clone` at the accepted line, `kitprobe/clone` at the candidate).
- What I never wrote: nothing in `/Users/javrodher/aegis-builds/fold3-20261030` (still at `ec62dec8`, `git status --porcelain` empty at the end), nothing in gap4-walk-records or athena, nothing to any remote. I never typed ACCEPT and never ran the real kit. The only file I wrote outside my scratch folder is this review.
- Python: `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV /usr/local/bin/python3.12 -I -B`, TMPDIR in the scratch folder.

## In plain words, for Javier

What changed: among the nine files the Gemini acceptance hashes, only drive.py moved, and by exactly one line.
That line, in `TakeDriver._postflight`, now hands the take's own session id and run tree to the config-folder check that runs after a live take.
It sits in code that only runs during a live take; nothing the Gemini reader, its stream join or its snapshot-history join reads goes through it.
The other eight hashed files are byte-identical at both heads.

What you accept: the same walk, w-g21, with the same native snapshot, the same two turn streams and the same join (PASS, 2 interactions), bound to the new sources hash `267ac0e2bc56a7e86991f77886d95b4784c33f5325f3d8e4c9d2764c263a29e0` and to this review.

Every arm-G walk reads the same: all 36 committed arm-G practice walks in the register were read through the reader at both heads, and the output (every snapshot's facts and properties, the session metadata, the join, the floor and the snapshot history) is identical, byte for byte.
35 join PASS; one, w-g24, refuses at both heads for the same reason (its native interaction is incomplete), as before.
Every arm-G walk's regrade.json re-derives byte for byte at both heads (36 of 36).

w-g21 still joins PASS with 2 interactions, clears the acceptance floor (34 tool round trips), and its snapshot history joins.

What stays unverified: that the walks are real rather than a consistent fabrication (the road's own docstring: the guarantee is procedural, your commit); the new postflight code on a live take (no take was run); the Codex reader (its own reviewer); the real kit run under your identity.

## Evidence

### 1. Hashed sources at the two heads

Per-file sha256 of every READER_SOURCES file, computed in the archived trees, and `reader_sources_sha256` computed by `native_reader_registration` itself at each head (script `gemrv/q1.py`):

```
file                          961e232d          ec62dec8
gemini_projection.py          b80cdfaebf36…     b80cdfaebf36…   same
gemini_stream_join.py         bd3803d275a2…     bd3803d275a2…   same
gemini_session_replay.py      f46b2cd2ffe2…     f46b2cd2ffe2…   same
vendor_record_binding.py      5db643b7521f…     5db643b7521f…   same
transcript_view.py            fbf7ac6d2356…     fbf7ac6d2356…   same
transcript_gemini.py          6856354dc5f3…     6856354dc5f3…   same
native_reader_registration.py c9100df76a5b…     c9100df76a5b…   same
drive.py                      a68b269e190f…     1a907aac2c5e…   MOVED
vendor_provenance.py          067758fb8124…     067758fb8124…   same
gemini reader_sources_sha256  f58cfd1dee6591b676bc9f9c23b5b76d08cea183c7ecf3e335eb9580e1380079
                              267ac0e2bc56a7e86991f77886d95b4784c33f5325f3d8e4c9d2764c263a29e0
codex  reader_sources_sha256  48540c455e1a…  ->  b7018ec53b040adcc5427c43e4eae50c4026330381eba085530352641c786851
```

The new Gemini hash is the one the brief, the kit (`GEMINI_SOURCES`) and the helper (`SOURCES_NEW`) name.

The whole diff between the heads: `git diff --shortstat 961e232d ec62dec8` gives `8 files changed, 261 insertions(+), 15 deletions(-)`, all under `evals/gap-study-4`: `COPIED.d/fold6-kill-leftovers.json`, `box/preflight.py`, `drive.py`, and five files under `tests/`.
`diff drive.py` between the archives is 4 lines of output: one `2438c2438` hunk, one line out, one line in:

```
-            post = _preflight.postflight(take.config_dir, row["agent"]["harness"])
+            post = _preflight.postflight(take.config_dir, row["agent"]["harness"], session_id=(take.identity or {}).get("session_id"), run_tree=take.spec.run_tree if take.spec else None)  # noqa: E501  lane fold6/kill-leftovers
```

The helper's own `line-check` on my dry clone agrees: `line holds: 961e232d is under HEAD; only drive.py moved among the readers' hashed sources, by exactly the fold6 keyword line; native-readers/ and rehearsals/ are the accepted line's; both records refuse only for their stale sources` (exit 0).
`rehearsals/` is tree `63738925af51…` at both heads (`git rev-parse HEAD:evals/gap-study-4/rehearsals` in both clones), and `diff -rq` of the two archives shows no difference under `rehearsals/` or `native-readers/`.

Can it reach the reader?
The three reader modules import only `gemini_session_replay`, `transcript_view`, `transcript_gemini` and `vendor_record_binding` (`grep` of their imports); none imports drive.py or `box/preflight.py`.
`vendor_provenance.py` names preflight only in comments (lines 6, 103, 121).
The acceptance road imports drive lazily and uses only `drive.walk_files`, `drive.DriveRefused`, `drive.LEDGER_FILE` and `drive.WALK_SUBJECT`, all unchanged; `drive.walk_files` checks file names and kinds and never parses postflight.json.
The changed line runs only inside `TakeDriver._postflight` during a live take, after the turns; its only effect is on that take's postflight.json (for every harness, `recorded` now carries an `admitted_session_pair` key whenever a session id or run tree is passed, an empty list unless a Claude Code killed-take pair is admitted).
The only other non-test change reaching the acceptance road is `box/preflight.py`, imported at module load through drive.py: it adds module constants, `session_pair` and the new keyword arguments, and changes no reader code.

### 2. Every committed arm-G walk, read at both heads

The register at the candidate holds 387 walks (A 277, O 74, G 36).
The 36 arm-G walks: w-g12 to w-g21, w-g23 to w-g48 (no w-g22 entry in the register).
For each one, `gemrv/survey.py` read every native snapshot the driver ledger names (sha256 re-checked against the ledger: all match), and recorded `gemini_projection.project` facts, `project_with_properties` properties, `gemini_session_replay.replay` metadata, `check_session` on the last snapshot against the ledger's streams, `floor_problem`, and `gemini_history` over all the ledger's snapshots, with the reader modules of each head in turn over the same committed walk bytes.

```
survey-acc.json and survey-cand.json: 71410 lines each; `diff` shows only line 2 (reader_sources_sha256)
sha256 of everything after that line: ecb30a0dbcfc90481ab9c6eca1d2a3000362ff77732c5c748cd3b55fb415f614 at both heads
walks: 36, same set, 36 identical
```

Per walk (identical at both heads):

- PASS, 1 interaction, below the floor (1 interaction, so acceptance-ineligible as before), history joins: w-g12, w-g15 to w-g20, w-g23, w-g25 to w-g30, w-g33 to w-g38, w-g41 to w-g46 (26 walks).
- PASS, floor met, history joins: w-g13 (3), w-g14 (4), w-g21 (2), w-g31 (3), w-g32 (3), w-g39 (2), w-g40 (2), w-g47 (2), w-g48 (2) (9 walks).
- DISAGREE: w-g24, `interaction 1: native: the Gemini projection refused the snapshot: native interaction is incomplete…`; its history join refuses for the same reason (1 walk).

Regrade: every one of the 36 arm-G walks carries regrade.json, and `walk_regrade.regrade_doc(walk, study, readers={"gemini": gemini_reader})` re-derives it byte for byte in both clones (`Counter({'re-derives byte for byte': 36})`, output files `q3-961e232d.txt` and `q3-ec62dec8.txt` identical by `diff`).

No walk differs.

### 3. The anchor walk w-g21

At the candidate head, from the survey and from `acceptance_problems`:

```
join: {"status": "PASS", "interactions": 2,
       "shapes": {"interactions": 2, "tool_round_trips": 34, "tool_error_statuses": 1,
                  "object_display_results": 8, "multi_segment_interactions": 0},
       "properties": {"history_rewrites": 0, "tool_outputs_masked": 0, "ignored_prompt_resumes": 0,
                      "loop_feedback_injected": 0, "resumes_after_rerecord": 0}}
floor_problem: None
native: session/native-turn-2.jsonl 92ca8f1eef4d636380920297b64728f98371acf3a441f80b78a4bb171256edb2
streams: turn-1.jsonl e11b4c22a5fb…, turn-2.jsonl 64ec94e36a7e…
```

The current `native-readers/gemini-acceptance.json` binds `{"status": "PASS", "interactions": 2}` and the same native and stream refs; same interactions.
With the committed record changed only in its sources hash (set to the candidate's), `acceptance_problems(record, study, "gemini")` raises nothing in the candidate clone, and the same holds at the accepted line (`gemrv/q3.py`: `gemini record with only the sources hash swapped: HOLDS` at both).
So every gate except the sources hash (walk commit, ledger, check and grade records, launch journals, regrade, snapshot prefix and history join, floor, the marker scan) already holds at the candidate with the old review.

### 4. The record the kit would build, in my dry clone

In `gemrv/accept-readers-both-dry.rv01/clone` (`gemrv/q4.sh`), with a draft of this review, then re-run on this file's final bytes before hand-off:

- `build --acceptor ACCEPTOR-PLACEHOLDER --out gemrv/placeholder-out` (outside any repository): `built gemini-acceptance.json: walk w-g21, 2 stream(s), join PASS 2, reviewer 'a fresh Opus 5.5 reviewer agent of glitch-45', sources 267ac0e2bc56` (exit 0).
- The same placeholder build aimed into the clone refuses: `STOP: a placeholder record is written only outside every git repository` (exit 1).
- `build --acceptor javier` into the dry clone's `native-readers/`: the same line, exit 0; the placeholder and javier records differ only in `accepted_by`.
- Against the committed record, the built one differs only in `reader_sources_sha256` (f58cfd1d… to 267ac0e2…) and the review's `sha256` and `reviewer`; walk, native, streams and join are the same.
- Committed in the dry clone, `acceptance_problems` on the built Gemini record: none raised.
- With only the Gemini record and review rebuilt and committed (Codex still the old record), `verify` prints `REFUSED: the reader's sources changed since the record: a new acceptance is needed` (exit 1): no reader registers, Gemini included.
- After the Codex record is also built (on a stand-in Codex review in my dry clone only, never the Codex reviewer's file) and committed: `registered: ['codex', 'gemini']; …` (exit 0), the diff from `ec62dec8` is exactly the four reader files, all `M`, and the clone is clean.

So `registered: ['codex', 'gemini'];` prints only once both records are rebuilt.

### 5. The kit, read whole

`/Users/javrodher/glitch/plans/gap-study-round-4/accept-readers-both-20261101.sh` (240 lines) and its helper `accept_readers_both_build.py` (326 lines), read whole.

- Commits anything but the four files? No. The real commit stages only `FOUR`, refuses unless `git diff --cached --name-status` is exactly the four `M` lines, and `after` re-checks the commit's diff is exactly those four. The clone must be clean before (untracked included).
- Commits without ACCEPT? No. The real section follows `[ "$word" = "ACCEPT" ] || no …`, and a rehearsal (either kit variable set) stops before it whatever is typed.
- Sets a git identity? No. It reads `user.name`/`user.email` and refuses if either is missing; the only `-c user.name=` is on the throwaway dry clone's commit, per command, never written to any config.
- Sends anything off the Mac? No. No push, fetch, remote, curl or ssh (`grep`); the dry clone is `git clone --no-local` of the local lane clone; `commit_msg.py` imports only `importlib.util`, `re`, `sys`, `pathlib`; the helper runs only local git.
- Leaves the clone dirty on a failure? Probed: a copy of the kit in `gemrv/kitprobe/` pointed at my own clone, with an injected failure after the real commit (and with the ACCEPT line replaced by a no-op, so no ACCEPT was typed). It made the commit, verify printed `registered: ['codex', 'gemini']`, then the injected failure gave `NOT ACCEPTED: PROBE: injected failure after the real commit; un-committed d7741c4c… (recoverable from the reflog); the kit put back what it had changed; the clone is back at ec62dec8… and clean`; `git status --porcelain --untracked-files=all` empty, and the throwaway folder under TMPDIR removed.
- One window it cannot fully undo: an interrupt during `git commit` itself (before `NEW` is set) would restore the four files against a HEAD that may have moved; the kit then prints the leftover state rather than claiming clean (MINOR 2).

### 6. What stays unverified

- Walk authenticity: every gate is a consistency check over producer-written bytes; a consistent fabrication committed under `WALK_SUBJECT` would pass. The guarantee is procedural (Javier's own commit), as the module states.
- The new postflight code on a live take: I ran no take and no test suite (the brief asks for none); the `session_pair` admission, and whether `take.spec` always has `run_tree` on a real take, are the lane's review, not this one.
- The Codex reader and w-o46 (the Codex reviewer); I used a stand-in Codex review only to show the both-records condition.
- The real kit run, Javier's identity and `commit_msg.py` on his machine state; my probe ran a modified copy against my own clone.
- The shapes the reader never counts (`NEVER_COUNTED`): parallel calls from one model message, a turn killed mid-tool, thoughts and thought signatures; and `multi_segment_interactions` is 0 in w-g21.

## Findings

No BLOCKER, no MAJOR.

- MINOR 1 (kit and helper): the review gate checks that some line of the review is exactly `VERDICT: PASS`, not that line 1 is. `review_fields(b"VERDICT: FAIL\nReviewer: x, y\n\nquoted:\n" + b"VERDICT" + b": PASS\n", "gemini", None)` returns `{'verdict': 'PASS', …}`, and the kit's `grep -Fxq` has the same gap. A failing review that quotes the passing line on its own would be recorded as a PASS. Not live here: this review holds that line once, as line 1. Fix: require line 1 to be exactly it (and no other `VERDICT:` line).
- MINOR 2 (kit): an interrupt that lands during `git commit` itself, before `NEW=$(git rev-parse HEAD)`, leaves `undo` restoring the four files without un-committing; the kit then reports the leftover state (head and `git status`) instead of claiming clean, so nothing is silent, but the clone can be left needing a hand. Low exposure (Javier would have to press Ctrl-C in that instant).
- MINOR 3 (pre-existing, not from this lane): `box/preflight.py` is imported by the acceptance road (through drive.py) but is not in READER_SOURCES, so a change to it never unregisters a reader. In this lane it changes nothing the reader reads (Q1), so it does not touch this acceptance; worth a line in the hash-coverage follow-ups.
- NIT 1: the `Reviewer:` parse stops at the first comma, so the record's reviewer reads `a fresh Opus 5.5 reviewer agent of glitch-45` rather than the whole line; consistent with the earlier records' form.
- NIT 2: from this lane on, every live take's postflight.json carries `recorded.admitted_session_pair` (an empty list unless a pair is admitted); no reader or walk check parses it, but anything that compares postflight records across the line should know.
