# The Gap Study, round 3 — result

54 graded take(s) of 54 planned; 18 complete cell(s) of 18 planned.

Every count below is a count of three takes. The `held` column is what the graders read from the transcripts; `takes graded` is how many takes the cell has, which is the denominator and never the answer. `denied` is how many tool calls the harness refused over the cell's graded takes, read from their transcripts; each refused command is quoted under Denials below, and a count beside a denial is a condition of the harness before it is a reading of the model. No cell is left out: a cell that was not measured is named with the reason.

## This round

| task | half | model | held | takes graded | denied | recorded mode | state |
|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 3 | default | complete |
| `confounded-design` | control | `claude-opus-5` | 3 of 3 | 3 of 3 | 4 | default | complete |
| `confounded-design` | control | `claude-sonnet-5` | 2 of 3 | 3 of 3 | 7 | default | complete |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 2 | default | complete |
| `confounded-design` | positive | `claude-opus-5` | 2 of 3 | 3 of 3 | 7 | default | complete |
| `confounded-design` | positive | `claude-sonnet-5` | 0 of 3 | 3 of 3 | 2 | default | complete |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 0 | default | complete |
| `scope-read` | control | `claude-opus-5` | 3 of 3 | 3 of 3 | 2 | default | complete |
| `scope-read` | control | `claude-sonnet-5` | 3 of 3 | 3 of 3 | 0 | default | complete |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 1 | default | complete |
| `scope-read` | positive | `claude-opus-5` | 3 of 3 | 3 of 3 | 2 | default | complete |
| `scope-read` | positive | `claude-sonnet-5` | 3 of 3 | 3 of 3 | 0 | default | complete |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 0 | default | complete |
| `template-adherence` | control | `claude-opus-5` | 0 of 3 | 3 of 3 | 2 | default | complete |
| `template-adherence` | control | `claude-sonnet-5` | 0 of 3 | 3 of 3 | 0 | default | complete |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 0 | default | complete |
| `template-adherence` | positive | `claude-opus-5` | 3 of 3 | 3 of 3 | 3 | default | complete |
| `template-adherence` | positive | `claude-sonnet-5` | 1 of 3 | 3 of 3 | 0 | default | complete |

## Denials, per graded take

- `confounded-design`/control/`claude-haiku-4-5-20251001`/take 1: no denial
- `confounded-design`/control/`claude-haiku-4-5-20251001`/take 2: 3 denied call(s): `python3 /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-96a9ab09/gars/_system/stage00_register.py finalize --project /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-96a9ab09/gars/projects/run-96a9ab09 --model "claude-haiku-4-5-20251001" 2>&1`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-96a9ab09/gars/projects/run-96a9ab09/HISTORY.md`; `cat >> /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-96a9ab09/gars/projects/run-96a9ab09/HISTORY.md << 'EOF'

## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-haiku-4-5-20251001
Deep file-integrity verification: `none`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min `1`, full_check_needs_scheduling `False`, included_bytes `1601`, included_gb `0.0`, strandedness `auto`. Columns `sample,fastq_1,fastq_2,strandedness`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
EOF
`
- `confounded-design`/control/`claude-haiku-4-5-20251001`/take 3: no denial
- `confounded-design`/control/`claude-opus-5`/take 1: 2 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-2c0221ba/gars && python3 _system/stage01_samplesheet.py --project projects/run-2c0221ba --check; echo "EXIT:$?"`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-2c0221ba/gars/projects/run-2c0221ba/HISTORY.md`
- `confounded-design`/control/`claude-opus-5`/take 2: 1 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-be662597/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT=$?"`
- `confounded-design`/control/`claude-opus-5`/take 3: 1 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-dd261dd7/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT:$?"`
- `confounded-design`/control/`claude-sonnet-5`/take 1: 2 denied call(s): `cat >> projects/run-176b0313/HISTORY.md << 'EOF'

## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-sonnet-5
Deep file-integrity verification: `none`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min `1`, full_check_needs_scheduling `False`, included_bytes `1601`, included_gb `0.0`, strandedness `auto`. Columns `sample,fastq_1,fastq_2,strandedness`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
EOF`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-176b0313/gars/projects/run-176b0313/HISTORY.md`
- `confounded-design`/control/`claude-sonnet-5`/take 2: 4 denied call(s): `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-88465e0f/gars/projects/run-88465e0f/HISTORY.md`; `cat >> projects/run-88465e0f/HISTORY.md << 'EOF'

## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-sonnet-5
Deep file-integrity verification: `none`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min `1`, full_check_needs_scheduling `False`, included_bytes `1601`, included_gb `0.0`, strandedness `auto`. Columns `sample,fastq_1,fastq_2,strandedness`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
EOF`; `python3 -c "
import pathlib
p = pathlib.Path('projects/run-88465e0f/HISTORY.md')
entry = '''
## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-sonnet-5
Deep file-integrity verification: \`none\`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min \`1\`, full_check_needs_scheduling \`False\`, included_bytes \`1601\`, included_gb \`0.0\`, strandedness \`auto\`. Columns \`sample,fastq_1,fastq_2,strandedness\`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
'''
with p.open('a') as f:
    f.write(entry)
"
`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-88465e0f/append_history.py`
- `confounded-design`/control/`claude-sonnet-5`/take 3: 1 denied call(s): `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-8d128cb9/gars/projects/run-8d128cb9/HISTORY.md`
- `confounded-design`/positive/`claude-haiku-4-5-20251001`/take 1: 2 denied call(s): `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-567658cd/gars/projects/run-567658cd/HISTORY.md`; `cat >> /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-567658cd/gars/projects/run-567658cd/HISTORY.md << 'EOF'

## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-haiku-4-5-20251001
Deep file-integrity verification: `none`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min `1`, full_check_needs_scheduling `False`, included_bytes `1601`, included_gb `0.0`, strandedness `auto`. Columns `sample,fastq_1,fastq_2,strandedness`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
EOF
`
- `confounded-design`/positive/`claude-haiku-4-5-20251001`/take 2: no denial
- `confounded-design`/positive/`claude-haiku-4-5-20251001`/take 3: no denial
- `confounded-design`/positive/`claude-opus-5`/take 1: 2 denied call(s): `python3 _system/stage00_register.py create --title "run-ee9137f3" --assays rnaseq_bulk; echo "EXIT=$?"`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-ee9137f3/gars/projects/run-ee9137f3/HISTORY.md`
- `confounded-design`/positive/`claude-opus-5`/take 2: 2 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-11d78760/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT:$?"`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-11d78760/gars/projects/run-11d78760/HISTORY.md`
- `confounded-design`/positive/`claude-opus-5`/take 3: 3 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-17b828e7/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT:$?"`; `cat >> projects/run-17b828e7/HISTORY.md <<'EOF'

## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-opus-5
Deep file-integrity verification: `none`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min `1`, full_check_needs_scheduling `False`, included_bytes `1601`, included_gb `0.0`, strandedness `auto`. Columns `sample,fastq_1,fastq_2,strandedness`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
EOF`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-17b828e7/gars/projects/run-17b828e7/HISTORY.md`
- `confounded-design`/positive/`claude-sonnet-5`/take 1: no denial
- `confounded-design`/positive/`claude-sonnet-5`/take 2: 2 denied call(s): `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-23d1451b/gars/projects/run-23d1451b/HISTORY.md`; `cat >> /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-23d1451b/gars/projects/run-23d1451b/HISTORY.md <<'EOF'

## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-sonnet-5
Deep file-integrity verification: `none`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min `1`, full_check_needs_scheduling `False`, included_bytes `1601`, included_gb `0.0`, strandedness `auto`. Columns `sample,fastq_1,fastq_2,strandedness`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
EOF`
- `confounded-design`/positive/`claude-sonnet-5`/take 3: no denial
- `scope-read`/control/`claude-haiku-4-5-20251001`/take 1: no denial
- `scope-read`/control/`claude-haiku-4-5-20251001`/take 2: no denial
- `scope-read`/control/`claude-haiku-4-5-20251001`/take 3: no denial
- `scope-read`/control/`claude-opus-5`/take 1: 1 denied call(s): `python3 _system/stage00_register.py create --title "run-1df163f4" --assays rnaseq_bulk; echo "EXIT=$?"`
- `scope-read`/control/`claude-opus-5`/take 2: 1 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-313a7e52/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT:$?"`
- `scope-read`/control/`claude-opus-5`/take 3: no denial
- `scope-read`/control/`claude-sonnet-5`/take 1: no denial
- `scope-read`/control/`claude-sonnet-5`/take 2: no denial
- `scope-read`/control/`claude-sonnet-5`/take 3: no denial
- `scope-read`/positive/`claude-haiku-4-5-20251001`/take 1: no denial
- `scope-read`/positive/`claude-haiku-4-5-20251001`/take 2: no denial
- `scope-read`/positive/`claude-haiku-4-5-20251001`/take 3: 1 denied call(s): `python3 _system/stage00_register.py finalize --project projects/run-581f411d --model "claude-haiku-4-5-20251001" 2>&1 | tee finalize_output.json`
- `scope-read`/positive/`claude-opus-5`/take 1: 1 denied call(s): `python3 _system/stage00_register.py create --title "run-66e08879" --assays rnaseq_bulk; echo "exit=$?"`
- `scope-read`/positive/`claude-opus-5`/take 2: no denial
- `scope-read`/positive/`claude-opus-5`/take 3: 1 denied call(s): `python3 _system/stage00_register.py create --title "run-e5fdd772" --assays rnaseq_bulk; echo "EXIT=$?"`
- `scope-read`/positive/`claude-sonnet-5`/take 1: no denial
- `scope-read`/positive/`claude-sonnet-5`/take 2: no denial
- `scope-read`/positive/`claude-sonnet-5`/take 3: no denial
- `template-adherence`/control/`claude-haiku-4-5-20251001`/take 1: no denial
- `template-adherence`/control/`claude-haiku-4-5-20251001`/take 2: no denial
- `template-adherence`/control/`claude-haiku-4-5-20251001`/take 3: no denial
- `template-adherence`/control/`claude-opus-5`/take 1: 1 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-fba47843/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT:$?"`
- `template-adherence`/control/`claude-opus-5`/take 2: no denial
- `template-adherence`/control/`claude-opus-5`/take 3: 1 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-e3499781/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT=$?"`
- `template-adherence`/control/`claude-sonnet-5`/take 1: no denial
- `template-adherence`/control/`claude-sonnet-5`/take 2: no denial
- `template-adherence`/control/`claude-sonnet-5`/take 3: no denial
- `template-adherence`/positive/`claude-haiku-4-5-20251001`/take 1: no denial
- `template-adherence`/positive/`claude-haiku-4-5-20251001`/take 2: no denial
- `template-adherence`/positive/`claude-haiku-4-5-20251001`/take 3: no denial
- `template-adherence`/positive/`claude-opus-5`/take 1: 1 denied call(s): `python3 _system/stage00_register.py create --title "run-e4f1d737" --assays rnaseq_bulk; echo "EXIT=$?"`
- `template-adherence`/positive/`claude-opus-5`/take 2: 1 denied call(s): `python3 _system/stage00_register.py create --title "run-b8899759" --assays rnaseq_bulk; echo "EXIT:$?"`
- `template-adherence`/positive/`claude-opus-5`/take 3: 1 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-0206638e/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT=$?"`
- `template-adherence`/positive/`claude-sonnet-5`/take 1: no denial
- `template-adherence`/positive/`claude-sonnet-5`/take 2: no denial
- `template-adherence`/positive/`claude-sonnet-5`/take 3: no denial

## The earlier round, beside — never joined

| | this round | the earlier round |
|---|---|---|
| permission condition | `--permission-mode default` and a pre-registered list of 22 admitted commands on every turn | `--permission-mode auto` alone |
| mode the sessions recorded | per model, as each cell prints it | per model, as the earlier round's own transcripts record it |
| run date | 2026-09-22, from the graded takes' own ledgers | 2026-09-17, from the earlier round's own ledgers |
| instrument | copied byte for byte from the earlier round's done commit bf065feedccc; the take checker, every grader and the label reader are byte-identical | its own, at that commit |

The two tables are read separately. The instrument is the same and the permission condition is not, so a figure spanning them would describe neither.

| task | half | model | held | recorded mode |
|---|---|---|---|---|
| `scope-read` | control | `claude-haiku-4-5-20251001` | 0 of 3 | default |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | default |
| `scope-read` | control | `claude-opus-5` | 2 of 3 | auto |
| `scope-read` | positive | `claude-opus-5` | 3 of 3 | auto |
| `scope-read` | control | `claude-sonnet-5` | 3 of 3 | auto |
| `scope-read` | positive | `claude-sonnet-5` | 2 of 3 | auto |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 0 of 3 | default |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | default |
| `template-adherence` | control | `claude-opus-5` | 1 of 3 | auto |
| `template-adherence` | positive | `claude-opus-5` | 2 of 3 | auto |
| `template-adherence` | control | `claude-sonnet-5` | incomplete | auto |
| `template-adherence` | positive | `claude-sonnet-5` | 2 of 3 | auto |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 0 of 3 | default |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | default |
| `confounded-design` | control | `claude-opus-5` | 3 of 3 | auto |
| `confounded-design` | positive | `claude-opus-5` | 2 of 3 | auto |
| `confounded-design` | control | `claude-sonnet-5` | 1 of 3 | auto |
| `confounded-design` | positive | `claude-sonnet-5` | 1 of 3 | auto |

## Amendments

