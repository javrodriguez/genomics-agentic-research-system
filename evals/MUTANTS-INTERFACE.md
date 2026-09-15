# Row 3 sealed mutation interface — version 1

This is the complete handoff to an independent sealer. **Do not read the producer's tests,
transcript, fault controls, or test results before sealing.** Work from the committed producer
SHA in a separate context and checkout (R-162). A coordinator supplies this document and a
source-only export of that SHA. It contains `gars/_system/`,
`gars/02_bioinformatics/`, `gars/_references/` and `gars/_templates/`. No `tests/` or
`gars/tests/` is in that export. The latter two source directories support fixtures but are
read-only. Do not inspect Git history to recover tests. The coordinator runs the sealed set
against the full checkout after the seal. The runner itself is not needed to author the set.

## What the set measures

R-164 (§16.3 and §18 Row 3): a whole-suite pre-push gate refuses failures and either empty
collection; deterministic prepare emits identical bytes for identical inputs; wrapper
contracts cover the seven nf-core wrappers; interrupted execution resumes without repeating
completed side effects. Ten **semantic** faults must be sealed before scoring. The exit is
at least 8/10 killed and 7/7 wrapper contracts. Thresholds are fixed. The producer cannot
supply the sealed set. `independent_context` sealing supports development only;
`external_human_seal` is required for public credibility claims. No score exists yet.

The shipped guard is a harness token/path scanner, not a typed-tool sandbox. It consumes
JSON on stdin with `tool_name`, object `tool_input`, and `cwd`; `CLAUDE_PROJECT_DIR` identifies
the workspace. Exit 2 refuses; exit 0 allows. A denied protected write or unparseable call
must be refused; instructed reads and helper invocations remain allowed. Git bypass-switch
denies, full role profiles and protected-path governance belong to later policy work. Do
not present an existing gap as a regression introduced by a mutant.

## Source layout and scope

| Path | Interface |
|---|---|
| `gars/_system/guard_hook.py` | Harness PreToolUse stdin JSON, allow/refuse exit |
| `gars/_system/wrapperlib.py` | Shared config/preflight functions; `write_params_yaml`, `write_submit_sh`, `write_reproducibility`; generated Nextflow requeue guard |
| `gars/_system/executorlib.py` | `header`, `submit`, `status`, `describe`; local and scheduler descriptors; no resume subcommand |
| `gars/_system/workspace.py` | Atomic file writes, pipeline pins and shared workspace functions |
| `gars/_system/wrappers/<name>/<module>.py` | One module per wrapper; `check`, `prepare`, `collect`; JSON stdout; exit 0 success, 1 failure, 2 refusal, 3 usage |
| `gars/_system/wrappers/<name>/SKILL.md` | Wrapper interface and requirements |
| `gars/02_bioinformatics/<assay>/<substage>/CONTEXT.md` | Corresponding eight-section stage contract |

Seven nf-core wrapper directories exist: `nfcore-atacseq-wrapper`, `nfcore-chipseq-wrapper`,
`nfcore-cutandrun-wrapper`, `nfcore-methylseq-wrapper`, `nfcore-rnaseq-wrapper`,
`nfcore-scrnaseq-wrapper`, `nfcore-spatialvi-wrapper`. Three downstream wrappers also exist:
`rnaseq-de`, `scrna-qc-cluster`, `spatial-cluster-count`. Enumerate the supplied tree; do not
assume these lists remain complete. `ASSAY` and `SUBSTAGE` in each module locate its contract.

Mutations may edit existing ordinary files under `gars/_system/**` or
`gars/02_bioinformatics/**`. Tests, evaluation code, Git metadata, `.github/`, reference
files and templates are outside mutation scope. No additions, deletions, renames, permissions
changes, symlink edits or traversal. Each mutant applies independently to the same base SHA;
never stack mutants. Each must attack a named requirement by changing observable behavior,
not merely comments, whitespace, wording, a docstring, or an error message's spelling.
The eight contract headings are Purpose, Inputs, Scope Boundaries, Definitions, Process,
Response Format, OUTPUT and Human check; altering their prose alone does not establish a
behavioral fault. Baseline defects and syntax/import failures are not semantic faults.

## Sealed directory and diff format

Choose an external scratch directory; it must not be inside the producer repository. Set
`TMPDIR`, `TEMP` and `TMP` to that existing directory for every command. Put the set in a
separate directory supplied only after sealing:

```text
sealed/
  M01/
    mutant.diff
    expected.json
  ...
  M10/
    mutant.diff
    expected.json
```

IDs must match directory names and be unique. Exactly ten mutant subdirectories are required
for the exit measurement. Use UTF-8 **plain unified diff**, with matching `--- a/<repo-path>`
and `+++ b/<repo-path>` headers and normal `@@` hunks. Multiple files may be changed in one
mutant. Use `difflib.unified_diff` with those filenames, or remove Git's `diff --git` and
`index` extended headers from a textual `git diff`. Extended headers, binary patches, file
creation/deletion, paths with whitespace and fuzzy/non-applying patches are refused.

