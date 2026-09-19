---
name: New skill proposal
about: A pipeline or tool you would like wrapped as a GARS skill.
---

**Which pipeline or tool?**
Its name, version and a link to its source.

**Which assay and stage?**
The assay it serves and the stage under `gars/` it would run in.

**What goes in and what comes out?**
The input files and the outputs, named with the types in `gars/_references/artifact_types.md` where one fits.

**Have you drafted it with the authoring toolkit?**
If so, paste the output of `python3 gars/_system/authoring/create_bioinformatics_skill.py conform <your wrapper dir>`.

**Is there test data?**
A public accession or a small fixture the skill could be checked against.
