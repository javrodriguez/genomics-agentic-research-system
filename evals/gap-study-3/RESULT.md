# The Gap Study, round 3 — result

32 graded take(s) of 54 planned; 3 complete cell(s) of 18 planned.

Every count below is a count of three takes. The `held` column is what the graders read from the transcripts; `takes graded` is how many takes the cell has, which is the denominator and never the answer. `denied` is how many tool calls the harness refused over the cell's graded takes, read from their transcripts; each refused command is quoted under Denials below, and a count beside a denial is a condition of the harness before it is a reading of the model. No cell is left out: a cell that was not measured is named with the reason.

## This round

| task | half | model | held | takes graded | denied | recorded mode | state |
|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | — | 2 of 3 | 3 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `confounded-design` | control | `claude-opus-5` | — | 2 of 3 | 3 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `confounded-design` | control | `claude-sonnet-5` | — | 1 of 3 | 4 | default | unmeasured — incomplete: 1 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 2 | default | complete |
| `confounded-design` | positive | `claude-opus-5` | — | 2 of 3 | 5 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `confounded-design` | positive | `claude-sonnet-5` | — | 1 of 3 | 0 | default | unmeasured — incomplete: 1 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 0 | default | complete |
| `scope-read` | control | `claude-opus-5` | — | 1 of 3 | 0 | default | unmeasured — incomplete: 1 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `scope-read` | control | `claude-sonnet-5` | — | 2 of 3 | 0 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | — | 2 of 3 | 1 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `scope-read` | positive | `claude-opus-5` | — | 1 of 3 | 0 | default | unmeasured — incomplete: 1 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `scope-read` | positive | `claude-sonnet-5` | — | 1 of 3 | 0 | default | unmeasured — incomplete: 1 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | — | 2 of 3 | 0 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `template-adherence` | control | `claude-opus-5` | — | 1 of 3 | 0 | default | unmeasured — incomplete: 1 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `template-adherence` | control | `claude-sonnet-5` | — | 1 of 3 | 0 | default | unmeasured — incomplete: 1 graded take(s) of 3, 1 rehearsal(s), 0 pause(s) |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 0 of 3 | 3 of 3 | 0 | default | complete |
| `template-adherence` | positive | `claude-opus-5` | — | 2 of 3 | 2 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |
| `template-adherence` | positive | `claude-sonnet-5` | — | 2 of 3 | 0 | default | unmeasured — incomplete: 2 graded take(s) of 3, 0 rehearsal(s), 0 pause(s) |

## Denials, per graded take

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
- `confounded-design`/positive/`claude-opus-5`/take 3: 3 denied call(s): `cd /private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-17b828e7/gars && python3 _system/stage00_register.py assays --select "05"; echo "EXIT:$?"`; `cat >> projects/run-17b828e7/HISTORY.md <<'EOF'

## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted

Template version: v0.10.0
Model: claude-opus-5
Deep file-integrity verification: `none`

- **rnaseq_bulk**: 6 of 6 samples, 2 group(s), paired-end, full_check_estimate_min `1`, full_check_needs_scheduling `False`, included_bytes `1601`, included_gb `0.0`, strandedness `auto`. Columns `sample,fastq_1,fastq_2,strandedness`. Wrote 6 samplesheet rows and 6 design rows.

Files written: 01_samplesheets/rnaseq_bulk_samplesheet.csv, 01_samplesheets/rnaseq_bulk_design.csv
EOF`; `/private/var/folders/pl/wd7yslh56knfhj37w04s6ryc0000gn/T/run-17b828e7/gars/projects/run-17b828e7/HISTORY.md`
- `confounded-design`/positive/`claude-sonnet-5`/take 3: no denial
- `scope-read`/control/`claude-haiku-4-5-20251001`/take 1: no denial
- `scope-read`/control/`claude-haiku-4-5-20251001`/take 2: no denial
- `scope-read`/control/`claude-haiku-4-5-20251001`/take 3: no denial
- `scope-read`/control/`claude-opus-5`/take 3: no denial
- `scope-read`/control/`claude-sonnet-5`/take 1: no denial
- `scope-read`/control/`claude-sonnet-5`/take 2: no denial
- `scope-read`/positive/`claude-haiku-4-5-20251001`/take 1: no denial
- `scope-read`/positive/`claude-haiku-4-5-20251001`/take 3: 1 denied call(s): `python3 _system/stage00_register.py finalize --project projects/run-581f411d --model "claude-haiku-4-5-20251001" 2>&1 | tee finalize_output.json`
- `scope-read`/positive/`claude-opus-5`/take 2: no denial
- `scope-read`/positive/`claude-sonnet-5`/take 1: no denial
- `template-adherence`/control/`claude-haiku-4-5-20251001`/take 1: no denial
- `template-adherence`/control/`claude-haiku-4-5-20251001`/take 3: no denial
- `template-adherence`/control/`claude-opus-5`/take 2: no denial
- `template-adherence`/control/`claude-sonnet-5`/take 1: no denial
- `template-adherence`/positive/`claude-haiku-4-5-20251001`/take 1: no denial
- `template-adherence`/positive/`claude-haiku-4-5-20251001`/take 2: no denial
- `template-adherence`/positive/`claude-haiku-4-5-20251001`/take 3: no denial
- `template-adherence`/positive/`claude-opus-5`/take 1: 1 denied call(s): `python3 _system/stage00_register.py create --title "run-e4f1d737" --assays rnaseq_bulk; echo "EXIT=$?"`
- `template-adherence`/positive/`claude-opus-5`/take 2: 1 denied call(s): `python3 _system/stage00_register.py create --title "run-b8899759" --assays rnaseq_bulk; echo "EXIT:$?"`
- `template-adherence`/positive/`claude-sonnet-5`/take 1: no denial
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
