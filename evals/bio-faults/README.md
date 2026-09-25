# Science review contracts — round 1, blocked

This is a partial implementation of row 10. It cannot build, launch or score a
science run. The required schema and public-manifest sweep conflict with the
required science prompt path and manifest fields. The concrete witnesses and
options are in `docs/implementation/row_10_change_report.md`, under
**Owner rulings needed**. No exception has been applied to either contract.

Implemented: the ten science class definitions; private imports of row 9's
shared functions and their bare-name compatibility; the science schema document;
the any-of oracle with science path pre-normalisation; the two-phase reviewer
prompt. Neither phase has been run. The prompt is not tuned against any case.

The phase-B mechanism specified for this round is resume only, as decided by
Glitch under the owner's standing delegation in record 0135, R10-5a. No launcher
or fresh-session fallback is implemented here. No record-validity adapter or
score is represented as operational while the prompt-path pin remains unresolved.

<!-- Schema differences from row 9, lane item 7:
1. Finding class enum: the science vocabulary plus other.
2. Envelope phases: exactly two objects, A then B, with session id, timestamps,
   exit code, usage-limit ending, blindness calls/hits, and A's notes_sha256.
3. Envelope narrative_withheld_until_phase_b: required boolean stamped by code.
Every other key, enum and required list remains equal, including the code-only
prompt_path enum. This last pin is an unresolved blocker, not an exemption.
The schema's array cardinality and prefixItems also need enforcement by the
future science adapter because row 9's limited validate ignores these keywords.
-->

`bio_common.py` loads row 9's common first, then its record, oracle, launcher and
score modules with private aliases. Canonical bare names refer only to row 9
objects, so either import order works in the suite's single interpreter. The
row 9 folder is on sys.path only while a module is loaded. The audit and helpers,
validator, original invalid-reasons function, caught function, false alarms,
severity vocabulary, masking and ratio helpers are imported objects.

`bio_oracle.caught` strips one leading `./` and then one leading `project/`,
drops a finding whose remaining file starts with `repo/`, and delegates each
match_any entry to row 9. The finding's class, file, severity floor and three-line
interval tolerance are never matched by prose. MINOR or above is a false alarm
on a clean case. This primitive does not judge record validity or publish rates.

Run the independent contracts from the repository root, with all temporary
variables set to the approved scratch folder:

```sh
python3 tests/test_bio_faults_core.py
python3 tests/test_bio_faults_faults.py
```

These tests include conflict witnesses. Their green result does not mean the
blocked builder or schema adapter is accepted. Seven disposable mutations each
run an unchanged green control before the named red witness. Remaining lane
acceptance and mutation requirements have not been implemented or verified.

Read enforcement belongs to the deployment sandbox. Row 9's imported static
audit only detects its named grammar; the residuals in records 0072 items 20–23,
0125, 0127 and 0128 apply unchanged. No model, seal, measured run, first-run
claim, protected-path approval, row exit or public credibility claim is supplied.
