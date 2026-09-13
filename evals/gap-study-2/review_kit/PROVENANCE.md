# Where round 1's review kit came from

Round 1's review and verifier kit was never committed; its only copy sat in a session scratchpad the operating system can clear.
On 2026-09-13, at round 2's kickoff, the six files were read in full and copied byte-identical to a machine-only folder in this repository's working copy, which is never committed.
They are not committed here unmodified because they carry machine paths and account identifiers.
The kit this folder will hold is built from them at the last checkpoint before blind review 1, with those identifiers removed and every path taken from `study.py`.

| Round 1 file | sha256 of the rescued bytes |
|---|---|
| `review23/BRIEF.md` (the pre-freeze reviewer brief, review 23) | `b446c61ceaa39e46989bb95438871a3626d3942e9b5b7ace70413ccf8413f838` |
| `review12/why.md` (the purpose statement given to reviewers) | `07f35009428712f0a97c9bb343e4575071f383c36696dabe342a7f69e4115108` |
| `review23/blindness.py` (the reviewer blindness check) | `98463ba67483043e2d50475fe4e61dad1091a4fbe81f95add70c2963348cb66b` |
| `verifier2/launch.py` (the headless reviewer launcher) | `90398d0dd1da4bfb2754b705ad42c8a127aa39a793b9bfb722f6ec2fec8c9197` |
| `BRIEF-verifier-2.md` (the final verifier brief) | `f0a0f4da5438e50e89e53bf689d7e04b8de9766f242b9130263ce94775d7a731` |
| `commit_verifier_report.py` (commits a verifier report unedited) | `b1bc33a6c77917970153c39547d145e03c5288f400a92bf8a486a3b18c4830e9` |
