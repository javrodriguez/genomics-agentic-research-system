# The action reading of Gap Study round 4 (exploratory, post hoc)

**EXPLORATORY. This reading was made after the study's results were verified; it changes no published count, and the study's counts stay as graded.**
It is not on the study's records line: it was never part of the pre-registration, the run, the grading or the verification of round 4.
The round 4 report (`docs/gap-study-4/REPORT.md`, section 4.4 and Appendices F to H) prints its numbers beside the study's counts, never in place of them.

## What it is

The study's graders read each try's end state and the one string a task keys on.
This reading asks a different question of the same 900 graded tries: what did the agent actually do after the question, and what did it say?
Each try's whole reply after the question (or its last turn, for a try that never reached the question) was extracted by script from the committed records at `1ded8e9a2ada`, with model and harness names redacted in tool text, and read blind.

- Two model readers, `ra` and `rb`, labelled every try; both are Claude Opus 5.5 at medium effort, so they are one model family, the same family as three of the five graded models (`results/ACTION-READING.md` says so at its top).
- Each reader was a fresh agent per packet, given `reader-brief.md`, one packet from `packets/` and that task's rubric from `rubric/`; neither saw the model, the harness, the half or the grade.
- `merge.py` compares the two readers' labels, applies the key (`key/mapping.json`, under two standards, explained in `key/README.md`), and writes the page.
- Where the two readers' labels differed on a try in a way that changes a count, the repository owner ruled; there were six such tries, and his six rulings are `rulings.json` (each entry says who ruled, when, and which reader it matches).
- The kit was reviewed twice before any reader ran, and the results twice after, with an outside read: `reviews/`.

## The files

| Path | What it is |
|---|---|
| `PLAN.md` | the reading's plan, written before the readers ran |
| `reader-brief.md` | the brief each reader was given |
| `rubric/` | one rubric per task: the content, action, stall and pushback classes a reader picks from |
| `key/README.md`, `key/mapping.json`, `key/right-moves.md` | the key: which classes count as right, under the registered standard and under the contract standard |
| `key/ids.json`, `key/salt.txt` | opaque id to slot, attempt, model, harness, version and grade (hidden from the readers); the salt of the opaque id |
| `key/check_one_habit.py` | the one-habit check (`CHECK.md` section 6) |
| `extract.py` | the extraction from the committed records; writes `extracted/` and `key/ids.json` |
| `extracted/tries.jsonl` | the 900 blind objects (packet material) |
| `extracted/totals.json`, `extracted/leak-sweep.json` | the extraction's totals and its leak sweep (`CHECK.md` sections 3 and 5) |
| `wording.py`, `wording.json` | exact wording against the grader's string, by script only |
| `packets/` | the 34 packets the readers read |
| `labels/ra/`, `labels/rb/` | the two readers' labels, one file per packet |
| `rulings.json` | the six rulings |
| `merge.py` | the merge; writes `ACTION-READING.md`, `disagreements.md` and `agreed-sample.md` |
| `results/` | the published results (below) |
| `check_known.py`, `check_regressions.py`, `test/` | the kit's self-checks and their fixtures |
| `CHECK.md` | the kit's self-check record, as run on 19 Nov 2026 |
| `reviews/` | the five review files the report's trace cites: two kit reviews, two results reviews and the outside read |
| `trace-inputs/` | the two files the report's trace read that are not otherwise published as they were (below) |
| `TRACE-SOURCES.md` | every file the report's trace read, by sha256, mapped to its path here |

