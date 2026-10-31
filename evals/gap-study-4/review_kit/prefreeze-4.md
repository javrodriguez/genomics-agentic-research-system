prereg.json sha256: 37fd08047b66cbaee8cc12cd05a823692e2bafebaaa599d6db53178482b5c0e3

# Pre-freeze review 4 of gap-study-4

**Ruling: DO FREEZE.**

My table below holds no MAJOR. Review 3's one MAJOR is fixed. I found one new MINOR (m10): the walk path gate does not open the sub-agent streams of two Claude walks. It names no checkout path, so it does not block. Every other open item is a MINOR or NIT carried from review 3, and none moves a count, a criterion or a published sentence.

`prereg.json` is byte-identical to `study/evals/gap-study-4/prereg-draft.json` (`diff` printed nothing). It is also byte-identical to `prereg-as-the-previous-review-read-it.json`: both hash to the digest on line 1, and the step-2 `diff` of their pretty-printed forms printed nothing. So nothing in the draft changed since review 3. What changed is code: 15 commits from `e63be402` to `COMMIT` = `4163754f38ac5b8729c008904b1f6dc03d4f6015`. `study/` is clean at `COMMIT` (`git status --short` prints nothing). I changed nothing in it.

## Threat model, restated

There are two adversaries:

- **The operator, once takes exist.** They hold the machines and every unpushed commit. They may edit, re-date, re-run, re-route or re-order any one record or attempt. They may choose among commits, beacon rounds and reviews, or change code, configuration or pins after the freeze. The checks bind them only through what is committed here, what the public mirror's push records witness, and what re-derives at HEAD.
- **The agent during a take.** Inside its container it may do anything its uid allows. It may use the one vendor host with the credential it was given, write its run tree and config mount, and start child processes, including a nested vendor CLI. It must not reach the study's files, graders or evidence, or make an untaken step look taken.

I make two corrections to the brief's statement:

1. **Some operator choices come before the takes.** The seed review and the beacon round are both fixed by the operator before any take. So the choice among reviews and among beacon rounds is in scope before the freeze, not only after it. The seed review is now bound to a registered round (review 3's m2, fixed). The choice of beacon round is bound by the push witness and the superseded list, with no bound on swaps (m3, carried).
2. **One operator choice comes after results.** Arm G is deferred. It starts only on a recorded owner go given after the arm A and arm O results exist (`deferred_arms.G`). That is an outcome-informed choice of whether to measure a cell. The draft names it, and says that a follow-up run is published as one chosen after seeing those results. So it is a named limitation, not a defect.

The brief's out-of-scope list stands: a complete, coherent fabrication across every ledger; what a vendor serves beyond what its client records; and the honesty of the machine and the runner. Records written only by the operator, such as the decision log, the witness record and the blindness records, rest on that same trust.

**Does the draft say this honestly?** Yes, with the gaps review 3 named and that are still open:

- the hot-reload gap is missing from the draft (m6), though the code's docstring now names it;
- arm A's account state is missing from the account-state residual (m5);
- two agent-caused driver stops are missing (m4);
- beacon swaps are unbounded and not printed (m3).

`limitations`, `box_residuals`, `round_4_limitations`, `not_poolable` and `predictions_rule` otherwise say what the checks bind. All predictions are null under the "no informed basis" rule, and the walks read before the freeze are disclosed. None of these sections says more than the code does.

## MAJOR findings

None.

### Review 3's MAJOR 1 is fixed

`fixture_walk.py` now reads each walk through its own harness's reader:

- `walk_harness`, `walk_files` and `walk_texts`, at `study/evals/gap-study-4/fixture_walk.py:977-1056`;
- codex and gemini walks go through `transcript_view.events`, which reads the turn streams the ledger names.

A walk counts as "unread", and so as a failure, in three cases:

- its reader yields no turn;
- its reader yields fewer tool calls than a parser-free count of its raw records (`read_problem`, `:1058`);
- its reader refuses it.

Any vendor envelope in a walk read as claude-code is refused. At `COMMIT` (athena file 13):

```
read, each walk through its own harness's reader: claude-code 277 walk(s), 673 turn(s), 3089 tool call(s); codex 74 walk(s), 167 turn(s), 470 tool call(s); gemini 36 walk(s), 50 turn(s), 2481 tool call(s)
evals/gap-study-4/rehearsals/w-o77/transcript.jsonl: excepted — 12 absolute path(s), {'run-tree': 9, 'excepted': 3}; read as codex: 2 turn(s), 19 tool call(s)
```

Review 3's example walk, w-o77, now reads 19 tool calls, and its scratch path `/tmp/sample-pca-header` needs a recorded exception.

**The 112 vendor exceptions.** These are `VENDOR_RECORDED_EXCEPTIONS`, at `fixture_walk.py:229-790`. Each is bound to its walk, its stream file, its line numbers and the sha256 of each line, with a class and a ruling. `_exception_for` (`:794`) applies an entry only when every naming line of every read file is a recorded line with those bytes. `stale_exception_problems` (`:836`) fails any entry that matches nothing. I read a sample of 15 entries. Each falls into one of these classes:

- the config mount `/opt/cfg`;
- the fixture's `/gpfs/home[/]<user>` placeholder;
- the agent's own `/tmp` scratch.

None is a checkout path. A ruled exception can only place a path that would otherwise be "elsewhere". A study path is still classed `study` and is a leak before any exception is consulted (`classify_path`, `:852`; `replay`, `:1087`).

## Other findings

### MINOR

**m10 (new). The path gate does not read Claude walks' sub-agent streams.**

For a claude-code walk, `walk_files` returns only `transcript.jsonl` (`fixture_walk.py:998`). `walk_texts` parses only that file (`:1036-1037`). The parser-free tool-call count also counts only that file's `tool_use` blocks (`recorded_counts`, `:1012`). So a sub-agent's own transcript, `subagents/agent-<id>.jsonl`, is neither read nor counted, and the "grades nothing" guard cannot see the shortfall. Two committed walks have one:

```
$ find rehearsals -path '*subagent*' -name 'agent-*.jsonl'
rehearsals/w260/subagents/agent-aed991169cdfd81f2.jsonl
rehearsals/w255/subagents/agent-a88acf31935b5eeaa.jsonl
$ grep -c '"tool_use"' rehearsals/w255/subagents/*.jsonl rehearsals/w260/subagents/*.jsonl
19   /   28
$ grep "w255\|w260" athena/13-fixture-walk-py-check.txt
.../w255/transcript.jsonl: clean — 38 absolute path(s), {'run-tree': 38}; read as claude-code: 5 turn(s), 20 tool call(s)
.../w260/transcript.jsonl: clean — 9 absolute path(s), {'run-tree': 9}; read as claude-code: 1 turn(s), 4 tool call(s)
$ grep -oE '/(Users|home|private|var|tmp|opt|etc)/[^"\\ ,;:)`'"'"'>]*' rehearsals/w255/subagents/*.jsonl rehearsals/w260/subagents/*.jsonl | grep -v '/tmp/run-' | sort | uniq -c
   2 .../w255/subagents/agent-a88acf31935b5eeaa.jsonl:/home[/]<user
   2 .../w260/subagents/agent-aed991169cdfd81f2.jsonl:/home[/]<user
```

The unread streams name `/home[/]<user`. That is line 67 of w255's sub-agent file and line 76 of w260's: a `cat` of `gars-env.sh`. Neither walk has an exception for it. So under the gate's own rule, both walks would read "unplaced", not "clean", if the gate read every stream the session wrote. I grepped both files for checkout-shaped strings (`/Users[/]`, `gap-study`, `evals/`, `prereg`, `graders`, `aegis`) and found 0 hits. So nothing has leaked; the gate just did not look.

The take checker does read sub-agent files (`check_take.py:3234-3254`), so takes are not affected.

I lean MINOR rather than MAJOR, for three reasons:

- the gate reads every arm's walks and grades 3,500+ tool calls;
- the gap covers 47 tool calls in 2 of 387 walks, and walks are never counted;
- the only unplaced path is the w142-class placeholder that already has 27 ruled entries.

**Fix:** add the copied sub-agent files to a claude-code walk's read files and to its raw tool-call count, then rule the two placeholder lines. That tightens the gate and changes no criterion or reading. It corrects the claim "every path each named is placed" for those two walks.

**Carried from review 3, unchanged at `COMMIT`.** I re-checked each one. The draft is byte-unchanged, and `batch.py`, `check_results.py`, `stats.py`, `result.py` and `order_beacon.py` are not in `git diff --stat e63be402 HEAD`.

- **m1.** A take of unknown phase that stopped can be re-run after its end state is seen, and the discarded attempt's reading is not published. The early return is still at `batch.py:512`.
- **m3.** Beacon swaps are unbounded (`order_beacon.py:238-250`, `history_problem`), and RESULT.md never prints them: `grep -c supersed result.py stats.py check_results.py` gives 0, 0, 0.
- **m4.** The settings-guard stop and the arm O/G config-census stop are missing from the agent-caused-routes limitation.
- **m5.** Arm A's account state, which a nested `claude` could change through the inherited token, is missing from the account-state residual.
- **m6.** The hot-reload gap is now named in `box/settings_guard.py:35-38`, but not in the draft: `grep -c "hot reload\|hot-reload\|reloads a settings" prereg-draft.json` gives 0.
- **m7.** The hashed codex `config.toml` template leaves out the per-take `[projects."<run tree>"]` trust table that `box/take_config.py` appends.
- **m8.** Table 6 (`stats.py:1209-1218`, `render_across`) still prints within-harness model rows and cross-harness agent-system rows under one heading, with columns `Harness | Model | Harness | Model`. Each row is labelled by family, and `check_families` keeps the families apart, so nothing is pooled. This is presentation only.

**Fixed since review 3.**

- **m2.** `freeze.registered_review_problem` (`freeze.py:1112-1162`) requires exactly one unvoided prefreeze row N. It also requires the session id that the row's introducing commit derives to appear in the report's committed blindness record.
- **m9.** `walk_pins.py` and `walk_regrade.py` now say what they compare and what they skip.

### NIT

- **n1–n4, n6, n7** (from review 3) stand. They cover:
  - the wording "re-tested at its first real walk";
  - legs i and ii not reading the register;
  - "in none of the three views";
  - the self-attested recheck machine;
  - lints that scan files, not rendered pages;
  - arm A's config mount not being censused.
- **n5** is partly folded: the `settings_guard.py` docstring and the `fixture_walk.py` usage lines now name round 4. I did not re-check the `rehearsals/README.md` lines.
- **n8 (new).** The path gate does not read codex's native rollout files (`rehearsals/w-o*/session/native-turn-*.jsonl`). These hold the harness's loaded context, including `/opt/cfg/skills/.system` 334 times. The code states this ("Not read, on either road: … the harness's own records", `fixture_walk.py:924-927`). `leak_grep.py` sweeps the loaded context through the checker's vendor reader. A grep of those files for checkout-shaped strings finds 0.
- **n9 (new).** The push-witness rule binds the registering commit and the last commit that changed the draft, not other code.
  - Beacon round 33536472 published at 2026-10-31T02:13:00Z. The fold3 commits from `1cb4ee64` on came after that.
  - Those commits touch only gates (`fixture_walk.py`, `lint_pooling.py`, tests and text). They do not touch the order function, whose sha256 the draft holds, nor `batch.py`, the graders or `routing.json`.
  - The freeze's own pins bind the code from the freeze on. So this window is narrow and today's use of it is benign. The draft could still say so.
- **n10 (new).** `lint_pooling.py` now leaves `review_kit/prefreeze-3.md` unscanned. The exemption is exact, bound to that file's sha256, and printed on every run. It is a minor widening of the lint, and an honest one.

### Read and found sound

- **Copy record (step 6).** `copy_manifest.py --check` passes: 847 files, 102 fragments, 22 identical, 29 edited, 796 new. I compared all 22 "identical" entries byte for byte with their sources: 0 differ. The `fold3-m1` fragment names each edit the diff shows, and I found no unnamed change in `git diff e63be402 HEAD`.
- **System under test.** `variants.PINNED_TREE` = 844a4ce0, and `git rev-parse 844a4ce0:gars` = `8a54e0f8…` = `check_take.GARS_TREE_SHA`.
- **Container, vendor arms, outcome and publication (steps 7–11).**
  - None of the box files, adapters, config templates, image locks, price table, routing markers or `routing.json` changed since review 3. The draft that hashes them is byte-unchanged.
  - `freeze.py --check` re-verifies the pins (853 paths) and legs i–iii, and passes at `COMMIT`.
  - So review 3's readings of these steps carry over, and I confirmed the gates that rest on them:
    - `routing.py --check` holds;
    - `probes4.py --check` grades 1,690 cells with 0 defects;
    - `result.py`, `stats.py`, `check_results.py`, `takes.py`, `costs.py`, `completeness.py` and `denials.py` each say plainly that they measured nothing. None prints a pass.
  - Arm G is deferred, and the freeze requires walk coverage only of the arms it runs: A at 18/18, 18/18 and 90/90, and O at 18/18 and 18/18.

## Step 3: the athena files

Every file names commit `4163754f38ac5b8729c008904b1f6dc03d4f6015`, which equals `COMMIT`. Together they cover:

- `run_checks.py` (01), which includes the battery and every lane's listed checks (530 of 530);
- each `freeze_rehearsal.COMMANDS` entry, run directly (02–17);
- `freeze.py --check` (18);
- the three legs (19).

| file | commit | last line |
|---|---|---|
| 01-run-checks-py-its-lines-24-at-a-time-by-the-remote-suite-s-b.txt | 4163754f | `run_checks: 530 of 530 commands passed` |
| 02-test-round4-py.txt | 4163754f | `OK (skipped=62)` (5918 tests) |
| 03-copy-manifest-py-check.txt | 4163754f | `ok: 847 files from 102 fragment(s) (…) … 8 frozen paths unchanged since 68ec902f63bf` |
| 04-tests-test-box-integration-py.txt | 4163754f | `OK` (61 tests) |
| 05-tests-test-pipeline-py.txt | 4163754f | `OK` (88 tests) |
| 06-probes4-py-check.txt | 4163754f | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| 07-build-draft-py-check.txt | 4163754f | `ok: the committed draft is what build_draft.py builds` |
| 08-leak-grep-py-check.txt | 4163754f | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| 09-holdout-py-check.txt | 4163754f | `OWED: holdout.py --check lives in private aegis (ruling C4); this rehearsal was given no --holdout-tool …` (exit 1; it names itself as not run, never as a pass) |
| 10-review-kit-rounds-py-check.txt | 4163754f | `ok: 3 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |
| 11-walk-register-py-check.txt | 4163754f | `ok: 387 registered walk(s), each with its folder, none counted` |
| 12-mode-binding-py-walks-check.txt | 4163754f | `36 of them are input-side only: their CLI writes no mode record, so the launch argv is what was checked, never a mode the session recorded.` |
| 13-fixture-walk-py-check.txt | 4163754f | `ok: 387 committed walk(s) graded, each read through its own harness's reader, none names this checkout and every path each named is placed; 41 by a recorded per-walk exception, printed above` (see m10) |
| 14-run-py-walks-check.txt | 4163754f | `run: 387 walk(s) regraded, every grade.json the regrade's bytes (313 graded, 74 pending documents that grade nothing yet); never counted` |
| 15-walk-regrade-py-check.txt | 4163754f | `walk_regrade: ok` (the line above it: `… 141 check.json file(s) carry no integer count to re-derive (not read)`) |
| 16-walk-plan-py-coverage-require-run-arms.txt | 4163754f | `ok: every required walk of the arms the freeze runs is covered` |
| 17-walk-pins-py-check.txt | 4163754f | `walk_pins: 387 registered walk(s) read; every one on the draft's version pins and image ids, its ledger naming the pinned gars tree (a walk records the pin, so this compares the pin with itself: …)` |
| 18-freeze-py-check.txt | 4163754f | `freeze: 847 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| 19-freeze-unrecorded-shapes-problem-prereg-draft-json-legs-i-ii.txt | 4163754f | `every leg holds` |

The only red is 09, and it names itself as owed and not run. Files 02 and 03 record operator-marker masking only. 13 also masks absolute paths and person names, which is consistent with a public record.

## Step 4: the light checks, run from `study/`

Every command below exited 0.

| command | tail of output |
|---|---|
| `python3 evals/gap-study-4/copy_manifest.py --check` | `ok: 847 files from 102 fragment(s) (…)` |
| `python3 evals/gap-study-4/freeze.py --check` | `… vendor legs i-iii: ok … take-order function: ok … prepare (dummy review, synthetic beacon reading): ok` / `freeze: 847 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| `(cd evals/gap-study-4 && python3 -c "… freeze.unrecorded_shapes_problem …")` | `every leg holds` |
| `build_draft.py --check` | `ok: the committed draft is what build_draft.py builds` |
| `leak_grep.py --check` | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| `probes4.py --check` | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| `routing.py --check` | `before-first-turn, last turn none (no turn ran) -> route rehearsal` |
| `contracts.py --check` | `every stored sentence is a byte substring of the blob it was pinned to` |
| `harness_bookkeeping.py --check` | `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini` |
| `denials.py --check` | `ok, having read 0 graded takes: none is committed yet, so nothing here is evidence about any denial. Not a pass.` |
| `completeness.py --check` | `completeness: no takes; no cells measured` |
| `takes.py --check` | `takes: no takes; no registration or outcome measured` |
| `costs.py --check` | `costs: no takes; no cost measured or written` |
| `stats.py --check` | `stats --check: no takes (0 results files); nothing was compared` |
| `intervals.py --check` | `gap-study intervals: PASS` |
| `result.py --check` | `result: no takes; no table measured or written` |
| `check_results.py --check` | `check_results: no takes; no frozen pins or publication measured` |
| `batch.py --check` | `batch: routing.json ready` |
| `python3 evals/gap-study-4/lint_language.py evals/gap-study-4/` | `clean — 217 input(s) scanned, 84 excused line(s) on record` |
| `python3 evals/gap-study-4/lint_pooling.py evals/gap-study-4/` | `clean — 216 file(s) and 0 commit(s) scanned, no excusal path` |
| `python3 evals/gap-study-4/prereg.py --status` | `This is a DRAFT. No take may run against it and no number may be graded from it. The walks are what turn it into the frozen file.` |
| `python3 evals/gap-study-4/review_kit/rounds.py --check` | `ok: 3 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |

`rounds.json` holds rows 1–3 at `COMMIT`, and this review's row is not in it. Under review 3's m2 fix, the freeze will refuse to seed from this report until row 4 and its blindness record are committed. That is the intended order.

## Findings

| # | finding | class | loosens / tightens | would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|---|
| m10 | The walk path gate does not read Claude sub-agent streams. Two walks (w255, w260; 47 tool calls) go unread, and their unread `/home[/]<user` placeholder would be unplaced under the gate's own rule. No checkout path is present. | MINOR (I lean MINOR, not MAJOR: 2 of 387 walks, walks never counted, no leak found) | tightens | No criterion or reading. It corrects the gate's claim "every path each named is placed" for two walks. |
| m1 | An unknown-phase take that stopped can be re-run after its end state is seen, and the discarded reading is not published (carried) | MINOR | tightens | No criterion. It could change a reading in a cell where this happens. |
| m3 | Beacon swaps are unbounded and not printed in RESULT.md (carried) | MINOR | tightens | No criterion or reading. It makes the order's provenance visible. |
| m4 | Two agent-caused driver stops are missing from the agent-caused-routes limitation (carried) | MINOR | tightens | Disclosure only |
| m5 | Arm A's account state is missing from the account-state residual (carried) | MINOR | tightens | Disclosure only |
| m6 | The hot-reload gap is named in code but not in the draft (carried) | MINOR | tightens | Disclosure only |
| m7 | The hashed codex template leaves out the per-take trust table (carried) | MINOR | tightens | No reading. It makes the hashed-bytes claim exact. |
| m8 | Table 6 mixes the model and agent-system kinds under one heading (carried) | MINOR | tightens | Presentation only, no count |
| n1 | "re-tested at its first real walk" overstates what the freeze runs (carried) | NIT | n/a | Wording only |
| n2 | Vendor legs i and ii do not read the walk register (carried) | NIT | n/a | No; today they agree with leg iii |
| n3 | "in none of the three views" is wrong for the failures view (carried) | NIT | n/a | Wording only |
| n4 | The recheck machine is self-attested (carried; already named) | NIT | n/a | No |
| n5 | Stale docs, partly folded (carried) | NIT | n/a | No |
| n6 | The lints do not scan rendered result pages (carried) | NIT | n/a | No |
| n7 | Arm A's config mount is not censused (carried) | NIT | n/a | No |
| n8 | Codex native rollout files are not read by the path gate. This is stated in code, and leak_grep covers loaded context. | NIT | n/a | No |
| n9 | The push witness binds the draft and the registering commit, not other code changed between beacon publication and freeze. Today only gates changed. | NIT | n/a | Disclosure only |
| n10 | `lint_pooling.py` exempts one review record, bound by its sha256 and printed on every run | NIT | n/a | No |

The table holds no MAJOR, so the ruling is DO FREEZE. Fixing m10 before the freeze is cheap and would make the walk gate's printed claim true for every stream. I recommend it, but it does not block.
