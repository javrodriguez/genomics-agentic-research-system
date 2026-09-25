---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - .gitignore
  - gars/tests/test_nonpublic_read_block.py
  - gars/tests/test_protected_paths.py
symptoms:
  - a guarded agent session can read a non-public project's samples.csv, files.csv, samplesheets or outputs
  - a typed tool run on a deidentified project prints its contents into a hosted-model prompt
  - a guarded agent can choose a project's data class by running finalize --data-class public
---
# Non-public projects are closed to a guarded session; a human declares public data

## Context

Spec §21 Q4's default (spec line 452, with §6.1 R-060 to R-063 at line 138) is that only
data_class `public` enters a hosted-model prompt. §7.3 (R-074, line 171) makes sending data to a
third party, a hosted model included, approval-gated for every class but `public`. Row 8's
planning (its ruling 3) sent the enforcement to a read block in `gars/_system/guard_hook.py`.

At the base (public main `0754ec6`, which carries row 6's `dataset.tsv`
([0095](0095-row-6-manifest-groups-and-applicability.md),
[0096](0096-row-6-collect-time-manifest-r042.md),
[0099](0099-row-6-delegated-approval-of-protected-changes.md)), item 1 of this lane
([0105](0105-rc-restore-log-reader-reads-the-table.md)) and row 8 step B
([0100](0100-row-8-data-handling.md), [0102](0102-row-8-venue-policy-and-backend-bench.md),
[0104](0104-row-8-delegated-approval-of-protected-changes.md))), nothing stops a guarded agent
session from reading a non-public project's `samples.csv`, `files.csv`, samplesheets or outputs,
or from running a typed tool that prints them. Row 13 (pilot 1, non-public data) must start
behind a mechanical line, not a prose one.

The rule's purpose: a guarded agent never **chooses** a project's data class, and non-public data
never enters a hosted-model prompt. Carrying out a class that a human-written, protected
declaration already names is not choosing.

**What the base writes and reads** (re-derived at `0754ec6` with
`git grep -n "dataset.tsv" -- gars/_system scripts`):

- the format: `00_data/dataset.tsv`, tab-separated, LF, one header and one data row, eight
  columns `data_class purpose agreement_ref input_data_location permitted_backends
  provider_exposure retention expiry` (`DATASET_BASE_FIELDS + DATASET_ROUTE_FIELDS` in
  `stage00_register.py`); a row-6-era four-column file is migrated in place by
  `write_dataset_record`, so a reader meets both shapes;
- writers: `stage00_register.write_dataset_record` (called by `finalize`, the agent's use of which
  Q8 below governs); `scripts/backend_bench.py`, which writes a fixed `public`/`fixture` row into
  a project it creates itself (unregistered; residual 13); and `gars/tests/support.py`
  `write_fixture_dataset` (tests only; `test_venue_policy.py` also calls the writer directly);
- readers: `wrapperlib.dataset_record` (used by `executorlib` and the manifest facts),
  `venue_policy.py`, `stage00_register.dataset_values` (the immutability lock),
  `scripts/rerun_check.py` through `wrapperlib`, and now the guard's own parser.

Q8's completeness rests on `_system/` being `READ_ONLY`: an agent cannot add a writer there.

## Decision

The rulings in this record are the lane's, under the owner's standing delegation of
23 Sep 2026; none of its sentences is the owner's.

### The rule

1. **Closed by default.** A project is closed unless its `00_data/dataset.tsv` is a regular
   file (not a symlink, not reached through a linked `00_data/`) whose header names `data_class`
   exactly once and whose every data row, with a cell count equal to the header's, reads exactly
   `public` in that column: no casefolding, no stripping. CRLF, an empty file, zero data rows,
   mixed rows, a missing or unreadable file all mean closed; what the guard cannot judge, it
   refuses. The column is located by header name, so the eight-column and the migrated
   four-column shapes both read. The parser is local to the guard (stdlib, Python 3.6); it does
   not import the laxer `wrapperlib.dataset_record`, and the drift test binds it to the writer.
2. **Every registered tool is refused on a closed project.** A Bash call of any registered
   tool, bare or through `_system/tool_call.py`, is refused when any swept token reaches a
   closed project or the session cwd lies inside one, unless (a) the tool's name is on
   `CLOSED_PROJECT_DOORS`, or (b) the call is a declared registration (point 4), and then only
   for hits on its target project. Read and the `fs.*` read tools may still read exactly
   `00_data/dataset.tsv` and every file named exactly `STATUS` under the project (the sub-stage
   lifecycle files `wrapperlib.write_status` writes, R-151). No other tool gets that exemption.
