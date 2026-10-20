Status: design stop (round 1)

## ROUND 1 (local executor, Tue 20 Oct 2026, 17:40 EDT / 21:40 UTC)

glitch-26's ruling B23-1: design first, no code. Base `a76b4dd2` (B22, reviewed PASS).

- Design note: lane-reports/vendor-b23-DESIGN.md.
- Source: openai/codex `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` (`git ls-remote ... 'refs/tags/rust-v0.162.1^{}'` printed it), fetched read-only into the session scratchpad.
- athena, read-only, file names only: no w-o* rollout holds a FileChange; the one stream holding a file_change is w-o38's turn 1, whose rollout was not copied out.
- Findings:
  - The view graders read only the path and write versus edit, for Claude as for Codex.
  - Content is read only by reach (T-8). For a patch it lives in the rollout: the FileChange item and the patch text in a READ custom_tool_call.
  - The rollout's FileChange keys its changes by path, and reach's string walk skips dict keys, so the build must hand reach the paths as values.
- For the ruling (design section 12):
  - Q1 m1: recommended option C, the view keeps a started patch as an unanswered call;
  - Q2 n3: recommended, a rename is held under a named reason;
  - Q3: T-8:file-change stays PENDING with its reader wired at the site, until a RECORDED fixture of a patch edit exists;
  - Q4 delete and Q5 a patch refused before Begin: named, not built;
  - Q6: no change to native_reader_registration.
- B23-3's parity note text is proposed in design section 10. It is not built until the ruling.
- Correction (B23-4, review of a76b4dd2 NIT n1), checked at the pin:
  - Design note vendor-b22 section 10c says "nothing else in the world-state assembly reads the version". That is too broad.
  - session/world_state.rs:108-138 switches the environment context's subagent list on it (V2 at :110, Disabled and V1 at :132).
  - session/turn.rs:1294 records it in the analytics TurnResolvedConfigFact (built from :1248).
  - With no child threads both list formatters render empty, and the analytics fact is not model-visible, so 10c's conclusion stands.
  - B22's design note stays as written.
- No code, test or fixture. No push, no mirror, no athena run.

Status: review stop (round 2)

## ROUND 2 (local executor, Tue 20 Oct 2026, 18:06 EDT / 22:06 UTC)

glitch-26's rulings on e1a63311: Q1 option C; Q2 hold a rename; Q3 the row stays PENDING with its reader wired; Q4 delete stays refused; Q5 addendum first; Q6 no change to native_reader_registration.py; B23-3 built.

Commits, each its own stage:
- `c17292b8` Q5 addendum (design section 14, append-only).
  No record carries a patch refused before Begin: arm O reaches apply_patch only inside an exec cell (both models' catalog tool_mode code_mode_only), a tool call emits no turn item, and executed-call metadata is off (0 of 989 metadata records in the 76 committed rollouts record a call).
  So it became a named limitation, built in 522ebe26.
- `5e4f80ba` red. test_codex_patch_reads on a76b4dd2's product: "Ran 13 tests", "FAILED (failures=10, errors=1)" (V1, V4 x2, N1, N2's move_path case, N3 x2, K1, K2, K3 red; the mutants not performable; V2 and V3 green).
  test_codex_started_file_change: "Ran 5", "FAILED (failures=1, errors=1)", F3 "the started record maps to [], not to its one edit call".
- `9e1d923a` green: transcript_codex.py, codex_native.py, check_take.py, three COPIED.d sentences.
- `f8a87a72` witnesses: checks.d/vendor-admission.txt runs the test and its --witnesses.
- `522ebe26` B23-3 and Q5: two parity_notes entries through build_draft.py; prereg-draft.json numstat "8 0", only those two entries.

