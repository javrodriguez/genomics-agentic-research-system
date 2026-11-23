status: handed back

# Lane w8e-lint-reds: Gap Study round 4, the two linters clean over the study folder (ruling W8D-lint)

Written Mon 12 Oct 2026, 09:53 EDT (`date`), by the lane's sole writer (Claude Opus 5.5), assigned by glitch-1b under Javier's standing delegation.
Branch `gap4/w8e-lint-reds`, base `98424794`.
Code commit `b043a750`; draft re-derivation `6a3d8473` (build_draft.py only, the last code commit, redoable on the wave 8 merge); this report is report-only.
Nothing was pushed, merged or dispatched; no lint, lint rule, ci.yml or plan was touched; no holdout, sealed grader part, brief, saved output or credential was opened.

## Result

- `lint_language.py evals/gap-study-4/`, run from the repository root as ci.yml:461 runs it: base rc=1 with 27 findings; head rc=1 with 1 finding, `COPIED.d/w8a-walk-layout.json:8 [always]`, left to the w8d fold as ruled.
- `lint_pooling.py evals/gap-study-4/` (ci.yml:464): base rc=1 with 9 findings; head rc=0, "clean — 78 file(s)".
- With that one line reworded in a scratch edit (restored by `git checkout`, status clean after), the new checks.d line exits 0: "clean — 78 input(s) scanned, 23 excused line(s) on record".

## Per finding

| Finding (base line) | Lint | Done |
|---|---|---|
| contract_quotes.json:134 [free] | language | allowlist entry re-pointed from evals/gap-study-3 to evals/gap-study-4, same line_text; recorded as a correction to the home fix 0800f3b9 (allowlist `why` and w1a's entry) |
| COPIED.d/w3c-cp3-graders-confound-newtasks.json:8 [free] | language | exact-line excusal: the reason quotes the grader's NEGATIONS entry "free from" |
| tests/fixtures_confounded_design.json, 18 reply lines (15, 55, 85, 145, 265, 315, 385, 395, 515, 545, 625, 675, 935, 975, 1005, 1055, 1085, 1105) | language | exact-line excusals: preserved grader test input (test_confounded_design.natural_problems runs the grader on each reply against `expected`) |
| tests/fixtures_confounded_design.json, 3 note lines (979 residual, 980 note, 1110 note) | language | exact-line excusals: the lane's own notes naming the shape. Line 1110 was not in the brief's list of 20; it is the 21st finding, one finding per line |
| COPIED.d/w4n-cp4-gen-confounded-seed2.json:42 [ratio-slash] | language | "the five stage 00/01 wait points" to "the five stage 00 and stage 01 wait points" |
| COPIED.d/w7b-walk-wiring.json:8 [out-of] | language | "lifts ... out of the routable reasons" to "removes ... from the routable reasons" |
| COPIED.d/w8a-walk-layout.json:8 [always] | language | left alone (w8d's); the only residual |
| tasks/approval-scope.json:68 [consisten] | language | "consistent with the contract and glitch-f3's (B)" to "as the contract and glitch-f3's (B) say" |
| COPIED.d/w4f-cp5-coverage.json:22 [pooled] | pooling | "the language and pooling linters" to "lint_language.py and lint_pooling.py" |
| rehearsals/README.md:17 [pooled] | pooling | "a pooled number" to "a figure joined across takes"; no text assertion in test_walk_layout.py (only synthetic READMEs and a path check) |
| tasks/confounded-design.json:175 [across-halves] | pooling | "stay identical across the halves" to "stay identical in both halves" |
| tasks/plan-gate.json:104 [better-than] | pooling | "is worse than an absent one" to "misleads where an absent one does not" |
| tasks/scope-read.json:175, :238 [across-halves] | pooling | "Byte-identical across the two halves:" to "Byte-identical in both halves:" |
| tasks/template-adherence.json:188, :302 [across-halves] | pooling | "Byte-identical across the two halves." to "Byte-identical in both halves." |
| tests/fixtures_number_fidelity.json:304 [in-total] | pooling | "2.4 KB in total." to "2.4 KB all told."; expected label unchanged, test_number_fidelity green |

## The task fields and the agent's prompt (W8E-instrument-1)

No reworded task field reaches the prompt, so no line is recorded under W8E-instrument-1.
The fields are `decisions[].text` (approval-scope, confounded-design, plan-gate) and `halves.*.fixture.note` (scope-read, template-adherence).
The trace: `drive.script_from_design` sends `design.script`, which `check_take.design_view` takes from `variants.operator_steps`; `variants.render_steps` builds each line from `halves[h].operator_script` plus the wording's opening and probe and the factor text, nothing else.
`decisions` is read only by `variants` shape checks and `plan_shape_problems`, and by `tasks/check_task.py` (act-hold); `fixture.note` only by `variants.fixture_problems`.
`design.spec` carries the fixture object, note included, to check4 on the grader side, never to the agent; `claude_code_adapter.py` adds no system prompt.
Not audited: the box image's full contents beyond a grep of box/Dockerfile, run_take.py and take_config.py, which name no evals or tasks path.

## Records

- `COPIED.d/w8e-lint-reds.json` (new) claims `checks.d/w8e-lint-reds.txt` and itself, and lists every edit without transfer.
- Owners' entries carry an "Edit W8D-lint ... no ownership transfer" note: w1a (language-allowlist.json), w2b (fixtures_number_fidelity.json), w4p, w4n, w4m, w4i (task and test_task_scope_read.py), w4j.
- Departure w8e-1: the rehearsals/README.md edit is recorded only in this lane's fragment, not in w8a's entry, so the w8a fragment the w8d fold edits is untouched (fewer merge conflicts).
- Departure w8e-2: the checks.d line is one shell line that runs both linters and fails if either fails (`...; a=$?; ...; b=$?; exit $((a | b))`), not two plain lines; it is red until the w8d fold lands.
- prereg-draft.json gets no owner note, so its commit stays build_draft.py output only.

## Evidence (Mac; each command prefixed by `mac_slot.py light-ok &&` and `timeout -s INT 120`, Python 3.13.2, run from the repository root)

- lint_language: base rc=1 (27), head rc=1 (1, the w8a line). lint_pooling: base rc=1 (9), head rc=0. The base runs passed the folder as an absolute path from outside the repository; both linters report paths relative to the repository, so the finding lines read the same.
- copy_manifest.py --check rc=0 (275 files, 43 fragments, 31 identical, 22 edited, 222 new).
- build_draft.py --check rc=0 at `6a3d8473` (six hashes changed: five task_sha256 and number_fidelity's fixtures_sha256).
- Modules, each rc=0: test_task_scope_read (39), test_number_fidelity (45), test_walk_layout (14), test_task_approval_scope (41), test_task_confounded_design (84), test_task_plan_gate (72), test_task_template_adherence (114), test_task_number_fidelity (74), test_coverage (45), test_rehearsals (9), test_wave4_bindings (12), test_stats (98), test_build_draft (45), test_prereg_order (10).
- Not run: test_round4.py. It discovers every tests/test_*.py, including the whole test_scaffold and test_pipeline, which the hard rules keep off the Mac; it is owed on athena with run_checks.
- One attempt at test_scaffold's TheManifest and TheBinding classes alone hit the 120 s limit (SIGINT; no process left).
