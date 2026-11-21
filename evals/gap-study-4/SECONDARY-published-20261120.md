# SECONDARY.md, published after the verified head (20 Nov 2026)

`SECONDARY.md` beside this note is the round 4 reader-gap secondary analysis, byte-identical to the file built on 13 Nov 2026 on branch `analysis/reader-gap-secondary` (head `dcc3538d5f3af0e4750b94512b8fecd6225cb2d2`, from `1e097b2f5f99a4d5134234d5553dcb8cdaff45ca`), sha256 `b09bc48f746610cfa85bdaaeaefa09a6fd8a061833e855cf29be0b5e027ebaa7`; it is not edited.
It was added after the verified head `1ded8e9a2ada68ecf3ececc1c6c33dd0634f7ca3`, which it does not change.

The code `SECONDARY.md` names at `evals/gap-study-4/transcript_view_secondary.py` and `evals/gap-study-4/tests/test_reader_gap_secondary.py` (its lines 16 and 18), with `reader_gap_secondary.py` and `tests/test_reader_gap_secondary_driver.py`, is published byte-identical at `docs/gap-study-4/secondary/`, because the study's `copy_manifest.py --later-files` refuses an importable file added under `evals/` after the freeze.
The pre-registration and the five recorded inputs of the `report` step are published there too.

How to run it: `docs/gap-study-4/secondary/README.md` stages the four files in a scratch checkout of `1e097b2f5f99`, runs the two tests, re-derives the two grade files (equal to the published ones in every field but `tree`, the checkout path) and the blind check (byte for byte), and regenerates `SECONDARY.md` byte for byte from the published inputs; the first attempt's check and the shapes file are recorded inputs.
