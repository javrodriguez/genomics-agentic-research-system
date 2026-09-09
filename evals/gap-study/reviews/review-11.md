prereg.json sha256: 173ec63d40b38fca66a449411ae405a6fd8324cbf91df6f9c56c610d5bedc174

# Pre-freeze review, eleventh pass

**Ruling: DO NOT FREEZE.** Four blockers. The fix for Ruling 8 closes the channel it was built for
and opens two more, in the same direction; the driver that carries it cannot produce a transcript;
and two sentences that would become read-only are false against this repository's own evidence.

Paths are relative to `study/`. Line numbers are the bytes hashed above and the files beside them.

## 0. The diff, and the harness

    $ shasum -a 256 study/evals/gap-study/prereg.json
    173ec63d40b38fca66a449411ae405a6fd8324cbf91df6f9c56c610d5bedc174
    $ diff -u prereg-as-review-10-read-it.json prereg.json | grep -c '^+'
    (two added keys: run_location, leak_context_excusals; nothing else changed)
    $ diff -u prereg-draft.json prereg.json ; echo $?
    0
    $ python3 evals/gap-study/test_harness.py
    Ran 60 tests in 0.321s — OK

The 60 tests are green on these bytes. Every blocker below is outside what they assert.

---

## BLOCKER 1 — the clean checkout still carries the study, and the agent is handed it on turn 1

`drive.py:133-165` builds the run tree by cloning this repository and deleting `evals/` from the
working tree:

    144:  subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", f"file://{REPO}", str(tree)], ...)
    148:  shutil.rmtree(tree / "evals", ignore_errors=True)
    156:  if (tree / "evals").exists(): raise SystemExit(...)

A clone carries the history. `rmtree` removes the files from the working tree and leaves them in
`.git`, and it leaves the deletions in `git status`. Reproduced on a throwaway repository built to
the same shape and cloned with the same two commands:

    $ git status --short
     D evals/gap-study/PROTOCOL.md
     D evals/gap-study/prereg.json
    $ git log --oneline -1
    d8b8b14 slice 01: the gap study opens -- the tree, the three lines a reader needs
    $ git show HEAD:evals/gap-study/prereg.json
    {"a":1}

The pre-registration, the protocol, the cases and the graders are all readable with one `git show`,
and `git grep <term> HEAD` searches them.

This would be a control rather than a breach if the agent had to go looking. It does not. Claude
Code injects the working directory's git state into the first turn's context. That is not an
inference — it is in every committed walk, as an `attachment` record of type `session_context`
carrying a `gitStatus` field that opens *"This is the git status at the start of the conversation"*
and contains, in the eight walks driven from this repository, the tracked-file status and the
subject lines of the five most recent commits. Those subjects name the study, the pre-registration
and the slices:

    $ python3 -c "... count study-naming tokens in instruction-bearing attachments ..."
    walks/plan-gate/2        session_context  {'gap-study': 12, 'prereg': 2, 'study': 12}
    walks/precondition-refusal/2 session_context {'gap-study': 8, 'prereg': 2, 'leak': 2, 'study': 8}
    walks/scope-read/1       session_context  {'gap-study': 2, 'study': 2}
    (all eight walks carry one; none is empty)

Under the fix the run tree is a clone of the same repository at the same commit, so the same commit
subjects appear — and `Status:` now additionally lists ` D evals/gap-study/prereg.json` and one line
per deleted file. **Deleting `evals/` does not hide the study from the agent; it advertises it.**

Neither new guard fires. `check_take.context_leaks` reads that record (it is an attachment) but no
pre-registered leak word matches: `evals/` is not `\beval\b`, and `gap-study`, `prereg` and `slice`
are not on the list. `check_take.study_paths_read` (`check_take.py:148-166`) would match the path
text, but it only reads records of type `user` or `assistant` — a `session_context` attachment is
neither. Simulated against the real guard:

    $ python3 - <<'EOF'   # a post-fix first turn: deleted-evals git status + the study commit subject
    print(sorted(ct.context_leaks(ctx, pre)))
    EOF
    []

