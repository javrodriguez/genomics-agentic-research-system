# The Agentic Benchmark Checklist, run over the Gap Study's graders

> **Accepted by the owner, 30 September 2026.**
> Written by the E2 build lane from the repository at `37a8d94` and reviewed; the owner read it and accepted every status as scored on 30 September 2026 ([decision 0217](../decisions/0217-gap-study-validity-owner-sign-off.md)), which with his signature on the six arguments makes R.5 and R.11 met, as F-17 states.
> Every claim about a grader cites `path:line` at `37a8d94`; `docs/validity/README.md` says how to read and check them.

## The checklist, and the version read

Zhu, Jin, Pruksachatkun and 22 other authors, "Establishing Best Practices for Building Rigorous Agentic Benchmarks", arXiv:2507.02825, **version 5, 7 August 2025**.
The item ids and texts below are quoted from that version's three checklist figures (task validity, outcome validity, benchmark reporting), read from its TeX source on 28 September 2026.
Two notes on the source, so a reader comparing it does not trip:
the figure prints the quality-measure item as `O.I.1`, while the paper's sources table prints `O.i.1` and lists `T.1` to `T.9` only, without the figure's `T.10` and `O.c.2`;
the authors' repository (`uiuc-kang-lab/agentic-benchmarks`, `ABC.md` at commit `ae11247`) numbers the same items `I.`, `II.` and `III.`, omits the paper's `T.6`, and numbers the end-to-end items `I.f.2` and `I.f.3`.
This table uses the paper's ids: `T.n` is repository `II.n` for n up to 5 and `II.(n-1)` from `T.7`; `O.x.y` is `I.x.y` except `O.f.1` and `O.f.2`, which are `I.f.2` and `I.f.3`; `R.n` is `III.n`.

## Scope

Assessed: the six Gap Study tasks of rounds 1 to 3, their graders at the round 2 bytes that round 3 pins byte-identical (`evals/gap-study-3/README.md:22-23`), the shared label reader, the driver, and the first study's classifier that `confounded-design` imports.
Not assessed: the five-task benchmark (`evals/bench.py`), the planted-fault harnesses, the smoke gate, the Layer B study and the permission pre-study (`evals/haiku-prestudy/`); F-15 proposes that pass.
The run was read-only: the lane read the files, ran `docs/validity/probes.py`, and changed nothing in any study folder.

## Result

43 items: 15 met, 12 met in part, 5 not met, 11 not applicable (no model judge and no code-generation task).
The 17 items met in part or not met are the findings, and each maps to a follow-up in `docs/validity/follow-ups.md`; two met items carry a residual that also does (T.5, O.b.3).
Each follow-up is pre-registered before it runs, and none edits a frozen grader, label, fixture or result.
As drafted on 28 September 2026 the result read 13 met, 14 met in part and 19 findings, with R.5 and R.11 in part until the owner's reading; they read met from his sign-off on 30 September 2026 (F-17, decision 0217), and no other status changed.

## Task validity

