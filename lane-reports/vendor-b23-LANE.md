Status: design stop (round 1)

## ROUND 1 (local executor, Tue 20 Oct 2026, 17:40 EDT / 21:40 UTC)

glitch-26's ruling B23-1: design first, no code. Base `a76b4dd2` (B22, reviewed PASS).

- Design note: lane-reports/vendor-b23-DESIGN.md.
- Source: openai/codex `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` (`git ls-remote ... 'refs/tags/rust-v0.162.1^{}'` printed it), fetched read-only into the session scratchpad.
- athena, read-only, file names only: no w-o* rollout holds a FileChange; the one stream holding a file_change is w-o38's turn 1, whose rollout was not copied out.
- Findings:
  - The view graders read only the path and write versus edit, for Claude as for Codex.
  - Content is read only by reach (T-8). For a patch it lives in the rollout: the FileChange item and the patch text in a READ custom_tool_call.
  - The rollout's FileChange keys its changes by path, and reach's string walk skips dict keys, so the build must hand reach the paths as values.
- For the ruling (design section 12):
  - Q1 m1: recommended option C, the view keeps a started patch as an unanswered call;
  - Q2 n3: recommended, a rename is held under a named reason;
  - Q3: T-8:file-change stays PENDING with its reader wired at the site, until a RECORDED fixture of a patch edit exists;
  - Q4 delete and Q5 a patch refused before Begin: named, not built;
  - Q6: no change to native_reader_registration.
- B23-3's parity note text is proposed in design section 10. It is not built until the ruling.
- Correction (B23-4, review of a76b4dd2 NIT n1), checked at the pin:
  - Design note vendor-b22 section 10c says "nothing else in the world-state assembly reads the version". That is too broad.
  - session/world_state.rs:108-138 switches the environment context's subagent list on it (V2 at :110, Disabled and V1 at :132).
  - session/turn.rs:1294 records it in the analytics TurnResolvedConfigFact (built from :1248).
  - With no child threads both list formatters render empty, and the analytics fact is not model-visible, so 10c's conclusion stands.
  - B22's design note stays as written.
- No code, test or fixture. No push, no mirror, no athena run.