## expected.json and behavioral evidence

Every file has exactly these keys:

```json
{
  "id": "M01",
  "requirement": "R-164",
  "description": "Explain the behavior changed and why it violates this requirement.",
  "probe": {
    "argv": ["{python}", "-c", "<stdlib Python that observes the behavior>"],
    "stdin": ""
  },
  "before": {"returncode": 0, "stdout": "<exact original output>", "stderr": ""},
  "after": {"returncode": 0, "stdout": "<exact mutated output>", "stderr": ""}
}
```

`requirement` is an `R-NNN` ID. `description` states the intended behavioral violation;
`probe.argv` is a nonempty list of strings executed without a shell, from the scratch tree's
root. `{python}` selects the runner's interpreter. `stdin` is a string. Both observations
contain an integer return code and exact UTF-8 stdout/stderr strings; they must differ. Avoid
absolute paths, nondeterministic values, network calls and runtime dependency installation.
Use Python 3.6.8 syntax and stdlib only. For file-output behavior, make disposable fixtures
under `TMPDIR`, observe the resulting artifact semantically, and clean those fixtures. Never
write into the supplied source tree. Set fixture-specific environment variables within the
probe rather than relying on the coordinator's machine. The subprocess limit is 300 seconds.

The probe must independently demonstrate the **behavioral** difference. It may call a library
function or an existing CLI against synthetic inputs; it must not dump or hash source text,
count words/lines, inspect the mutation diff, or inspect/execute producer tests. A semantic
witness is not a guessed name of the test that might kill the mutant. The sealer validates
the original and changed observations before freezing the set. The independent reviewer
checks that the witness demonstrates a real requirement violation: arbitrary semantic
equivalence cannot be decided mechanically. Python AST comparisons reject comment,
formatting and docstring-only changes even if a textual probe would distinguish them.

## Seal, then run

Freeze the ten diffs, metadata and their SHA-256 hashes outside the producer context, with
the source SHA, seal type and sealer identity. Only then give the coordinator the set. Do not
tune surviving faults after seeing producer tests; retain the first score at the original
run SHA. A later set is a separate sealed run, not a replacement of its first result.

From the full, clean committed repository root, the coordinator runs:

```sh
# TMPDIR, TEMP and TMP already identify the approved external scratch directory.
# SEALED_DIR is the externally sealed folder; no producer-authored mutants go there.
GARS_SEALED_MUTANTS_DIR="$SEALED_DIR" python3 evals/mutate.py
GARS_SEALED_MUTANTS_DIR="$SEALED_DIR" python3 evals/mutate.py --require
```

Dependencies: Python (stdlib), Git and Bash. Pinned pipelines/Apptainer are optional for the
offline suite; any existing environment skips must be reported with the score. `GARS_PIPELINES`
may identify an empty external fixture directory for an explicitly offline run. This is not
R-166 Linux integration. The runner refuses a dirty source checkout so `run_sha` identifies the tested source,
then copies the working tree (excluding `.git`) under `TMPDIR`,
checks the intact whole suite first, then applies one diff at a time. Each probe must match
its declared before/after observation and leave source files unchanged. A failure to load,
apply, observe, or restore refuses the run; it is never a kill.

Each effective mutant runs `python3 tests/run_tests.py` in its scratch copy. Nonzero with a
named failing unittest yields `killed`; success yields `survived`. An unchanged probe or
unchanged Python AST yields `ineffective`, never `killed`, and cannot satisfy a ten-semantic-
mutant set. The first failing test is recorded in execution order (including subtests).
The scratch tree is restored from its snapshot after each mutant and hashed before/after;
the source tree is independently hashed before/after the entire run. Names, bytes, modes,
empty directories and symlink targets are included; `.git` is excluded. This is process
isolation for trusted independent fault authors, not an operating-system security sandbox.

Output: one JSON row per mutant (`id`, `requirement`, `run_sha`, `status`, `test`, optional
`reason`), followed by `killed/total` with the actual numbers. Capture stdout/stderr outside
the checkout. Without `GARS_SEALED_MUTANTS_DIR`, output is `unmeasured`, exit 0 in report mode
and exit 1 with `--require`. With a set, report mode exits 0 after a valid measurement;
`--require` exits 1 unless there are ten effective mutants and at least eight kills.
Malformed input, failed intact baseline, or integrity drift exits 2. Neither mode edits
`evals/mutants.md`. The sealer copies the results into that record, preserving survived and
ineffective entries and adding seal metadata and the first-run score. Empty cells are not
passes. No public claim is permitted before an external human seal.
