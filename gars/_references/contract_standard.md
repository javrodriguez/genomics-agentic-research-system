# Stage contract standard

Every stage and sub-stage `CONTEXT.md` contains these eight sections, in this order.
`00_initialize_project` is the worked example.

| Section | Role |
|---|---|
| **Purpose** | What the stage produces, in two or three sentences. |
| **Inputs** | What must be collected from the user or read from a prior stage. Exact paths, split into *working* (this run) and *reference* (every run). |
| **Scope Boundaries** | What the stage may **not** do. Stated negatively and specifically. |
| **Definitions** | Every term the Process relies on, defined precisely enough that no judgment call is needed. |
| **Process** | Numbered steps, one action per step. Every failure branch is its own step with its own response template. |
| **Response Format** | The complete set of message templates. The agent sends nothing outside them. |
| **OUTPUT** | Table of artifacts written, with their exact contents. |
| **Human check** | The one thing a person does before the next stage runs. |

An agent running a stage follows its contract literally. If a step seems to need deviation, it
stops and asks rather than acting.

## Why these sections, and not fewer

Three of them exist because positive instructions alone failed to constrain a real agent, in a
real run. Do not simplify them away.

**Scope Boundaries — stated negatively.** The first live test carried "do not improvise steps it
does not specify" at workspace level *and* an explicit failure branch in the contract. Given a
path with no FASTQs, the agent searched subdirectories, read a colleague's `settings.txt` and
sample sheets, and volunteered an analysis of an unrelated experiment. Both instructions were
present; both were ignored. What works is naming the forbidden action literally: "do not read
sample sheets, settings files, QC reports, or pipeline outputs found there."

**Response Format — fixed templates.** Free-form replies varied every run and buried decisions in
prose. Numbered templates `T1…Tn` make the set of things the agent can say finite and reviewable.

**Process — decomposed.** One action per numbered step, every failure branch its own step. The
original step 7 of stage 00 was a 90-word sentence containing five conditionals; buried branches
get skipped.

**Response Format — the agent runs the stages, the user decides.** A template must never tell
the user to run a stage, a sub-stage, or a script: they do not, and saying so misdescribes the
system. Name what the user must decide or edit, then say what *you* will do once they confirm —
"tell me when the design is filled in and I will emit the samplesheets", not "then run
01_prepare_samplesheets". A closing template that points at an unimplemented stage is worse still:
say plainly that nothing further is automated.

**Response Format — a template that ends by asking is a wait point.** The agent sends it and
stops. So two templates must never ask the same thing, and two consecutive Process steps must
never both send one: the agent sends the first, waits, and the second never happens.

Stage 00 shipped exactly that bug. `T2` acknowledged the title *and* asked "Which assay types will
this project include?", while step 3 ran `assays` and sent the menu that asks the same question
properly. The agent sent `T2`, waited, and the menu was never rendered — the user saw
`Supported: Bulk RNA-seq` with no IDs to choose from and asked why. `T2` was a leftover from
before the menu existed; the fix was to delete it and fold its one useful line into the menu.

When adding a template, check what the step before it sends. When adding a step that replies,
check that the step before it waits.

**And when a stage starts doing something a different way, check the templates of the stages
around it.** A handoff template describes what happens next; change what happens next and the
handoff becomes wrong without becoming invalid. Stage 01's closing template went on offering to
take reference paths as free text after stage 02 had begun offering them as menus — nothing was
broken, it was just no longer true.

**Human check — exactly one, and concrete.** State something a person *does* — "read the first
three rows and confirm the sample IDs match your notebook" — not "review the output". A stage
whose human check is vague has no gate, and the next stage will consume whatever is there.

## Editing a contract

Replace whole sections by heading. A previous edit cut on `t.index("---")`, matched a markdown
table separator, and silently duplicated half the document.

Adding a section to the standard means adding it to **every** contract in the same change.
A standard that half the contracts follow is not a standard.
