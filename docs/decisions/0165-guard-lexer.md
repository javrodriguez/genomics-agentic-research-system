---
date: 2026-09-27
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/_system/tools/policy.py
  - gars/tests/test_bash_lexer.py
  - gars/tests/test_guard_hook.py
  - gars/tests/test_nonpublic_read_block.py
  - README.md
  - DEVELOPMENT.md
symptoms:
  - a bare `ls` (or `cat`, `head`, `tail`, `stat`, `shasum`, `wc`, `find`) is refused with "the guard failed while checking this call (IndexError …)"
  - a grep or rg pattern holding a quoted `|` (a regex alternation) is refused as a shell operator (R-092)
---
# Guard lexer: a bare `ls` crashes the guard, and a quoted `|` reads as a shell operator

Follow-up to [0058](0058-row-4-typed-surface-and-attack-list.md), [0107](0107-pg-nonpublic-projects-closed-to-reads.md) and [0141](0141-row-13-closed-project-doors.md), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and ruled by the lane's coordinator on 27 September 2026; no sentence in this record is the owner's.
0166 is the lane's delegated approval of the protected change; this record does not write it.

## Context

The launch pad's probe and fourth take (27 Sep 2026, at public main `4597dd4`) met two refusals in a visitor's first minutes, both reproduced with the guard fed json-built hook payloads and no model.

1. **A bare filesystem command crashed the guard.**
   `ls` exited 2 with "the guard failed while checking this call (IndexError: list index out of range) … (decision 0042)", while `ls .` and `ls -la` exited 0.
   `parse_argv` accepts a one-word filesystem command with its paths defaulting to `.`, and then the pilot-log check added by 0141 read `tokens[1]` without a bounds check; 0042's fail-closed catch turned the crash into the deny.
   Every one-word filesystem command reached the same line: `ls`, `cat`, `head`, `tail`, `stat`, `shasum`, `wc`, `find`.
2. **A quoted operator counted as an operator.**
   `simple_tokens` refused any command whose raw text held `; | & < >`, before any quote handling, so `grep -n "sanitiz\|add_argument" _system/stage00_register.py` was refused as a shell operator although bash passes the quoted `|` to grep as a literal byte.
   0058 refuses operators and expansion; a quoted `|` is neither, and 0107's row 4 follow-ups already named "a Bash transport that refuses unquoted metacharacters" as the intended shape.
   The code comment's alternative, a native tool caller for the JSON dispatcher, does not exist in Claude Code: the dispatcher is itself reached through Bash, where its quoted JSON met the same test, so a visitor had no way at all to search for `a|b`.

## Decision

