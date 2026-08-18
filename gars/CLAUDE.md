# Genomics Agentic Research System (GARS)

## What This Is
A workspace for the management of research projects in genomics. Accessed through dialogue interactions with LLM. The filesystem is the agent, the LLM is the navigator. A user usually does; 1) invoke a project creation, 2) ingests data and metadata, 3) Runs automated/validated bioinformatic frameworks, and 4) Manages Multi-projects throught a project-based memory/context system. GARS was developed following the Integrated Context Methodology (ICM) architecture for agentic-orchestration, integrated with ClawBio and in-house bioinformatics skills.

> **Scope of this file.** This is orientation for *using* a GARS workspace to run an analysis.
> If you are developing GARS itself — editing contracts, docs or this template — the entry point
> is the `CLAUDE.md` at the root of the GARS repository, not this one.

## Current State
- This folder is a reference architecture until it contains a project. Once projects/ holds one or more projects, treat it as an active workspace.
- Work in progress: the tree below is the target layout, scaffolded incrementally. Stage contracts exist for `00_initialize_project`, `01_prepare_samplesheets`, and `02_bioinformatics` (with both `rnaseq_bulk` sub-stages); `03_custom_analysis` is planned.
- Skills are **not vendored**. They ship with the installed `clawbio` package and are read-only; this workspace holds contracts only. A sub-stage directory under `02_bioinformatics/` contains a CONTEXT.md, never a `.py`. See `02_bioinformatics/CONTEXT.md` for resolving the skills path at runtime.
- To use this workspace: copy the GARS folder and initialize a project.

## Agent Entry Point
Before responding to any project request, read CONTEXT.md for the stage map, then read the CONTEXT.md of the stage the request maps to. Execute that stage's contract literally:

- Its **Scope Boundaries** section is binding. Do not read, search, or act outside it, however helpful the deviation would seem.
- Its **Response Format** templates are the only messages to send. Do not add observations, suggestions, or offers of work beyond the template.
- If a step appears to need deviation, stop and ask. Never act first and report afterwards.

## Structure
```
gars/
    CLAUDE.md             # You are here. Workspace map and entry point.
    CONTEXT.md            # Workflow routing. How stages connect.
    projects/
        CONTEXT.md
        <project_title>/    # example project          
            CONTEXT.md      # Project information and details 
            HISTORY.md      # Registry of actions and production  
            _config/        # Project specific references, settings, etc    
            00_data/
                <assay01>/
                    raw/
                    files.csv       # one row per sample-lane. machine-owned
                    samples.csv     # one row per sample. user fills the design
                <assay02>/
                    raw/
                    files.csv       # one row per sample-lane. machine-owned
                    samples.csv     # one row per sample. user fills the design
                ...    
            01_samplesheets/
                <assay01>_samplesheet.csv
                <assay01>_design.csv
                ...
            02_bioinformatics/
                <assay01>/<stage01> 
                <assay01>/<stage02> 
                <assay02>/<stage01>
                <assay02>/<stage02>
                ...
            03_custom_analysis/
                <custom_01>
                <custom_02>             
                ...
    00_initialize_project/
        CONTEXT.md
    01_prepare_samplesheets/
        CONTEXT.md
    02_bioinformatics/
        CONTEXT.md
        <assay01>/   # e.g. rnaseq_bulk
            <stage01> # e.g 01_nfcore-rnaseq-wrapper   # Can include in-house artifact/s
                CONTEXT.md 
            <stage02>   # e,g 02_rnaseq-de
                CONTEXT.md
            ...     
        <assay2>    # e.g atacseq_bulk
            ...
        ...
    03_custom_analysis/
        CONTEXT.md
    tools/
        gars-env.sh       # the single definition of the execution environment.
                          # Sourced by every submit.sh; sets PATH, JAVA_HOME, caches,
                          # $GARS_PY and $GARS_SKILLS. No skills/ here -- skills ship
                          # with the installed clawbio package and are never vendored.
        presentation/
        manuscript/
            01_draft/
            02_review/
        grant_proposal/
            01_draft/
            02_review/
        divulgation/
        database/
        literature_review/

    _references/          # domain knowledge (standards, technical documentation)
        ICM_agents.pdf  # Integrated Context Methodology Manuscript
        assay_stage_skill_map.md    # Assay -> Stage -> Sub-Stage -> Skill Map. Supported assays = the Assay column.
```

## How to Use
1. Read CONTEXT.md for the full workflow and stage map.
2. Copy the GARS folder to your working location.
3. Tell the agent you want to start a new project. This triggers 00_initialize_project, which creates projects/<project_title>/, symlinks your raw data under 00_data/<assay_type>/raw/, and writes the project's CONTEXT.md, HISTORY.md, and per-assay files.csv + samples.csv.
4. Fill in the experimental columns (condition, group, replicate) of each 00_data/<assay_type>/samples.csv — one row per sample, so each value is entered once. To analyze only a subset, delete the other rows: stage 01 treats a sample with no row as excluded, and leaves its raw data in place so the choice is reversible.
5. Proceed through the remaining stages in order (01_prepare_samplesheets → 02_bioinformatics → 03_custom_analysis), reviewing output between each.

## Layer Annotations
- CLAUDE.md: L0 (always loaded, ~800 tokens, orientation)
- CONTEXT.md: L1 (loaded on workspace entry, routing)
- Stage CONTEXT.md files: L2 (loaded per-task, stage contract)
- _config/ files: L3 (project-level reference, loaded selectively per stage)
- _references/ files: L3 (workspace-level domain knowledge, loaded selectively)
- Source material and stage outputs: L4 (working artifacts, loaded selectively)
