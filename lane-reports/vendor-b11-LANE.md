Status: in-progress

# Lane vendor-b11

ROUND 1 SUMMARY FOR REVIEW (cloud executor, Mon 19 Oct 2026, about 03:50 UTC): lane-reports/B11-DESIGN-NOTE.md written by static reading of Codex rust-v0.162.1 (092d3acd) and Gemini CLI 0.64.0 (tarball 891a794e..., bundle hashes in the note); no code changed, nothing run. Findings that shape B11:
- H1: Codex rewrites config.toml on turn 1 of every take (trust persistence: the bypass flag plus the run tree's .git), adding [projects."<run tree>"] trust_level = "trusted" via temp file and rename. Strict byte identity would refuse every honest multi-turn Codex take. Recommended: take_config places that table up front (ruling needed).
- H2: Codex refreshes auth.json in place (access token within 5 minutes of exp, or a 401): same inode, new bytes. B11 checks it by facts only; a rotated refresh token also leaves the host lease source stale (flagged for the lease road).
- H3: a killed Codex turn leaves tmp/arg0/codex-arg0*/ with .lock and four symlinks; B11 must admit exactly those, and take_config.config_sha256 refuses links.
- Gemini never rewrites .gemini/settings.json as placed (no migration key matches).
- H5 (ruling needed): HOME is the config mount, so the agent's own tools (conda, R, Nextflow, pip caches) write under it and a closed listing refuses those honest turns; recommended a separate agent HOME.
- Refused set includes shell start files (Codex's snapshot runs a login shell and sources .bashrc), root settings.json (Gemini launcher), .gemini/GEMINI.md and tmp/<slug>/memory/** (model-writable memory), and an edited skills/.system with its marker untouched.
- B9 citation NIT: take_config cites the orphan bundle gemini-6ESINPDZ.js; the running chain's lines are gemini-Q2GRYIAK.js 11145 and 11153 (behaviour unchanged).

RESUME HERE: review stop (round 1)

## Log

- Round 1 started Mon 19 Oct 2026 03:24 UTC on lane/vendor-b11 at f257a99d; design note written; status needs-review.
- Round 2 (glitch-26's rulings R-H1 and R-H5 on the design note) started Mon 19 Oct 2026 04:26 UTC on lane/vendor-b11 at 56d7713b. Baseline, clean environment, TMPDIR outside the clone: test_take_config 10, test_run_take 68, test_env_allowlist 29, test_walk_builders 93, test_vendor_roads 13, test_live_box 38, test_build_draft 49, test_harness_bookkeeping 21 all OK; of the 38 other modules naming TAKE_ENV, the launcher or the draft, 35 OK and test_nested_agent, test_preflight, test_sidecar (with test_settings_guard) red as in earlier rounds (this root sandbox). test_vendor_workspace_guard is not present.
