# Step 1 verdict (dated record, append-only; PREREG.md itself is unchanged)

_Recorded Wed 30 Sep 2026 02:04 EDT by the geo-recompute lane for glitch-14._
_PREREG.md sha256 at the time of this record: `1f1a9d59132e16c815449e7752d29bf1141c2165e87543acf1c3583232eadb12` (same as the step-0 freeze)._
_P10 asks for the verdict to be appended to `PREREG.md` in a dated section. glitch-14's instruction was never to edit the frozen file, so the verdict lives in this separate dated file beside it, and PREREG.md keeps its freeze hash. The copy that ships in GARS can carry this section appended._

- B1-B5 are all not EXACT.
- B6 (pyBigWig `stats(type="mean", exact=False)` on hg19 10-kb tiles) is EXACT on every target: 0.0073, 0.053-0.083, and z>2 ratios of 43.8 / 101.8 / 109.8 (1 s.f. 40 / 100 / 100).
- B7 is not EXACT.
- **Verdict under P5's clause "If only B6 or B7 is EXACT, the verdict is IN KIND (under B1)": IN KIND, adopted basis B1.** RESULTS.md's figures came from the zoom-level approximation, B6.
- Flag: P6's relation does **not** hold under B1. The z>1 ratios are 4.17 / 4.42 / 4.56, below 5, and one z>2 ratio is 19.15, below 20. So the binding P10 prescribes for IN KIND ("asserts the P6 relation") would assert something false under B1. Resolving that needs a dated PREREG-2. It never changes this verdict (P9).
- Full numbers: `evidence/step1.md` and `checks/out/analysis.txt`.
