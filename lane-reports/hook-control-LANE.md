# Lane file: hook-control (the D8 hook positive control for arms O and G; Gap Study round 4, a D8 walk-phase duty)

Append-only.
Builder: a Claude Opus 5.5 (medium) sub-agent of glitch-f1 (the Lane-orchestrator), on the Mac, under Javier's standing delegation.
Clone: /Users/javrodher/aegis-builds/hook-control-20261021, a clone of /Users/javrodher/aegis-builds/vendor-b27-20261021, branch lane/hook-control from B27's head 49c350a9b008e3ea15f83f3873fe62b3766722fe; its push URL is set to `DISABLED-no-push` and nothing is pushed.
Design: lane-reports/hook-control-DESIGN.md, a byte copy of /Users/javrodher/glitch/plans/gap-study-round-4/hook-control-DESIGN-2026-10-21.md (sha256 da686566ef4a50e610524af289b12cb393a0de96b76a1873473be2601ac4ee45 on both, `shasum -a 256` at 22:45:29 EDT).
Build and test on fakes only on the Mac; the athena run is a later operator's step. Nothing here runs a container, a CLI, a model or a login.

## glitch-f1's rulings on the design's open calls (as received in the brief, Wed 21 Oct 2026)

1. Base: B27's head 49c350a9 (it carries no walk records, so its ships pass athena's door), in this new clone; the lane later merges into lane/vendor-b28 after B27 does (small conflicts expected in B27's probe and tests; changes kept additive).
2. Gemini: the G-on/G-off pair on B27's stub road as designed.
3. Codex: the four configurations as designed (O-on-bypass must fire, O-off-bypass silent, O-off-study with the exact walk argv silent, O-on-study informational); the trust-bypassed pair is accepted as the proof that the switch gates hooks.
4. Codex roads: C0 (no model, no login, internal network) and C1 (a dead local provider) in one athena trip; C2 only if both on twins stay silent, and then it is a new ruling.
5. Verdicts: PASS only when every on twin fires and every off twin stays silent; INCONCLUSIVE when an on twin stays silent (never a pass); FAIL when any off twin fires, which holds that arm's counted runs.
6. The fail-safe pre-run marker check and the twin diff rule stay as designed.
7. The record: the fetched folder /Users/javrodher/aegis-builds/hookctl-<date>/ plus a labelled note in lane-reports/, read by the pre-freeze reviewers.
8. Arm A (Claude) is out of this lane's scope: a separate read-only investigation answers whether GARS's hooks run there.
9. Tests on fakes as the design lists them, red first; mutants for the verdict rule, the diff rule and the marker pre-check; the one-process hazard check.

## Stage 1: the base, the design copy, this file

- Clone and branch: `git clone` of vendor-b27-20261021, `git checkout -b lane/hook-control 49c350a9b008e3ea15f83f3873fe62b3766722fe`; `git log --oneline -1` read "49c350a9 vendor-b27 stage 8: the A1-fake cross-check gets one fake file per process (glitch-f1's B27 ruling 4)".
- Mac discipline: every batch runs behind `/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok --work gap-study-r4` (exit 0 = go); first read 22:38:13 EDT, "light ok: load1 11.62 < 16.00, memory pressure normal, CPU speed limit 52 >= 50".