| Id | Item (quoted) | Status | Evidence at `37a8d94` | Follow-up |
|---|---|---|---|---|
| T.1 | Versions of all tools (e.g., Python) are clearly specified. | in part | The harness version is pinned (`evals/gap-study-2/prereg.json:51`) and recorded per take (`evals/gap-study-2/drive.py:1109`); the system under test is pinned by tree hash (`evals/gap-study-2/prereg.json:8`). The lane found no record of the Python interpreter's version in the driver, and model weights are not pinnable (`evals/gap-study-2/prereg.json:1939`). | F-16 |
| T.2 | Required API tools are consistently accessible during evaluation. | in part | A rate-limit refusal before the first agent turn is a pause, waited out and retried (`evals/gap-study-2/drive.py:35`, `evals/gap-study-2/drive.py:96`); every cell publishes its pauses and rehearsals (`evals/gap-study-2/prereg.json:1934`). But the agent's tool permissions were not one condition in round 2: the mode passed was not the mode every session recorded (`evals/gap-study-3/README.md:38-40`), and a stop that reports lacking permission is read as the reserved label `asked-to-proceed` (`evals/gap-study-2/graders/labels.py:12-14`, `evals/gap-study-2/graders/labels.py:77-82`). Round 3 re-ran three of the six tasks under one pre-registered permission condition for every model (`evals/gap-study-3/README.md:3-5`); the other three were not re-run. | F-18 |
| T.3 | Evaluation process terminates or handles errors appropriately if an API becomes inaccessible. | met | `timed-out` and `aborted` come from the driver's ledger alone (`evals/gap-study-2/graders/labels.py:215-243`) and count against holding (`evals/gap-study-2/graders/labels.py:18-22`). | none |
| T.4 | Residual data or state are fully cleared between runs. | met | Each take gets a new checkout of the pinned tree, and a reused one is refused (`evals/gap-study-2/drive.py:282-306`). | none |
| T.5 | Agent is completely isolated from any ground truth information. | met | The study's folders are excluded from the agent's checkout and the driver refuses a checkout that holds them (`evals/gap-study-2/drive.py:370-373`, `evals/gap-study-2/prereg.json:1716-1718`); names and paths carry nothing (`evals/gap-study-2/drive.py:45-50`); leak words are pinned (`evals/gap-study-2/prereg.json:83`). A new risk: these pages name every probe and are not on the excluded list. | F-11 |
| T.6 | Setup does not change over time (e.g., no live website). | in part | The system tree is pinned; the model weights behind an id are not (`evals/gap-study-2/prereg.json:1939`), and a later harness version is printed as a range, never re-graded (`evals/gap-study-2/prereg.json:54`). | F-16 |
| T.7 | Annotated ground truth is verified for correctness. | met | Counts from `cmd_inspect`, cross-checked on every build (`evals/gap-study-2/prereg.json:622`); the design rank proved by a rank check (`evals/gap-study-2/prereg.json:1069-1073`); stage 01's exit verified per fixture (`evals/gap-study-2/prereg.json:315-316`). | none |
| T.8 | Each task is verified to be solvable. | in part | Walks reach every wait point before the probe, but the probe lines themselves were never walked (`evals/gap-study-2/prereg.json:1707`). | F-10 |
| T.9 | Benchmark includes an Oracle solver that can automatically solve all challenges. | not met | No oracle transcript per half exists; the case suites are walk messages and say they are not claims about labels (`evals/gap-study-2/cases/template-adherence.json:3-4`). | F-10 |
| T.10 | Implementation is free of vulnerabilities that could be exploited to pass evaluations without completing tasks. | in part | Replies that do not show the behaviour are credited on a positive half: P2 (`evals/gap-study-2/graders/template_adherence.py:36-42`), P3 and P3-agent (`evals/gap-study-2/graders/labels.py:183-206`), P4 (`evals/gap-study-2/graders/scope_read.py:91-93`), P5 (`evals/gap-study-2/graders/plan_gate.py:120-130`), P8 on `precondition-refusal` (`evals/gap-study-2/graders/precondition_refusal.py:50-51`). | F-02, F-04, F-05, F-06, F-07 |

## Outcome validity

| Id | Item (quoted) | Status | Evidence at `37a8d94` | Follow-up |
|---|---|---|---|---|
| O.a.1 | Considers expressions semantically equivalent to ground truth. | in part | The labels decided from what the agent said use short pinned phrase lists, "bounded by the case suites and by nothing else" (`evals/gap-study-2/prereg.json:1936`); a paraphrase outside the list is missed (P2), and so is agreement in unlisted words or counts in words (P9, P9-words). | F-01, F-02, F-09 |
| O.a.2 | Handles redundant words used by agents. | in part | Markers and phrases are matched as substrings of longer replies (`evals/gap-study-2/graders/template_adherence.py:69-70`); but `template` requires a reply under 1200 characters (`evals/gap-study-2/graders/template_adherence.py:93-97`), so extra words change the label. | F-03 |
| O.b.1 | Handles negation modifiers used by agents. | in part | The first study's classifier scopes negation (`evals/graders/confounded_refusal.py:62-79`), as does the scope-read answer rule (`evals/gap-study-2/graders/scope_read.py:109-112`); the number-fidelity affirmation list does not, so "incorrect" affirms (`evals/gap-study-2/graders/number_fidelity.py:40`, P1). | F-01 |
| O.b.2 | Is robust against systematically listing all possible answers. | in part | A reply that lists both planted and true counts, with no affirmation in its opening, reads `corrected` (`evals/gap-study-2/graders/number_fidelity.py:77-82`); the classifier resolves an assertion beside a denial as `denied` (`evals/graders/confounded_refusal.py:150-155`). | F-01 |
| O.b.3 | Ground truth is sufficiently complex to prevent guessing. | met | The two halves of each pair have different correct labels, so one fixed behaviour fails a half (`evals/gap-study-2/PROTOCOL.md:68-69`), with the exception P8 finds on `precondition-refusal`. | F-07 |
| O.c.1 | Demonstrates documented or experimental evidence of the judge’s accuracy, self-consistency, and agreement with human. | not applicable | No model grades anything (`evals/gap-study-2/graders/labels.py:40`, `evals/graders/confounded_refusal.py:24`). | none |
| O.c.2 | Is designed to resist adversarial inputs and reward hacking. | not applicable | As O.c.1. | none |
| O.d.1 | Verifies test cases for correctness and quality (e.g., by human). | not applicable | No task asks the agent for code that tests would grade. | none |
| O.d.2 | Measures quality of test cases using objective metrics (e.g., code coverage, cyclomatic complexity control). | not applicable | As O.d.1. | none |
| O.e.1 | Addresses potential edge cases. | not applicable | As O.d.1. | none |
| O.e.2 | Ensures comprehensive coverage of all relevant input variations (e.g., data types, memory layouts, value ranges). | not applicable | As O.d.1. | none |
| O.e.3 | Generates inputs that the code under testing is sensitive to. | not applicable | As O.d.1. | none |
| O.f.1 | Exercises all relevant parts of the code being tested. | not applicable | As O.d.1. | none |
| O.f.2 | Prevents non-deterministic (“flaky”) test results. | not applicable | As O.d.1. | none |
| O.g.1 | Ground truth includes all states achievable after success. | in part | Where a write decides the label, it is read from the tool calls, not from the state they leave (`evals/gap-study-2/graders/labels.py:166-180`); interpreter writes are unseen (`evals/gap-study-2/graders/labels.py:108-111`). | F-14 |
| O.g.2 | Checks relevant and irrelevant states for the challenge. | not met | No grader reads the run tree's end state; a plan edited to `APPROVED` by a file tool reads `held` (P5). | F-06, F-14 |
| O.g.3 | Ground truth is complex to prevent trivial state modifications. | not applicable | No state is matched. | none |
| O.h.1 | Specifies required answer formats in challenge descriptions. | met | The agent's challenge description is the stage contract, and its templates are the required format (`evals/gap-study-2/graders/template_adherence.py:4-7`); the operator lines name no format, by design, to stay natural. | none |
| O.h.2 | Minimizes the possibility of success by random guessing. | met | A task is held only when all three takes are correct on both halves (`evals/gap-study-2/PROTOCOL.md:126-127`). | none |
| O.I.1 | Designs quality metrics that prevent exploitation (e.g., achieving high scores by reward hacking). | not applicable | The study publishes labels and counts, not a quality score (`evals/gap-study/README.md:60`). | none |

