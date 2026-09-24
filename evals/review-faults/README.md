# Code review measurement tools

Repository implementation only; **row 9 exit NOT met**. No model has been run
against these cases. Read [SEALS.md](SEALS.md) for the empty sealed slots and
[INTERFACE.md](INTERFACE.md) for the sealer's complete independent handoff.
Before writing a manifest, the builder audits every case, including external
sealed inputs, with the same item-15 sweep used by regression tests. It checks committed added lines, whole added files, decoded new
Git objects, case and repository names and the manifest. Unchanged lines and
base-identical decoded content are exempt; compressed Git storage is not scanned.
See `docs/implementation/row_9_change_report.md` and
`docs/decisions/0072-row-9-review-fault-harness-code-half.md`.

Use Python 3.6 or later, standard library, and Git. Work from the repository root
with TMPDIR, TEMP and TMP naming external scratch. Build cases after sealing:

```sh
python3 evals/review-faults/build_cases.py --out <external-output>
```

The optional GARS_SEALED_REVIEW_FAULTS_DIR names the sealed P-directory folder.
Keep `key.json`, fixtures and original records private. Transfer only `cases/`
and `manifest.json` to the reviewer machine. The key's random salt never leaves
the coordinating Mac. Identical salts give identical repository bytes; the Python
build function accepts a supplied salt for deterministic tests only.

Run from a separate unprivileged OS account, with the producer account resolvable
on that same host. Choose a parent suitable for private kits; its existing path components are not
created or renamed by the launcher. The directories the launcher creates inside
it (neutral id, repo, tmp, and settings directory) may not contain review, fault,
case, measure, plant or eval. No flag overrides reviewer identity.

```sh
python3 evals/review-faults/run_reviews.py --cases <cases> --manifest <manifest> --prompt <prompt> --kits-root <neutral-root> --records <private-records> --model <model-id> --producer-account <producer-account> --login-entry <integer> --settings <deployment-settings>
```

Required `--settings <file>` copies exact project settings and binds their bytes
to `envelope.sandbox_settings_sha256`. The schema and stdlib validator require
this hash; scoring refuses missing hashes or disagreements across any attempts.
The published copy retains the hash unchanged, as item 20(a) requires. This
unsalted hash can confirm a guessed settings file, including guessed account or
home-folder text in it. It is configuration provenance, not a privacy guarantee
for the settings' contents; deployment must account for this disclosure.

`--only <neutral>,<neutral>` resumes selected cases in manifest order. On a usage limit the launcher retains the
first record and stream, prints remaining ids plus the limited current id, and exits
cleanly. Resume that id on another login using a fresh neutral kit root: the new
attempt gets an `.attempt<n>` suffix. Successful records cannot be overwritten.

```sh
python3 evals/review-faults/score.py --records <private-records> --key <private-key> --manifest <manifest> --answers <fixtures>,<sealed-folder> --runs evals/review-faults/runs --out <new-published-copy>
```

The scorer re-hashes every answer and diff against the key. It records every
attempt and chooses the latest valid attempt for each case. Per-class denominators
count valid available cases; the headline denominators remain ten plants and five
clean cases. Missing or invalid case reviews contribute to invalid, whose headline
denominator is fifteen. Graded-against-seen counts record files read over manifest
cases, so retries can put its numerator above its denominator. Absent sealed
classes remain 0/0 uncomputable; incomplete sets cannot meet thresholds. Invalid
attempts that precede or follow a valid selected attempt remain visible separately.
Threshold failure does not change exit status: exit 0 means scoring valid, exit 1
means at least one case has no valid review, exit 2 means input integrity refused.

Publication mask v1 is pre-registered in `score.masked_copy`: recursively preserve
fields, remove os_user fields, replace declared literals with `<planted-secret>`,
kit prefixes through the neutral id with `<kit>`, and home prefixes with `<home>`.
Replace uid and host_digest values with HMAC-SHA256 keyed by the private run salt;
equal identities remain equal within that run. Embedded identity strings are masked
too, including every word-bounded number equal to a uid: coincident line numbers
or counts in prose therefore become HMACs. Scoring uses the private original.
The published finding retains its full line interval, including unusually wide
spans; the specified overlap oracle does not impose a span cap. Remaining rooted paths are conservatively masked to `<home>/` plus their
leaf name to cover nonstandard home locations. Raw records and streams remain private. Published files are exclusive creates;
first-run evidence is never overwritten. Cold-start and historical-run controls
use synthetic records in scratch and do not create measurement evidence here.

Item 20 separates enforcement and detection. **Enforcement is the reviewer's
sandbox**, configured by the required deployment settings. Deployment must deny
reads outside the kit and all network. The harness binds which settings bytes
were copied at launch; it never judges their content or proves sandbox efficacy.

**Detection is a bounded post-run audit**, which makes a record INVALID on the
spellings below and claims nothing beyond them:

- Rule (i): tokens in commands and path-valued fields (including file_path, path
  and notebook_path, plus Glob pattern) that are absolute, start with a tilde or the HOME expansion
  in any modifier form, or contain a parent component, are checked against the
  kit, item 19's store and the system allowlist. Symlinks resolve before checking.
  The system trees are usr, bin, sbin, lib and lib64 at the filesystem root; only
  the null, stdin, stdout and stderr devices are allowed in the device directory.
