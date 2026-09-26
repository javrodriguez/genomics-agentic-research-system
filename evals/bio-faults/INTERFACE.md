# Science sealed interface — version 1

This is the complete sealer handoff, together with classes.json, the generated
base trees and this layout map. Do not read producer fixtures, tests, source,
transcripts or results. Work in a fresh context. Each patch applies separately
to the supplied base, never over another patch. Independent-context seals are
development evidence only; public credibility requires an external human seal.
One plant per class is a thin sample. Invalid reviews remain in denominators;
any MINOR-or-higher finding on a clean case is a false alarm.

## Class definitions

- **swapped-condition-labels**: Condition labels are assigned to the wrong samples, changing the biological contrast.
- **wrong-reference-in-params**: The executed parameters select a reference different from the approved reference.
- **replicate-dropped-after-approval**: An approved biological replicate is omitted from the analysis without a new approval.
- **pseudoreplicated-de**: A differential test treats dependent observations as independent biological replicates.
- **fabricated-citation**: A cited source or attributed result is invented rather than supported by the available literature evidence.
- **causal-language-on-correlational-da**: A differential accessibility claim asserts causation from evidence that establishes only association.
- **batch-confounded-contrast**: A condition contrast is inseparable from a processing effect despite a full-rank fitted design.
- **p-value-edited-in-report**: A reported p-value differs from the corresponding statistical result.
- **missing-n2-limitation**: An analysis with two biological replicates per level omits the resulting limitation on inference.
- **contradictory-literature-omitted**: A claim omits available literature evidence that contradicts its interpretation.

A finding may also carry `other`; no other class is accepted.

## THE SEALED INTERFACE

This is the case format; the producer implements exactly it, and the sealer writes to it after the merge, against the merged head's own base trees.