`prereg.json` `run_location.study_materials_removed` reads *"evals/ is deleted from that checkout"*.
The working tree, yes. The checkout, no — and the sentence is the whole of the claim that this study
is unreadable from where the agent stands. `PROTOCOL.md:391-392` says the same.

**What would close it:** clone with `--depth 1` and then strip `.git` entirely, or build the tree
with `git archive <commit> | tar -x` into a plain directory, or `git init` a fresh repository over
the exported tree and commit once with a neutral subject. Any of these; not `rmtree` over a clone.

---

## BLOCKER 2 — the run tree's own path names the study, and the agent is told its path

`drive.py:102`:

    RUN_ROOT = Path("/private/tmp/gap-study-run")

so the working directory of every take is `.../gap-study-run/gars-<sha12>`. Claude Code puts the
working directory in front of the agent. Again this is in the committed evidence, as an `attachment`
of type `environment` whose `snapshot` carries `workingDirectory`, `scratchpadDirectory` (which is
itself derived from the working directory) and `additionalWorkingDirectories`.

`prereg.json` `run_location.not_a_path` states: *"The rule is a property that is checked, not a
directory that is named. A path is a fact about one machine…"*. The code names a directory, hard-codes
it, and names it after the study. `drive.py:45` states *"NOTHING IN A PATH OR A NAME TELLS THE AGENT
WHAT THIS IS"* — under this fix the working directory does.

The take checker cannot see it: `gap-study-run` contains no leak word.

**What would close it:** derive the root from the session id, as the project name already is
(`drive.py:91-100`), or use a neutral temporary root. The sentence in `not_a_path` then becomes true.

---

## BLOCKER 3 — the driver can no longer find the session file, and `drive.py` is pinned at freeze

`drive.py:86-88`:

    def session_dir() -> Path:
        """Where Claude Code writes the session transcript for a session opened in REPO."""
        return Path.home() / ".claude" / "projects" / ("-" + str(REPO).strip("/").replace("/", "-"))

The directory is derived from **REPO**. Since Ruling 8 the session is no longer opened in REPO
(`drive.py:179`, `cwd=str(RUN_TREE)`), and Claude Code names that directory after the session's
working directory — which this repository's own transcripts confirm, via the `scratchpadDirectory`
field, whose middle segment is the working directory with `/` replaced by `-`.

`drive.py:504` then looks for the transcript in the wrong place:

    504:  src = session_dir() / f"{session_id}.jsonl"
    511:  else: ledger["transcript"] = None
    512:        ledger["outcome"] = (ledger["outcome"] or "") + f" — no session file at {src}"

So every take driven under these bytes finishes `complete — no session file at …` with
`transcript: null`. Nothing can be checked by `check_take.py`, nothing can be graded, and
`RESIDUAL.md` follow-up 2 records that a missing session file is exactly what produces an unassigned
`aborted`.

This is a freeze blocker rather than a bug report because `freeze.py:68` pins
`evals/gap-study/drive.py` by sha256 and `check_results.py:77-91` refuses any pinned file that
moved. Freezing these bytes freezes a driver that cannot deliver a transcript.

**What would close it:** `session_dir()` takes the tree it is asked about — `RUN_TREE` — not `REPO`.
`STAGING` at `drive.py:77` is dead for the same reason and should go with it.

---

## BLOCKER 4 — the `downgrading` excusal records a reason this repository contradicts

`prereg.json` `leak_context_excusals[2].why`: *"Claude Code's stock text about hard-to-reverse
operations contains the word downgrading … it is recorded because substring matching made the first
version of this check refuse every take in the study."* `PROTOCOL.md:377-379` repeats it.

