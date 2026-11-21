# How the round 4 report is built and checked

`docs/gap-study-4/REPORT.md` is generated: its prose is `docs/gap-study-4/REPORT.src.md`, and every table in it is a fragment under `build/fragments/` written by the scripts in this folder from the committed records.
`docs/gap-study-4/TRACE.md` gives the source of every number: the committed file and line, the traced table cell, or the computed fact.

## The scripts

| Script | What it does |
|---|---|
| `src.py` | where things are; makes a `git archive` copy of the records commit `1ded8e9a2ada` (the paths in `copy-paths.txt`) in a scratch folder outside the clone, and stages the action reading's files under the names the trace uses (`../action-reading/TRACE-SOURCES.md`) |
| `build_tables.py` | every table of the study's results, from the committed pages, each recount compared with its page; writes `build/fragments/`, `build/trace_tables.tsv`, `build/facts.json` |
| `build_reading.py` | the action-reading tables, copied cell by cell from the reading's page, its "As graded" column compared with the study's result page; refuses any input that does not match `../action-reading/trace-inputs/SHA256SUMS`; writes `build/fragments/ar_*.md`, `build/trace_reading.tsv`, `build/facts_reading.json` |
| `connector_facts.py` | the figures of section 9's sentence on the connected tools offered to arm O, recounted read-only with `git` from the records at `1ded8e9a2ada`; writes `build/facts_connectors.json` |
| `assemble.py` | `REPORT.src.md` with each include marker replaced by its fragment, written to `REPORT.md` |
| `check_trace.py` | checks every traced claim against the committed records and writes `TRACE.md` (below) |
| `trace_prose.py`, `trace_prose_v2.py` | the source of each prose claim, read by `check_trace.py` |
| `prose_lines.py` | finds the prose lines of `REPORT.md` that carry a figure, read by `check_trace.py` |

`check_trace.py` exits 1 unless every prose line of `REPORT.md` that carries a figure is covered by a trace entry, every cited needle stands on its line in the committed file at `1ded8e9a2ada`, every table cell and fact matches, every table row was generated, every line revision 3 changed is a trace entry's text, and the study's own wording checks (`evals/gap-study-4/lint_language.py` and `lint_pooling.py`, as committed at `1ded8e9a2ada`) exit 0 on `REPORT.md`.

## Rebuild from a clone

From the repository root, with Python 3.9 or later (standard library only) and `git` on the path, in a clone that holds commit `1ded8e9a2ada` (a full clone does):

```
python3 docs/gap-study-4/report-build/build_tables.py
python3 docs/gap-study-4/report-build/build_reading.py
python3 docs/gap-study-4/report-build/connector_facts.py
python3 docs/gap-study-4/report-build/assemble.py
python3 docs/gap-study-4/report-build/check_trace.py
git status --short docs/gap-study-4/
```

Expected output:

- `build_tables.py`: `ok: 529 traced cells, 32 fragments; every page count equals its recount from records/` (exit 0)
- `build_reading.py`: `ok: 300 traced cells of the action reading; As graded equals the result page in 90 of 90 half-cells and 45 of 45 unit rows; 39 half-cells differ` (exit 0)
- `connector_facts.py`: `build/facts_connectors.json written from <your clone> at 1ded8e9a2ada` (exit 0)
- `assemble.py`: `REPORT.md written: 1308 lines, 32 tables; fragments not used: []`
- `check_trace.py`: `ok: 619 prose sources over 302 entries, 823 table cells, both lints exit 0; TRACE.md written` (exit 0)
- `git status`: nothing; the rebuilt `build/`, `REPORT.md` and `TRACE.md` are byte-identical to the committed files.

The first three lines are optional: `assemble.py` and `check_trace.py` alone check the committed fragments and facts.

## Notes

- The trace's line numbers point at the files as they stand at `1ded8e9a2ada`, the head the final verifiers checked, not at a later commit; the scripts read the records from that commit, never from the checkout.
- Inside `build/trace_reading.tsv` the action reading's page is named `inputs/action-reading/ACTION-READING.md`, its name in the folder the report was built in; `TRACE.md` writes each such name as its published path, from `../action-reading/TRACE-SOURCES.md`.
- The report's text was revised (revision 2, then revision 3 with the publication edits its author chose) by scripts of exact sentence replacements kept in the private build folder; they are not published. `REPORT.src.md` and `REPORT.md` here are revision 3 as accepted.
- The scripts were moved here from that build folder with only their locations changed: the folder paths in `src.py`, `assemble.py`, `prose_lines.py`, `check_trace.py` and `connector_facts.py` (whose default `--git-dir` is now the clone itself), the input folder of `build_reading.py` (its line 23), the published paths `check_trace.py` writes into `TRACE.md`'s header and path columns, and the interpreter `check_trace.py` runs the two lints with (the one running it, where it named one path).
