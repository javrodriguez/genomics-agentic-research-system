# Contributing to GARS

Each section below names the file or folder in this repository that governs that part of a change; [README.md](README.md) and [CLAUDE.md](CLAUDE.md) orient the rest.

## Running the tests

From the repository root, run `python3 tests/run_tests.py` and `python3 tests/check_contracts.py`; [README.md](README.md#try-it-without-a-cluster) says what each covers and which tests skip off-cluster.
To run the backup tests as CI does, name a scratch folder outside the repository in the form [README.md](README.md#try-it-without-a-cluster) prints.
The `tests` job in [.github/workflows/ci.yml](.github/workflows/ci.yml) runs those commands plus `tests/check_counts.py`, `evals/test_harness.py` and `evals/check_results.py` on every push and pull request to `main`.
If you add a test, `tests/check_counts.py` compares the suite's size with the count `README.md` and `DEVELOPMENT.md` state, so update those numbers in the same change.

## Good starting contributions

A failing test that reproduces a defect, added under `tests/` with any fixture data under `tests/fixtures/`, is a good starting contribution.
A correction to a document under `docs/` that disagrees with the code it describes is another; name the file and line in the pull request.

## Architecture boundaries

Read `docs/architecture.md` before changing how stages connect: it sets out the rules the system is built on.
Each stage is a written contract, every contract follows `gars/_references/contract_standard.md`, and `tests/check_contracts.py` lints them.
The scripts under `gars/_system/` are the agent's tools, and `docs/execution-model.md` explains how the environments, the workflow engine and the containers relate.

## Proposing a skill

A new skill starts from the method in `gars/_system/authoring/SKILL.md`.
`gars/_system/authoring/create_bioinformatics_skill.py` scaffolds one from a spec with `scaffold` and checks it with `conform`; open the pull request once `conform` passes.
To discuss a skill before writing it, open an issue with `.github/ISSUE_TEMPLATE/new-skill.md`.

## Decision records

A change that settles a design question adds a record under `docs/decisions/`, following the conventions table in `docs/decisions/CONTEXT.md`: one decision per file, numbered in order, and the log is appended to, never rewritten.
A decision is never edited to reverse it; write a new record and mark the old one superseded, as `docs/decisions/CONTEXT.md` describes.
After adding a record, rebuild the index in `docs/decisions/CONTEXT.md` by running `docs/decisions/build_index.sh` with bash.

## Reporting a scientific-correctness issue

If a result, parameter or method choice looks scientifically wrong, open an issue with `.github/ISSUE_TEMPLATE/scientific-correctness.md` and give the commit and the file that holds the value.
`docs/RESULTS.md` records what the reproduction campaign scored and against which deposited data, so a report can name the row it disputes.
Bugs, installation or HPC problems and feature requests each have a template in `.github/ISSUE_TEMPLATE/`.
