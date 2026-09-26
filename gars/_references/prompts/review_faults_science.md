# Science review

The whole world is this folder. Use relative paths from this folder in every
command and never change directory. Run every command in the foreground.
No network. TMPDIR is ./tmp; create it first. Do not modify anything under project/.

## Phase 1

Review the design, data and results in project/1-design, project/2-data and
project/3-results. Check the contrast, reference, approval, independent biological
units, replication, nuisance factors, rank, exclusions and statistical correction.
Check RNA dispersion, normalization and outliers against their dispositions.
For ATAC, check the declared consensus strategy, blacklist handling, FRiP, TSS
enrichment, fragment sizes and the global scaling assumption. Distinguish
observations from interpretations and hypotheses; two biological replicates per
level require an explicit limitation.

Write notes.json as an object with one field, findings, containing preliminary
findings in the shape below. Finish Phase 1 before reviewing any narrative.

## Phase 2

After the narrative arrives in project/4-report, review the report and claims
against the evidence you already reviewed. Check numerical claims, citations,
contradictory evidence, limitations and causal wording. Claims need evidence
links and separate biological support and process risk; a hypothesis must not
be represented as an observation.

The report may contain the literal placeholder text `UNKNOWN (owned by ...)`,
where ... stands for an owner name, exactly as the GARS report renderer writes
it. Such a placeholder is a GARS process placeholder outside this science
review, and a finding about one is at most a NOTE. This applies only to text
of that literal form; every other part of the report stays fully in scope.

Write review.json as one object with exactly verdict and findings. Verdict is
APPROVE, APPROVE_WITH_CHANGES or REJECT. Findings may be empty.

## Finding shape

Each finding has exactly id, severity, class, file, line_start, line_end,
summary and evidence. Severity is BLOCKER, MAJOR, MINOR or NOTE. A NOTE is
informational. Use positive integer line numbers with line_end at least
line_start. File is relative to project/, for example 3-results/de_results.csv,
never project/3-results/de_results.csv. Summary states the concrete problem;
evidence identifies the supporting observations in these files and any limits
on verification. Do not invent analysis execution or results.

Class is one of these identifiers, or other for a problem outside this vocabulary:

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