3. **The declaration.** `gars/data_sources.tsv`, written only by a human: protected by one new
   `READ_ONLY` line `"data_sources.tsv"` and the matching `Edit`/`Write` denies in
   `gars/.claude/settings.json`; `check_write_tool` refuses it with its own message; one
   `.gitignore` line `gars/data_sources.tsv` keeps it out of git (it names machine paths).
   Format, tab-separated, LF: the header `source data_class declared_by`; each row an absolute
   path to an existing directory, compared on its realpath and normpath, casefolded, at path
   boundaries; `data_class` exactly `public` (declarations are public-only, because registering
   data prints its file and sample names into the prompt, which is the §21 Q4 line itself);
   `declared_by` a non-empty free-text label, never checked and never an authorization. A
   source that equals or contains the workspace root, or equals, contains or lies inside
   `projects/`, any project, `_system/`, `_references/`, `_templates/`, `.claude/` or the
   repository's `.gars-approvals/`, invalidates the whole file; so do a relative source, a
   source holding `* ? [ ] { } ( )` or starting with `~`, a missing directory, a duplicated
   source, two nested sources, a wrong header, CR bytes, a symlinked file, a non-`public` class
   or an empty label. A missing or invalid file declares nothing. A refusal names the failed
   rule, never the file's contents. A source may lie elsewhere inside the repository or the
   workspace (an `inbox/` folder, say), or outside it.
4. **Declared registration, the one opening.** A project is registrable only when it has no
   `dataset.tsv` and holds nothing beyond `create`'s stamp (`CREATE_STAMP`, derived from the real
   `create` and drift-tested) plus entries directly under `00_data/<assay>/raw/`. On a
   registrable project P a guarded agent may run exactly: `inspect --source S` when S's realpath
   lies inside a declared source on every base × form; `link --project P --assay A --source S`
   without `--force` when S lies inside a declared source on every base × form, every top-level
   entry of S and every entry already under `P/00_data/*/raw/` resolves inside one;
   `finalize --project P --data-class public …` when P holds at least one raw entry and every
   one resolves inside a declared source. A dangling entry counts as undeclared. `sample_dir`
   entries are judged by their own realpath; their contents are not walked (residual 14). The
   exemption covers only hits on P through its `--project` token or a cwd inside P; any other
   token that reaches a closed project still refuses, and S must reach no project at all. Any
   other class, `--force`, a non-registrable project, or a `SHELL_GLOB`/`~` token in the
   project, source or class argument is refused. Outside a declared registration, the agent's
   `inspect` and `link` are refused (link on every project, public ones included); stage 00 on
   undeclared data is human-run.
5. **Q8.** Only a human, or a protected declaration, supplies `public`. The agent's `finalize`
   whose class is `public` after casefolding and stripping is refused unless it is a declared
   registration or the project already reads public on every base × form (a same-value re-run).
   The message names §21 Q4 ("classifying data is the owner's"), 0107 and the way out: the human
   runs `finalize --data-class public` in their own terminal, or declares the source in
   `gars/data_sources.tsv`. `create`, `assays` and the path-free `configure` calls stay allowed.

**The sweep.** Every token after the executable, and every string value of a dispatcher call's
JSON (recursively), is judged as the token itself, with leading `-` stripped, as the part after
the first `=`, and for a single-dash cluster as every suffix after each letter. Each candidate is
resolved against the session cwd and the workspace root, in its normalized and resolved forms,
and compared casefolded at path boundaries (`projects/pilot-2` is not inside `projects/pilot`).
A candidate holding a `SHELL_GLOB` character is also judged by its static prefix, recursively,
from the session cwd, where the shell expands it; a candidate starting with `~` is refused. The
recursive (ancestor) rule covers Grep, Glob, `fs.search`, `fs.inspect`, `fs.find`, a recursive
`fs.list`, and every `SHELL_GLOB` candidate; for other tools an ancestor token alone does not
refuse. Before any of this, every token is scanned for `--pre`, `--pre=…`, `--pre-glob`,
`--pre-glob=…` and refused with its own message citing R-092 and 0107.

**Doors.** `CLOSED_PROJECT_DOORS` is empty in this lane. Row 13 adds each door only for a tool
whose output passes its keep-list filter; its `closed_output.py` imports these helpers
(`static_prefix`, `project_is_public`, `closed_projects`, `closed_hit`, `declared_sources`,
`inside_declared`, `registrable`, `declared_registration`, `first_public_classification`) rather
than copying them.

