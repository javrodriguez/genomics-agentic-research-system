---
date: 2026-09-24
status: standing
kind: decision
touches:
  - tests/test_planted_defects.py
  - benchmarks/defects/SEALED-INTERFACE.md
  - docs/ledger.csv
symptoms:
  - row 8's catalogue has producer-authored development plants only, and §11.2 asks for at least three sealed outside the producer context
  - the sealed catalogue runner exists but has never been run against held-out plants
---
# Row 8: the held-out seals and the sealed measurement

Addendum to [0101](0101-row-8-defect-catalogue-and-detectors.md), which stays byte-identical.
Decided and recorded by Glitch under the owner's standing delegation of 23 Sep 2026; no sentence in this record is the owner's.
The seal, the measurement and every check below were run or launched by Glitch from the owner's workstation; the plants, the seal manifest and the per-step evidence stay outside this repository.

## Context

§11.2 (R-114) asks for at least three catalogue plants sealed outside the producer context, with the seal type recorded, and §17 sets the design-defect bar at "≥ 9/10 on the sealed catalogue; ≤ 1/10 false flags".
Row 8's step A built the ten-entry catalogue, the detectors and `tests/test_planted_defects.py`, whose `SealedCatalogueTests` reads `GARS_SEALED_DEFECT_FIXTURES` through the interface in `benchmarks/defects/SEALED-INTERFACE.md`, fixed before any plant existed.
This record says who sealed what, how the seal was kept away from the producer and the reviewer, what was measured, and what was not.

## Decision

### The seal

