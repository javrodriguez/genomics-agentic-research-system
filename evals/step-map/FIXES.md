# The fix batch from Javier's answers: what each item becomes

_Written 8 Oct 2026 from his answers in `REVIEW.md` (typed 7 Oct, committed at `193b2b04`), against GARS at the pin `a626cdc2`._
_This is a plan for the post-freeze GARS fix batch (task T50, which unparks on Fri 16 Oct); nothing here changes GARS, and nothing is built from it before the freeze allows._
_Every `gars/...:N` reference below is checked against the pin by `tests/test_build_map.py`._

## The fourteen he agreed to

Each takes the fix his page proposed, in the page's words; `MAP.md` ("His answers to REVIEW.md") lists them, read from his page at every build:
S00-yes, S00-onepattern, S01-declare, S01-table, S01-yes, R-protocol, R-confirm, R-formula, D-input, G-model, D-supplier, S03-scripts, S03-order, S03-assay.

## Item 1 (S00-class): his different fix, and the plan around it

### His fix, in his words

> Different fix: agree that the model must not infer the dataset’s class or purpose, but simplify the policy before adding questions.
>
> For the normal workflow, use public versus restricted data, with restricted data requiring a separate setup process. Distinguish software tests from real analyses only where that affects execution; derive this from the selected workflow when unambiguous, otherwise ask.
>
> Remove internal/pilot/commercial distinctions from routine registration unless a concrete supported capability requires them. Keep execution permissions in configuration and enforce them in code. Ask about agreements and usage restrictions only when relevant, and never infer that public availability permits every use.
>
> Revise the proposed fix and implementation plan around this simpler flow, including migration of existing records and tests that preserve the restrictions on unsupported data.

The proposal it replaces (a closed menu of the three classes and five purposes, asked at registration) is superseded and kept in `judgment/00_initialize_project.json` as the reviewer's reading.

### What GARS does today (at the pin)

- Finalize takes `--data-class` from three values and `--purpose` from five, and refuses anything else (`gars/_system/stage00_register.py:619`, `gars/_system/stage00_register.py:622`); the contract's Definitions say the same (`gars/00_initialize_project/CONTEXT.md:58`).
- The values are written once into `00_data/dataset.tsv` and locked: a re-finalize with different values is refused (`gars/_system/stage00_register.py:557`).
- Where a project's jobs may run comes from the class's row of the policy table (`gars/_references/data_policy.tsv:2`, `gars/_references/data_policy.tsv:3`, `gars/_references/data_policy.tsv:4`), enforced in code by `check()` (`gars/_system/venue_policy.py:56`).
- Of the five purposes, only three ever appear in a permitted route: `fixture`, `internal` and `pilot_internal`. `pilot_external` and `commercial` are permitted nowhere, so they already run nothing.
- `pilot_internal` changes execution in exactly one place: on the cluster it needs a named agreement (`gars/_system/venue_policy.py:77`).
- `fixture` changes execution only on the local machine, which accepts nothing else (`gars/_system/venue_policy.py:87`); a public fixture there may also skip declaring its memory.
- Each run's record copies the purpose (`gars/_system/wrapperlib.py:1031`), the record check accepts the five values (`gars/_system/manifest_check.py:144`), and the report prints it (`gars/_system/claims/render_report.py:198`).
- The guard keeps every non-public project closed to the agent and lets the agent register only data a person declared public (`gars/_system/guard_hook.py:119`, `gars/_system/guard_hook.py:551`).
- `identifiable` has no route at all (`gars/_system/venue_policy.py:65`).

So his simpler flow loses no supported capability: the purposes that do something are "a software test" (`fixture`) and "a real analysis" (`internal`), and the agreement that `pilot_internal` carries belongs to restricted data's own setup.

### The revised fix

1. **Routine registration knows two kinds of data: public and restricted.**
   Public is what a person declared public, as today.
   Anything else is restricted, and registration stops there and points to a separate setup the person runs in their own terminal (the guard already refuses non-public data from the agent).
   That setup records what restricted data needs: its class as the policy table names it, the agreement, the expiry and any usage restrictions.
2. **Test or real analysis is derived, not asked, when the workflow settles it.**
   A project built on a GARS test fixture is a test; a project on the person's own data is a real analysis.
   When the selected workflow does not settle it, registration asks one question with two fixed answers (`test`, `analysis`) and re-asks on anything else.
   The model never picks it.
3. **internal, pilot and commercial leave routine registration.**
   They come back only if a concrete supported capability needs them (none does today: see above).
4. **Execution permissions stay in configuration, enforced in code.**
   The policy table keeps saying where each kind of data may run, and `check()` keeps refusing everything else; only the vocabulary it reads changes.
5. **Agreements and usage restrictions are asked only where they matter.**
   For restricted data, always, in its setup.
   For public data, only when the person says the data comes with terms; otherwise the record says the usage terms are unknown, never that every use is allowed.
   A capability that needs a use permission (none is supported today) must refuse on "unknown".
6. **The closing message shows what was recorded**: public or restricted, and test or analysis.

### Migration of existing records

- Every existing `00_data/dataset.tsv` row is migrated by one deterministic script, never by hand and never by the model.
- The old values are kept in the row, beside the new ones, so nothing is lost and the lock still compares like with like.
- The mapping: `public` + `fixture` → public, test; `public` + `internal` → public, analysis; `public` + `pilot_internal` → public, analysis, with its agreement kept; `deidentified_under_agreement` → restricted (its class, agreement and expiry kept); `identifiable` → restricted with no route; `pilot_external` and `commercial` → refused by the migration and listed for a person, since no route ever served them.
- **No migrated row may gain a route.** The script writes each row's permitted routes explicitly as the old set translated, and refuses a row whose new routes would be wider. In particular, a public `pilot_internal` project keeps needing its agreement on the cluster.
- Run records already written are records: they are never rewritten, and the record check keeps accepting the old purpose values for runs made before the change, while new runs carry only the new ones.
- The script has a dry run that prints every row's old and new values, and the live run refuses unless the dry run's output is unchanged.

### Tests that keep the restrictions on unsupported data

- **Routes never widen:** for every class, purpose and machine combination the old table allowed or refused, the migrated equivalent gives the same answer, or a refusal; never a new allow. This is one table-driven test over all of them.
- `identifiable` stays refused everywhere; restricted data stays cluster-only with an expiry; the local machine stays test-only.
- The guard still refuses registration of non-public data from the agent, and still keeps restricted projects closed.
- Registration refuses a test-or-analysis value the workflow did not derive and the person did not type; and it never records "every use allowed" for public data.
- The existing route and policy tests move to the new vocabulary with their expectations unchanged in effect: `gars/tests/test_data_route.py:9`, `gars/tests/test_venue_policy.py`, `gars/tests/test_venue_policy_faults.py`, `gars/tests/test_data_class_required.py` and `gars/tests/test_nonpublic_read_block.py`.

### Choices his words leave open (settled when T50 is planned)

- The exact names in the record for "test" and "analysis", and whether the old `purpose` column stays as the canonical field with two values or gives way to a new one.
- How the workflow is judged unambiguous: a fixed list of GARS's own test fixtures is the narrowest reading.
- Whether the separate setup for restricted data is a new command or the existing human-only declaration file extended.