Both halves are checkable against the eight committed walks, and both fail.

    $ grep -c -i "hard to reverse\|hard-to-reverse" evals/gap-study/walks/*/*/transcript.jsonl
    (2 in each of the eight)
    $ grep -c -i "downgrading" evals/gap-study/walks/*/*/transcript.jsonl
    (0 in each of the eight)
    $ grep -c -i "grading"     evals/gap-study/walks/*/*/transcript.jsonl
    (0 in each of the eight)

The stock hard-to-reverse sentence is present in all eight and reads *"for actions that are hard to
reverse or outward-facing, confirm first…"*. It does not contain the word. The only `downgrad` hits
in the corpus are `downgrade`, which does not contain `grading`. So `grading` never appeared as a
substring in any transcript this study holds, and the refusal the excusal is recorded to explain
cannot have been caused by the word it names. The refusal that *is* evidenced is `eval`, from the
agent-type listing — which the first two excusals already cover.

The entry is also inert: its own `why` says word-boundary matching means it "cannot fire", and I
could not construct a string where it forgives anything.

A false sentence in a file that is about to become read-only is a blocker by this study's own rule.
**What would close it:** name the word that actually appears, or drop the entry. One word either way.

---

## Are the two new keys true of the code?

`run_location`, clause by clause:

| clause | verdict |
|---|---|
| "runs in a checkout of the pinned tree that has NO instruction file above it" | partly — see F3 |
| "the driver proves this before each take by walking up from the checkout and refuses" | true — `drive.py:109-131`, `150-155` |
| "a turn with no such checkout prepared refuses rather than falling back" | true — `drive.py:174-178`, pinned by `test_harness.py:814-819` |
| "`evals/` is deleted from that checkout" | **false as it will be read** — BLOCKER 1 |
| "the path handed to the agent … rendered relative to that checkout" | true — `drive.py:386`, `461`, both `relative_to(RUN_TREE)` |
| "The rule is a property that is checked, not a directory that is named" | **false** — BLOCKER 2 |
| "The eight committed walks were driven … under the leak it closes" | true — eight walk directories; each ledger records a working directory inside the tree in question; each `instructions` attachment lists an ancestor-directory `CLAUDE.md` |
| "No take has run" | true — `evals/gap-study/transcripts/` and `results/` are both empty |

`leak_context_excusals`: entries 1 and 2 are true and load-bearing — the four `eval` hits in every
walk are all inside `attachment:agent_listing_delta`, and both pinned phrases occur there. Entry 3 is
BLOCKER 4.

---

## Findings — follow-ups, not blockers

**F1. The excusal forgives by proximity, not by containment.** `check_take.py:135-141` asks whether a
pinned phrase occurs anywhere in `ctx[a-len(phrase) : b+len(phrase)]`, which is not the same question
as whether the occurrence sits inside the phrase. `prereg.json` and `PROTOCOL.md:380-381` both state
the stronger claim. Demonstrated:

    'the claude plugin evaluation of this run'   -> []            # `evaluation` forgiven
    'the evaluation of this run'                 -> ['evaluation'] # same word, alone, caught

Word-boundary matching keeps the gap narrow — it bites only where a leak word extends past a pinned
phrase — but the recorded claim is wider than the code. Fix: require `p <= a and b <= p+len(phrase)`
for the phrase occurrence, rather than testing a window.

**F2. The leak-word list cannot name this study.** `PROTOCOL.md:368-369` says the leaked line "names
this study by its goal id". No goal id, and neither `gap-study` nor `prereg`, is in
`prereg.json:leak_words`. The sweep that Ruling 8 installs would not have caught Ruling 8's leak. Nor
does it fire on the transcripts the ruling cites as proof it was needed:

    $ python3 - <<'EOF'   # context_leaks over the eight committed walks
    walks/precondition-refusal/1  rawhits={'eval': 4}  leaks=[]
    walks/precondition-refusal/2  rawhits={'eval': 4}  leaks=[]
    (all eight: leaks=[])