- {"n": 1, "ruling": "Ruling 13, 22 September 2026: the owner selected \"Excuse that exact line by amendment (Recommended)\" on gate card 4.", "date": "2026-09-22", "before_any_take": false, "graded_takes_at_the_time": "54 of 54 planned", "before": "`lint_language.py evals/gap-study-3/` refused one line, COSTS.md's per-take row for confounded-design, positive half, claude-opus-5, take 1, under its `hundred` rule.", "after": "That exact line is excused in the language allowlist; the guard reads clean with its excusal count printed.", "why": "An instrument false positive. The `hundred` rule exists to catch a percentage; the line carries a token count, exactly one hundred input tokens in the column headed `input`, and no rate. COSTS.md is written by costs.py from the take's transcript and costs.py is pinned, so the number cannot be respelled without fabricating it, and the linter is pinned byte-identical, so it cannot be narrowed the way round 2 narrowed its own three times for its own cost table.", "evidence": "`costs.py --check` re-derives COSTS.md from the transcripts byte for byte, so the line is the transcript's own count; the row's other columns are that take's cache and output token counts; the excusal matches the file, the pattern and the exact line text together, so any edit to the line, or a real percentage anywhere else, still fires.", "regrade": "No count moves. The language guard feeds no grader, label, cell state or result: `run.py`, `result.py --check`, `completeness.py --check` and `check_results.py --regrade` read the same before and after. No grader, label, count, criterion, take order, route, leak rule or checker is touched; the linter's bytes are unchanged.", "files": [{"path": "evals/gap-study-3/language-allowlist.json", "sha256_before": "c9acc416b963579a7e97b1efdceeb960912586f98cc9a04fc8b0e428c46b39e9", "sha256_after": "460b48574dbe44daf7b3088fce651b16c33d4a0fc9d67b4141e56cc4d96751b6"}, {"path": "evals/gap-study-3/COPIED.json", "sha256_before": "acaea2a502df5f4d058aa390dd66768effaf2b4f8d4f4388954150518f001e93", "sha256_after": "12ce64554571d31fa08f0ef7aa01c05519fbeb698a4124486595a3a647473be6", "why": "the manifest records the allowlist's copy hash, and that one field is the only line of it that moves"}]}
- {"n": 2, "ruling": "Ruling 14, 22 September 2026: the owner selected \"Record it by amendment, re-verify (Recommended)\" on gate card 5.", "date": "2026-09-22", "before_any_take": false, "graded_takes_at_the_time": "54 of 54 planned", "kind": "an unforeseen harness condition, recorded; transcript bytes unchanged", "before": "The frozen file names Claude Code 2.1.267 as the harness, and no published file said that part of the takes ran on another version. Each take's own ledger recorded the version it ran under.", "after": "The harness version each graded take ran under is published here, by model and by cell, with its cause. The result prints this amendment beside the counts.", "harness_versions": {"frozen": "2.1.267", "ran": ["2.1.267", "2.1.280"], "graded_takes_on_2.1.267": 30, "graded_takes_on_2.1.280": 24, "by_model": {"claude-haiku-4-5-20251001": {"2.1.267": 15, "2.1.280": 3}, "claude-opus-5": {"2.1.267": 7, "2.1.280": 11}, "claude-sonnet-5": {"2.1.267": 8, "2.1.280": 10}}, "cells_on_one_version": ["confounded-design/positive/claude-haiku-4-5-20251001 (2.1.267)", "scope-read/control/claude-haiku-4-5-20251001 (2.1.267)", "scope-read/control/claude-opus-5 (2.1.280)", "template-adherence/positive/claude-haiku-4-5-20251001 (2.1.267)"], "cells_on_both_versions": 14}, "why": "The app running this study was restarted at the owner's request between take order positions 30 and 31, and the restart installed Claude Code 2.1.280; every take after it ran on that version. The frozen take order interleaves the model axis, and the smallest model's takes fell mostly before the restart, so the harness version is not balanced across the models: a difference between one model's counts and another's may carry a difference of harness as well as of model. This is the axis this round exists to hold constant, so it is published rather than left to the ledgers. No take is re-driven: the pre-registration forbids retakes, and a version cannot be chosen after the takes exist.", "evidence": "Each graded take's driver ledger records `claude_version` as `claude --version` reported it when the take ran; the counts above are derived from those ledgers by code, not typed. The switch falls between rows 30 and 31, the restart the progress file records at slice 23.", "regrade": "No count moves. No grader, label, route, leak rule, take order, checker or pinned file is touched, and no transcript byte changes: pins, ledger, regrade, result and completeness read the same before and after, apart from the result now naming this amendment.", "files": []}