- A case folder is `P<nn>/` (plant) or `C<nn>/` (clean) with `plant.diff` (a unified diff against the base project tree the merged head's `bio_generate_base.py` writes for `base_project` and `base_seed`; an empty diff is legal only for a clean case) and `expected.json`.
- `expected.json`, all required: `id`; `kind` (`plant` | `clean`); `class` (a science class id, or null for clean); `base_project` (a base id the merged head's `bio_generate_base.py` knows; the sealer receives the list, the generated trees and their seeds as data); `base_seed` (int); `base_sha` (the full 40-hex harness base); `seal_type` (`unsealed` | `independent_context` | `external_human_seal`); `requirement_ids`; for a plant `match_any` = a non-empty list of `{"file": <case-relative path>, "line_start": int, "line_end": int, "mode": "file_lines" | "file"}` and `min_severity` (default `MINOR`).
  Optional: `mask_literals`.
- Every `file` in `match_any` is relative to the case's `project/` folder (e.g. `1-design/samples.csv`, `3-results/de_results.csv`, `4-report/report.md`), following the builder's layout map (which base file lands at which case path); line numbers are in the post-plant file as the builder lays it out.
- Files the builder renders rather than copies (`4-report/report.md`, rendered by row 7's renderer) may be matched in `mode: file`; a `file_lines` entry on a rendered file is allowed only when the sealer has seen its own built case through the door's `validate`, whose built copy stays inside the seal folder.
- A plant has exactly one flaw of its class; a clean case has none.
  The flaw is detectable by a careful reviewer from the case's own files alone.
  The flaw is real under the class definition and §14's assay rules, and the plant passes every deterministic gate the builder runs (R10-6).
- A plant never names its class, a flaw, a fault, a plant, a seal or a harness in any byte it adds.
- The reviewer-facing layout after building: `project/1-design/` (the design: `samples.csv`, `_config/<assay>.yaml`, the approved plan and its approval record), `project/2-data/` (`files.csv`, a count or peak matrix summary), `project/3-results/` (`de_results.csv`, `manifest.json`, QC summary), `project/4-report/` (`report.md` rendered by row 7's renderer, `snapshot.json`); `4-report/` is withheld until phase B.
- The sealer's inputs (copied by the door at `launch`, each sha256 recorded): the merged head's `INTERFACE.md`, `classes.json`, the generated base trees under `input/bases/<base id>/` with their seeds, the layout map, and the list of gate names from R10-6 (names only).
- Seal folder layout (the sealer's): `plants/P03/`, `P04/`, `P05/`, `clean/C03/` (and `P06`/`P07`/`C04` only for a replacement), `generator/` (seeded scripts), `SEAL.md` (line 1 `fingerprint <sha256 over the sorted (relative path, sha256) list of plants/ and clean/>`, then date, seal type, counts per class; no content description), `BLINDNESS.md`, `tmp/`.
- Case ids: the producer writes `P01`, `P02`, `C01`, `C02`; the sealer writes `P03`–`P05` and `C03` (replacements `P06`, `P07`, `C04`); `P90` and `C90` are reserved for Glitch's rehearsal and never enter a measured run; the ids are assigned to classes only inside `expected.json`.

## Named base trees

The pinned harness base is `a77908474f2fc463f481a55f2d0c2ceeee8be660`.

| base_project | assay | base_seed |
|---|---|---|
| rna-a | rnaseq_bulk | 731947205861304921 |
| rna-b | rnaseq_bulk | 731947205861304922 |
| atac-a | atacseq_bulk | 731947205861304923 |

The coordinator generates each base with:

```sh
python3 evals/bio-faults/bio_generate_base.py --base rna-a --seed 731947205861304921 --out "$base_folder"
```

Substitute the base id and seed from the table. The trees are deterministic data.
Each base contains 240 negative-binomial features with dispersion 0.015,
a lognormal baseline (log location log(120), log standard deviation 0.8), differing
library exposures, and a seeded 10% subset with effects of absolute log2 size
between 1 and 3 in both directions. The pre-specified analysis uses
median-of-ratios size factors, log2(normalised count + 1), a two-sided pooled
Student t-test (df = 4), and BH across all tested rows at alpha 0.05. Reports
state significant counts and directions, descriptive association and the
n = 3 per group limitation. The seed and base id are handoff metadata only;
neither is copied into reviewer-visible files. Approval records are historical
data, never an approval command.

The supplied count matrix is the analysis input; no raw reads are supplied.
files.csv lists each library's analysed read count (the sum over supplied
features) and the SHA-256 of its per-library count export. It does not assert
a total sequencing depth. Upstream read-level QC is unavailable from these
inputs, marked DEGRADE with the limitation attached to the rendered claim;
no mapping, strandedness, FRiP, TSS or fragment-periodicity measurement is
invented. ATAC coordinates have seeded widths of 150–900 bases and gaps of
500–25000 bases over three chromosomes. Numeric CSV values use twelve
significant digits, floating sums use math.fsum, and all files use UTF-8/LF.
The execution manifest supplies public data classification, reference release,
command and analysis hashes, and a justified N/A cost. From the folder containing
project, `bash project/3-results/commands.sh tmp/reproduced` recomputes both
numerical CSVs using only the supplied counts and standard-library Python.
The ATAC report limits interpretation because the declared consensus-peak union
and blacklist exclusion cannot be verified from these files. The inherited
renderer still emits UNKNOWN for hard-coded sections; that rendering boundary
awaits a separate ruling and these inputs do not establish clean rendered reports.
Base fingerprints use the sorted (relative path, SHA-256) JSON list and hash
algorithm shown below for seals, applied to every file in a base tree.

## LAYOUT MAP

Every target below is under the anonymous case's `project/` folder.

| Base file | Case path |
|---|---|
| samples.csv | 1-design/samples.csv |
| config.yaml | 1-design/_config/ASSAY.yaml (assay from the base table) |
| PLAN.md | 1-design/PLAN.md |
| approval.json | 1-design/approval.json |
| files.csv | 2-data/files.csv |
| counts.tsv | 2-data/counts.tsv |
| provenance.csv | 2-data/provenance.csv |
| libraries/A_REP1.tsv | 2-data/libraries/A_REP1.tsv |
| libraries/A_REP2.tsv | 2-data/libraries/A_REP2.tsv |
| libraries/A_REP3.tsv | 2-data/libraries/A_REP3.tsv |
| libraries/B_REP1.tsv | 2-data/libraries/B_REP1.tsv |
| libraries/B_REP2.tsv | 2-data/libraries/B_REP2.tsv |
| libraries/B_REP3.tsv | 2-data/libraries/B_REP3.tsv |
| de_results.csv | 3-results/de_results.csv |
| normalized_counts.csv | 3-results/normalized_counts.csv |
| manifest.json | 3-results/manifest.json |
| commands.sh | 3-results/commands.sh |
| analysis.py | 3-results/analysis.py |
| qc.md | 3-results/qc.md |
| snapshot.json | 4-report/snapshot.json |
| rendered from snapshot.json and manifest.json | 4-report/report.md |

No other files may be added. Match files use the case paths in this table,
without `project/`. Count lines in the post-patch copy starting at one. Each
match_any entry is an alternative; class and severity must also match. A
file_lines interval is widened by exactly three at each end. Use `mode: file`
for rendered files unless the sealer has seen the built copy through validate.
Never widen an interval to cover unrelated content. MINOR is the default floor.

## Gate names

stage01_design · catalogue_integrity · catalogue_probabilities ·
group_rep_presence · count_matrix_header · de_identifiers · stage03_verify ·
catalogue_evidence · render_report

## Seal, then run

The builder uses case-sensitive substring matching for all class ids, case ids,
and `plant`, `seal`, `fault`, `flaw`, `defect`, `fixture`, `expected`, `canary`,
`harness`. All case bytes and names are checked, including unchanged base bytes.
Do not put answers, these tokens or a personal identity in patch content.
For example, a longer word containing `fault` is still refused. The two exact,
constant public-manifest exceptions carry no case information; they never exempt
case content. Keep answers and patches outside the constructed cases.

Keep P03–P07 and C03–C04 for sealing; P90 and C90 are rehearsal-only and refused
by the measurement builder. Set GARS_SEALED_BIO_FAULTS_DIR to the directory with
plants/ and clean/. The coordinator validates with no model:

```sh
GARS_SEALED_BIO_FAULTS_DIR="$sealed_dir" python3 evals/bio-faults/bio_build_cases.py --out "$private_build" --log "$private_log" --quiet-ids
```

The output must be a fresh folder outside every Git work tree. All temporary
folders and the log stay in approved scratch. Gate names and results are private;
the quiet invocation prints no per-case diagnostics. The door keeps its built
copy within the seal folder. Mechanical acceptance does not certify statistical
honesty. At most two correction rounds precede one replacement under the next
reserved id; preserve prior evidence. Never author C03 in the producer repository.

Freeze plants/ and clean/ before measurement. From the repository root, with
sealed_dir naming the seal folder, the fingerprint command is:

```sh
python3 - "$sealed_dir" <<'PYCODE'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
entries = sorted((p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
                 for group in ('plants', 'clean') for p in (root / group).rglob('*') if p.is_file())
payload = json.dumps(entries, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
print('fingerprint ' + hashlib.sha256(payload).hexdigest())
PYCODE
```

SEAL.md starts with that line, then date, seal type and counts per class; no
content description. Retain BLINDNESS.md, generator/ and tmp/ as described above.
A changed seal is a separate run with retained first-run evidence. Never replace
an outcome after seeing the measured results. Four eventual private outcomes
are hash-checkable; four of eight are publicly recomputable. The partial set
never establishes the full science threshold of ten classes and five clean cases.
