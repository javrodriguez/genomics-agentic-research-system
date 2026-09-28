---
date: 2026-09-27
status: standing
kind: decision
touches:
  - gars/_system/tools/registry.json
  - gars/_system/tools/policy.py
  - gars/tests/test_fs_vocabulary.py
  - gars/tests/test_bash_lexer.py
  - gars/tests/test_nonpublic_read_block.py
  - README.md
  - DEVELOPMENT.md
symptoms:
  - grep -E (or -F, -w, -l, -c) is refused with "value is outside the declared vocabulary" (R-092)
  - find DIR -maxdepth 1 (or -name, -type) is refused with "paths cannot be options or stdin" (R-092)
  - an unquoted *, ? or [ in a filesystem command is refused (R-092); quote the pattern
---
# Filesystem-tool vocabulary: `grep -E`, a safe `find` predicate set, and no unquoted globs

Follow-up to [0058](0058-row-4-typed-surface-and-attack-list.md), [0107](0107-pg-nonpublic-projects-closed-to-reads.md) and [0165](0165-guard-lexer.md), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and ruled by the lane's coordinator on 27 September 2026; no sentence in this record is the owner's.
0186 is the lane's delegated approval of the protected change; this record does not write it.

## Context

A visitor's agent reading the workspace reaches for `grep -E "a|b" FILE` and `find DIR -maxdepth 1` in its first minutes.
At public main `a80df2d` both were refused by rule, reproduced with the guard fed json-built hook payloads and no model.

1. **grep's vocabulary.** `fs.search`'s flag list in `registry.json` held `-n -i -r -R`; `validate` refused anything else (0165's D7).
2. **find's expression.** `parse_argv` put every word after the leading flags into `paths`, so `find _system -maxdepth 1` met "paths cannot be options or stdin" and the one-path rule; `fs.find`'s flag list is empty, and `argv_for` had no place for an expression, so the dispatcher could not carry one either.
3. **The shell glob (found while reproducing, pre-existing).** The guard judges the unexpanded word; bash expands an unquoted `*`, `?` or `[` afterwards.
   At `a80df2d` each of these exited 0: `cat ..*/CLAUDE.md`, `ls ..*`, `grep -r x .*` (the macOS system bash is 3.2, and bash before 5.2 lets `.*`, `..*` and `..?` match `..`, so the read leaves the workspace: R-073), `rg -n x *` (a file named `--pre=<program>` in the working folder expands into an rg option, and rg runs that program on every file it searches), and `find *` (a file named `-delete` becomes a find action).
   This is 0165's D8 class.

## Decision

**Ruling 0185 (the lane's).**

1. **grep (data only).** `fs.search`'s flag list gains `-E`, `-F`, `-w`, `-l` and `-c`, each a read-mode switch that takes no value.
   Bundled flags (`-En`, `-rn`), value-taking flags (`-f FILE`, `-e`, `-A N`) and long flags (`--include=…`) stay refused.
2. **find (data plus one generic reader).** `fs.find` gains an `expression` array in its input schema and a `predicates` table, each predicate mapped to a full-match pattern for its one value: `-maxdepth` and `-mindepth` `^(0|[1-9][0-9]{0,2})$`; `-name` and `-iname` `^[^-/\n][^/\n]*$`; `-type` `^[fd]$`.
   `tools/policy.py` reads that table and hard-codes nothing about find's predicates.
   `parse_argv` ends find's paths at the first word that begins with `-` or is exactly `!`, `(`, `)` or `,`, and the rest is the expression.
   `validate_args` walks the expression in pairs (predicate in the table, value present and matching), refuses a find path equal to `!`, `(`, `)` or `,`, and keeps the one-path rule and every R-073 path check unchanged.
   `argv_for` builds `find PATH EXPRESSION`, so the dispatcher's `fs.find` runs the argv the Bash spelling does.
   Every starting point is judged by R-073 and 0107 exactly as `find PATH` was; 0107's walk also judges every expression word.
3. **The glob rule.** A command whose first word is a registry filesystem executable (`ls cat head tail stat shasum wc grep rg find`, read from the registry) and which holds an unquoted, unescaped `*`, `?` or `[` in any word is refused (R-092): "an unquoted *, ? or [ is expanded by the shell before the guard's check applies; quote the pattern (grep -n "x*" FILE), or for file names use find DIR -name "*.py"".
   A quoted or backslash-escaped glob is a literal and stays allowed.
   The coordinator brought this into the lane as a refusal-path fix after the reproduction; the lane first built it for `find` alone.
   The text does not suggest `rg -g`, because `-g` is not in rg's vocabulary; adding it is a separate reviewed change.

Newly allowed (each exit 0 through the guard): `grep -E "a|b" f`, `grep -n -E …`, `grep -F|-w|-l|-c x f`, `grep -r -l x DIR`; `find DIR -maxdepth N`, `-mindepth N`, `-type f|d`, `-name "PAT"`, `-iname "PAT"` in any combination; their dispatcher spellings.
Still refused, each with a test row: every `-exec`, `-execdir`, `-ok`, `-okdir`, `-delete`, `-fprint*`, `-fls`, `-newer*`, `-samefile`, `-o`, `-not`, `!`, `-print*`, `-ls`, `-follow`, `-regex`, `-path` and `-L` form; outside starting points (R-094); a closed project's folder as starting point (0107); a missing or malformed value.

**Visitor-visible side effect.** An unquoted glob in a filesystem command must now be quoted: `cat *.md` and `ls _system/*` are refused where `find . -name "*.md"`, `grep -n "x*" f` and `ls _system` pass.
Four `test_nonpublic_read_block.py` EXPANSION rows (`glob`, `bracket`, `pattern-slot`, `raw`) now meet the glob rule before 0107's static-prefix check; they are still refused, and 0107's glob handling stays exercised by the Glob tool rows.

**Why `!`, `(`, `)` and `,`.** The Bash tool's `find` in a Claude Code session is Claude Code's bundled bfs, with GNU semantics, which begins the expression at those words as well as at a `-`-led one.
Accepted as a path, `find , -maxdepth 9` or `find "!" -name x` would walk the default `.` that 0107 refuses beside a closed project; review r1 reproduced that listing of a closed project's raw file names.
The dispatcher runs `/usr/bin/find` (BSD), so a test of argv equality alone could not see it.

Rejected alternatives: a find-specific expression parser in code (the predicate table is data, one generic reader); allowing bundled short flags (a combinatorial surface for a small gain, left for a visitor's need); glob modelling that expands the pattern inside the guard (the quoted spelling is always available and is what find and grep mean).

## What this does not close

- **D1** Any transport that is not a registry filesystem command (the registered helpers' Bash spellings and the dispatcher) is outside the glob rule; whether an unquoted glob in a helper's argument can reach a path the guard did not judge is a separate audit, alongside 0165's D2 per-helper audit.
- **D2** (review r2 F-1, NOTE) The dispatcher rows cover `!`, `,` and `(`, not `)`; not a leak (bfs errors on a lone `)`, GNU reads it as an operator, and the check covers all four).
- **D3** (review r2 F-2 and r1 F-3, NOTE) With a closed project present, 0107's static-prefix judgement reads a `-name` value as a path: `find _system -name "*.py"` and `find _system -name "("` from the workspace root are refused; it errs toward refusing and is pinned by a test row.
- **D4** Bundled grep flags (`-rn`, `-En`) and rg's `-g` stay out of the vocabulary.

## Test

`gars/tests/test_fs_vocabulary.py` is new, 21 tests through the guard with json-built payloads and through `tools.policy` directly: every newly allowed and still-refused row above in a plain fixture, the closed-project rows (each new find form refused exactly as its bare form; the `dataset.tsv` read the same with and without `-E`), the dispatcher's argv equal to the Bash spelling's and one real `fs.find` read as a positive control, one valid and one invalid value per declared predicate, 26 dangerous predicates never declared, find's operator words in both transports, and the grep and find rows of `test_bash_lexer.py`'s and `test_policy_attacks.py`'s refusal tables still refused, counted per source.
`gars/tests/test_bash_lexer.py` gains the glob table (eleven refused, seven allowed) and runs it through its bash and zsh argv differentials (85 accepted rows each, identical).
They must fail when `-exec` or `-delete` is declared, when a value pattern is widened, when the value check is skipped, when the glob rule is dropped, narrowed to `find`, skipped for `rg`, or loses any of `*`, `?`, `[`, when `argv_for` drops the expression, when R-073 is skipped for a call with an expression, when `-f` joins grep's list, when the operator-word path check is dropped, and when the parser's operator-word stop is dropped.
The lane's mutation proof at the branch head killed all sixteen with the unchanged control green.
The suite total moves from 1150 to 1172.
The landing's evidence is recorded in 0186.

## Status

Standing. The change record for the filesystem-tool vocabulary follow-up; its protected-change approval is 0186.

## Date

2026-09-27
