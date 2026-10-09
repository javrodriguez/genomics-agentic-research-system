# Lane report: w4a-cp2-image-egress (gap4 wave 4, CP2: the box images, their locks and the egress proxy)

This report was written by the lane's builder on Thu 8 Oct 2026, and created at the gap4 lane lead's direction (fold 4 brief).
It carries only fold 3 and fold 4.
The lane's first build and its builder review rounds 1-2 are recorded in the builder's hand-back and in `scratchpad/w4-review/w4a-builder-review.md`.
Every decision below marked "the lane lead's" is the gap4 lane lead's.
None is Javier's or glitch-f3's.

## Fold 3 (the lane report's section)

All decisions below are the gap4 lane lead's, from the fold 3 brief. Calls left to me are labelled "this lane's choice".

### Whole-file swaps

Each new clause mutant was proved red by one whole-file swap in one process: the mutated module is loaded under its real `__file__` and name, then the whole test file runs. The harness is `scratchpad/w4a/swap.py`. The two no-op controls first, to show the harness reads green when nothing is mutated:

- control (no-op), test_image: `exit=0 Ran 40 tests closing: OK`
- control (no-op), test_egress: `exit=0 Ran 19 tests closing: OK`

| Finding | Fix | Test | Swap mutant, and its closing line |
|---|---|---|---|
| **W4A1-1** MAJOR | `parse_dockerfile` joins the way BuildKit does: `_CONTINUATION_RE` is `([^\\])\\[ \t]*$` → `$1`, with no separator and the continuation's leading whitespace kept. Comment and empty lines inside a continuation are skipped. Any character outside printable ASCII, space and tab is refused. RUN lines are compared with `expected_runs` after `normalized()` (whitespace runs made one space). | MUTANT_DOCKERFILES gains "P1a the Python check split around its =", "P1b the installed-version check split around its =" and "a continuation joined inside a word". `test_the_parser` asserts the BuildKit join (`te\`+`st "a"\ ` + `=\` + ` "b"` → `test "a"= "b"`) and refuses `\r`, NBSP and `\x0b`. | Join with a space, as before: `FAILED (failures=3)` |
| **W4A1-2** MAJOR | `proxy_conf.parse` refuses any line over `MAX_LINE = 512` characters (comments included), and any `\r` or other character outside printable ASCII, space and tab. Tokens split on `[ \t]+`. | MUTANT_CONFS gains "P2 a long comment hiding a directive" (8191 characters, then `http_access allow all`), "a line over 512 characters", "a carriage return", "a non-breaking space" and "a control character in a comment". New ParseTest: a tab-separated line reads as squid reads it, and exactly 512 characters is read while 513 is refused. | No length limit: `FAILED (failures=3)`. No character check: `FAILED (failures=1)`. |
| **W4A1-3** MAJOR | Checks line 13 is now an allowlist (see the next section). | Both review probes are planted positives, plus 7 more for the new rules. 37 planted positives in all; every one is refused. | Applied to the line itself: dropping the chain rule makes `missed planted` list 14 positives (exit 1). Dropping the bare-use rule misses 3 (exit 1). Removing `json.load` from the allowlist gives `hits: ... ['chain json.load']` (exit 1). Adding a stale `re.findall` entry gives `unused allowlist: ['re.findall']` (exit 1). |
| **W4A1-4** MAJOR | (a) The "the same acl defined twice" mutant now puts the extra definition first. (b) A duplicate-key lock file through `load`. (c) A lock not beside its Dockerfile, through `load`. | (a) in MUTANT_CONFS. (b) `test_a_duplicate_key_in_a_lock_file_is_refused` writes take-a's lock with `"base": "PENDING"` twice, beside its Dockerfile (BOX_DIR patched), asserts LockError "duplicate key 'base'", and checks that the in-test mutant (hook = `dict`) loads it. (c) `test_a_lock_not_beside_its_dockerfile_is_refused` copies take-a's lock byte for byte to a temp folder and asserts LockError. Both use `tempfile`, outside the worktree. | (a) dup acl allowed: `FAILED (failures=1)`. (b) no duplicate hook: `FAILED (failures=1)`. (c) no beside binding: `FAILED (failures=1)`. |
| **W4A1-5** NIT | `print_mutants` prints `'red' if found else 'GREEN'` for locks, inspects and nullable rows. | (the runner itself) | n/a |
| **W4A1-6** NIT | **This lane's choice:** mutate the flag itself. The test is renamed `test_a_dropped_pull_flag_goes_red`. It loads a copy of image_lock's source with `"--pull=false", ` removed, as a module of its own, asserts the mutant's argv lacks the flag, and asserts that the new `pull_ok(argv)` (flag exactly once, right after `build`) goes red. `test_the_argv` now uses `pull_ok`. | in test_image | The pull flag dropped from the real module: `FAILED (failures=7)` |
| **W4A1-7** NIT | **This lane's choice:** delete all six, because each is dead under the closed sequences. In image_lock: `FORBIDDEN_RUN_WORDS` (and the scan of RUN words against the forbidden packages), `SETUID_RE`, the `apt install` spelling check, and the `10003` search. In proxy_conf: the continuation refusal and `ACL_NAME_RE`. `forbidden()` and `FORBIDDEN_PACKAGES` stay, applied to the one apt-get line, as requirement 4 asks. Every Dockerfile mutant those clauses used to catch is still red, through the closed RUN sequence or the package line. A conf continuation is still refused, because a trailing `\` becomes a token that no exact directive check accepts (the "a continuation" mutant is red). | existing mutants | n/a (deleted) |
| **W4A1-8** NIT | `build_argv`'s docstring says it builds from any lock that validates, and that the drive step passes only `load()` output. | n/a | n/a |
| **W4A1-9** NIT | No code change. Named below under open items. | n/a | n/a |
| **W4A1-10** NIT | `SIDECAR_PROGRAM = "/opt/w/sidecar.py"`, and `SIDECAR_COPY = "sidecar.py " + SIDECAR_PROGRAM`. | `test_the_sidecar_program_path` asserts both. | The program moved: `FAILED (failures=3)` |