**Why this file.** Not `benchmarks/tasks/*.yaml`: they are not `READ_ONLY` and they name remote
profiles. Not `_references/`: it ships with the template to every user. The `.gitignore` line
covers the repository checkout only; a live workspace kept outside the repository must ignore
the file itself. `READ_ONLY`'s header comment ("the template ships them, `git pull` updates
them") does not describe this file, which is machine-local, and the lane's rules forbid editing
that comment in this change; the dedicated refusal message says what the file is instead.

### Channels

| Channel | Checked token(s) | Recursive? | Cannot see |
|---|---|---|---|
| Read | `file_path` | no | — |
| Grep | `path` (else cwd) | yes | links it follows below the root |
| Glob | `path` (else cwd) + `static_prefix(pattern)` | yes | links followed below the root |
| Bash `cat head tail wc stat shasum` | the sweep | no | a file named inside another file |
| Bash `grep rg find` | the sweep | yes | links followed below the root |
| Bash `ls` | the sweep | with `R`/`--recursive` | as above when recursive |
| Any other registered tool, bare or dispatcher | the sweep + the cwd | no | what it enumerates from an ancestor; its printed output; free path arguments outside `projects/` (residual 17) |
| stage 00 `inspect`/`link`/`finalize` | points 4-5 | — | links a human placed inside a declared folder (residual 14) |
| Any `SHELL_GLOB` token | static prefix | always | expansions not modelled (residual 5) |
| Any `~` token | refused | — | — |

### Threat model

Covered: a producer or reviewer agent session whose every tool call passes this hook. It must
not be able to:

- read, list or search the contents of a closed project through Read, Glob, Grep or any
  registered Bash read command, in either Bash spelling;
- run any registered typed tool on a closed project, except a door and a declared registration
  on its own target;
- get there through `..`, a symlink, a case variant, the dispatcher's root-relative spelling, an
  option-attached file name (a single-dash cluster included), the modelled shell-expansion forms,
  a `~` path, or a recursive search from an ancestor;
- choose a project's data class: write `dataset.tsv` (row 6's `READ_ONLY` entry, bound by a
  test), write `data_sources.tsv` (the new `READ_ONLY` entry, bound by a test), or run `finalize`
  with a class that neither a human nor a valid declaration supplied (the every-tool rule,
  point 4 and Q8);
- inspect or link data that no declaration names public.

### R-042: behaviour that changes

1. Stage 00 on a project with no `dataset.tsv` is open to a guarded agent only for sources a
   human declared `public` in `gars/data_sources.tsv`; for every other source (all non-public
   data, row 13's pilot included) a human runs `inspect`, `link` and `finalize`. `create`,
   `assays` and path-free `configure` calls stay open. The agent's `link` is refused on every
   project outside a declared registration.
2. Every project with no `dataset.tsv` is closed. The lane's census of its own working copy on
   25 Sep: 36 projects, 0 with `dataset.tsv`, 36 closed. This repository's `gars/projects/` holds
   none.
3. The suite's own positive control (`test_normal_project_edit_positive_control`, moved to a root
   with no `projects/`), and GARS's R-164 pre-push gate in any working copy that holds a closed
   project.
4. Root-level searching is refused while any closed project exists. B1's cost: a regex holding
   `* ? [ ] { } ( )` searched from an ancestor of a closed project is refused, the dispatcher's
   JSON included; so is any registered call whose argument holds one of those characters or
   starts with `~` while the cwd is an ancestor of a closed project, for example a title with
   parentheses, a `--sample-id-pattern` regex, or a `configure apply --formula '~ condition'`
   (the default formula, used when `--formula` is omitted, is unaffected).
5. The stage 00 contract's bounded voice is refused for a closed project.
6. Editing `_config/<assay>.yaml` in a closed project is refused in practice (Edit needs a prior
   Read).
7. Q8: a human, or a declaration, supplies `public`.
8. The Gap Study harnesses open sessions at the checkout root (no `.claude/`), so the hook does
   not load there; a future guarded round would need a public `dataset.tsv` from its fixture
   generator, or a declaration.
9. CI and a fresh clone have no projects, so fresh-clone checks pass; the lane proves the gate
   separately in a working copy that holds live projects.
