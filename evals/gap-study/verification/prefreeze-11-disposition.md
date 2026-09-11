# What was done with each finding of `reviews/review-11.md`

Review 11 read the pre-registration at sha256 `173ec63d40b38fca66a449411ae405a6fd8324cbf91df6f9c56c610d5bedc174` and ruled **do not freeze**, with four blockers and seven follow-ups.
Its closing observation mattered most: each new guard had been verified against a constructed string rather than against the channel it claims to cover, and one take driven end to end into a throwaway tree would have found all three code blockers.
So every fold below was checked on a real session as well as in a test, and each new guard was watched failing.

Reviews 8 to 11 are committed verbatim under `reviews/`.
The next pre-freeze review will be `prefreeze-12.md` in this folder.

## The four blockers — all folded

**BLOCKER 1 — the checkout carried the study in its history and its status.** Folded.
`clean_run_tree()` no longer clones.
It exports the pinned commit with `git archive`, minus the pre-registered exclusions, into a directory of its own, initialises a new repository there, and commits once under the subject `checkout` with the identity `gars`.
Before the first turn, `run_tree_problems()` checks the built tree: no `CLAUDE.md` above it, no excluded path in it, one commit, no remote, a clean status, the neutral name and subject.
`TheRunTreeCarriesNothing` builds such a checkout from a repository whose history holds the study and reads it back through git: `git show HEAD:evals/gap-study/prereg.json` fails, and there is one commit, no remote and a clean status.
Watched failing: with the exclusions dropped, the driver refuses with "evals is in the checkout, so the agent could read this study".
On a real session (`verification/run-tree-smoke/4/report.json`): one commit, subject `checkout`, no remote, empty status, git user `gars`, and no leak word in the loaded context.

**BLOCKER 2 — the checkout's path named the study.** Folded.
The checkout is named `run-<8 hex>` from the session id, like the project, under the machine's temporary directory; `RUN_ROOT` is gone.
Watched failing: with the study's name prefixed, the driver refuses with "the checkout is named 'gap-study-run-18b7f9c2', not the neutral name for its session".

**BLOCKER 3 — the driver looked for the transcript in the wrong place.** Folded.
`session_dir()` and the dead `STAGING` are gone.
`session_file()` finds the transcript by the session id the driver imposed, wherever Claude Code wrote it, and refuses when more than one file carries that id; a test covers found, absent and duplicated.
On real sessions: all four smokes found their transcript by id, and so did `number-fidelity` walk 2, after a resumed turn in its checkout.

**BLOCKER 4 — the `downgrading` excusal recorded a false reason.** Folded by removal.
The entry is gone from `leak_context_excusals`.
The test and the docstring that repeated the claim now use the evidenced case, `score` occurring only as `scored`.
Ruling 8's sentence is append-only; Ruling 9 corrects it.

## The follow-ups

**F1 — the excusal forgave by proximity.** Folded.
A pinned phrase now covers a hit only when the hit lies wholly inside an occurrence of it.
`test_an_excusal_forgives_only_what_it_contains` uses the review's own string.

**F2 — the leak list could not name the study.** Folded.
`gap-study`, `gap study`, `prereg`, `pre-registration` and `pre-registered` are on `leak_words`.
On the committed walks the check now reports the study's name in the git status of seven of eight, where it reported none.
`test_the_guard_sees_the_study_named_in_each_walks_git_status` binds that to the bytes.
Watched failing with the names dropped: "plan-gate/1: its git status names ['gap-study', 'prereg'] and the guard reported []".

**F3 — the inheritance check predicted rather than read.** Folded, and it found more than the review expected.
`check_take.inherited_context()` reads what the session recorded it was given: every instruction file inside the checkout, no additional working directory, and no account-connector tool.
The first smoke, in a clean checkout, recorded two working directories granted by the operator's user settings and 49 account-connector tools, mail among them, in auto permission mode.
All eight committed walks carry both, with 11 connector tools each.
The driver now sends `--setting-sources project,local` and `--strict-mcp-config`, and sets `ENABLE_CLAUDEAI_MCP_SERVERS=false`, the documented switch for the connectors, because what `--strict-mcp-config` reaches is not documented.
Smokes 2 to 4 recorded neither, and a test binds the pre-registered flags and environment to the driver's constants.

**F4 — repository content about the evaluations outside `evals/`.** Folded in part, with the rest named.
`docs/EVALS.md` and `.github/` are excluded beside `evals/`.
A sweep of the built checkout finds four remaining lines, in `README.md` and `docs/RESULTS.md`, that say this repository's agent has been evaluated without describing a probe; `run_location.residual` names them and says why they stay.
`DEVELOPMENT.md`, the review's example, carries no line naming the evaluations: its scored campaigns are the system's own reproduction work.

**F5 — checkouts were reused.** Folded.
One checkout per take, refused if it already exists, removed when the take ends.

**F6 — the walks' no-leak test measured post-scrub bytes.** Folded.
It is replaced by the test under F2, which asserts what the committed bytes do carry and goes red when the guard is blinded.

**F7 — the clone kept its origin.** Folded.
The checkout has no remote, and `run_tree_problems()` refuses one.

## Found while folding: the account's email address

Claude Code 2.1.267 injects the signed-in account's email address into every session as `session_context.userEmail`, and no documented setting removes it.
It is not a leak of the study, but it is the operator's personal address, and the study's own test refuses any published walk that carries it, which is how it was caught on walk 2.
`scrub.py` removes that one field from the new walk's and the smokes' published transcripts, asserts that every record a grader reads is unchanged, and writes the sha256 before and after to `scrub.json`.
Whether a graded take's transcript may carry the same removal is the repository owner's decision, and it is open.

## Evidence at the end of this pass

- `python3 evals/gap-study/test_harness.py` → 66 tests, OK
- `python3 evals/gap-study/test_harness.py --mutations` → every one of the 18 guards went red when broken
- `python3 evals/gap-study/check_take.py evals/gap-study/walks/number-fidelity/2/transcript.jsonl --task number-fidelity --half control --walk` → valid
- the same checker over the eight earlier walks → all eight refused
- `python3 evals/check_results.py --controls --lexicon` → clean, and `python3 evals/run.py --all` leaves the first study's results byte-identical