**One mutant stays green, and it is equivalent:** in `proxy_conf.parse`, replacing `re.split(r"[ \t]+", line)` with `line.split()` leaves the whole test file green (`exit=0 Ran 19 tests closing: OK`). The character check runs first and refuses every whitespace character other than space and tab. So the two splits cannot differ on any line that reaches them. I kept the explicit split because it says what squid does, and it is not a separate guard.

### Checks line 13, the allowlist (W4A1-3)

- **Imports:** exactly `from __future__ import annotations`, `import fnmatch`, `import json`, `import os`, `import re`, `from dataclasses import dataclass`, `import harness_bookkeeping` and `from box.egress import proxy_conf`. No alias, no star import.
- **AL**, the attribute chains an imported name may start: exactly
  - `os.path.join`, `os.path.dirname`, `os.path.abspath`, `os.path.isabs`
  - `re.compile`, `re.fullmatch`, `re.search`, `re.split`, `re.IGNORECASE`
  - `json.load`, `fnmatch.fnmatchcase`
  - `harness_bookkeeping.CLAUDE_CODE`, `proxy_conf.CODEX`, `proxy_conf.GEMINI`
- **How a chain is checked:** each maximal chain rooted at an imported name must be in AL, so a deeper chain such as `os.path.join.x` is refused.
- **What is refused besides:**
  - a bare use of an imported module, as a value or an argument;
  - storing to an imported name, deleting one, or using one as a parameter name;
  - any dunder attribute, anywhere;
  - the names `__import__`, `importlib`, `getattr`, `setattr`, `delattr`, `eval`, `exec`, `compile`, `globals`, `locals`, `vars`, `type`, `breakpoint` and `__builtins__`;
  - the `shell=` keyword;
  - any string that is a process-start name.