**Ruling 0165 (the lane's).**

1. **No argv index without a bounds check** (`gars/_system/guard_hook.py`).
   The pilot-log check applies only when the call has an operand (`len(tokens) > 1`): an operand-free call cannot name `pilot_log.py`, so the rule simply does not apply.
   Every other subscript on the Bash path was read and is bounded (the dispatcher's by `len(tokens) == 4`, `parse_argv`'s by its own length checks).
2. **An operand-free filesystem call is judged at its default path** (`gars/_system/guard_hook.py`).
   Found by the lane's own probe after fix 1: with a closed project present, a bare `find` (refused at `4597dd4` only by the crash) became allowed while `find .` was refused, and `grep -r x` and `rg x` were already allowed at `4597dd4` while their `.` spellings were refused, because the closed-project checks judged only the typed words and never `parse_argv`'s default.
   A non-dispatcher filesystem call whose paths are the default now has `.` judged exactly as if it had been typed; every bare filesystem call gets the verdict of its `… .` spelling.
3. **A shell operator counts only when unquoted, and only filesystem commands may quote one** (`gars/_system/tools/policy.py`, `simple_tokens` only).
   A quote-state scan follows POSIX rules: inside `'…'` no escapes; inside `"…"` a backslash escapes only `"` and `\`; unquoted, a backslash escapes the next byte.
   The only thing that becomes allowed is the bytes `; | & < >` inside single or double quotes, in a command whose first word is a registry filesystem executable (derived from the registry, never hard-coded).
   `$`, backtick, CR and LF refuse anywhere, quoted or not (bash still expands `$` and backticks inside double quotes).
   An unquoted operator refuses, and so does an escaped unquoted one (`a\|b`); an open quote refuses.
   A quoted operator in a Python helper's arguments or in the dispatcher's JSON over Bash still refuses with R-092, unchanged.
   `shlex.split` stays the tokenizer after the scan, and the guard's `tokens = simple_tokens(command)` line is byte-identical.
4. **Shell syntax that survives quote removal refuses, for every command** (`simple_tokens`).
   Tolerating quoted bytes is only safe if the shell then runs exactly the argv the guard judged, so the lane and its reviewers compared the scan with bash and zsh and closed every construct where they differed:
   - an unquoted `#` that begins a word starts a comment (found by the lane's probe: with a closed project, `grep -r x # README.md` was allowed at `4597dd4` and grep searched the whole working folder);
   - an unquoted `{`, `}` or `~` expands (review r1: `ls {..,"|"}` and `ls ~/"|"` had become allowed; pre-existing and worse, `cat {../projects/closed/…,x}` from a public folder reached a closed project's file at `4597dd4`, because the brace word was judged unexpanded; `}` joined after zsh refused to parse `a\{b,c}` that bash ran);
   - an unquoted `(` or `)` is glob or code syntax in zsh (review r2: zsh runs a glob qualifier's `e:'…'` string and `=(…)` as commands, so `ls *(e:'touch a;touch b':)` had become allowed, and the single-command form, including a read of a closed project's file, was allowed at `4597dd4`).
   Each refuses with R-092's message; the same byte quoted (`"~"`, `'{2}'`, `"(a|b)"`) or escaped (`\(`) stays literal.
5. **The flag vocabulary is unchanged.**
   The coordinator asked before the build whether an installed ripgrep has a flag that runs a program (`--hostname-bin`, `--pre`) that the guard allows.
   It does not: the macOS build machine's ripgrep 12.1.1 has `--pre`, `--pre-glob` and `-z/--search-zip` and no `--hostname-bin`, the Linux build node has no ripgrep, and every such spelling (`--pre`, `--pre=`, `--pre-glob`, `--hostname-bin` both spellings, `-z`, `--search-zip`, `-nz`, `--pr`, `--files --pre=cat`) exits 2 at `4597dd4` with "value is outside the declared vocabulary", because each filesystem tool's flags are already an allow-list in the registry (grep `-n -i -r -R`, rg `-n -i --files`, ls `-a -l -la -al`, shasum `-a`, wc `-l`, the rest none), and a flag after the pattern is refused as a path that is an option.
   The planning note that "the filesystem tools still take any flag" was wrong; no flag fix was needed.
   Because `-E` is not in grep's vocabulary, `grep -nE "a|b" …` stays refused (now for its flag, no longer for the `|`); the alternation road is `rg -n "a|b" …` or `grep -n "a\|b" …`.

**Visitor-visible side effect.** A literal `~`, `{`, `}`, `(` or `)` anywhere in a Bash command, and a `#` at the start of a word, must now be quoted: `ls file~` is refused where `ls "file~"` passes, and `grep -n x{2} f` is refused where `grep -n "x{2}" f` passes.
Review r2 searched every `gars/**/*.md` for helper and filesystem commands and found none that spells such a byte unquoted.
Four existing expectations in `test_nonpublic_read_block.py` (`cat projects/{pilot,open1}/CONTEXT.md`, `cat ~/x`, `ls ~`, `ls projects/*(/)`) move from 0107's refusal to R-092's, still refused.

Rejected alternatives: `shlex.shlex(punctuation_chars=True)` returns a quoted `"|"` and an unquoted `|` as the same token, so it cannot tell them apart; widening every registered helper at once needs an audit that no argument reaches a generated script unquoted (D2); widening grep's vocabulary with `-E` is a vocabulary change of its own (D7).

## What this does not close

- **D1** The whole-call raw-byte rule stays as it was (`$`, backtick, CR, LF refused anywhere); other control bytes (tab, VT, NUL) are not newly refused.
- **D2** Quoted operators in a registered Python helper's arguments or in the dispatcher's JSON over Bash stay refused; widening them needs a per-helper audit that no argument reaches a generated script, config or R template unquoted.
- **D3** `$` inside single quotes (a regex anchor such as `'foo$'`) stays refused.
- **D4** Settled, not deferred: the per-tool flag allow-list already exists (Decision 5).
- **D5** The R-092 message and its `alternative` are generic; a message that says "quote literal operators, braces, tildes and parentheses" would help visitors. Wording only.
- **D6** After fix 1, bare `cat`/`head`/`tail`/`wc`/`shasum` are judged as reading `.` while the binary reads its (empty) standard input; harmless, as `grep PATTERN` with no path already was.
- **D7** `grep -E` (and `-F`, `-w`) are not in grep's vocabulary; add them only on a visitor's need.
- **D8** (review r1) A glob component such as `.*` can match `..` under bash before 5.2 (the macOS system bash is 3.2), so `cat .*/projects/closed/…` from a public folder reaches a closed project at `4597dd4` and here alike. Closing it needs the glob modelled, a separate change.
- **D9** (review r2) With a closed project under the working folder, a quoted regex holding a glob byte is judged as a path (`rg -n '\d{4}' CONTEXT.md` is refused); pre-existing, and it errs toward refusing.
- **zsh `=word`** A word beginning with `=` expands to a command's path in zsh; the committed zsh comparison excludes such words by name.
- **Review r3 was not held.** Review r3 of `792a4cf..dbebd7c` was stopped by Claude's safety classifier at 13:57:41Z and not retried; the r3 range is exactly r2's proposed fix, verified by r2 on a patched copy and by the lane's mutation proof killing `(` and `)` individually; no further independent review of that range.

## Test

`gars/tests/test_guard_hook.py` gains three tests (every registry command bare, in a plain and a closed-project fixture, never crashes; bare `ls` lists; every bare filesystem call equals its `… .` spelling, exit code and rule).
`gars/tests/test_bash_lexer.py` is new, 16 tests through the guard with json-built payloads: the reported commands; unquoted/quoted pairs for every operator in both quote kinds; expansions and line breaks refused in every quote state; the quote-boundary rows; word-start comments against literal hashes; brace, tilde and parenthesis rows against their quoted literals; helpers and the dispatcher staying strict; the filesystem executables read from the registry; a harvested table of refusals from the existing suite, still refused, counted per source file; and a real-shell comparison in which every accepted row's argv from bash and from zsh (`printf` in place of the command, skipped when the shell is absent) must equal the tokenizer's.
They must fail when the bounds check goes, when the default path is not judged, when the quote state is dropped, when a backslash escapes inside single quotes, when `\\` stops escaping inside double quotes, when `$` is let through, when the filesystem-first-word condition goes, when an escaped unquoted operator is accepted, when a word-start `#`, a tab boundary, or any one of `{`, `}`, `~`, `(`, `)` is let through, or when a quoted operator is never flagged.
The lane's mutation proof at the branch head killed 16 of those 17 mutants with the unchanged control green; the survivor, the open-quote refusal dropped, is covered by `shlex` raising the same refusal and is not counted as a kill.
The suite total moves from 1125 to 1144.
The landing's evidence is recorded in 0166.

## Status

Standing. The change record for the guard-lexer follow-up; its protected-change approval is 0166.

## Date

2026-09-27
