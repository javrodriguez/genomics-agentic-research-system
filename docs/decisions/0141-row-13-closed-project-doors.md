---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/tools/closed_output.py
  - gars/_system/tool_call.py
  - gars/_system/tools/registry.json
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/pilot_log.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - scripts/bring_home.py
  - scripts/unit_economics.py
  - docs/pilot/README.md
  - gars/tests/pilot_fixture.py
  - gars/tests/test_pilot_log.py
  - gars/tests/test_closed_project_outputs.py
  - gars/tests/test_bring_home.py
  - gars/tests/test_pilot_doors.py
  - tests/test_session_turns.py
  - tests/test_unit_economics.py
  - tests/pilot_emulation.py
  - docs/implementation/row_13_change_report.md
symptoms:
  - a sample name, a failure's detail or a path inside a non-public project in a typed call's output
  - a door tool reached on a closed project by its direct spelling
  - a typed call naming a file outside the workspace while a non-public project exists
  - an agent-written pilot-log row labelled human, or a typed minutes value
  - a re-run's failure text carried off the cluster in the bring-home paste
---
# Row 13 step B: the closed-project doors, the pilot-log writer and bring_home

## Context

Row 13's pilot 1 runs the DE stage of a non-public analysis. Under
[0107](0107-pg-nonpublic-projects-closed-to-reads.md) a guarded agent session can run no typed
tool on a closed project (`CLOSED_PROJECT_DOORS` was `()`), and 0107's item 11 names row 13 as
the row that adds doors "with output filtering". Step A
([0140](0140-row-13-pilot-instruments.md)) built the instruments that read the pilot's
artifacts; this step builds what the pilot needs to run: the doors, the pilot log's writer, and
the one path by which anything leaves the cluster.

**The owner's words** (relayed by the lane and confirmed by the owner; nothing else here is the
owner's): "§21 Q4: the spec default applies (`deidentified_under_agreement`; only `public`
enters a hosted-model prompt)." and "… a guarded agent can't read non-public project files, so
row 13 must run through typed calls that return only summaries (0107), unless [the owner]
reclassifies in his own words."

**Everything else in this record is the lane's specification** under the owner's standing
delegation of 23 Sep 2026: the design D1 (the writer), D5 (the doors), D6 (bring_home) and D8
(the threat model), and the lane's rulings D-i to D-vi, confirmed by the lane's coordinator on
25 Sep 2026. None of it is the owner's ruling.

**The producer and the review.** This step was produced by a headless Claude Code context
(Claude Opus 5.5) because the lane's usual producer is unavailable, and it is reviewed by a
separate fresh Claude Opus 5.5 context from a blind kit. Producer and reviewer are the same model
family, so the review's independence rests on a fresh context and a blind kit, not on model
diversity (the 0009/0013/0014 precedent).

## Decision

### D1 — the pilot log's writer (`gars/_system/pilot_log.py`)

The only writer of `projects/<title>/pilot/pilot1_log.csv` (0140 D1's format: the §19 columns
under one `# gars-pilot-log v1 nonce=<32 hex>` line, no free-text column).

- `begin --log <path> --stage S --action A --reason R` creates the log (header, fresh nonce) and
  its sidecar `<log>.open.json` (the same nonce, the open spans, the imported sub-stages) when
  both are absent, records an open span with its launching actor and prints
  `begin: span <16 hex>; actor <actor>`.
- `end --log <path> <span>` appends one row: `ts` is the span's start, `minutes` the difference of
  two readings of the clock, rounded half-up once to two decimals. No option types a minute.
  `abort` appends nothing: a forgotten span is dropped, never back-filled; a break is `abort` of
  every open span, then a new `begin`. Both are allowed only to the span's launching actor, else
  `refused: actor_mismatch`.
