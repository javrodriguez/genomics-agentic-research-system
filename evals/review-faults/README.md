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
  and notebook_path) that are absolute, start with a tilde or the HOME expansion
  in any modifier form, or contain a parent component, are checked against the
  kit, item 19's store and the system allowlist. Symlinks resolve before checking.
  The system trees are usr, bin, sbin, lib and lib64 at the filesystem root; only
  the null, stdin, stdout and stderr devices are allowed in the device directory.
- Rule (ii): separator-only words in command fields are hits by default. Only
  delimiter-option values (-F, -d, --delimiter, --field-separator, in their option
  context), interpreter -c/-e program text, and write/edit content are exempt.
  A directory-listing option is not a delimiter option. Visible separator words
  in quoted arguments (including dollar-quoted separators) and assignment values
  are counted without evaluating them.
- Rule (iii): prose fields (description, Grep pattern, agent prompt) get rule (i)
  only, never the separator-word rule. Named outside paths still count there.
- Rule (iv): cd is found in the shlex word stream after shell keywords, prefix
  commands and their options, or a leading backslash. It is bare, and a hit,
  when every argument is an option word. Redirect descriptors, operators and
  their targets do not supply a directory argument. Explicit in-kit arguments stay
  clear. Nested shell option clusters ending in c and full-path shell names are
  recognized for this bare-directory audit.

The default separator rule can invalidate ordinary review commands: quoted text
with a spaced separator, awk division, sed substitution text and git log formats
are not exempt unless they use a listed context. A prefix command can hide the
delimiter-option context. The shell-word audit also treats an echoed cd word as
bare. These conservative false positives are expected under item 20; no additional
context exceptions are introduced before the first measured run.

**Named residual:** the scan does not follow shell indirection it cannot see
statically: variables and assignments, command substitution, evaluated strings,
aliases, functions, nested shells beyond those it parses, brace expansion,
parameter-default expansion, URL-embedded paths (including file-scheme URLs), or
interpreter program text. Those reads are the sandbox's to refuse; if the sandbox
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
