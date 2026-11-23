VERDICT: CHANGES

# Review of lane ship-evidence-blobs at 2ced80f2 (freeze line 1b20a10a)

Reviewer: a fresh Opus 5.5 session, 2026-10-23 22:52 EDT.
No code was changed and nothing was committed.
The experiments ran in a scratch clone, with one worktree for each commit.
The Mac was on thermal hold the whole time (`mac_slot.py light-ok --work gap-study-r4` reported "light hold: CPU speed limit 45 is below 50"), so I ran single test classes only, each under a minute.

## Reproduced (Mac, the real athena_suite at aegis 1ab2aae, real gitleaks)

- 106ade8c (red): `TestTheRoad.test_l10_outward_evidence_blobs` FAILS, and `TestRealOutwardScan` has 4 failures (the clean rehearsal blob, the take blob, the AWS canary and the token canary each refuse with "binary blob(s) the scanner cannot read").
- c3106b28 (green): both tests pass (L10 in 33 s; RealOutwardScan, 6 tests, OK).
- 4ec7964e (red): `TestOD57TwinOutward` has 2 failures (the real five findings, and twins carried in the same commit), and `TestOD57TwinShipListing` has 1 failure.
- 2ced80f2 (green): L10 OK, RealOutwardScan OK (6 tests), TestOD57TwinOutward OK (14 tests, 55 s), TestOD57TwinShipListing OK. None of them skipped.
- The witness `outward-name-unbound` is red by L10 as claimed: both the "sha256 not of its stored bytes" case and the "name bound to the decompressed bytes" case ship under it.

## Findings