- `import-tool --log <path> --manifest <manifest.json>` (human only; no registry entry) appends
  two `tool` rows from the executor's slurm record: `wait_queue` (Start − Submit) and `compute`
  (sacct `Elapsed`), at the sub-stage the wrapper names (`rnaseq-de` → `02_02_de`,
  `nfcore-rnaseq-wrapper` → `02_01_counts`), reason `other`. A submission (its
  `idempotency_key`) is imported once.
- `check --log <path>` prints `rows: <n>; human: <h>; agent: <a>; tool: <t>; open spans: <o>;
  nonce: ok` and exits 1 while a span is open or a protocol stage (`02_02_de`, `rerun`) has no
  row. Every verb first validates the whole log: header, columns, every row in the vocabulary, the
  log and the sidecar present together and their nonces equal. A log or sidecar present without
  the other is refused (`sidecar_missing`, `log_missing`), so neither can be pre-created by hand.
- Every refusal is `refused: <code>` on stdout, exit 2, and quotes no input. The vocabulary is
  embedded and bound to `docs/pilot/pilot_log_vocabulary.json` by a drift test.
- **The actor is a launch-time fact.** Each `pilot_log.*` registry entry's argv carries the fixed
  token `--launched-by-dispatcher`, absent from its `input_schema` (`additionalProperties:
  false`) and its `cli` map, so a call's JSON can neither supply nor remove it. Token present:
  `agent`; absent: `human`. Guard addition 3 refuses the direct spelling of `pilot_log.py` in an
  agent session, which is what makes the binding hold. The `log` argument must match
  `projects/<name>/pilot/pilot1_log.csv`.
- **The log folder is machine-owned:** `READ_ONLY` gains `"projects/*/pilot/*"`, and
  `settings.json` its `Edit(…)`/`Write(…)` pair. Only the writer, outside the guard's view,
  writes there.

### D5 — the closed-project doors (`gars/_system/tools/closed_output.py`)

One module holds both halves, and the dispatcher and `scripts/bring_home.py` import it:

- `closed(path_args, workspace, cwd)` judges a call with 0107's reader, imported from
  `guard_hook.py` (`closed_projects`, `closed_hit`, `_bases`, `_forms`, `_inside`,
  `declared_sources`, `inside_declared`, `_raw_entries`, `_strings`), never copied. Every string
  of the call's JSON is judged, recursively (ruling D-v), on both bases (the session cwd and the
  workspace root) and both forms (normalized and resolved). A string is a path when it holds a
  separator or names something that exists on either base; a bare word that names nothing (an
  assay, a type, a verb, a model id) is not. Fail-closed, while any non-public project exists:
  a path inside a closed project, or onto the resolved target of one of its `00_data/*/raw`
  links, makes the call that project's (filtered); a path outside the workspace is refused
  `path_outside_workspace`; a closed project named with any path outside it (another project,
  `_system/`, an ancestor, a second closed project) is refused `path_outside_closed_project`. A
  path whose resolved form lies inside a source `declared_sources` validates is public data and
  neither (ruling D-iv). A `~` path is refused. With no non-public project, nothing changes.
- `filter_output(tool, stdout, stderr, exit_code)` applies the tool's registry `closed_output`
  keep-list. Only listed keys survive, each through its rule; every other value becomes
  `withheld: non-public project (0141)`; stdout that does not parse becomes
  `{"withheld": true, "exit_code": <n>}`; stderr becomes its line count. A failure entry keeps its
  code (`check`) and never its detail.
- `tool_call.py` refuses before running when `closed` refuses, and filters after output
  validation when the call is closed. A declared registration (0107's opening, judged by
  `declared_registration`) is neither refused nor filtered.

