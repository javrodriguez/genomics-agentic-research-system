# Science review harness

Development machinery for the partial science set under record 0135, decided by
Glitch under the owner's standing delegation. No model has run against these
cases. The prompt is fixed without case tuning. This is not row 10's exit, a
public credibility claim or protected approval; 0137–0139 remain reserved.

From the repository root, set TMPDIR, TEMP and TMP to runtime-resolved approved
scratch. All outputs must be outside a Git work tree, in fresh folders.

```sh
python3 evals/bio-faults/bio_generate_base.py --base rna-a --out "$base_folder"
python3 evals/bio-faults/bio_build_cases.py --out "$output_folder" --log "$private_log"
python3 evals/bio-faults/bio_run_reviews.py --cases "$output_folder/cases" --manifest "$output_folder/manifest.json" --prompt gars/_references/prompts/review_faults_science.md --kits-root "$neutral_kits" --records "$private_records" --model "$model_id" --producer-account "$producer_account" --login-entry 1 --settings "$sandbox_settings"
python3 evals/bio-faults/bio_score.py --records "$private_records" --key "$output_folder/private/key.json" --manifest "$output_folder/manifest.json" --answers evals/bio-faults/fixtures --runs evals/bio-faults/runs --out "$published_copy"
```

These are coordinator instructions, not commands to run a model during this
producer round. A measured run requires a separate reviewing account and the
sandbox deployment. Transfer only cases and the public manifest to that account.
Use `GARS_SEALED_BIO_FAULTS_DIR` for sealed inputs and comma-separated `--answers`
roots for scoring. `--only` selects comma-separated neutral ids. Only usage-limit
attempts may resume into a fresh neutral kits root. Records are never overwritten.
`--compare` names an earlier published run with the same prompt hash and model.

Phase A has design, data and results; phase B adds the narrative only after A
exits and resumes A's launch-owned session id. B's actual id comes from its own
init event. Both phase ids and the code-stamped equality flag are in the envelope;
each audit uses its own phase's id. There is no fresh-session fallback.

<!-- Schema differences from row 9, lane item 7 and ruling R1:
1. Finding class enum: science vocabulary plus other.
2. Envelope phases: exactly A then B, session id, timestamps, exit code,
   usage-limit ending, blindness calls/hits, A notes_sha256, and B's code-stamped
   session_matches_phase_a boolean.
3. Envelope narrative_withheld_until_phase_b: required code-stamped boolean.
4. envelope.reviewer.prompt_path enum: exactly the science repository-relative path.
Every other schema key, enum and required list is equal to row 9.
-->

Row 9's limited validator checks the science schema; the adapter additionally
checks phase cardinality and prefixItems. It checks record == manifest == science
prompt path before its pure projection changes only the path in copies of the
record and manifest. Hash comparison remains row 9's. Science findings become
`other` in the row 9 view, and phase blindness counts are summed. Phase failures,
limits, hits, a false withholding flag or a changed resume session are INVALID.

Every row 9 shared primitive is imported under private aliases with canonical
bare names bound only to row 9 objects. The two harnesses coexist in the suite's
single interpreter. The science oracle strips one `./` and one `project/`, drops
remaining `repo/` prefixes, and calls row 9's field matcher for each match_any.
No prose match or extra tolerance is used.

The builder imports stage 01, wrapper collectors, evidence emission and rendering.
Collectors run on scratch scaffolds with synthetic execution sidecars. Stage 03
runs its real verify with the supplied approval hash/timestamps/expiry, a scratch
protected store, a clock at the recorded execution finish, and synthetic
execution sidecars. Only store actor/path bindings are mapped to the local process;
no approval command or real job runs. These are data/content gates, not execution
or deployment evidence. Cases receive none of the scratch scaffolding. Files and
folders have fixed modes and mtimes; neutral ids are salted. R2 exempts only the
whole top-level manifest key `harness_commit` and the exact science path value
under `prompt_path`. No case-byte exemption exists.

INVALID cases remain in every denominator, never caught or clean. Ratios with
zero denominator print uncomputable. The partial-set §17 line always says NOT
met. First-run values are retained, including per-class values. Published copies
use row 9's masking function; private inputs, raw streams and keys stay private.

Run `python3 tests/test_bio_faults_core.py`,
`python3 tests/test_bio_faults_pipeline.py` and
`python3 tests/test_bio_faults_faults.py`. All tests are stdlib and use runtime
stubs, not a model or network. Every fault control first requires its unchanged
copy to pass, then requires the named assertion to fail in an isolated copy.

Read enforcement belongs to the deployment sandbox. Row 9's audit residuals in
0072 items 20–23 and 0125 apply unchanged, with 0127/0128's later placement rules.
See INTERFACE.md for the independent sealer handoff and SEALS.md for empty slots.
