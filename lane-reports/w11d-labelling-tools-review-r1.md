# Review round 1: w11d-labelling-tools

Written Mon 12 Oct 2026, 18:23 EDT (`date`), by a fresh reviewer (Claude Opus 5.5), on construction.
Branch `gap4/w11d-labelling-tools`, base `f14ab57b`, head reviewed `bc0f0c0c`.
Read: the lane report, the brief (next-slices-plan-2026-10-12.md, "### w11d-labelling-tools"), rulings Q-w11d-1..5 (accepted as proposed), the full diff of `labelling/sample.py`, `labelling/sheet.py`, `labelling/agreement.py`, and the test file's checks, witnesses and mutation machinery.
No code was edited; nothing was pushed, merged or launched; nothing under the three holdout paths was touched.

VERDICT: CHANGES

## Findings

| ID | Severity | Path:line | Requirement | Evidence | Bounded fix | Loosens a check |
|---|---|---|---|---|---|---|
| R1-1 | MAJOR | evals/gap-study-4/labelling/agreement.py:223-224, 249-251 (pinned by tests/test_labelling.py:1075-1078) | (c) every printed figure re-derivable by `--check`; (d) unmeasured stays unmeasured; labels.json committed once and unchanged | `derive` returns None whenever labels.json is absent from disk, and `check` then prints "no labels; nothing measured" and exits 0 without looking at AGREEMENT.md or at labels.json's history. G5 itself writes the golden page, unlinks labels.json, and asserts exit 0. So a page full of agreement figures with no labels behind it passes `--check`, and so does labels.json committed once and deleted in a later commit (the page stays, the history is never read). Under D6 B the same path lets a stray AGREEMENT.md stand beside "grader agreement unmeasured". The same shape in sample.py:266-267 and 285-287: a sample.json with no frame and no results passes `sample.py --check`. | In the "no labels" branch, fail when AGREEMENT.md exists, and fail when `git log --full-history -- labels.json` names any commit (labels once committed may not vanish); likewise `sample.py --check` fails when sample.json exists with nothing to derive it. Turn G5's line 1075-1078 case into a refusal, add the deleted-after-commit case to G6R, and add witnesses for both. | Yes |
| R1-2 | MAJOR | evals/gap-study-4/labelling/sheet.py:55-56, 66-71, 80-82 | (a) no path lets the labeller see a take's model through text | `hidden_tokens` masks only the whole design ids, the harness names and a hand list of vendor words, so the distinctive parts of the design's own ids survive, and `leak_problems` passes the result. Run on prereg-draft's harness_models: "I am GPT-6.1 Sol, running in Codex CLI" renders "I am [hidden]-6.1 Sol, running in [hidden] CLI"; "As Gemini 3.5 Flash-Lite I stop here" renders "As [hidden] 3.5 Flash-Lite I stop here"; "Claude Haiku 4.5 here" renders "[hidden] [hidden] 4.5 here" (Haiku is the only 4.5 model); "I am Luna" passes untouched. Each leak list is empty. These are not words "off these lists" (the docstring's stated residual): they are components of the ids the design itself names. K2 tests only synthetic ids (m-alpha, m-beta, m-gamma), which have no such parts. | Derive the hidden set from each design id: a separator-insensitive pattern of the whole id (-, _, ., space interchangeable, so "Claude Haiku 4.5" matches claude-haiku-4-5-...) and each alphabetic component of three or more letters (sol, luna, flash, lite, ...); have `leak_problems` refuse (not mask) a version number next to a mask ("[hidden]" followed by an optional separator and a digit), so a human rewrites that take's content. Add a K2 case built from the real prereg-draft harness_models with the four strings above, plus witnesses for the component and separator rules. | Yes |
| R1-3 | MINOR | evals/gap-study-4/labelling/sheet.py:19-21, 59, 92-94 | (a) no path through action names | The docstring says the neutral format means "no harness's own tool names ... reach the sheet", but `NEUTRAL_ACTION` binds only the verb: "run apply_patch", "write update_plan", "run exec_command ls" and "read AGENTS.md" all fullmatch and pass the leak check (run above). The guarantee rests wholly on the unbuilt CP8 reader (Q-w11d-2) while this file claims it. | Either add a refused-object list (each harness's own tool names and its instruction-file names, e.g. AGENTS.md, apply_patch, update_plan, exec_command, TodoWrite, run_shell_command, with a test per harness), or narrow the docstring to the verb and move the object rule into Q-w11d-2's slice as a named acceptance test. | Yes |
| R1-4 | MINOR | evals/gap-study-4/labelling/sheet.py:175 | Q-w11d-3: the sheet is never written inside the study folder | Reviewer mutant `startswith(_STUDY + os.sep)` -> `startswith(_HERE + os.sep)` survives every check: K6 and X1 only try `labelling/sheet.md`, so the study-wide scope is unbound. The guard also compares `abspath` strings, so on this Mac's case-insensitive disk a lower-cased path into the study folder is admitted. | Compare `os.path.realpath` with `os.path.normcase` (or `os.path.commonpath` on real paths), and test an `--out` in the study root and one spelled in another case. | Yes |
| R1-5 | MINOR | evals/gap-study-4/labelling/agreement.py:159 | (c) the pooling ban, each row holds only its own takes | Reviewer mutant dropping `rec["task"]` from the pool key (so a row may hold another task's take of the same model) survives every check; witness pool-take-unchecked deletes the whole test, never this part. | Add a G4 case with a row holding a same-model take of another task. | Yes |
| R1-6 | MINOR | evals/gap-study-4/labelling/agreement.py:139 | (c) every printed figure correct; the dominant real row shape | Reviewer mutant replacing a row's bounds with ("0.000", "1.000") whenever n is 1 survives every check, golden page included: the fixture has no row of one labelled take. Q-w11d-4 says most real rows will hold 1 to 3. | Add rows with n = 1 (x = 0 and x = 1) to the fixture and pin their exact bounds as literals. | Yes |
| R1-7 | MINOR | evals/gap-study-4/labelling/agreement.py:214 | the generated sweep is clean (athena's gate) | `--generated-mutants --shard 40/40` (not in the builder's sample): "SURVIVED agreement: bool-drop#0 L214 6ecc14bf rc != 0 or blob != disk"; 41 ran, 39 killed, 1 equivalent, 1 survived, so the whole sweep on athena exits 1. Listed because it turns athena's gate red, not because it loosens a binding (a failed `git show` gives an empty blob, which a valid labels.json never equals). The same run prints "message-text strings skipped by rule: 79"; the lane report says 76. | Kill it with a G6 case where `git show` fails on a file whose text is empty (or list it EQUIVALENT with that reason), and correct the report's 76. | No |

## What holds

- Tests: 74 run, OK (`timeout -s INT 120`, python3.13, behind `mac_slot.py light-ok`).
- Witnesses: 34 of 34 red, registry 34.
- Generated sweep sampled: shard 4/40, 42 ran, 42 killed; shard 40/40 as R1-7.
- Reviewer mutants (37, operators the generator lacks: slice and key changes, sort removal, arithmetic and factor changes, argument swaps, weight replacement, Bonferroni and ceiling changes, history-log narrowing, row-key reordering): 33 killed. The four survivors are R1-4, R1-5, R1-6 and one near-equivalent in `split` (`>=` to `>` on the cap at sample.py:204, where a stratum given exactly its cap is still set to its cap, so the cap is never passed).
- EQUIVALENT audit (27): the 3 `return None` entries are identical mutants (sample.py:267, agreement.py:99, 224). The 24 import-plumbing entries are equivalent only under the test's own sys.path; run as a script, deleting the `_STUDY` insert would break `import stats`, but X1 runs the unmutated file, so this is honest as stated and no guard depends on it.
- Blindness by ordering, ids and counts: sheet ids come from one seeded shuffle after the per-stratum draws, the sheet orders by sheet id, items carry only sheet id, task, text and actions, and `render` refuses any other key. Inferring a hidden field from order needs the frame and the seed together, that is, sample.json itself.
- Reproducibility: one `random.Random(seed)`, sorted frames, byte-for-byte comparison of sample.json, and the design read only from prereg.json; the factors and the frame and drawn weights are each bound by their own tests.
- Pooling: rows only by (arm, harness, model, task), with no line across them.

## Residuals (not findings)

- sample.json is the key, and it sits in the same tree as the labeller's labels.json: blindness rests on Javier not opening it (the docstring says so). The same holds for the `--contents` file, which is keyed by take id; whoever runs sheet.py should not be the labeller.
- frame.json's `readers` flag and each take id's link to its record are not bound to anything here (the frame binds only its records to the results); this belongs to Q-w11d-2's reader slice, which should bind the take id to the record's try key.
- A (arm, harness, model, task) cell with no drawn take gets no row at all, not an "unmeasured" row; the page does not say rows are missing. Worth one sentence on the page.
- Not run on the Mac (rule): the whole generated sweep, test_round4.py, test_scaffold.py, and the gates; athena's.

# Round 2

Written Mon 12 Oct 2026, 19:12 EDT (`date`), by the same reviewer, on head `5958190f` (fold of ruling w11d-R1-fold; tests first at `60b114bf`).
Every run used `timeout -s INT 120` and python3.13 behind `mac_slot.py light-ok` (the reviewer waited whenever it held), and only targeted mutants and two sweep shards were run (the Mac reached load 57 this evening).

VERDICT: CHANGES

## Findings

| ID | Severity | Path:line | Requirement | Evidence | Bounded fix | Loosens a check |
|---|---|---|---|---|---|---|
| R2-1 | MAJOR | evals/gap-study-4/labelling/sheet.py:92-95, 125-127 | (a) the text must not reveal the model (R1-2 not yet closed) | The fold lists its separators (`[-_. ]?`) in `id_pattern`, `VERSION_AFTER` and `NEIGHBOURS`, so the next spelling of a model's name gets through. Run on prereg-draft's real harness_models, each of these renders with an empty leak list: "GPT‑6.1‑Sol" with U+2011 non-breaking hyphens (the way GPT models usually typeset their names) gives "[hidden]‑6.1‑[hidden]", which names gpt-6.1-sol exactly; "GPT‑6‑Luna" gives "[hidden]‑6‑[hidden]"; "Gemini" + U+00A0 + "3.8" gives "[hidden] 3.8"; "Haiku v4.5" gives "[hidden] v4.5"; "Haiku: 4.5", "I am Haiku, version 4.5" and "Sonnet (5.5)" keep the version beside the mask; and "Opus\n5.5" and "I am CLAUDE\nHAIKU\n4.5" (an id split across lines) keep "4.5" or "5.5" after a masked line break. The ASCII spellings ("GPT-6.1 Sol", "Opus 5.5", "haiku4.5") are now masked or refused, as the fold report says. | NFKC-normalise the text before masking, and fold the Unicode dash and space classes into one separator class. Make the separator in `id_pattern` any short run of non-alphanumeric characters (`[\W_]{0,3}` with whitespace and newlines included). Let `VERSION_AFTER` and `NEIGHBOURS` allow up to about 12 non-alphanumeric characters or words such as "v", "version" and "ver" between the mask and a digit, so that a human rewrites the take. Add K2 cases for each string above. | Yes |
| R2-2 | MINOR | evals/gap-study-4/labelling/sheet.py:78, 158 | R1-3: every harness tool name is refused in an action; the sweep is clean | Shard 24/40 prints "SURVIVED sheet: str-change L78 'glob'": Gemini's `glob` can be renamed and "run glob" is then accepted, so not every listed name is bound by a test. The same shard prints "SURVIVED sheet: return-none L158 return False", which is equivalent in use (`None` is falsy) but is not listed, so athena's whole sweep exits 1. | Add a K4 loop that refuses "run <w>" for every w in every HARNESS_WORDS list (the same loop binds Q-w11d-6's lists at the merge). List the L158 mutant as an identical-mutant entry, or make `harness_word` return the `any(...)`. | Yes |
| R2-3 | MINOR | evals/gap-study-4/labelling/agreement.py:123 | (d) unmeasured stays unmeasured: every empty frame cell prints its unsampled line | Reviewer mutant `cells = sorted({... for e in frame if sample.verdict(e) == "wrong"})` survives every check. A cell left empty whose frame takes are all "right" then gets no row, silently. G9 checks that some unsampled line is printed, never that the set of rows equals the set of frame cells. | Have G9 assert that the rendered rows' keys equal `{stratum[:4] for e in frame}`, using a fixture that leaves an all-right cell empty. | Yes |
| R2-4 | MINOR | evals/gap-study-4/labelling/sheet.py:140, 252 | R1-2 and R1-4 as folded | Two reviewer mutants survive. The first narrows the neighbour rule to residual parts that are digits (dropping `.lower()`), so a short non-digit id part beside the mask is never tested; the real ids' residual parts are all digits today, so it is latent. The second makes `inside_study` use `abspath` instead of `realpath`, so the symlink half of the fix is never exercised. | Add a K2 case with a short alphabetic id part (the synthetic ids' "m") beside the mask, and a K6 case whose `--out` passes through a symlink into the study folder. | Yes |

## Round-1 findings, re-checked

- R1-1: closed. G5 and G6R refuse three cases: a standing page without labels, labels that were committed and then deleted, and a shallow clone. The reviewer's `if len(shas) > 1`, `isfile(PAGE)` and `isfile(SAMPLE)` mutants are all killed.
- R1-2: closed for ASCII spellings. "GPT-6.1 Sol" and "Gemini 3.5 Flash-Lite" are masked whole; "Claude Haiku 4.5", "GPT 6.1", "Opus 5.5", "haiku4.5", "Sol-6.1" and "3.8 flash" are refused; "I am Luna" is masked. Open for the spellings in R2-1.
- R1-3: closed in the main. "run apply_patch", "read agents.md", "write Edit" and "run Bash" are refused in actions, and apply_patch, TodoWrite, run_shell_command and AGENTS.md are refused in text. The one gap is R2-2.
- R1-4: closed. The reviewer's `_HERE` mutant is killed, and so is the drop of casefold. The symlink half is R2-4.
- R1-5, R1-6 and R1-7: closed. The pool-task witness and the n = 1 literal bounds are red when removed, and a G6 case kills the bool-drop at agreement.py L214 (now moved).

## Test expectations changed after the red run (60b114bf to 5958190f), each checked

- In K2, the expected outputs for "GPT-6.1 Sol" and "Gemini 3.5 Flash-Lite" went from a version-number refusal to masked whole. This is a true reason: with separators interchangeable, the whole id matches before any part does. A new "GPT 6.1 here" case keeps a refusal for a version after a mask.
- In K2, the expected leak lists gained the id-part line. This is a true reason: a digit beside the mask is both a version and a residual id part, and both rules fire.
- In G5, the committed-and-deleted message is now checked by prefix and suffix rather than exactly. This is a true reason: the temporary labels path, relative to the repository, varies per run. The exit code and both ends are still bound, and the reviewer's `len(shas) > 1` mutant is killed.
- In G9, about_n went from 6 to 4. This is plausible: it leaves a frame cell empty so that the unsampled line is drawn. Both witnesses, one-take-bounds-widened and unsampled-cells-dropped, are red.
- In G3 and G6, two cases were added to kill two sweep survivors. These are additions, not loosenings.

## What holds

- Tests: 89 run, OK.
- Witnesses: 48 of 48 red.
- Sweep shards: 8/40, 48 ran and 48 killed; 24/40 is R2-2.
- Reviewer mutants, re-anchored and extended to 50, with one anchor that is ambiguous now: survivors are R2-3, R2-4, and four that do not loosen a check.
  - The cap `>=` to `>` in `split` is near-equivalent, as in round 1.
  - `sorted(out)` to `out` in `rows` is now equivalent, because the rows are seeded in sorted order.
  - Dropping the left word boundary of an id part only masks more.
  - Printing the first row's confusion block when it is unsampled adds no figure.
- EQUIVALENT: 27 entries at their new lines, the same two kinds as round 1, and still honest.

## Residuals (not findings)

- A version number on its own is not refused: "I'm version 4.5 of my family", "I am the 4.5 model" and "model: 6.1" pass. Each is a weak signal without a family word, and refusing every digit pair would refuse ordinary content. Javier's call whether the CP8 reader should flag the design's version strings ("4.5", "5.5", "6.1", "3.5", "3.8") for a human pass.
- Harness furniture outside the tool lists passes and is left to the CP8 reader (Q-w11d-2):
  - "[hidden]-cli 0.144";
  - "~/.[hidden]/config.toml" (a Codex-only file);
  - "[hidden]_ENTRYPOINT";
  - "[hidden] CLI", which separates the two non-Claude harnesses from Claude Code.
  The new acceptance-test sentence in the docstring is the right place to name them.
- "run shell_command ls" is accepted. Whether `shell_command` is a Codex tool name is for Q-w11d-6's binding to the Codex module, which the reviewer could not check on this base.

# Round 3

Written Mon 12 Oct 2026, 20:04 EDT (`date`), by the same reviewer, on head `4be4269e` (the token road of ruling w11d-R2-fold; tests first at `99ae098d`).
Only targeted runs were made, each behind `mac_slot.py light-ok` with `timeout -s INT 120` and python3.13; athena runs the sweep.

VERDICT: CHANGES

## Findings

| ID | Severity | Path:line | Requirement | Evidence | Bounded fix | Loosens a check |
|---|---|---|---|---|---|---|
| R3-1 | MAJOR | evals/gap-study-4/labelling/sheet.py:147, 176-195 (tests/test_labelling.py:735 pins it) | (a) the text must not reveal the model; the round-2 refusal of a version beside the mask | The token road masks only whole design versions (5 5, 4 5, 6 1, 6, 3 8, 3 5 and the date part). The round-2 backstop that refused a digit beside a mask was dropped: the residual now holds only alphabetic parts, which are empty on the real ids, and K2 now asserts that a lone 4 is not hidden and removed the "[hidden] 5 stars" refusal. A family's major version on its own therefore passes with an empty leak list, and on this design the major version names the family: "I am Gemini 3" gives "I am [hidden] 3" (only Gemini is a 3), "Gemini 3 Flash here" gives "[hidden] 3 [hidden] here", "I'm Claude 4" and "Haiku 4" give "[hidden] 4" (only Haiku is a 4), "I am Sonnet 5", "Claude Opus 5" and "Claude 5 family" give "[hidden] 5" (Opus or Sonnet), and "I'm a Gemini 3-series model" and "Gemini 3.x" do the same. A model naming itself by family and major version is ordinary self-description. | In `leak_problems`, refuse any digit token adjacent to a mark in the token stream (only separators between them), so a human rewrites that take; ordinary numbers away from a mark ("16 files", "4 cats") stay untouched. Or add each design version's leading digit run to the sequences only where it is adjacent to a mark. Add K2 cases for the strings above. | Yes |
| R3-2 | MINOR | evals/gap-study-4/labelling/sheet.py:101-112 | (a), and the backstop's "any hidden sequence left" | Invisible format characters (Unicode category Cf) are read as separators, so a name split by one is neither masked nor refused, yet shows to a human as the name. "Hai" + U+00AD (soft hyphen) + "ku", "Hai" + U+200D + "ku", "Hai" + U+200B + "ku" and "Gem" + U+2060 + "ini" each pass `mask` and `leak_problems` unchanged. | In `tokens`, drop characters of category Cf (no separator, no letter) before grouping, and add K2 cases for U+00AD, U+200B, U+200D and U+2060. | Yes |

## Round-2 findings, re-checked

- R2-1: closed for every round-2 string. "GPT‑6.1‑Sol" (U+2011) and "GPT‑6‑Luna" mask whole. "Haiku v4.5", "Haiku: 4.5", "I am Haiku, version 4.5", "Sonnet (5.5)", "Opus\n5.5", ids split across lines, NBSP, full-width forms, "I'm version 4.5" and "model: 6.1" are all masked, and each raw string is refused by the backstop. The remaining gap is R3-1's major-version digit, which this fold opened.
- R2-2: closed. My "add a word" mutant is killed by the pinned lists, the "run <w>" loop covers every word, and `harness_word` returns `any(...)`.
- R2-3: closed. My "cells from failed takes only" mutant is killed by G9 ("the rows are not every frame cell").
- R2-4: closed. My `realpath` to `abspath` mutant is killed by K6's symlink case, and the short-part neighbour mutants (left-only, mark without brackets) are killed by K2.

## Test expectations changed after the red run (99ae098d to 4be4269e), each checked

- "codex-cli 0.144" now masks to "[hidden]-[hidden] 0.144". This is true: `cli` is a FURNITURE sequence of its own, so there are two spans.
- The U+2011 witness now compares against U+2010. This is true: NFKC decomposes U+2011 to U+2010.
- The removal of the digit-beside-mask assertions happened in the tests-first commit (99ae098d), not after the red run. It is the source of R3-1, not a test error.

## What holds

- Tests: 95 run, OK.
- Witnesses: 54 of 54 red.
- Targeted reviewer mutants: 12, of which 10 were killed. NFKC dropped is killed by K2's full-width case; the furniture, version stretches, mark brackets, neighbour side, sequence order and date part are each killed. The two survivors loosen nothing on this design: `casefold` to `lower`, and a residual built from models only (the harness names have no short parts).

## Residuals for Javier (out of scope: a model does not write its own name this way unprompted)

- Homoglyphs from other scripts pass: "Sоnnet" (Cyrillic о), "Clаude" and "Hаiku" (Cyrillic а), "Ηaiku" (Greek Eta), and "ǫpus". NFKC does not map scripts. A confusables fold (Unicode TR39 skeleton) would close them if he wants it.
- Spelled-out names pass: "H a i k u", "C-l-a-u-d-e" and "S.o.n.n.e.t", and so do number words such as "Haiku four point five" (the name is masked but "four point five" is left).
- Escapes and markup pass the token road: "&#72;aiku", "&#x48;aiku", "Hai&shy;ku", "**Hai**ku", "Hai`ku`" and "Haiku". Inside the text's ``` fence these show literally. `render` (sheet.py:275) puts the text between fixed ``` fences, so a take whose text holds ``` closes the fence, and what follows renders as Markdown and HTML, entities included. Actions render as list items, where entities decode. A fence longer than any backtick run in the text, and escaped actions, would close this. Worth one line in the CP8 brief.
- Misspellings pass: "Claud", "Sonet", "Gemeni", "Antropic" and "OpenAl". Digits from other scripts ("٤.٥") also pass.
- Over-masking is accepted by ruling: every lone "6" and the word "code" are masked.