**Ruling D-i (the lane's): the doors.** `CLOSED_PROJECT_DOORS` is exactly these eleven, each
justified by what its output may carry after `filter_output`:

| Door | Keep-list: what the agent sees |
|---|---|
| `resolve_artifact` | `ok`; `missing` types (reasons withheld); per type its `substage` and a `resolved` path only in the fixed sub-stage layout |
| `rnaseq_de.check` | `ok`; failure codes; `wrote` (fixed file names) |
| `rnaseq_de.prepare` | `ok`; failure codes; `wrote` (fixed file names) |
| `rnaseq_de.collect` | `ok`; failure codes; `outputs[].type/.role`; `template_version`; `model`; never `history_entry` |
| `rnaseq_de.summary` | its aggregates: `genes_tested`, `padj_lt_0.05` up/down, `padj_lt_0.1`, `na_padj`, `samples_in_design`, `gate` codes, `status`, `ok`, failure codes |
| `executor.submit` | `ok`, `job_id`, `state` (closed prefix), `terminal`, `refusal` codes |
| `executor.status` | `ok`, `job_id`, `state` (closed prefix), `terminal`, `refusal` codes |
| `pilot_log.begin` | its line in the closed pilot-log vocabulary (span id, actor) or a refusal code |
| `pilot_log.end` | its line (span id, computed minutes) or a refusal code |
| `pilot_log.abort` | its line (span id) or a refusal code |
| `pilot_log.check` | its counts line and failed-check line, or a refusal code |

`executor.cancel` (its keep-list is set, but it is not a door), every `configure.*`,
`stage01_samplesheet`, `stage03_analysis.*` and every other tool stay refused on a closed
project; the human runs them. Every other registered tool's keep-list is `[]`: fully withheld.

**Ruling D-ii (the lane's): a door is the dispatcher spelling only.** Guard additions 1 to 3 run
before 0107's door `return` in `closed_bash_refusal`, so a door tool's direct spelling on a
closed project is refused. A door call through the dispatcher that names a path outside the
workspace, or outside its closed project, passes the guard and is refused by `tool_call.py`.

**Ruling D-iii (the lane's; the coordinator's condition): summaries only.** Every door's output
passes `filter_output` and carries only codes, counts, fixed file names, fixed-layout `resolved`
paths, the pilot-log vocabulary and the summary's aggregates.

**Rulings D-iv and D-v** are stated in `closed` above.

**Two implementation choices, named.** (1) D5 says `rnaseq_de.summary` keeps "all". Its
keep-list names every key it prints, so a key the wrapper might grow later is withheld, not
passed. (2) The `pilot_log.*` keep-list `*` ("all, closed vocabulary") keeps each stdout line
that has one of the writer's fixed formats, and withholds and counts any other line.

**Guard additions (exactly four) and the one changed line**, in `guard_hook.py`, beside 0107's
closed-project check:

1. the direct spelling of a registered helper (not a `fs.*` read) whose path argument is closed
   under `closed()`, or run with the session cwd inside a closed project, is refused, naming 0107,
   0141 and the dispatcher spelling;
2. the direct spelling of a registered helper naming a path outside the workspace while a
   non-public project exists is refused (`path_outside_workspace`); a declared registration is
   judged by 0107 alone;
3. the direct spelling of `pilot_log.py` is refused in every agent session;
4. `READ_ONLY` gains `"projects/*/pilot/*"` (with the `settings.json` pair);

and `CLOSED_PROJECT_DOORS` changes from `()` to the eleven names above.

### D6 — bring_home (`scripts/bring_home.py`)

Runs on the cluster, stdlib only. For each input it writes `== <kind> sha256=<hex of the raw
file> ==` and only its keep-listed lines, from the line table in `closed_output.py`
(`BRING_HOME`, `RERUN_REASONS`, `PATH_KINDS`, `pilot_lines`, `SUMMARY_KEYS`): the re-run console
and `comparison.json` (reproduction, graded counts, each artifact's path-kind, mode, match,
metric and value, each run's job and match, and its reason cut to its closed prefix, the text
before the first `:`, which must be one of `rerun_check.py`'s own reasons (bound by a drift
test), else `withheld`); `manifest_check`'s group lines (names from the manifest schema) and
summary lines, with `ERROR` lines as `ERROR withheld`; the pilot log's rows and its `check`
line (a value outside the vocabulary exits 2); `rerun_diff`'s and `session_turns`' fixed lines;
the summary's aggregates and `quantity samples_in_design <n>`; row 8B's allowlisted evidence
fields and `quantity cpu_hours <backend> <h>` from a `COMPLETED` record. Every other line is
withheld and counted, and the file ends `bring-home: <k> sections; withheld lines: <w>`. A
missing input exits 2 and writes nothing. The owner pastes only this file, after `sha256sum`
of it; the raw files stay on the cluster.

### D8 — the threat model (the lane's specification, verbatim)

Covered — a producer agent session whose every tool call passes the guard must not be able to:
- receive sample-level content of a non-public project through any registered tool's output (the filter, swept over every tool), or through a path outside the project (refused), or bypass either by a direct spelling (refused);
- write, pre-create, alter, end or abort a `human` pilot-log span or row, type a `minutes` value, or put free text in the log;
- cause any HPC output to reach Glitch except through `bring_home.py`'s keep-lists.
Not covered (named in 0141/0143): a tool with no keep-list is fully withheld (safe, unhelpful); the SessionStart hook's prints (0107 residual 2; the runbook requires a generic title and HISTORY lines); anything the human types or pastes into the agent session; a human writing `agent` rows; closed data a human copies inside the workspace outside `projects/` (0107 residual 9, narrowed but not closed); a forgotten human span with no human turn in it (D4b); the truth of the baseline; the scientific adequacy of the summary thresholds.

### Carried from step A (ruling D-vi, the lane's)

- **n1:** a test pins that a human turn outside the session window gets no attention interval.
- **n2:** `unit_economics.py` refuses a line starting `human turns:` that is not session_turns'
  shape (`quantity_malformed`, exit 2), where it was counted and ignored.
- **n5, the lane's rulings (the step A producer's three readings of L7, confirmed):** a human
  turn outside the window counts as a turn and adds no minute; a transcript with no main-thread
  record has an empty window and 0.00 minutes, printed with `human turns: 0`; `isMeta` and
  `isCompactSummary` must be booleans on assistant records too.