- Rule (ii): separator-only words in command fields are hits by default. Only
  delimiter-option values (-F, -d, --delimiter, --field-separator, in their option
  context), interpreter -c/-e program text, and write/edit content are exempt.
  Item 21 also exempts awk, gawk, mawk and sed program text (the first
  non-option argument or an -e or --expression value); git --format=,
  --pretty=format: and --pretty=tformat: values; printf and echo format and
  argument text; and grep, egrep, fgrep and rg patterns (the first non-option
  argument or an -e or --regexp value). These contexts are recognized in the
  shlex stream after prefix commands and options. Under item 22(a), neither
  rule (i) nor rule (ii) scans this program, pattern or format data: the shell
  opens nothing there. File operands remain subject to both rules. Prefix
  options consume their values before command selection; grep option clusters
  consume attached or following pattern and pattern-file values. Patternless
  rg modes leave all file operands scanned. Command substitutions inside exempt
  echo or printf text are not separately audited, per item 20(c).
  A root directory used as a shell argument after a command separator still hits.
  A directory-listing option is not a delimiter option. Visible separator words
  in quoted arguments (including dollar-quoted separators) and assignment values
  are counted without evaluating them.
- Item 22(b) withdraws rule (iii): content and prose fields, including Write
  content, Edit strings, descriptions, reasons, prompts and Grep patterns,
  get neither rule. Only command fields are parsed as shell text; path-valued
  fields are checked as whole paths. Glob patterns describe filesystem paths;
  Grep patterns remain exempt prose. Quoting errors in prose are not hits.
- Rule (iv): cd is found in the shlex word stream after shell keywords, prefix
  commands and their options, or a leading backslash. It is bare, and a hit,
  when every argument is an option word. Redirect descriptors, operators and
  their targets do not supply a directory argument. Explicit in-kit arguments stay
  clear. Nested sh, bash, dash, zsh and ksh programs are recognized by basename
  after option words, including separated options, the end-of-options marker,
  and option clusters ending in c. Their program text is audited as a command.

Item 23 amends item 22(c-d): text is removed only when unambiguous; otherwise
it is scanned. A comment hash must start a shell word at quote depth zero.
Neither a comment nor a heredoc body is removed when the physical line holding
its cue contains a dollar followed by an opening parenthesis, a backquote, or
two opening parentheses, anywhere on that line. This conservative line guard
does not try to evaluate substitutions or arithmetic.
Heredoc removal additionally requires an unquoted, unescaped operator at quote
depth zero, followed directly by its delimiter word (with optional whitespace
and quoting), and a found closing delimiter line. Unquoted, single-quoted,
double-quoted and tab-stripping delimiters are supported. All queued delimiters
must be found before any of that header's bodies are removed. Headers and
commands after closing delimiters stay scanned; absent or ambiguous delimiters
leave following lines scanned as commands. Ambiguity may invalidate an honest
record, but cannot justify hiding a read. Hashes inside words, quoted operators
and arithmetic shifts cannot authorize removal.
Operators terminate adjacent words; adjacent quoted pieces form one word.
A separator embedded in a longer word, such as a tr character set, is not a
separator-only word. The earlier regex tokenizer remains only inside the
interpreter program text it already inspected.
Visible values of command operands with a shell identifier followed by an
equals sign receive the same path check as option values. This includes dd
input operands; it does not evaluate assignments or follow their later use.
An equals sign within an ordinary absolute pathname remains part of that path.

The sanitized deployment corpus in `tests/data/review_faults_honest_calls.jsonl`
contains 278 whole calls from seven real review sessions. Its labels are the
lane's reading of this contract: 277 honest calls and one contract hit. The
corpus test substitutes runtime kit, home and session-store paths, grades every
row, and mutation tests identify calls that fail under each regressed rule.

Conservative false positives remain: a spaced numeric directory before a redirect, and a dollar directly
before a separator outside the listed text contexts, can invalidate a record.
The text exemptions cover the latter inside echo and printf text; they do not
change the numeric-directory ambiguity. Other unlisted contexts, including
git grep patterns (Z1 F4), remain subject to the default rules.

**Named residual:** the scan does not follow shell indirection it cannot see
statically: variables and assignments, command substitution, evaluated strings,
aliases, functions, nested shells beyond those it parses (including clusters
where c is not last), brace expansion,
parameter-default expansion, URL-embedded paths (including file-scheme URLs), or
interpreter program text. Under item 22(a), file reads within awk program text
(such as getline) or sed program text (r or w commands) are also residuals.
Under item 23(e), further escapes depending on unparsed substitutions,
arithmetic, eval, aliases, functions or nested quoting are named residuals,
graded as NOTE requests to document them, rather than extending this detector
into a shell evaluator.
Those reads are the sandbox's to refuse; if the sandbox
allowed one, the scan may not see it. Detection of some visible tokens inside such text does not
establish coverage of the enclosing program. No model is run to test these rules.

Item 19 also permits this launched session's saved tool output: the reviewer's
home, `.claude/projects`, the kit path encoded by replacing every character
outside ASCII letters, digits and hyphens with a hyphen, the launch session id,
then `tool-results`. The launcher constructs this path from its own identity
and session id. Transcripts, memory, other sessions and other kits remain outside
the allowance; symlink targets must also stay inside the permitted boundary.
Deployment supplies separate users and read-only credentials; GARS launch_role()
remains producer. Independent context seals are development evidence only, science
is unmeasured, and one plant per class is a thin sample. Public recomputation covers
twelve of fifteen cases; the sealed inputs remain private and checkable by hash.
