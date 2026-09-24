**The sealed interface (fixed here so the seal can run beside the build).**
`GARS_SEALED_DEFECT_FIXTURES` names a directory holding one subdirectory per plant, named `p01`, `p02`, … (never a descriptive name; review MINOR-4), each with one of three layouts:
- (a) a complete stage-00 project for classes 3–6: `00_data/<assay>/{samples.csv,files.csv,raw/}` and `_config/<assay>.yaml`, exactly as row 1's sealed interface, with the columns of "The schema the detectors read";
- (b) for class 8, `de_results.csv` (the schema `gene,baseMean,log2FoldChange,pvalue,padj`), which the runner places into its own scaffold and grades through the real `collect`;
- (c) for classes 7 and 9, `snapshot.json` in row 7's `claims_export` shape plus a `project/` tree, graded through `emit_report.py`.
- A plant with `class_id: 0` is a sealed **clean** project in layout (a), expected to raise no flag.

Every plant carries `expected.json`: `{"class_id": <0-10>, "expected_flag": "<flag or none>", "expected_stage": "<stage>", "seal_type": "independent_context" | "external_human_seal", "canary": "<32 hex characters>"}`.
The `canary` is a random token the sealer also writes into one data cell the plant's layout carries, where no detector reads it (review NOTE-A): an extra `samples.csv` column named `plant_note` in layout (a) (the open schema, 0043, allows it, and no detector reads that column; never in a sample id, which stage 00 derives from file names); an extra trailing column `plant_note` in `de_results.csv` for layout (b) (the collect gate reads columns by name; Brief A's clean projects include one table with that extra column, proving it changes no verdict); a claim's `text` in `snapshot.json` for layout (c). The runner never prints it; `seal_ops.py complete` copies it once into the manifest, and every later leak count reads the manifest (below).

The runner routes by `class_id`, grades through the stage entry point, and counts a catch only when the named flag appears there.
Output discipline (review MINOR-4), enforced by a test:
- each plant runs in a `try/except`, with the entry point's stdout and stderr captured and discarded;
- a plant that raises is counted `error` (graded, not caught), never skipped;
- it prints only `sealed <id>: <caught>/<planted>` per class, `sealed clean: <flagged>/<n>`, the seal-type counts, `sealed graded <g> of <s> plants seen`, and `row 1 mapped: <m>` / `row 1 unmapped: <u>`;
- a test builds a synthetic sealed folder whose sample ids, file names, folder names and `expected.json` extras all carry a sentinel string, runs the sealed class, and asserts the sentinel appears 0 times in the captured output.

It also accepts row 1's `GARS_SEALED_DESIGN_FIXTURES` (`tests/test_stage01_design.py:8-16` interface), mapping through a committed map that keeps row 1's own `detail_contains` requirement (review MAJOR-5):
- `confounded_condition` → class 1;
- `insufficient_biological_replicates` → class 2;
- `invalid_design` → class 2 **only** when `detail_contains` falls in the group-of-one message family (the runner matches `detail_contains` against the committed family, the literal fragments of the stage 01 messages at `:588-590` and the ATAC floor; for example "cannot be tested for differential expression");
- anything else → `unmapped`: printed on its own line, never counted as caught, and kept out of the catalogue arithmetic, because it is one of row 1's §7.2 checks outside §11.2's ten classes.
A mapped plant is caught only when the stage 01 CLI's failure carries both the reason and `detail_contains`, exactly as `SealedDesignTests` grades it.

**The schema the detectors read (review MAJOR-2).**
It is a contract, not detector rule text.
The same block is copied verbatim into the sealed interface, into `benchmarks/defects/SEALED-INTERFACE.md`, and into the stage 00/01 contracts (`gars/00_initialize_project/CONTEXT.md`, `gars/01_prepare_samplesheets/CONTEXT.md`), so a sealer and a user read the same words.
All columns are optional `samples.csv` columns under the open schema (decision 0043); no config key is added (review MAJOR-9).
- `subject`: the independent biological unit (donor, patient, animal); rows sharing a value are not independent replicates.
- `biological_unit`: a synonym of `subject` kept for row 2's fixtures; when both are present, `subject` wins.
- `cell_barcode`: present only when each row is a single cell (or a cell-level sub-sample); its presence marks the design as cell-level.
- `library_index`: the library's i7 index sequence, or `i7+i5` for dual indexing, in the exact form the CASAVA 1.8 FASTQ header carries after the last `:` (for example `ACGTACGT` or `ACGTACGT+TTGACCAA`); never a library name.
- `sex`: one of `F`, `M`, `unknown` (case-sensitive).
- `age`: age in years, a non-negative number; blank means unknown.