10. Agent-driven workflows the lane enumerated on 25 Sep at the base: the stage 00 contract
    (`gars/00_initialize_project/CONTEXT.md`, create → inspect → link → finalize) for a guarded
    Claude Code session; row 2's B4/B5 scored sessions (its driver runs sessions rooted at
    `gars/`, so the hook loads) for its bulk tasks, which at the base have no local raw folder,
    so they need row 2 to stage one and declare it. Not affected: every `evals/` harness that
    launches `claude -p` (it opens at the checkout root), fixture generators and controls
    (direct calls), `evals/run.py`/`bench.py` (graders), `evals/review-faults` (its own kit
    settings), the demo (replayed traces; its live lane is a server subprocess with no Claude
    Code hook), and the suite (synthetic payloads).
11. Stages 01-03 on a closed project: the contracts' in-project reads (stage 01's design and
    samplesheet, stage 02's config, OUTPUTS and STATUS routing, stage 03's plan and inputs),
    every `HISTORY.md` append that needs a prior Read, and every typed stage 01-03 tool are
    refused. On a non-public project the agent works only through doors, and there are none yet;
    row 13 adds them with output filtering, and must be planned that way, or the owner
    reclassifies the project in their own words.

### Rulings (the lane, under the owner's standing delegation of 23 Sep 2026)

- **Q3.** `rg --pre` and `--pre-glob` are refused by their own check, in every token, before the
  closed-project check.
- **Q4 to Q7.** The lane's rulings Q4 to Q7 are carried by this record's rule as the lane's
  binding specification states it (points 1 to 5, the sweep and the channels); this record does
  not restate them one by one.
- **Q8.** Only a human, or a protected declaration, supplies `public` (point 5).
- **B1.** The `SHELL_GLOB` rule applies to every candidate in both spellings, one rule, and its
  cost is R-042 item 4.
- **The 25 Sep every-tool ruling.** Every registered tool, not only the `fs.*` reads, is refused
  on a closed project (point 2).
- **Amendment 1 and its review-round-3 fixes.** The human-declared registration opening for
  public data (points 3 and 4), as the lane's specification states it after its round-3 fixes.

### Row 6 dependency

The class flip is closed by row 6's `READ_ONLY` line `projects/*/00_data/dataset.tsv` and its
settings denies, unchanged here. A test binds it: Write and Edit on a closed project's
`dataset.tsv` are refused by that line, and a Bash `tee` into it is refused by the transport
(`unregistered helper`), not by `READ_ONLY`, which mutation P10 shows.

### Row 4 follow-ups

A per-tool flag allowlist; the tilde R-073 gap at `dc6a72a`; per-helper output rules; widening
the hook matcher; a Bash transport that refuses unquoted metacharacters; residual 17's
per-argument path rule (rows 4 and 13).

## What this does not close

Each item below is NOT met.

1. **Typed helpers' output.** A door's output, and a non-`fs` tool given only an ancestor path
   that enumerates projects itself.
2. **The SessionStart hook.** `_system/session_state.sh` runs `project_state.py`, which prints
   into every session, per project: its name, the CONTEXT.md table fields `Template version` and
   `Created`, its assay directories, each assay's design state with the `samples.csv` row count,
   samplesheet presence, the `<REQUIRED>` key names still in `_config/<assay>.yaml`, each
   sub-stage's STATUS first line and OUTPUTS.tsv artifact types, each custom analysis's STATUS
   first line, and the last HISTORY.md entry headers (confirmed by reading `project_state.py`).
   `projects/_index.md`, which the same hook rebuilds and which Read may still read, carries the
   project name, template version, assay, design and samplesheet state and the furthest
   sub-stage's STATUS word.
3. **Links followed below a search root** (`grep -R`, `rg -L`, `find -L`, and the harness's own
   Grep and Glob if they follow links).
4. **Files named inside files** (`shasum -c <list>`): names and hash agreement, not contents.
5. **Unmodelled spellings.** Option spellings the sweep does not split; shell expansions the rule
   does not model (zsh `^`/`~` negation under `EXTENDED_GLOB`, zsh `=cmd`, interactive history
   expansion); flags that run programs other than `rg --pre`.
6. **Tools the matcher** `Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Glob|Grep` does not name.
7. **Sub-agents** are assumed to pass through the same PreToolUse hook.
8. **Outside the session.** A human shell or unseen process can rewrite `dataset.tsv` or
   `data_sources.tsv`, change modes, copy closed data into an open folder, or paste it into a
   prompt.
9. **Data outside the project layout.**
10. **Edit's echo**, left to the harness's read-before-edit requirement.
11. **The approval-gated exposure of R-074** is not built.
12. **Approved execution.** Stage 03 scripts, wrapper runs and the local backend execute code that
    reads and writes wherever the OS allows, `dataset.tsv` and `data_sources.tsv` included; the
    human approval is that line.