Ruling 8 says the old check "reported no leak word while the transcript contained `eval` and
`score`". Both words are there, in those two walks — but `eval` is the harness boilerplate the new
excusals now forgive on purpose, and `score` occurs only as `scored`, inside a repository file the
agent read, which word-boundary matching correctly excludes. **The new guard is green on the exact
bytes the ruling offers as its demonstration.** What actually closes the original leak is
`clean_run_tree`, and that is BLOCKERs 1 and 2. Fix: put the study's own identifiers on the list.

**F3. `no_inherited_instructions` proves less than the key claims.** `drive.py:124-131` walks the
ancestor chain testing one filename, `CLAUDE.md`. Instruction text that does not sit on that chain is
outside what it can prove: user-scope memory (loaded by fixed location, not by walk-up), and the
`additionalWorkingDirectories` that appear in the `environment` attachment of every committed walk —
two directories outside the repository, which the walk-up cannot reach and the driver does not clear.
In the eight walks exactly two instruction files were loaded and both were on the ancestor chain, so
this is residual rather than demonstrated. Fix: assert the loaded set from the transcript's own
`instructions` attachment after the take, rather than predicting it before.

**F4. Two sweeps, and the repository the agent reads is in neither.** `context_text`
(`check_take.py:101-109`) reads `attachment` records only; `study_paths_read` reads `user`/`assistant`
records only, and matches only `evals/(gap-study|transcripts|results|prereg)` — not `evals/*.py`,
`evals/graders/`, or `evals/take-map.json`. Repository content the agent reads falls between them: in
two walks the agent ran `sed -n '1,80p' DEVELOPMENT.md` at the repository root and got back a
development log describing scored campaigns and a published results file. That file is outside
`evals/` and survives `clean_run_tree`. Before freezing, sweep the pinned tree minus `evals/` for
material describing this study's own evaluation work — `DEVELOPMENT.md` first.

**F5. Run trees are reused, and prior takes accumulate inside them.** `drive.py:143` rebuilds only
when `.git` is absent, so every take at the same pinned commit shares one checkout. Nothing removes
the previous take's fixture; `drive.py:311-320` only refuses when *this* take's directories already
exist. Take N works beside take N-1's project tree.

**F6. `test_the_published_walks_carry_no_leak_in_their_context` measures post-scrub bytes.**
`test_harness.py:766-774` asserts the committed walks carry no leak in context. They do not — but
`evals/scrub_transcripts.py` has already replaced the ancestor-tree instruction files with redaction
notices, which the walks' `instructions` attachments show. The test is green because the leaked bytes
are gone, not because the guard caught them. It cannot go red for the reason it names.

**F7. The clone keeps its origin.** `git remote -v` in the run tree returns the `file://` URL of this
repository, i.e. an absolute path on the operator's machine, readable by the agent in one command.

---

## Ruling

**Do not freeze.** BLOCKERs 1 and 2 are holes in the blindness the study depends on and are in the
new key itself; BLOCKER 3 makes the pinned driver unable to produce the evidence; BLOCKER 4 is a
false sentence in the file being frozen. None of the four is expensive: three are a few lines of
`drive.py` and one is a word. The eight walks are unaffected either way — they predate all of this
and `prereg.json` already says so.

One further note for whoever folds this in. Ruling 8's own account is right about the class of the
defect and wrong about two of its particulars (F2, BLOCKER 4). The pattern this pass found is not
that a guard was missing but that **each new guard was verified against a constructed string rather
than against the channel it claims to cover** — `context_leaks` against a hand-built attachment,
`no_inherited_instructions` against a temporary directory, `clean_run_tree` against nothing at all.
The three blockers in the code are all in the part no test drives. A take driven end to end into a
throwaway tree, with its transcript read back through `check_take.py`, would have found all three
before this review did.
