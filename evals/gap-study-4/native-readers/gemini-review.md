VERDICT: PASS

# Gemini reader review (F4, item b28-gemini-review): lane/vendor-b28 at 854f6c3e against the accepted reader 5457e75e

Reviewer: a fresh Opus 5.5 agent of glitch-f1, adversarial, under Javier's standing delegation.
Written Thu 22 Oct 2026, 03:17 EDT (`date`).
Head: 854f6c3ef0627e14df67abab5e3c5f3cf85976ee (code equal to e72279086192573db1bf7dea500def9d73e62659: `git diff --stat e7227908 854f6c3e` names only lane-reports/vendor-b28-LANE.md).
gemini_session_replay.py at the head: sha256 f46b2cd2ffe26538aff6ad00dbf49e15aa4a142b0d000541dc80274912b30c2f (read with shasum), as the brief says.
The lane clone was never written: all work ran in `git clone --shared` scratch clones (push URL no-push://disabled) and `git archive` trees under /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/review-b28-f4/ (called SP below).
Every Mac batch waited for `mac_slot.py light-ok --work gap-study-r4` (SP/tools/gate.sh); the re-read ran under `mac_slot.py run --kind heavy` (acquired, 03:05:40-03:06:11 EDT, released, rc 0).
No holdout data, no held-out wording, no login or credential file was opened; the tools print verdicts, counts, names and hashes only.

## The answer

Yes.
The new reader reads all 36 committed Gemini walks exactly as the accepted reader does.
The facts the study uses are byte-equal on every walk: 120 of 120 per-interaction reader outputs and 36 of 36 history joins are byte-identical.
The replay, projection and cross-check outputs differ on every walk by one thing only: the new properties key `resumes_after_rerecord`, which is 0 on all 36.
With that key taken out, 432 of 432 walk-side compared outputs are byte-equal.
Every difference on the probe snapshots is road (a) or F-B26-9, as designed.
w-g24's regrade_doc bytes are byte-equal at 5457e75e and at the head (sha256 0290da3b…).
No Codex reader file changed, and the Codex reader_sources_sha256 still equals codex-acceptance.json's value.
One MINOR remains: four of my mutants on new default-deny conjuncts survive the lane's suite. The head code is right in each case (my witnesses pass on the head and kill each one), but the suite does not pin those conjuncts. It can be fixed with tests alone; tests/ is outside READER_SOURCES, so the hash the kit binds does not move.

## 1. The diff

- READER_SOURCES (native_reader_registration.py:85-87) and CODEX_SOURCES (:191-192), each diffed 5457e75e..854f6c3e: gemini_session_replay.py has 247 diff lines. Every other file has 0: gemini_projection.py, gemini_stream_join.py, vendor_record_binding.py, transcript_view.py, transcript_gemini.py, native_reader_registration.py, drive.py, vendor_provenance.py, codex_native.py and native_snapshot.py.
- Outside tests/, box/, COPIED.d/, checks.d/ and lane-reports/, the only changed path is gemini_session_replay.py.
  B27's box files (walk_launch.py, stub_model_*) are in no source list. The one COPIED.d line that changed (live-box-2026-10-14.json) only appends B27's reason text to walk_launch.py's entry.
- reader_sources_sha256, computed with the study's own function: Gemini ec9c80e6… at 5457e75e, equal to the record; f58cfd1dee6591b676bc9f9c23b5b76d08cea183c7ecf3e335eb9580e1380079 at the head (the value the kit will bind). Codex c0121f0c… on both sides, equal to codex-acceptance.json.
- Consumers of the replay output: gemini_projection reads `timeline` and passes `properties` through (gemini_projection.py:405, :456). check_take reads `timeline + copies + dead_results` (check_take.py:4104-4110). No production code tests the properties dict's key set, so the new key is inert.

Each behaviour change, the shape that justifies it, and whether it admits only that shape:

| Change (head line) | Justifying shape (EN = evidence note) | Admits only it? |
|---|---|---|
| Re-entry: a retired CONTEXT_ID record inside an open window goes to `_context_reentry` (message, :556-558) | A-ctx: A1 r70 and r113, A2 r91, A3 r77, B2 r70, each the record right after S | Yes. The record must come straight after the last `$set {sessionId}` (resume_at). It must have exactly {id, timestamp, type, content}, type user, and one {text} part whose text opens with CONTEXT_OPEN (both wrapper lines) and ends with CONTEXT_CLOSE. It becomes CONTEXT_COPY and never a fact: `result` builds the timeline from frozen and live ORIGINALs only, and frozen[CONTEXT_ID] keeps record 2. A retired id other than the context turn, or the context turn outside a window, keeps the retired-id refusal. |
| Live-copy guard (:553-555) | the writer patches an indexed id and appends it once | Stricter only; it fires only on a CONTEXT_COPY. |
| `$set` refused while ctx_pending (replay, :634-636) | the re-entry and the patch are written in one initialize call | Stricter only. |
| Pending patch rule (patch, :322-326) | P-resume {orderIds, removeIds, updates} | Inside the open window, only that key set consumes the re-entry. A re-record shape runs `_rerecord` first, so true compression keeps its name. Every other shape refuses as "not consumed". |
| `_context_copies` (:428-442) and the skip in `_ignored_prompts` (:405-406) | removeIds = the re-recorded context copy, plus A2's "/" copy | Every removed re-recorded copy must be a user copy on text parts only whose trimmed text is ignored. Exactly one must start with "<session_context>", and none may stay live (O6). Removed originals still pass B26's own check. |
| Context turn first after the reorder (:348-351) | orderIds lists the context id first | Yes. |
| End of snapshot while pending (result) | the same one initialize call | Stricter only. |
| F-B26-9: any message that is neither the context turn nor `_response` closes the window (:551-552) | inside a resume the writer appends only those two kinds (:287190-287196) | Yes, keyed on the producer: ids from sendMessageStream are fresh ids, never the stable context id or a `_response` id. See NIT 4 for what the close also changes. |
| `resumes_after_rerecord` property | road (a)'s count | Inert: 0 on all 36 walks. |

The design's precedence and the review's rulings are as the build review and its closure found: re-entry first after $set; the M4 guard widened; the pre-call whatever the window; MINOR 3 dropped; the wrapper tags pinned equal to the projection's. I re-read each in the diff above and did not re-litigate them.

## 2. The full re-read (36 walks, and the B27 probe snapshots)

Tool: SP/tools/cmp_f4.py, my own, sha256 475d1632…. It runs each code folder in its own process (`python3.12 -I -B`, the code folder alone on sys.path, asserted).
For every snapshot it records five things:
- `replay`;
- `project_with_properties`;
- `gemini_reader` for ordinals 1..k+1;
- `check_session` against the first k streams.

For every unit it also records `check_session` of the last snapshot against all streams, and `gemini_history`.
Each result is canonical JSON with sorted keys, or the refusal text.
The comparison is SP/tools/compare_f4.py (375bc472…).
Inputs:
- the 36 w-g walks of dry/vendor-74 at 0554fd6a0c4729295d14e25ba12678449506e727, by `git archive` from /Users/javrodher/aegis-builds/vendor-b26-20261021 (50 native snapshots);
- stub-probe-full1 (8 scenarios), stub-probe-full2 (A1, A1-fake) and stub-probe-smoke1 (A1): 32 snapshots in all.

Code: `git archive` of 5457e75e (replay sha256 c6e2d85e…, equal to `git show`) and of 854f6c3e (f46b2cd2…).
Outputs: SP/out-base.jsonl (adad7718…) and SP/out-head.jsonl (d2ea2feb…). Rows: SP/table.txt and SP/compare.txt.

Tallies (walks): reader facts 120/120 byte-equal; history 36/36 byte-equal; replay 0/50, projection 1/50 (w-g24, refused on both sides), check 1/36 and per-snapshot check 1/50 byte-equal, every inequality being the added `resumes_after_rerecord: 0` alone (432/432 equal once that key is removed).

Per unit: check is the cross-check verdict (last snapshot, all streams) and history the Gemini history join. "Bytes" means: facts = every gemini_reader output and the history output byte-equal; "+key" = the replay, projection and check outputs equal except for `resumes_after_rerecord: 0`.

| Unit | snaps | 5457e75e check / history | head check / history | head properties (non-zero), rar | Bytes |
|---|---|---|---|---|---|
| w-g12 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g13 | 3 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g14 | 4 | PASS / joined | PASS / joined | rewrites 1, masked 20, ignored-prompt resumes 1; 0 | facts equal, +key |
| w-g15 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g16 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g17 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g18 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g19 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g20 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g21 | 2 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g23 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g24 | 1 | DISAGREE "native interaction is incomplete: its last model message ends on tool calls" / refused, same | the same / the same | n/a | check and history byte-equal; replay +key |
| w-g25 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g26 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g27 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g28 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g29 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g30 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g31 | 3 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g32 | 3 | PASS / joined | PASS / joined | rewrites 1, masked 25, loop 1; 0 | facts equal, +key |
| w-g33 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g34 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g35 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g36 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g37 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g38 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g39 | 2 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g40 | 2 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g41 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g42 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g43 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g44 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g45 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g46 | 1 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| w-g47 | 2 | PASS / joined | PASS / joined | rewrites 1, masked 40; 0 | facts equal, +key |
| w-g48 | 2 | PASS / joined | PASS / joined | none, 0 | facts equal, +key |
| full1/A1 | 3 | snap 1 PASS {1,2,0}; 2-3 retired-id name; check DISAGREE, history refused | {1,2,0,0} {2,5,0,1} {2,5,0,2}; PASS / joined | rewrites 2, masked 5; rar 2 | snapshot 1 facts equal; 2-3 differ: road (a) |
| full1/A1-fake (defective folder) | 3 | as A1 | replay PASS {1,2,0,0} {5,11,0,1} {8,17,0,2}; check DISAGREE and history refused "native tool call id reused" (projection) | n/a | snapshot 1 equal; differs by road (a), then refused by the projection as the design predicts |
| full1/A2 | 3 | {0,0,0} {1,2,0}; snap 3 retired-id; DISAGREE / refused | {0,0,0,0} {1,2,0,0} {2,5,0,1}; PASS / joined | rewrites 2, masked 5; rar 1 | snapshots 1-2 facts equal; 3 differs: road (a) |
| full1/A3 | 3 | {0,0,0} {1,7,0}; snap 3 retired-id; DISAGREE / refused | {0,0,0,0} {1,7,0,0} {2,9,0,1}; PASS / joined | rewrites 2, masked 9; rar 1 | snapshots 1-2 facts equal; 3 differs: road (a) |
| full1/B1 | 3 | snaps 2-3 "writer-possible resume shape {removeIds, updates} inside a resume" | snaps 2-3 "native chat compression (the context turn survives a re-record)" | n/a | name only: F-B26-9's close |
| full1/B2 | 3 | snap 1 {1,2,0}; 2-3 retired-id | snap 1 {1,2,0,0}; 2-3 compression name | n/a | name only: road (a) re-entry, F-B26-9 close, pre-call |
| full1/C1 | 3 | 2-3 truncation name | the same | n/a | facts equal, +key |
| full1/C2 | 2 | {0,0,0} {1,0,0}; PASS / joined | {0,0,0,0} {1,0,0,0}; PASS / joined | rewrites 1; rar 0 | facts equal, +key |
| full2/A1 | 3 | as full1/A1 | as full1/A1; PASS / joined | rar 2 | road (a) |
| full2/A1-fake | 3 | as full1/A1 | {1,2,0,0} {2,5,0,1} {2,5,0,2}; PASS / joined (test 5) | rar 2 | road (a) |
| smoke1/A1 | 3 | as full1/A1 | as full1/A1; PASS / joined | rar 2 | road (a) |

Properties are shown as {history_rewrites, tool_outputs_masked, ignored_prompt_resumes[, resumes_after_rerecord]}.
On the probe side, every snapshot that the base admits keeps byte-equal facts at the head: 38 reader outputs.
On the head, every interaction's facts are stable from one snapshot to the next wherever both read: 3 of 3 pairs in each road (a) unit.
So road (a) changes no earlier interaction.
Every count matches the lane's expectations (65c7cc55) and the build review's survey.

## 3. The w-g24 guard (freeze-path plan v2, line 189; ruling (1))

Two scratch clones of vendor-b26-20261021:
- rg-base: detached at 0554fd6a. Its code equals 5457e75e: `git diff --stat 5457e75e 0554fd6a` outside rehearsals/ is empty, and 5457e75e is an ancestor.
- rg-head: the same commit with 854f6c3e merged by exact SHA (scratch merge 216a381b, parents 0554fd6a and 854f6c3e, clean; replay f46b2cd2…). This is the freeze-line shape.

SP/tools/rg_wg24.py (9804555e…) calls `walk_regrade.regrade_bytes(walk_regrade.regrade_doc("w-g24", study, readers=…))`:

| Tree | readers | Result |
|---|---|---|
| 5457e75e code | production_readers (equal to every profile's reader: True) | sha256 0290da3b7a2d756a8b2a41764f78964926a044a6c59640ed3ac215a58d1bb744, 559 bytes |
| 5457e75e code | the profiles' readers, passed explicitly | 0290da3b…, 559 bytes |
| head code | the profiles' readers, passed explicitly (Gemini registered, as after the kit) | 0290da3b…, 559 bytes; `cmp` equal to both above |
| head code | production_readers | RegradeRefused "the reader registration refuses: the reader's sources changed since the record: a new acceptance is needed" (expected until the kit's commit: MAJOR 1's ruling, lane stage 5) |

The document is graded false with the cross-check refused for the reason "native interaction is incomplete: its last model message ends on tool calls", walk_commit 27eef359….
The guard holds on the ruled condition (Gemini registered when the regrade runs).

## 4. Mutants (my own, on the head replay)

SP/tools/mutf4.py (3f6d0c40…) works in a third scratch clone (mutclone).
Each mutant is one edit. Seven modules then run, each in its own process: test_b28_resume_after_rerecord, test_b26_rewrites, test_b25_real_shapes, test_b26_scanner, test_gemini_session_replay, test_gemini_projection and test_b27_reading.
After each mutant the file is restored from a byte backup and its sha256 checked; the final value is f46b2cd2…, and `git status` is clean.
The surviving mutants were then run against my witnesses (SP/tools/wit_f4.py 32431c84…, SP/tools/mutf4b.py 619bc4dd…). Every witness passes on the unmutated head.

| Mutant | Lane suite | My witness |
|---|---|---|
| X1 re-entry kept as RERECORDED | RED (A1-A3, unmutated A1, …) | — |
| X6 road (a) also counts ignored_prompt_resumes | RED (property tests) | — |
| X8 `$set` guard only for sessionId | RED (m15b) | — |
| X23 F-B26-9 close removed | RED (FB269 three walks, m14) | — |
| X24 F-B26-9 close skipped on user records | RED (m14) | — |
| X3 `len(heads) != 1` → `< 1` (two context copies allowed) | SURVIVED | killed by W3 (head refuses "exactly one") |
| X13 ignored copy part may carry extra keys | SURVIVED | killed by W13 |
| X19 while pending, `_ignored_prompts` skips every removed id (originals unchecked) | SURVIVED | killed by W19 (head refuses "not an ignored user prompt") |
| X22 resume_at set on any `$set` (a `$set {lastUpdated}` between S and A-ctx admitted) | SURVIVED | killed by W22 (head refuses "not the first record …") |
| X15 whitespace-only copy not ignored (stricter than isIgnoredUserContent) | SURVIVED | killed by W15 |
| X17 re-entry text type unchecked (AttributeError instead of a refusal) | SURVIVED | killed by W17 |
| X18 live-copy guard on any live context id (stricter than 5457e75e on an ORIGINAL upsert) | SURVIVED | killed by W18 |
| X27 not-consumed refusal skipped for `{updates}` | SURVIVED | name only: W27 still refuses, under the `$set`-while-pending name; equivalent in verdict |
| X26 front check only when two or more are live | SURVIVED | equivalent: CONTEXT_ID is always live after a road (a) patch (removing a CONTEXT_COPY fails `_ignored_prompts`' ORIGINAL check), so a single live id is the context id |
| X25 (a third prefix variant) | not applied: its edit text was not unique | — |

Tally: 15 written, 14 applied. 5 are red on the lane's suite. 7 survive the suite and are each killed by my witness (4 would widen admission, 3 are stricter or crash-only). 1 is equivalent in verdict (name only), 1 is equivalent, and 1 was not applied.
Add the lane's 28 and the build reviewers' 14+5.

## 5. Tests

- Each module in its own process from the scratch clone's root, in checks.d's form (`python3.13 -B -W ignore evals/gap-study-4/tests/<m>.py`), 03:09:20-03:09:39 EDT. All OK:
  - test_b28_resume_after_rerecord 45;
  - test_b26_rewrites 43;
  - test_b26_scanner 3;
  - test_b25_real_shapes 18;
  - test_gemini_session_replay 3;
  - test_gemini_projection 8;
  - test_b27_reading 16;
  - test_stub_model_probe 51;
  - test_stub_model_server 29.
- The lane's one-process hazard set, with the lane's own hazard.py (c6a4391e…, copied unedited), python3.13:
  - test_b27_reading, test_b28, test_batch: 179 run, 0 bad;
  - test_stub_agents, test_stub_model_probe, test_stub_model_server: 98 run, 0 bad;
  - my extra order (test_b26_rewrites, test_b28, test_b25_real_shapes, test_b26_scanner, test_b27_reading, test_gemini_session_replay): 128 run, 0 bad.
  - In every set, sys.modules had nothing removed or replaced, and the environment and cwd were unchanged. test_b28 left sys.path unchanged. The other modules' sys.path changes are their pre-existing module-level inserts, as the lane recorded.

## Findings

### MINOR 1: four default-deny conjuncts of the new code have no witness in the suite

X3, X13, X19 and X22 each widen admission and survive all seven modules:
- X3, the upper bound of "exactly one context copy". The design's section 3 names "drops ... two" as a refusal; only M10's zero case is tested.
- X13, `set(p) == {"text"}` in `_ignored_copy`.
- X19, `_ignored_prompts` still checking removed originals inside a road (a) patch.
- X22, `resume_at` set by `$set {sessionId}` only.

The head behaves correctly on each (W3, W13, W19 and W22 pass on the head and fail under the mutant).
Facts are unaffected in every case: removed originals are frozen as they stood, and copies are never facts.
So no walk is read wrong and no claim is false: the lane's "28 mutants each red" holds for its own set.
Fold: add the four witnesses (scratch versions in SP/tools/wit_f4.py) to test_b28_resume_after_rerecord.py, red first under each mutant.
tests/ is not in READER_SOURCES, so reader_sources_sha256 (f58cfd1d…) and this review's tables stand. Re-run the module before the kit, or record the gap as accepted.

### NIT 2

X15, X17 and X18 are stricter or crash-only and the head is right: whitespace-only copies are ignored, as `isIgnoredUserContent` does; a non-string text part is refused by name; an upsert of the ORIGINAL context id is admitted exactly as at 5457e75e.
Pinning them would guard against later drift; W15, W17 and W18 do it.

### NIT 3

X27 changes only the refusal's name (an `{updates}` patch while pending still ends refused).
X26 is equivalent.
Name both with the lane's equivalent mutants (R2, R5).

### NIT 4 (residual wording)

F-B26-9's close also means that a `<gemini id>_response` record written after the close becomes an ORIGINAL rather than an unverified RESUME_COPY.
That is the same reading 5457e75e gives such an id outside any window, so it adds no new class of input.
The writer never produces it, and no walk changes.
One line in the residual list would make it explicit.

## Commands run (abridged; SP = the scratch folder above)

- `git clone -q --shared /Users/javrodher/aegis-builds/vendor-b28-20261021 SP/clone`, push URL set to no-push://disabled, detached at 854f6c3e. The same for SP/mutclone from SP/clone. SP/rg-base and SP/rg-head were cloned from vendor-b26-20261021 at 0554fd6a; rg-head then ran `git fetch` of 854f6c3e from the lane clone and `merge --no-ff` in scratch.
- `git -C SP/clone diff 5457e75e 854f6c3e -- evals/gap-study-4/<each source>`, `--stat`, `--name-only`. `git archive` of 5457e75e and 854f6c3e (evals/gap-study-4, without rehearsals/) and of 0554fd6a (rehearsals/) into SP/base, SP/head and SP/walks.
- `mac_slot.py run --kind heavy --work gap-study-r4 --owner review-b28-f4 --minutes 30 --needs-mac "…" --wait 1200 -- /bin/bash SP/tools/reread.sh`, which runs cmp_f4.py on each code folder. Then `python3.12 -I -B SP/tools/compare_f4.py SP/out-base.jsonl SP/out-head.jsonl`.
- `gate.sh python3.12 -I -B SP/tools/rg_wg24.py SP/rg-{base,head}/evals/gap-study-4 …`, then `cmp`.
- `gate.sh python3.13 -I -B SP/tools/mutf4.py SP/mutclone`, `… mutf4b.py SP/mutclone` and `… wit_f4.py SP/head/evals/gap-study-4`.
- SP/tools/mods.sh (each module in its own process, light-ok before each), and `gate.sh python3.13 -B SP/tools/hazard.py SP/clone/evals/gap-study-4 <modules>` for the three sets.
- The reader_sources_sha256 computation (inline python3.13 over SP/rg-base and SP/clone).

## Not checked

- athena's battery (it ran on e7227908, which has the same code; I did not re-read it).
- Any walk outside the 36 at 0554fd6a, and the Codex walks (no Codex source changed).
- Whether a real walk will ever show road (a) (residual R1: an unseen variant refuses by name).
- The design review's and the build review's findings beyond what the diff above shows folded.