- **Keeping the list exact:** every AL entry must be used by the two modules. A stale entry fails the line.

### Interface changes, exactly

- **New in `box/image_lock.py`:**
  - `SIDECAR_PROGRAM = "/opt/w/sidecar.py"`. Merge binding 6 can bind `sidecar.PROGRAM` to this constant.
  - `normalized(args: str) -> str`
  - private `_continued` and `_CONTINUATION_RE`
- **Changed in `box/image_lock.py`:** `Instruction.args` is now the BuildKit-joined text. Within the args, whitespace runs are no longer collapsed: `parse_dockerfile("RUN a \\\n  && b")` now gives `"a   && b"` rather than `"a && b"`.
- **Removed from `box/image_lock.py`:** `FORBIDDEN_RUN_WORDS` and `SETUID_RE`.
- **New in `box/egress/proxy_conf.py`:** `MAX_LINE = 512`, and private `_LINE_RE`.
- **Removed from `box/egress/proxy_conf.py`:** `ACL_NAME_RE`.
- **Behaviour change, `proxy_conf.parse`:** it now raises `ProxyConfError` on a long line, `\r` or a non-printable character. It no longer refuses a `\` continuation at parse time; `check` still refuses one.
- **Unchanged:** every interface 11 value (HOSTS, ALIAS, PORT, PROXY_URL, CONF_PATH, COMMAND, USER as PENDING) and every lock.

### Open items

- **W4A1-9: labels inherited from the base.** This is a decision for the base pin, on the real box. `check_labels` refuses any label the lock does not name, which the brief requires. So a base that carries its own labels (OCI keys) can never pass. At the pin, either choose a base with no labels, or record the base's labels in the lock as a field of their own. That second option would be a schema change, which needs a ruling.
- **Not verified on a real box:** that BuildKit joins exactly as `_CONTINUATION_RE` models it, and squid's BUFSIZ on the egress base. The model comes from the review's reading of parser.go and cache_cf.cc. No build or `squid -k parse` was run, as the rules require.
- **Normalised comparison:** `normalized()` would also accept a doubled space inside a quoted string of a closed RUN line. In the committed lines no quoted string holds a space whose count matters (`'import platform; print(...)'`, `'require(process.argv[1]).version'`, `'*'`). Stated here so a later line that adds one is checked.

**Correction (fold 4, W4A3-4):** fold 3 had 39 planted positives in checks line 13, not the 37 stated above.

## Fold 4 (lane review round 3)

**Commits:**
- `c7c18e64`: red, data only. 13 planted positives were added to line 13, taking it from 39 to 52.
- `48234aa1`: green. The rules changed.

**What the green commit was checked against:**
- test_image.py: `Ran 40 tests` / `OK`, with 178 mutants red and 0 GREEN.
- test_egress.py: `Ran 19 tests` / `OK`, with 38 mutants red and 0 GREEN.
- Checks line 13: `missed planted: [] hits: {... []} unused allowlist: []`, exit 0.
- `copy_manifest.py --check`: ok (122 files, 73 new).

| Finding | Fix (the lane lead's decision) | Witness (planted positive) | Rule-drop mutant (line 13 with that rule removed), result |
|---|---|---|---|
| W4A3-1 MAJOR | Three witnesses, each refused by only its own rule. Data only. | `import json as j`; `x = 1` then `x.__class__`; `eval("1")` | alias rule dropped: rc=1, misses `import json as j`. Dunder-attribute rule dropped: rc=1, misses `x.__class__`. N emptied: rc=1, misses `eval("1")`. |
| W4A3-2 MINOR | Refuse any Name that starts and ends with `__`, except exactly `__file__`. A closed list of builtin names stays a residual (below). | bare `__name__` | dunder-name rule dropped: rc=1, misses `__name__` |
| W4A3-3 MINOR | The rebinding check also reads def, async def and class names, except-as names, and match captures (MatchAs, MatchStar, MatchMapping rest). `dataclass` is allowed bare only as a ClassDef decorator item (bare, or as a Call's func). `annotations` is allowed only in its import. | `def os`, `async def os`, `class os`; `except E as os`; `case os`, `case [*os]`, `case {**os}`; `f(dataclass)`; a bare `annotations` | def/async def/class rule dropped: rc=1, misses all three. except-as rule dropped: rc=1. Match-capture rule dropped: rc=1, misses all three. Old FN exemption restored: rc=1, misses both. |
| W4A3-4 NIT | The count is stated: 39 before fold 4, 52 after. I did not split the two import forms (optional; `import box.egress.proxy_conf` cannot be used, because `box` is refused bare and no AL entry starts with `box.`). | n/a | n/a |
| W4A2-2 NIT | The `_CONTINUATION_RE` comment now cites moby/buildkit `frontend/dockerfile/parser/parser.go` on its master branch, as lane review round 1 read it on 8 Oct 2026. No commit was recorded, so this is a citation, not a pin. | n/a | n/a |

No guard-evasion probe was written, per glitch-f3's standing rule.
The only new planted forms are the witnesses above.

## Fold 5 (lane review round 4: fold and close)

glitch-f3 ruled fold and close under Javier's delegation, with no fifth review round. The fold below is that ruling's; it is not Javier's word.
The Mac was on hold while I wrote and committed this fold, so no gate has run on its commit. The gates run after the lift, and athena runs the battery.

| Finding | Fix | Witness (only its own rule refuses it) | Rule-drop mutant |
|---|---|---|---|
| W4A4-1 MAJOR | A witness for the process-start string rule. | a bare string statement `"system"` | the string rule dropped: should miss only `"system"` (pending the lift) |
| W4A4-2 MAJOR | The process-start name set C is applied to every `Attribute.attr`, whatever its root, as well as to string constants. | `x = 1` then `x.system("x")` | the attribute rule dropped: should miss only `x.system` (pending the lift) |
| W4A4-4 MINOR | An ImportFrom with `level > 0` keeps its leading dots in IM, so no relative import matches IMP. | `from .dataclasses import dataclass` | IM without the dots: should miss only that witness (pending the lift) |
| W4A4-3 MINOR | The residual sentence below is corrected. No code change. | n/a | n/a |
| W4A4-5 NIT | Named below. "A closed list" is corrected to "a fixed denylist". | n/a | n/a |

Line 13 now holds 55 planted positives: 52 before this fold, plus 3.
The closing gate is committed as checks line 16 and runs on athena through `run_checks`.
It runs line 13 as committed, which must miss nothing and exit 0.
It then runs line 13 three more times, each time with one of fold 5's three new rules removed.
Each of those runs must exit 1 and miss exactly that rule's witness.

The NITs of W4A4-5, named and not folded:
- The rebinding rule does not read PEP 695 type-parameter names (TypeVar, ParamSpec and TypeVarTuple). This is harmless, because the chain and bare rules key on the Name id.
- The `shell` keyword is read on `keyword.arg` only. Its reach is nil, because `subprocess` cannot be imported.

## Residual

The allowlist was judged by construction, not by adversarial probing.
Names that are not imported are governed by a fixed denylist of builtin names (N) plus the dunder-name rule, not by a full allowlist of builtin names.
Attribute routes from roots that are not imported, beyond the named sets (the process-start names C, the dunder rule and the chain rule), are not closed by construction. This is a named residual.

## Open items, carried to CP2

1. **Inherited base labels, at the base pin.** `check_labels` refuses any label the lock does not name, so a base that carries labels of its own can never pass. That fails closed. At the pin: choose an unlabelled base, or add a lock field for base labels. The second is a schema change, and it needs a ruling.
2. **BuildKit's continuation join and squid's line limit,** to be observed on the real box. Both are modelled from source reading today, and both fail closed on the cases worked through.
3. **Normalisation inside quoted strings.** `normalized()` would accept a doubled space inside a quoted string of a closed RUN line. No committed line has one whose count matters. A later line must be checked for it.
