# Claims report

## question

How do the synthetic groups differ?

## data and classification

UNKNOWN (owned by row 6: data_class, venue, purpose)

## methods (workflow versions, parameters, reference release)

pipeline_commit: synthetic\-workflow\-v1

params: \{"contrast": "treated,control"\}

- claim 1: workflow_version=workflow\-v1; reference_release=release\-A
- claim 2: workflow_version=workflow\-v1; reference_release=release\-A
- claim 3: workflow_version=workflow\-v1; reference_release=release\-B
- claim 4: workflow_version=workflow\-v1; reference_release=release\-B

Genome hashes, model/prompt/routing: UNKNOWN (owned by row 6)

## QC summary

- claim 1: UNKNOWN (owned by §14 QC dispositions)
- claim 2: DEGRADE
- claim 3: UNKNOWN (owned by §14 QC dispositions)
- claim 4: WARN

## claims table (type, both confidence groups, evidence links)

| id | type | claim | biological support | process risk | evidence links | reference |
|---|---|---|---|---|---|---|
| 1 | OBSERVATION | The synthetic table contains four rows\. | \{"statistical\_support": "synthetic only"\} | \{\} | \[\{"artifact": \{"id": 1, "path": "fixtures/counts\.tsv", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\}, "artifact\_id": 1, "id": 1, "kind": "computational", "relation": "supports", "source": null, "source\_id": null\}, \{"artifact": \{"id": 1, "path": "fixtures/counts\.tsv", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\}, "artifact\_id": 1, "id": 3, "kind": "statistical", "relation": "absent", "source": null, "source\_id": null\}\] | release\-A **REFERENCE RELEASE MISMATCH** |
| | | Limitation: UNKNOWN (owned by claims snapshot) | | | | |
| 2 | INTERPRETATION | A group difference is compatible with this fixture\. | \{\} | \{"limitation": "Synthetic cohort only", "qc\_disposition": "DEGRADE"\} | \[\{"artifact": \{"id": 1, "path": "fixtures/counts\.tsv", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\}, "artifact\_id": 1, "id": 1, "kind": "computational", "relation": "supports", "source": null, "source\_id": null\}\] | release\-A **REFERENCE RELEASE MISMATCH** |
| | | Limitation: Synthetic cohort only | | | | |
| 3 | HYPOTHESIS | A regulatory association may be possible\. | \{"literature": "contradictory synthetic source"\} | \{\} | \[\{"artifact": null, "artifact\_id": null, "id": 2, "kind": "literature", "relation": "contradicts", "source": \{"id": 1, "reference": "Synthetic literature reference"\}, "source\_id": 1\}\] | release\-B **REFERENCE RELEASE MISMATCH** |
| | | Limitation: UNKNOWN (owned by claims snapshot) | | | | |
| 4 | RECOMMENDATION | Consider an independent assay\. | \{\} | \{"qc\_disposition": "WARN"\} | \[\{"artifact": \{"id": 1, "path": "fixtures/counts\.tsv", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\}, "artifact\_id": 1, "id": 3, "kind": "statistical", "relation": "absent", "source": null, "source\_id": null\}\] | release\-B **REFERENCE RELEASE MISMATCH** |
| | | Limitation: UNKNOWN (owned by claims snapshot) | | | | |

## limitations adjacent to the affected claims

Limitations from process_risk.limitation appear directly under each affected claim above.

## manifest reference and "reproduce this analysis" (`commands.sh`)

Manifest path: gars/tests/fixtures/claims/manifest\.json

Manifest sha256: 25b6987c30b06e80f47d04caf0c860359d1c687ad91d4e7ab2efd635c1871008

Reproduce this analysis (`commands.sh`): UNKNOWN (owned by row 6)

## cost

UNKNOWN (owned by row 11: docs/ledger.csv has no per-run cost source)