1. **MAJOR: a gzip that looks like text ships with its payload unscanned.** The spec says the outward scan applies "the same rule the fetch trusts".
   The fetch's candidate set (`evidence_candidates`, MINOR 5 of an earlier review) includes every new blob that starts with `1f 8b`, even when git reads it as text.
   The outward road (`outward_evidence_blobs`) starts only from `suite_mod.binary_blobs_hashed`, which lists blobs with a NUL in their first 8000 bytes.
   A gzip with FLG=FEXTRA, a nonzero MTIME and an extra field longer than 8000 bytes has no NUL in that window.
   So git, gitleaks `git` and `scan_unpublished` all read it as text, and only its compressed bytes get scanned.
   Probe (`scratchpad/probes/p1.py`, real suite, real gitleaks): a gzip like that carries an AWS-key-shaped canary that is made at run time and never printed.
   The scan returns 1 and the blob ships, both at `rehearsals/w001/evidence/blobs/<sha256 of stored>` and at `rehearsals/w001/rec.json.gz`.
   The same probe ships on the freeze-line code (106ade8c's box/), so this is an existing hole, not a regression.
   This lane is the one that writes the outward evidence rule, though, and the brief names "text-looking gzip" as a hot spot.
   The fix: take the outward candidate set from the shipped commits' new blobs that are binary OR start with `1f 8b`, as `evidence_candidates` does.
   An evidence-shaped candidate is then decoded and scanned.
   Any other `1f 8b` blob refuses, on an evidence path or off it.
   One witness should go with the fix: this probe, put through `TestRealOutwardScan`.
   Normal `gzip.compress` output always has a NUL at byte 3, so an accidental leak is unlikely; the risk is crafted bytes.

2. **MINOR: two guards on the twin road have no witness.**
   The real code is correct on both, as the probe `scratchpad/probes/p3.py` shows with the real suite.
   Gemini bytes at a Codex record path are refused by the suite's door.
   With twins at both w-g21 and w-o21, the copy refuses because the w-o21 twin does not admit.
   A Codex-path copy of a w-g21 record refuses as well.
   But two mutants pass the whole `TestOD57TwinOutward` class:
   - (B) `all(` changed to `any(` in the group admission, which admits the w-g21+w-o21 copy;
   - (C) the `door["_od57_file"](path) is None` filter dropped in `twins_of`, which lets a ruled-path finding that the suite's door refused be admitted through a twin of another family (the Codex-path copy ships).

   Add one test each: the cross-family twins refuse, and a ruled-path finding the door refused is never twinned.
   Two more mutants are effectively equivalent and need only a note in the witnesses' comment: (F) the regular-file mode filter in `_tree_files` (a symlink or gitlink blob cannot equal a JSONL record), and (G) dropping the `... in ok` string check, leaving only `id(s) not in left_ids` (the original returns every finding either still refused or admitted).

3. **MINOR: the caps are cumulative across everything unpublished, so ships can stop over time.**
   On the fetch road `BLOB_MAX_COUNT=256` and `BLOB_TOTAL_MAX` are per walk.
   On the outward road they cover every evidence blob that is not on public GARS.
   At this head that is 13 evidence blobs (1 at w-g27, 12 at w-g29) out of 3,356 unpublished commits, against 435 evidence blobs in the tree.
   The road fails closed, so this is not a safety issue.
   But counted takes add 1 to 12 blobs each, and public pushes are Javier's word.
   Without a public push the ship refuses once 256 accumulate.
   Either state this in the lane note or count it in the ETA binds.
   (Two benchmark `fastq.gz` binary blobs, under development/c01 and d06, are also unpublished. This road leaves them to `scan_unpublished`'s committed allowlist, as before.)

4. **NIT: the decode loop is duplicated.**
   `outward_evidence_blobs` and `admitted_evidence_blobs` agree today on the stored-size cap, the sha256(stored) binding, the bound formula, `gunzip_to`, the NUL check on header fields and the `.header` file.
   Finding 1 already shows what this costs: the candidate selection diverged.
   A shared helper for "decode and stage one blob" would keep the two roads in step.

5. **NIT: the FakeSuite returns an empty list when the folder is missing.**
   `FakeSuite.binary_blobs_hashed` now returns `[]` when `repo` is not a directory.
   That is fine for the ship road's fake clone.
   But a fetch-road test that passes a wrong path would now go green without checking anything.
   Gating the empty answer on a flag set by the fake `scratch_clone`, instead of on `os.path.isdir`, would be narrower.

6. **NIT: the byte comparison in `_od57_door` reads the files at scan time.**
   It compares the bytes of the suite's `od57_rule.py` and `od57_shapes.py` as they are on disk when the scan runs.
   The code in memory is whatever `_load_pinned` loaded earlier.
   A change between load and scan would not be seen (a time-of-check gap; `load_suite` runs moments before, so it is not reachable in practice).

7. **NIT: two cases have no test.** Merge commits (remerge-diff findings) and a copy with several twins in different families have no test on the twin road.
   The merge semantics are the suite's own (the finding's commit and the `rev:path` blob), and they look right.

## Checked and sound

- The stored-bytes sha binding is the fetch's. Both the decompressed-name case and the wrong-name case refuse (witnessed).
- `_shipped_blob_paths`: `git log --raw -z --diff-merges=separate --root --no-renames`.
  `meta[3]` is the new id, the framing is NUL with the inter-commit newline stripped, and deletions are ignored.
  A blob that is also at a path that is not an evidence path is classified out and refused by `scan_unpublished` (witnessed by `outward-paths-unread`).
- The text check on the decoded payload (a NUL in the first 8000 bytes) plus the canary proof matches the fetch.
  Non-gzip, binary payload, ratio bomb, truncation, header fields, and the per-blob, stored, total and count caps all refuse (L10 cases and their witnesses).
- `_od57_twins`: the swap is in `scan_unpublished.__globals__`, the real module dict, even through `_PublicAt.__getattr__`.
  The restore is in `finally`, so it holds on a normal return, on a `Refused` raised inside the scan and on any other exception.
  Mutant A (restore moved out of `finally`) is caught by `test_the_suites_door_is_restored_after_each_scan`.
  Admissions are appended to `lines_ruled` only when the scan returns.
- The `_od57_door` byte check against `box/` is witnessed by mutant E (comparison dropped), which `test_a_suite_whose_rule_is_not_this_repositorys_copy_gets_no_twin_road` catches.
- A twin must have the same blob id, as a regular file, at the finding's commit, and must be agent text by the suite's own `_od57_file`.
  The one-byte change, the absent twin, the twin removed at the finding's commit, a twin outside the ruled set, another rule on the line, a second finding of the rule on the line, and the pin line on a line the rule does not read all refuse (real scanner).
- The admission string is built as `"%s:%s:%s:%d"`, matching the original.
  StartLine is a real int because the original checks `type(...) is int`, and ruled paths cannot contain `:`.
- `ship` lists every OD57 admission, twin admissions with their `via`, and nothing else from `ruled_used` (TestOD57TwinShipListing).
- `box/od57_rule.py` and `box/od57_shapes.py` are untouched; the diff touches only the three listed files.

## Not run

- The real-line outward scan of the candidate head (3,356 commits), because of the thermal hold; that proof belongs to the athena battery or the rehearsal ship.
- The full `TestWitnesses` battery (16 new L10 witnesses at about 30 s each); one was spot-checked.

## Closure check (24ca0d9f)

VERDICT: PASS

Checked 2026-10-23 23:28 EDT on head 24ca0d9fcc062e870f8bda2eaf9bee56a25277c7, which adds 04da2dfb, cb986f35 (red 2) and 24ca0d9f (green 2).
The only working-tree change is this appended section.

### Run on the Mac (light-ok --tests was ok at 23:24)

- At 24ca0d9f, `TestRealOutwardScan` passed: 11 tests, real suite, real gitleaks.
  It includes my old probe p1's exact bytes (FEXTRA of 8300) at an evidence path and off the evidence paths, and both now refuse.
  It also covers a text-looking gzip within the field caps: with a canary inside, it refuses by the private scan; clean, it is admitted at an evidence path and refused off the evidence paths.
- At 24ca0d9f, `TestTheRoad.test_l10_outward_evidence_blobs` passed (32 s), and so did `test_l8_blobs` (the fetch, through the shared decode step, 47 s), `test_l1_ship` (4 s) and `TestOD57TwinShipListing`.
- After that the gate turned to "tests hold: CPU speed limit 60 is below 80" (then 68), so nothing more ran on the Mac.

### Not run (left to the athena battery)

- `TestOD57TwinOutward` at 24ca0d9f: the new tests for two families, the ruled-path filter, merge twins, and the B and C witnesses.
- The red 2 reproduction at cb986f35.
- `TestWitnesses`.
- Re-runs of my probes p2 and p3 (p1 is now covered by the test above).
- The twin road's code (`_od57_door`, `_od57_twin_door`, `_od57_twins`) did not change since 2ced80f2, so the new twin tests change only the tests.
- This PASS holds on that battery coming back green.

### The rulings, read in the code

1. The candidate set is now the fetch's: `is_evidence_candidate` (binary, or gzip magic) is shared by `evidence_candidates` and `_unpublished_candidates`.
   A candidate on the evidence paths is decoded and scanned.
   A gzip-magic blob that git reads as text, anywhere else, refuses as `stray`.
   p1 is now a real-scanner test.
2. `stage_evidence_blob` is the one decode step.
   On the fetch its order and its arithmetic are unchanged: the stored cap, the read, the path and name at every path, the limit, `gunzip_to`, the NUL check on header fields, and the `.header` file.
   `FETCH_SAYS` is byte for byte the old fetch wording: `.format(cap=BLOB_MAX_BYTES)` and `.format(why=e)` render exactly as the old f-strings did.
   The one change in order: `total` grows after the header check instead of before it, and that matters only on a path that refuses anyway.
3. Mutants B and C each have a red test and a witness; the reasoning for F and G being equivalent is recorded.
4. The caps are counted per walk folder (`_evidence_walk`), and no value changed.
   A blob that sits in two walk folders counts in both, and its room is the smaller of the two, so it errs toward refusing.
5. `FakeSuite.binary_blobs_hashed` raises on a missing repository, and `FakeSuite.scratch_clone` really clones.
6. A merge twin test (an evil merge adds the copy) checks both the admission and its listing.

**The ruled deviation is accepted.**
A binary blob with a NUL, off the evidence paths, is left to `scan_unpublished`.
That refuses it unless the committed allowlist names it by both sha256 and blob id, or `allow_blobs` holds it.
`allow_blobs` holds only the decoded evidence ids, so no new allowance is added.
The two benchmark `fastq.gz` blobs are binary, so they go down this road and are never treated as `stray`.

**FakeSuite cloning for real makes no test pass vacuously.**
FakeSuite's default public tip is now the clone's root commit, so every `git ... --not <public>` in the outward rule resolves.
The happy path in L1 ships, which proves the evidence rule runs cleanly on the fake rig.
The L1 cases that expect a refusal differ from that happy path only in their own trigger.
They do not assert the reason for the refusal, but that was already true before this lane.

### Findings

1. **NIT: an error mid-stream in `_unpublished_candidates` can stall for 10 minutes.**
   If the main thread refuses in the middle of the cat-file stream (a header that does not match, a short read), its `finally` runs `feed.join(timeout=600)` before it closes `p.stdout`.
   With more than about 64 KiB of ids still unfed, which the real line has, the feed thread is blocked on a full stdin while cat-file is blocked on a stdout nobody reads.
   The refusal then waits the full 600 s, and the later wait raises "git cat-file failed", which hides the first message.
   It still fails closed, and it needs a corrupt clone that has passed the bundle's index-pack.
   Fix: close `p.stdout` (or kill `p`) before the join on the error path.
2. **NIT: the walk caps leave the total decoded per ship unbounded.**
   Per walk, the decoded size is still capped, but the sum across walks is now walks × `BLOB_TOTAL_MAX` on the Mac's disk, inside the 0700 temporary folder that is removed afterwards.
   Today it is small (all 435 evidence blobs together store 252 KB), so it matters only while the Mac is short of disk.

The stop rule is reached: only nits remain.
