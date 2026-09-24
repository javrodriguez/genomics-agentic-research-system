# Code review

The whole world is this folder. Review the change shown by
`git -C repo diff HEAD~1 HEAD` in the context of the repository in `repo/`.
Read surrounding code, contracts and tests to assess correctness, scope and evidence.
Use relative paths only in every command. Do not use the network or read outside
this folder. Run tests only inside `repo/`, with TMPDIR set to `./tmp`; create that
local scratch folder first. Do not change the implementation under review.

Write `review.json` in this folder as one JSON object with exactly these fields:
`verdict` and `findings`. The verdict is APPROVE, APPROVE_WITH_CHANGES or REJECT.
Each finding has exactly `id`, `severity`, `class`, `file`, `line_start`, `line_end`,
`summary` and `evidence`. Severity is BLOCKER, MAJOR, MINOR or NOTE. Use positive
integer post-change line numbers; line_end is at least line_start. For a deleted
file use line 1 and identify the deleted file. For a wholly added file identify
that file and the relevant lines. Summary states the concrete problem; evidence
names the observable consequence and the code or test supporting it. A NOTE is
informational. Do not invent test execution or results. Findings may be empty.

Every `file` is relative to the repository root, the inside of `repo/`; for example
`gars/x.py`, never `repo/gars/x.py`. Class must be one of the following identifiers,
or `other` for a problem outside this vocabulary:

- **off-by-one**: A boundary or index differs by one and changes which values are processed.
- **deleted-test**: A test is removed so that an existing behavioural guarantee loses coverage.
- **hardcoded-secret**: A credential is embedded in source instead of remaining outside the repository.
- **swallowed-exception**: An exception is suppressed so that a failed operation appears successful.
- **dropped-provenance-field**: A required provenance field is omitted from a recorded result.
- **provider-coupling**: Domain behaviour depends directly on a particular provider instead of its declared interface.
- **race**: Concurrent operations can interleave to violate a required invariant.
- **weakened-criterion**: An acceptance condition is relaxed so that a previously failing result passes.
- **fabricated-test-result**: A reported test outcome is invented instead of derived from execution.
- **unrelated-refactor**: A refactor changes code outside the stated purpose of the change.

Return the object itself, without an outer wrapper or execution metadata. Record
only findings you can substantiate from the change and repository. State limits
on verification in a finding's evidence when they bear on that finding.
