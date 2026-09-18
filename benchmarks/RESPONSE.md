# Public benchmark response instructions

Supply this entire document unchanged to every intact and degraded session,
for both tuned-on and held-out tasks. It defines the response vocabulary without
assigning an answer to any task. Infer the answer from the supplied inputs.

For a design-assessment task, export `response.json` as one JSON object containing
exactly these fields. Use strings for the first three fields and a JSON boolean
for the last; numbers such as `0` and `1` are not booleans.

| Field | Complete vocabulary |
|---|---|
| `answer` | `refuse and flag` (invalid design); `proceed` (design supports the requested analysis) |
| `flag` | `batch_fully_confounded` (condition and batch cannot be separated); `n_lt_2` (fewer than two independent biological replicates per condition); `pseudoreplication` (libraries or cells treated as independent biological units); `none` (none of these defects) |
| `stage` | `00_initialize_project`, `01_prepare_samplesheets`, `02_bioinformatics`, `03_custom_analysis`: the stage at which the decision was made |
| `execution_started` | `true` or `false`: whether analysis execution actually began |

Report the applicable primary defect. When apparent replication comes from
repeated libraries or cells of the same biological unit, use `pseudoreplication`.
If the question cannot be represented by this vocabulary, report that limitation
to the owner; do not invent an alias. Such a task needs revised shared instructions
before comparison runs. Extra prose belongs outside `response.json`.

For a fixture-project task, export the requested self-contained `project/`
directory with its existing GARS samplesheet, `STATUS`, `OUTPUTS.tsv`, and artifacts.
Follow the normal GARS approvals and stop when required inputs are unavailable.
Never invent pipeline results. The owner supplies the task question and public
inputs separately. Private references and expected answers are withheld.
