# Replay compatibility baseline

These are the exact wrapper bytes from the R9 tree (9def5b3), retained as data
for R-042 tests. The rnaseq-de wrapper is byte-identical at the R10 tree (6039276).
Tests copy a baseline into a disposable workspace at its normal wrapper path;
these files are never registered or executed in the source workspace.
`sha256.json` pins their bytes. No test needs either historical Git object.