Runner lines at f8a87a72/522ebe26 (Mac, `env -i` PATH /usr/local/bin:/usr/bin:/bin, Python 3.13.2, `-B -W ignore`):
- test_codex_patch_reads: "Ran 13 tests in 1.876s", "OK"; --witnesses: "witnesses: 14/14 red".
  Each mutant was applied alone and turned its own check red. Two also redden checks downstream of the same guard: started-maps-to-nothing-again also reddens reset, changed and second-start; filechange-not-projected also reddens shape, join and join-refusal; reader-not-handed-in also reddens reader.
- --walks against /Users/javrodher/aegis-builds/gap4-walk-records-20261019 (HEAD 45239b01, `git status --porcelain` 0 lines before and after): "walks: 76 streams of 31 walks, identical before and after", readings sha256 450946a3a7454492cc824d2c92f8c3561e457f2597cfb96768f1108a052ae43c (B22's value).
- --unchanged (a76b4dd2's evals/gap-study-4, evals/*.py and evals/graders, by git archive into a scratch folder, against this tree): "unchanged: fixtures readings sha256 (this tree) ee1e19ff6d5cd4e7b5ad8c001fd1a29d8dcd87d55a1eed238720e3e9d2b95902; identical on a76b4dd2 and this tree".
  It covers F1 (codex) and F2 (gemini): view, raw records, reach and the T-8 site; and the 15 codex-streams fixtures, items and view.
- The Claude road: check_take.py's diff from a76b4dd2 has five hunks, at lines 3984, 4057, 4822, 4857 and 4866, all after the T4 vendor banner at 3750. transcript_view.py and claude_code_adapter.py are untouched.
- test_codex_started_file_change: "Ran 5", "OK", "witnesses: 3/3 red". test_codex_native: "Ran 15", "OK". test_codex_adapter: "Ran 57", "OK", "test_codex_adapter witnesses: 16/16 red; registry 16". test_codex_agents_off: "Ran 4", "OK".
- Under `mac_slot.py run --kind heavy --owner vendor-b23`:
  - test_vendor_check "Ran 26", "OK"; test_vendor_body "Ran 11 tests in 46.670s", "OK"; test_take_checker_dispatch "Ran 5", "OK"; test_vendor_session "Ran 5", "OK"; test_vendor_entries "Ran 8", "OK";
  - test_build_draft "Ran 49", "OK"; test_take_config "Ran 16", "OK"; test_preflight "Ran 59", "OK".
- `copy_manifest.py --check` "ok: 494 files from 60 fragment(s) ..."; `build_draft.py --check` "ok: the committed draft is what build_draft.py builds"; `freeze.py --check` "freeze: 495 owned paths checked; no takes or freeze performed".
- lint_language over the folder: "clean — 115 input(s) scanned, 25 excused line(s) on record".
  lint_pooling over the folder: "2 finding(s)", COPIED.d/vendor-admission.json:247 (B22-10's reason) and w8b-holdout-digests.json:13. The same two are there without this lane's product edits (checked with the green edits stashed), so neither is new here. They are named for glitch-26.

Deviations and corrections, flagged:
- A completed file_change with no started record keeps its call and result. Design section 7 said it would refuse; the reason is in design section 14 (the D8 fixtures and exec's own fresh-id road).
- join's result is unchanged, and the count is join_file_changes' return value. Design section 4 said join's result would gain `file_changes`; adding it would have changed test_codex_native's exact pin for no reader.
- The test file changed between red and green:
  - V3's first form stayed green under the no-reset mutant (hollow), so its first stream is now cut with its patch started;
  - the witness rule reads "its own check red" (B22's rule), and two upstream guards also redden their downstream checks;
  - N3 reads the count through join_file_changes;
  - --unchanged also archives evals/*.py and evals/graders, which check_take imports.
- Design section 14 cites core/src/tools/mod.rs:76-85; the function starts at :75.

Open (Q3): T-8:file-change settles only from a RECORDED fixture, the first committed GPT walk that edits through the patch tool, with its rollout as committed. Until then its refusal is unchanged ("[transcript-unreadable] no vendor reader yet (T-8:file-change)").
Held (Q4): a delete patch stays refused; such a walk holds and goes to glitch-26.
check_vendor_sources: no piece line names this lane's files.
No push, no mirror, no athena run.

Status: fold stop (round 3)

## ROUND 3 (local executor, Tue 20 Oct 2026, 18:25 EDT / 22:25 UTC): the fold of review b0c917ff (CHANGES)

glitch-26's rulings on /Users/javrodher/aegis-builds/REVIEW-vendor-b23-b0c917ff.md: m1, m2, n1 and n2. This lane now lands B22 and B23 together.

Commits:
- `b1e8142f` m1: the join refusal cases call `join` alone (`_join(..., count=False)`), and the mutant `join-wiring-dropped` deletes `    join_file_changes(turn, call)\n` from codex_native.py. "Ran 13 tests", "OK"; "witnesses: 15/15 red", with join-wiring-dropped red on join-refusal alone. checks.d's comment says 15. COPIED.d: one sentence appended to the test's reason.
- `12c82840` m2: B22's two phrases reworded so lint_pooling is clean. This breaks the old-text-as-prefix convention for these two reasons only, as ruled:
  - COPIED.d/vendor-admission.json:247, tests/test_codex_agents_off.py's reason (B22 b088add5). Old phrase, verbatim: `(build_draft's combined sha256, pinned)`. New: `(build_draft's sha256 over each model's file list, pinned)`.
  - COPIED.d/w8b-holdout-digests.json:13, prereg-draft.json's reason (B22 6c60fc0e). Old phrase, verbatim: `(each model's config.toml sha256 and its combined sha256)`. New: `(each model's config.toml sha256 and the sha256 over its file list)`.
  - Why: lint_pooling bans "combined" (two rounds measured under different conditions are never added) and has no allowlist, so checks.d/w8e-lint-reds.txt:4 failed on B22's head and on b0c917ff. The value named is build_draft.config_templates' sha256 over the model's path and sha256 lines, so the new words say what the old one meant.
- `405cff22` n1: the "Patch refused before it starts (arm O)" entry now reads "(one that does not parse, fails verification, or fails the tool's own pre-checks, such as an empty patch)", through build_draft.py. prereg-draft.json numstat "1 1", that entry only.

Runner lines (Mac, `env -i`, Python 3.13.2):
- checks.d/w8e-lint-reds.txt:4, run from the repository root: "clean — 115 input(s) scanned, 25 excused line(s) on record", "clean — 115 file(s) and 0 commit(s) scanned, no excusal path", line exit 0.
  The other lint_* lines in checks.d (w4f-cp5-coverage.txt, over coverage_today.md): lint_language "clean — 1 input(s) scanned, 25 excused line(s) on record", lint_pooling "clean — 1 file(s) and 0 commit(s) scanned, no excusal path", each exit 0.
- test_codex_patch_reads "Ran 13 tests in 1.336s", "OK"; "witnesses: 15/15 red". test_codex_native "Ran 15", "OK". test_codex_started_file_change "Ran 5", "OK". test_build_draft "Ran 49 tests in 34.337s", "OK" (heavy slot).
- `build_draft.py --check` "ok: the committed draft is what build_draft.py builds"; `copy_manifest.py --check` "ok: 494 files from 60 fragment(s) ..."; `freeze.py --check` "freeze: 495 owned paths checked; no takes or freeze performed".

Open items:
- Q3: T-8:file-change settles only from a RECORDED fixture, the first committed GPT walk that edits through the patch tool, with its rollout as committed.
- n2, beside Q3: a kill race. If exec is killed after core persisted the FileChange but before exec printed its item.completed, the settled T-8 reader holds the take as "file change count disagrees" (the view keeps the edit as an unanswered call). A command in the same race is not compared on the T-8 road. The take is held under a named reason, never misread, and the window is narrow.
- Q4: a delete patch stays refused; such a walk holds and goes to glitch-26.
- Not run on the Mac (athena's battery): `--generated-mutants` for transcript_codex.py, codex_native.py and check_take.py, and the full checks.d and suite.
No push, no mirror, no athena run.
