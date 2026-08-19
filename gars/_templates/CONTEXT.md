# _templates — the stamps a stage copies

One job: hold the blank skeletons that stages instantiate. Nothing here is ever run, read as
input, or edited during an analysis.

## Why stamps rather than prose

A structure described in a contract's numbered steps has no single home: the same shape ends up
restated in the workspace map, in the exit gate, and in the worked example, and they drift.
`examples/demo-project/` was once missing the two files stage 00's own exit gate requires,
because the shape lived in prose in four places. A stamp is the one home — the schema *is* the
template, and the exit gate is "does this still look like the stamp".

## Contents

| Stamp | Copied by | To |
|---|---|---|
| `project/` | 00_initialize_project | `projects/<project_title>/` |

## Placeholders

Every placeholder is `{{name}}`, on its own or inline. A stamp is copied first and its
placeholders substituted afterwards; **no placeholder may survive into a created project.**
Stage 00's exit gate checks for a literal `{{` in any file it wrote.

| Placeholder | Filled with |
|---|---|
| `{{project_title}}` | the sanitized project title |
| `{{created}}` | ISO-8601 date of creation |
| `{{template_version}}` | contents of `_references/VERSION` |
| `{{assay_table}}` | one row per supported assay, columns as shown in the stamp |
| `{{source_paths}}` | one row per assay: Assay ID, raw data source path, files linked |

## Human check

Open the stamp before changing a stage that copies it. If a stage needs a new file in every
project, it belongs here, not in that stage's Process.