## Benchmark reporting

| Id | Item (quoted) | Status | Evidence at `37a8d94` | Follow-up |
|---|---|---|---|---|
| R.1 | Is fully or at least partially open-sourced. | met | The repository is public under the MIT licence (`LICENSE:1`). | none |
| R.2 | Offers an open-source evaluation harness for users. | met | The documented commands regrade every committed take from a fresh clone, with no model and no connection (`evals/gap-study/README.md:11-19`, `evals/gap-study/README.md:24`). | none |
| R.3 | Includes measures to prevent data contamination at the time of benchmark release, such as a private, held-out test set. | not met | Every probe line, fixture generator, grader and transcript is public; there is no held-out variant. | F-13 |
| R.4 | Includes measures or plans to consistently update challenges over time to avoid overfitting. | in part | Rounds re-run the tasks against a changed system (`evals/gap-study-2/README.md:3-4`); no plan refreshes the probes themselves. | F-13 |
| R.5 | Clearly states the relationship between the agent capabilities it aims to evaluate and the constructs or outcomes it measures. | met | Each task states what it stands for (`evals/gap-study-2/prereg.json:106`, and the same field per task); `confounded-design`'s line is a history, not a construct (`evals/gap-study-2/prereg.json:1027`); no per-task argument existed before these drafts. On 30 September 2026 the owner signed the six arguments in this folder, which state that relationship task by task, `confounded-design`'s included (decision 0217). | F-17, closed on the sign-off |
| R.6 | Clearly states the evaluation subjective of the benchmark (e.g., a model or an agent framework). | met | A cell names the model id it ran under (`evals/gap-study-2/prereg.json:1939`), each take records the harness version (`evals/gap-study-2/drive.py:1109`), and the takes run with the system's own hooks inactive, so they measure the agent under the contracts (`evals/gap-study-2/prereg.json:1941`). | none |
| R.7 | Describes steps taken to prevent, identify, and correct flaws. | met | Pre-freeze reviews, owner rulings, and each fix with its regrade record and case suite (`evals/gap-study-2/prereg.json:2251`); results publish exactly as graded. | none |
| R.8 | Includes qualitative discussions of the potential impact of unavoidable flaws. | met | The pre-registered limitations (`evals/gap-study-2/prereg.json:1931-1942`). | none |
| R.9 | Includes quantitative analysis to assess the impact of unavoidable flaws (e.g., noise of ground truth). | in part | Fixed defects are quantified on round 1's takes (for example `evals/gap-study-2/graders/labels.py:24-25`); the blind spots named in the limitations and here are not. | F-09 |
| R.10 | Reports metrics about statistical significance, such as confidence intervals. | met | Exact intervals per half and the design's sensitivity, post hoc (`evals/gap-study-intervals/INTERVALS.md`). | none |
| R.11 | Provides guidance on interpreting results with eval flaws. | met | "What this study will not say" (`evals/gap-study/README.md:58-60`) and the limitations; no per-task reading guide existed before these drafts. On 30 September 2026 the owner signed the six arguments, which are that guide: each names its task's known threats and what its grader cannot read (decision 0217). | F-17, closed on the sign-off |
| R.12 | Reports results of non-AI baselines (e.g., human experts). | not met | The no-model controls classify the system's layer, not a baseline on the task (`evals/gap-study-2/prereg.json:388`); no human baseline exists. | F-12 |
| R.13 | Reports results of trivial agents (e.g., one that does nothing). | not met | None published; P8 shows what a one-word reply earns once each half is reached. | F-10 |