`results/` holds six files.
`merge.py` writes three of them: `ACTION-READING.md` (the page), `disagreements.md` (every try the readers labelled differently, for the owner) and `agreed-sample.md` (30 agreed tries drawn with a fixed seed, for the owner's spot-check).
The other three are recorded outputs of two helper scripts that are not published: `DECISIVE.md` and `decisive-ids.json` (the six count-changing disagreements put to the owner for a ruling) and `page-data.json` (the data of a private visual page).

## Check it from a clone

Run each line from the repository root unless it says otherwise; Python 3.9 or later, standard library only; `git` must be on the path, and the clone must hold commit `1ded8e9a2ada` (a full clone does).

1. The merge, from this folder (`docs/gap-study-4/action-reading/`), into a scratch folder of your choice:

   ```
   python3 merge.py labels/ra labels/rb --rulings rulings.json --out <dir>
   ```

   It prints `read by both: 891; disagreements: 203; agreed: 688; sample: 30`.
   Then `diff -r <dir> results` from the same folder prints nothing for the three files `merge.py` writes, and "Only in results" for `DECISIVE.md`, `decisive-ids.json` and `page-data.json`, which `merge.py` does not write.

2. The extraction, which rewrites `extracted/` and `key/ids.json` in place from the committed records (reading them with `git cat-file` at `1ded8e9a2ada`, and the study folder of the checkout):

   ```
   python3 docs/gap-study-4/action-reading/extract.py
   git status --short docs/gap-study-4/action-reading/
   ```

   The second line prints nothing: the rerun reproduces every file byte for byte, because the salt in `key/salt.txt` is published.
   `python3 docs/gap-study-4/action-reading/wording.py` does the same for `wording.json`.

3. The kit's self-checks:

   ```
   python3 docs/gap-study-4/action-reading/check_regressions.py
   python3 docs/gap-study-4/action-reading/check_regressions.py --old
   python3 docs/gap-study-4/action-reading/check_known.py
   python3 docs/gap-study-4/action-reading/test/test_aborted.py
   python3 docs/gap-study-4/action-reading/key/check_one_habit.py
   ```

   The first prints five PASS lines (R1 to R5) and exits 0; `--old` runs the same checks on the pre-fix fixtures and prints five FAIL lines (exit 1, as it should); `check_known.py` prints `ALL THREE AGREE`; `test_aborted.py` prints `as expected (current passes, before fails)`; the outputs of `check_known.py` and `check_one_habit.py` equal `test/known.txt` and `test/one-habit.txt`.

4. The two copies of the page:

   ```
   sed -E 's/ \([0-9]+%\)//g' docs/gap-study-4/action-reading/results/ACTION-READING.md | diff - docs/gap-study-4/action-reading/trace-inputs/ACTION-READING-20261119T1358.md
   ```

   It prints nothing (exit 0).
   The report's trace read `trace-inputs/ACTION-READING-20261119T1358.md`, the page as rendered at 13:58 on 19 Nov 2026; `results/ACTION-READING.md` is the same counts with a percentage column beside each count, rendered 21 minutes later; no count moved.

## What differs from the folder the reading was built in

- Five files carried a path of the machine the reading was built on; each now names a path relative to the repository or to its own folder, and nothing else in them changed:
  - `extract.py` and `check_regressions.py` read the records with `git` in this repository (they named a records checkout on that machine) and the study folder of this checkout (they named a copy of it);
  - `wording.py` reads the study folder of this checkout;
  - `check_regressions.py` reads the 44 recovery tries from `test/recovery_ids.json` (it named a reviewer's scratch copy; the file is published here byte-identical to that copy);
  - `test/test_aborted.py` writes its fake labels into a fresh temporary folder (it named a scratch folder of that machine);
  - `CHECK.md` lines 4 and 5 name the folder and the records checkout without the machine's path.
  None of these five is a file the report's trace read.
- `test/recovery_ids.json` is added (above).
- `trace-inputs/` is added: the trace's 13:58 copy of the page (above) and the trace's own `SHA256SUMS`, both byte-identical to the files the report read.
- Left out: the builder's working notes (`FIXES-1.md` to `FIXES-3.md`, a reader queue, a packet-size list) and the helper scripts that built the key, the packets, `DECISIVE.md` and the private page.
- The five files in `reviews/` are published byte-identical to the files the report's trace read; four of them name the reviewers' working folders on the machine they ran on.