### R-042: behaviour that changes

Each item names the test the new code passes and the code at `e589ce8` does not.

1. **Eleven tools open on a closed project through the dispatcher**, with filtered output
   (`test_pilot_doors.test_dispatcher_spelling_allowed_on_closed`,
   `test_closed_project_outputs.test_door_keep_lists`). A door called through the dispatcher from
   a session cwd inside a closed project is no longer refused by the guard; the dispatcher judges
   its paths from that cwd too.
2. **A door's direct spelling is refused with 0141's message** (it was refused by 0107's)
   (`test_pilot_doors.test_direct_spelling_refused_on_closed`).
3. **No path outside the workspace while a non-public project exists**, through the dispatcher
   and by direct spelling, on any project, public ones included; a declared-public folder
   excepted (`test_pilot_doors.test_dispatcher_refuses_outside_paths`,
   `test_bare_outside_workspace_refused_by_addition_2`,
   `test_declared_source_is_not_outside`,
   `test_closed_project_outputs.test_outside_paths_refused_with_named_codes`).
4. **A closed project named with a path outside it is refused**
   (`path_outside_closed_project`; the same tests).
5. **A raw link's target counts as its closed project**
   (`test_closed_project_outputs.test_raw_link_target_is_the_closed_project`).
6. **Every dispatcher call on a closed project is filtered**, non-doors fully withheld (as a
   human running `tool_call.py` directly would see it too)
   (`test_closed_project_outputs.test_marker_absent_from_every_tool`).
7. **The pilot folder is machine-owned**: Write/Edit there is refused, on every project
   (`test_pilot_log.test_guard_refuses_writes_and_the_direct_spelling`).
8. **`pilot_log.py` exists and its direct spelling is refused**; four `pilot_log.*` entries and
   `rnaseq_de.summary` join the registry (`test_pilot_log`, whole module).
9. **`rnaseq_de.py summary`** is a new verb (`test_door_keep_lists`).
10. **`unit_economics.py` refuses a malformed `human turns:` line** (n2;
    `test_unit_economics.test_quantity_lines_canonical_or_refused`).
11. **Unchanged:** with no non-public project in the workspace the dispatcher's output is
    byte-identical to BASE's (`test_closed_project_outputs.test_public_output_byte_identical_to_base`,
    which runs `e589ce8`'s `_system/` beside this one on the same workspace).
12. **Follow-up, not changed here:** the stage 01–03 contracts still describe in-project agent
    reads (0107 item 11: stage 02's config, OUTPUTS and STATUS routing, the `HISTORY.md` appends
    after a Read). On a closed project those reads stay refused; the contracts' prose is a named
    follow-up.
13. **`test_nonpublic_read_block.py`** asserts 0107's empty door list; four of its methods go red
    under ruling D-i and are raised for a ruling in the change report (that file is outside this
    step's bounds).

## What this does not close

- **NOT met: the pilot.** No pilot has run; every number is a synthetic fixture with hourly
  value 1. Row 13's exit ("human-touch minutes measured; re-run diff explained") is open.
- **The D8 "not covered" list above**, each NOT met.
- **The path rule is lexical plus existence.** A bare word that names nothing on either base is
  not judged as a path; a tool that turns such a word into a path later (none of the eleven doors
  does) would escape `closed()`. A file created between the judgement and the run is not seen.
- **A human's direct run is unguarded.** The human runs `tool_call.py` or a helper in their own
  terminal; the filter applies to a `tool_call.py` run on a closed project whoever runs it, and
  not at all to a helper run directly.
- **The token binds the actor only for agents.** A human can run the writer with the token and
  write `agent` rows (trusted, the 0024 `--model` shape). The log's truth is the clock's and the
  writer's; a clock set wrong is not detected.
- **`import-tool` reads only slurm records**; a local run has no sacct record and is refused.
- **The stage 01–03 contract prose** (R-042 item 12) and **`test_nonpublic_read_block.py`'s four
  methods** (item 13).
- **The doors' output was swept with planted markers on fixtures only.** A real wrapper message
  of a shape not seen here reaches the agent only as a code, by construction of the keep-lists,
  but that is not measured on real data.
- **Not executed on Python 3.6.8**; the new code parses under `feature_version=(3, 6)` and ran
  on 3.8.2 and 3.13.2.

Records 0142 and 0143 are the owner's; 0144 is Glitch's delegated approval of this step's
protected changes. This step writes none of them.

## Test

`python3 gars/tests/test_pilot_log.py` (`EXIT pilot log (fixture): launch-bound actor`),
`python3 gars/tests/test_closed_project_outputs.py` (`EXIT closed outputs (fixture): marker absent
from every tool`), `python3 gars/tests/test_bring_home.py` (`EXIT bring home (fixture): detail
withheld`), `python3 gars/tests/test_pilot_doors.py` (`EXIT pilot doors (fixture): dispatcher
allowed on closed`). They are red at `e589ce8` and at step A's `9220877` and green here. Fifteen
planted faults go red (the change report, section "Step B"): the filter skipped for one tool; a
keep-list widened to a failure detail; to `history_entry`; the outside-path refusal removed; a
guard refusal removed; the `READ_ONLY` pilot line removed; the actor taken from an input; end
allowed across actors; the nonce check removed; bring_home passing a reason tail; a door echoing
raw stdout; a door reached by its direct spelling; the doors widened by one non-door tool; D-iv's
exemption removed; D-iv's exemption widened to any outside path.

## Status

Standing. Implemented on `build/gars-row-13-pilot`; subject to the fresh-context review named
above and to 0144's delegated approval of the protected changes. Not approved or merged by its
producer. Row 13's exit is not met.

## Date

2026-09-25
