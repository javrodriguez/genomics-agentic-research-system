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
python3 evals/review-faults/run_reviews.py --cases <cases> --manifest <manifest> --prompt <prompt> --kits-root <neutral-root> --records <private-records> --model <model-id> --producer-account <producer-account> --login-entry <integer>
```

Optional `--settings <file>` copies exact project settings. `--only <neutral>,<neutral>`
resumes selected cases in manifest order. On a usage limit the launcher retains the
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

This is a post-run blindness audit, following lane specification item 8, not an OS
sandbox. Tool path tokens are checked against the kit and the system allowlist.
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