13. **A human-run `finalize`, and every unregistered writer** (`scripts/backend_bench.py` among
    them), is trusted.
14. **A declared-public source is only as honest as the human who declares it.** Non-public data a
    human places in a declared folder, or a link a human places inside one (inside a `sample_dir`
    entry included, whose contents are not walked), is exposed.
15. **Agent-authored raw data.** The agent can Write files into a declared folder inside the
    workspace and register them as a public project: nothing non-public is exposed, but it is a
    provenance gap the stage 00 integrity checks and human review own.
16. **Time of check.** The checks run at call time; a change to a raw link or the declaration
    between the guard's check and the tool's run, by a human or an unseen process, is outside the
    session.
17. **Typed-tool path arguments outside `projects/`** (`--counts`, `--design`, `--h5ad`,
    `--counts-from`, `--h5ad-from`, and any later free path argument) read any folder the process
    can read: a named follow-up for rows 4 and 13 (a per-argument path rule in `policy.py`).

Also not met: no independent pre-build reviewer attacked the token spellings; coverage is the
builder's red-first grid. The producer and the reviewer are both Opus 5.5 Claude Code sessions,
in separate contexts, so a blind spot the model shares is a cost this review structure does not
remove. The bare `rg --pre`/`--pre-glob` spellings were already refused at the base by the
registry's schema (a path cannot be an option; the flag is outside `fs.inspect`'s vocabulary);
the new check is what refuses the spellings that pass the schema (a dispatcher pattern
`--pre=…`, a free string value `--pre`). Tested against ripgrep 12.1.1.

## Test

`python3 gars/tests/test_nonpublic_read_block.py`: 19 tests driving the real hook in fixture
roots built with the real `stage00_register.py` (`create`, `link`, `finalize`) and the real
`wrapperlib.write_status`. R0 has no declaration; R1 declares `decl/` and leaves `undecl/`
undeclared. The closed-project census of R0: `pilot` (`deidentified_under_agreement`, from the
real `finalize`), `ident` (hand-written `identifiable` row), `fresh`, `legacy`, seven `bad-*`
rows (`Public`, `public `, no `data_class` column, `public` + `identifiable`, empty, CRLF, a
symlinked public row), and the registration fixtures `ready`, `undeclraw`, `stamped`,
`dangling`; open: `open1` and `pilot-2` (real `finalize --data-class public`). The grid holds
72 literal rows (52 refused by this rule, 7 refused earlier by the schema or transport, 2 by the
`--pre` check, 11 allowed), plus: every registry tool that takes a project or path (53 of 58),
in both spellings, on `pilot` and `fresh` (refused, with the 0107 message wherever the base hook
allows the same call on `open1`) and on `open1` (the same decision and stderr as the base hook
copied from `git show 0754ec6:gars/_system/guard_hook.py`, except stage 00 `inspect`/`link`);
every registry tool from a cwd inside `pilot`; stage 00 without and with a declaration; 21
invalid declaration variants; the declaration's protection; the door mechanism in a test-only
copy; Q8, including a case refused by Q8 alone (finalize opened as a door in a copy); the moved
positive control; the class flip; the contract drift (`create` → `link` → `finalize` each
allowed then run, the guard's reader then public; `deidentified_under_agreement` run directly
then closed; the four-column shape read public); `CREATE_STAMP` against the real `create`; and
the cold-start twin. Every refusal is checked for `Blocked:`, its rule (`0107`, or `R-092`),
the absence of the planted `samples.csv` marker and of every `data_sources.tsv` line.

Red at parent: the module on a clone of `0754ec6` fails 17 of its 19 tests; the class flip (row
6's line already there) and the path-free controls pass. Mutations P1 to P31 (P21a to P21h one
per declaration clause) each went red on a hook-decision case on a disposable copy and were
restored byte-identical (sha256); the change report lists each with its first failing case.
`test_protected_paths.py` changes one test, `test_normal_project_edit_positive_control`, moved to
a root with no `projects/`; `test_settings_equal_guard_patterns` is unchanged and passes with the
new pair.

## Status

standing. The implementation is the lane's producer's, subject to independent review; the
rulings are the lane's, under the owner's standing delegation of 23 Sep 2026. The protected
changes (`guard_hook.py`, `settings.json`) take effect only with the lane's approval record,
0108, written at hand-off; 0109 is reserved.

## Date

2026-09-25