- **Sealer:** a fresh Codex context (`codex exec`, reasoning effort high), started once in a new folder created for it under a random 32-hex-character name that no session typed; seal type `independent_context` for every plant.
- **Session:** `rollout-2026-09-24T07-49-57-01a0d340-3ca3-7541-9e5a-96944965b1af` (launched 2026-09-24 07:49:56 America/New_York; exited before 07:55).
- **Input:** a kit of six files: the seal brief and five inputs (the spec's §11.2, §7.2, R-145 and §2.2 Hi-C line; the sealed interface with the schema block and the catalogue's id, class, expected flag and expected stage columns; the stage 00/01 contract text for `samples.csv`, `files.csv` and `_config/`; row 7's committed claims snapshot, for format; the DE-table header). No GARS code, no detector rule text, no development plant and no variant menu.
- **Plants:** six, in folders `p01` to `p06`: one each for class 4 (cells as replicates, `p05`), class 5 (swapped labels, `p01`), class 6 (truncated FASTQ, `p06`) and class 8 (uncorrected p-values, `p04`), and two sealed clean projects (`class_id` 0, `p02` and `p03`). How each plant departs from the textbook case was the sealer's choice alone and is recorded nowhere outside its folder.
- **Fingerprint:** `18c842767c61d491c566200baeeca6733e76b99b2b812000b0b38342b4194401` (row 1's method: `find projects -type f | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256`), matching the sealer's own `SEAL.md` line 1; 0 files under `projects/` newer than `SEAL.md`; the folder excluded from the workstation's backups before the sealer wrote anything.
- **Sealer transcript scan:** 0 hard hits (no seal-folder name outside its own folder, no canary, no manifest name).
- **Row 1's sealed plants** (fingerprint of record `SEAL-2.md` line 1) were run alongside through `GARS_SEALED_DESIGN_FIXTURES`, mapped by the committed reason map; their fingerprint matched `SEAL-2.md` line 1 before and after the run.

### What was prevented and what was only detected

The producer (Codex) and the reviewer (Claude Code) ran on the build node, where the sealed plants never were, under two separate unprivileged OS accounts whose 19-check isolation passed before the job (2026-09-24T11:04:00Z and 11:04:01Z) and after it (2026-09-24T14:57:04Z, both).
On the owner's workstation, the seal folder was created mode 700 under a random name, generated at launch and never typed (load-bearing), and no kit, drop, copy or clone carried a plant to the build node.
On that evidence they had no path to the plants in the seal folder; for the two copies named below, that rests on the unmeasured supporting layer only.
The supporting layer was NOT measured: the planned probes (each build-node account's list of key files, and a refused non-interactive ssh from each account to the workstation's backup-receiving account and to the owner's account) were blocked by the permission classifier of the session running the lane, so "prevented" rests only on the load-bearing layer above.
Residuals: tailnet egress from the build node to the workstation's remote login for its backup-receiving account; a workstation credential held or gained by either account, which nothing here measured; provider-side state shared between Codex logins, which is assumed possible because the producer account's Codex login was not read; and the two plant copies outside the seal folder, the sealer's Codex session file and row 1's sealed folder, whose folder chains were recorded as `drwxr-xr-x` (the session store and its dated folders; the session file `-rw-r--r--`) and `drwxr-xr-x` (row 1's folder and its fixtures), so both copies rest on the unmeasured supporting layer only.
Nothing in this record depends on scanning the producer's and the reviewer's transcripts (the build node's runner path scan gated each step; its counts, recorded for completeness: 0 forbidden paths on every step that published, and one false alarm on round 1, a formula tilde, ruled and not a read).

The sealer and Glitch (every session in its project folder) ran on the workstation as one OS user, where nothing prevents a session from opening the seal folder.
What was checked on the workstation:
(1) no tool call in any transcript in Glitch's project folder with a record between the seal launch and the measurement contains the seal folder's random name or the manifest's file name outside the seal tool's own commands (hard hits 0; code bodies included; every check, as transcripts/calls, each with hard 0 and canary 0: 5/1652 at completion, then after each producer and review step 7/2285, 7/2309, 7/2341, 10/2491, 11/2646, 11/2701, 11/2707, 11/2735, 12/2832, and 14/3235 before and after the measurement);
(2) none of those transcripts contains a sealed plant's canary (0 occurrences);
(3) the sealer's transcript names no seal source but its own folder (hard 0).
Not detected:
- a read by a workstation session that first learns the random name by reading the manifest (it stayed mode 0600 and on the do-not-open list), or finds the folder by listing its parent, and whose read content never reaches a transcript;
- reads by Claude or Codex sessions outside Glitch's project folder and outside the sealer's session, and by any other process under the same user;
- a read of the plants' other copies, `generator/` and `tmp/codex.out` inside the seal folder and the sealer's Codex session file, by a path built without the random name;
- a read of the plants through a copy made outside the seal folder (a local snapshot);
- Glitch's home-folder reads in general (only the hard names were graded for Glitch);
- any read of row 1's plants: their folder name is not a hard name, and they have no canary.

### The sealed measurement (run once, 2026-09-24 13:22-13:25 America/New_York, at the reviewed head `945dceee73b6fe37b42e7cc7be02ca91473ccaf5`)

Printed by `python3 -u tests/test_planted_defects.py SealedCatalogueTests`, filtered to its count lines:

```
sealed 2: 1/1
sealed 3: 0/0
sealed 4: 1/1
sealed 5: 1/1
sealed 6: 1/1
sealed 7: 0/0
sealed 8: 1/1
sealed 9: 0/0
sealed 10: 0/1
planted-defects sealed: 6/10 classes (placeholder 10 counted planted, not caught)
sealed clean: 0/2
sealed independent_context: 9
sealed external_human_seal: 0
sealed graded 9 of 9 plants seen
row 1 mapped: 2
row 1 unmapped: 1
```

**DERIVED, not printed: `sealed 1: 1/1`.**
The runner's first line was joined to the test framework's preceding output and dropped by the seal tool's line filter, which keeps only lines that begin with the count prefixes; the measurement cannot be re-run (the seal is spent).
Its value follows from the printed lines alone: 6 caught classes minus the 5 printed caught classes (2, 4, 5, 6, 8) leaves class 1 caught with plants, and 2 mapped row 1 plants minus class 2's one leaves one plant in class 1, so class 1 is 1/1.
It is kept apart from the printed values everywhere it is cited.

Fingerprints were equal before and after the run (row 8's equal to the manifest's; row 1's equal to `SEAL-2.md` line 1).
The runner's own threshold assertion (`caught >= 9`) failed, so its exit status was 1; that is the §17 clause below, not a detector miss.

### Clause 1 of the row's exit, as three lines

1. Development P(caught), producer-authored and unsealed: 9/10 (`planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)`; false flags 0/10; graded 19 of 19), in all three suite modes.
2. Sealed P(caught), per class, over the sealed classes {4, 5, 6, 8}: 4: 1/1, 5: 1/1, 6: 1/1, 8: 1/1; with row 1's mapped plants class 2: 1/1 (printed) and class 1: 1/1 (derived); sealed clean 0/2.
3. §17's "≥ 9/10 on the sealed catalogue" over all ten classes: **NOT met.** Classes 3, 7 and 9 have no sealed plant and class 10 is a placeholder, so the sealed headline is 6/10.

### Class 9 and live DOI evidence

Class 9 has no sealed plant in this row.
By the delegated ruling recorded in 0101's addenda, a sealed class-9 plant is graded with the live lookup on a networked host, never from the committed replay; the replay fixtures are synthetic protocol fixtures and prove the protocol logic only.
The live evidence of record for the ten test DOIs was taken on the owner's workstation at 2026-09-24 13:24 America/New_York through the production module's own live transport (`gars/_system/resolve_citation.py`), 10 of 10 as expected:

| DOI | expected | request | status | body sha256 |
|---|---|---|---|---|
| `10.1038/nmeth.1618` | resolved | Crossref works | 200 | `37c963844c7a3bc31823454cf73e22694d961b205067242ce33725baec4b44cb` |
| `10.1093/bioinformatics/btu170` | resolved | Crossref works | 200 | `cc2557f8d1876f36b9689e8c2d7841cc57f5dcfa076e91fe86c385496c351a14` |
| `10.1186/s13059-014-0550-8` | resolved | Crossref works | 200 | `566356555806412cc1e36c81e6c7754739e3c8b61fec9c85814341612f51edf2` |
| `10.1038/nmeth.2019` | resolved | Crossref works | 200 | `62bec2ce9f9453c0a56f7908dd946648d2c175c87a6eb645a85af3df98a6b962` |
| `10.5281/zenodo.3727209` (DataCite) | resolved | Crossref works | 404 | `ae8462e3af85ca7577aaa97ff22a194f9dfd7fada58cf4944b53d2fdfa7b1f92` |
| | | DOI handle API | 200 | `d403515f6bd3791bc0ef0dd00eae055cc5e3f8eccfe8362e3c9e66c3a9f8ff32` |
| `10.5555/gars-fabricated-801-1` | citation_unresolved | Crossref works | 404 | `ae8462e3af85ca7577aaa97ff22a194f9dfd7fada58cf4944b53d2fdfa7b1f92` |
| | | DOI handle API | 404 | `e61f44f2898c8a349bf5417a56cf78a6fbf894b63cce55f5c945ffea6f5e25e9` |
| `10.5555/gars-fabricated-801-2` | citation_unresolved | Crossref works | 404 | `ae8462e3af85ca7577aaa97ff22a194f9dfd7fada58cf4944b53d2fdfa7b1f92` |
| | | DOI handle API | 404 | `3540f0de9cb5d2de96b1067ca1cdeaa388b6b9c4e761e2207c424d1ccd932b63` |
| `10.5555/gars-fabricated-801-3` | citation_unresolved | Crossref works | 404 | `ae8462e3af85ca7577aaa97ff22a194f9dfd7fada58cf4944b53d2fdfa7b1f92` |
| | | DOI handle API | 404 | `b45c15edc59c727d4215687a42bd51aeb841d7c2b80395818e2e7e878f44072c` |
| `10.5555/gars-fabricated-801-4` | citation_unresolved | Crossref works | 404 | `ae8462e3af85ca7577aaa97ff22a194f9dfd7fada58cf4944b53d2fdfa7b1f92` |
| | | DOI handle API | 404 | `73ea284a995075ef23995faabad5bd9858f3424eeadc62e8ac413b3fa5619325` |
| `10.5555/gars-fabricated-801-5` | citation_unresolved | Crossref works | 404 | `ae8462e3af85ca7577aaa97ff22a194f9dfd7fada58cf4944b53d2fdfa7b1f92` |
| | | DOI handle API | 404 | `9da1e927440a7b04406b1ba9aad158f301d003b1daba18fa7e7e75ec09a54791` |

The request URLs are the Crossref works lookup and the DOI handle API for the percent-encoded DOI, exactly as the module builds them.
`GARS_NETWORK_TESTS=1 python3 gars/tests/test_citation_resolution.py` passed on the same host at the same head.

### The seals are spent

These seals are published here with their classes and plant folders, so they are spent for development: any later detector change in classes 4, 5, 6 or 8 is re-measured only on new plants.

## What this does not close

- §17's sealed ≥ 9/10 over all ten classes (NOT met, above); sealed plants for classes 3, 7 and 9.
- `external_human_seal`: none exists, so every public catch-rate cell stays `unmeasured` (§11.2, §21 Q9).
- The supporting no-credential layer of the seal's isolation (not measured; above). If the probes are run later, their output is appended here as a dated addendum, never a rewrite.
- A statistically broad per-class estimate: one sealed plant per class gives only 0/1 or 1/1.
- The instrument defect that dropped the class-1 line: the seal tool's line filter must accept a count line that does not begin a physical line, before any later measurement.
- DOI detection residuals left by the final review (all fail-safe or narrow, carried to a follow-up lane that must land before a real pilot report is rendered):
  - a clean reference that carries a registered DOI together with an ordinary `10.` or `10/` elsewhere (for example "Epub 2011 Apr 10.", "vol. 10.", pages "10.1-10.9", an access date "10/03/2020") is refused `citation_unverifiable`; it fails closed, and the ten clean projects are unaffected (0/10); the reviewer's suggested fix is to drop a leftover marker that is the removed DOI's own prefix and to apply the numeric test only next to a remaining marker; the producer's change of ruling 7's two clean controls (a title reference and a page-number reference, each with a recorded DOI) from must-emit to must-refuse is accepted under the delegation as part of this residual, and the follow-up lane restores them;
  - further spellings of the same short-DOI shape emit unchecked (`DOIs: 10/…`, `shortdoi 10/…`, `D.O.I. 10/…`, a percent-encoded `doi%3A10%2F…`, `doi 10 / …`, a bare `10/…`);
  - the producer's committed fault driver `benchmarks/defects/red_on_fault.py` anchors one fault on a line the last round removed, so its campaign stops there; the lane's own mutation proof below does not use it.

## Test

Glitch verified the row on the owner's workstation, each evidence run alone on it:

- At the reviewed head `945dceee73b6fe37b42e7cc7be02ca91473ccaf5`, the suite in its three documented modes: `Ran 491 tests`, `OK` with 13, 75 and 106 skips; canary 0 of 9 in modes A and B (mode C prints no canary line); `tests/check_contracts.py` clean; `tests/check_counts.py` clean; `evals/test_harness.py` `Ran 44 tests` `OK`; `evals/check_results.py --controls --lexicon` clean; no file left in the system temp folders; no new container or volume.
- The four new test modules fail at the parent `dc6b803` (three at import, naming `gars/_system/resolve_citation.py`; the FASTQ record test with two failures) and pass at the head.
- Six mutations re-planted in a disposable clone each turned their named test red and passed again once the bytes were restored: round F's three DOI-marker fixes (review E1's F1-F3), rule 4's subject-count half, rule 6's sequence/quality length check, and the evidence preflight's marker check.
- gitleaks over `dc6b803..945dcee` under the push door's ruleset and under `gars/.gitleaks.toml`: 0 findings; no canary; no account, host, address or home path in any added line or in commit metadata (the list of addresses named in the operations record was empty, so that one check was vacuous; the private-LAN and tailnet address checks read 0).
- The seal and measurement checks above.

## Status

Standing. Records the seals and the one sealed measurement; it does not claim the row's exit.

## Date

2026-09-24
