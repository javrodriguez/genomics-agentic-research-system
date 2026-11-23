# Rulings on the Codex2 sign-in road (glitch-b5, Sun 18 Oct 2026, 05:3x EDT)

Under Javier's standing delegation of every non-money call, on PLAN-codex2-signin-road-2026-10-18.md (read at vendor-lane head 7f0ae4614b3b70f5d6939721598d975a93963bf4).
These are glitch-b5's rulings, not Javier's words.

## R1. Arm O's egress host is chatgpt.com (B4)

The one host a Codex take may reach becomes exactly `chatgpt.com` (no subdomains), sourced from the pinned Codex 0.162.1's `CHATGPT_CODEX_BASE_URL`, recorded as a constant with its URL and tag.
Reason: the 13 Oct owner amendment requires subscription sign-in, and at the pinned version subscription traffic goes only to `chatgpt.com/backend-api/codex`, so `api.openai.com` would refuse every turn.
Named residual, written into the plan's section 6 table and the study's limitations: `chatgpt.com` is also where the Codex2 account's own ChatGPT data lives, and a take holds a copy of the lease; the proxy sees hosts, not paths, and the study does not intercept TLS.
Javier's card asks him to confirm Codex2 holds nothing he would mind a test agent reaching.

## R2. The login container uses the default bridge network, a named exception (B1)

No one-host proxy for the login.
The container runs only the pinned Codex binary's device login (by image id, `--pull=never`): no model, no agent, at most 15 minutes.
It runs as container root (host javier under rootless Docker) with `--cap-drop ALL`, `--security-opt no-new-privileges`, `--read-only`, a tmpfs `/tmp`, and exactly one bind mount, the lease folder.
Reason: the threat a take's one-host proxy answers, an untrusted agent reaching out, is absent here, and the simpler road has fewer moving parts during Javier's five minutes.
The review checks those flags, that nothing else is mounted or passed, and that no environment variable carries a credential.
`proxy_conf.render_host` is not built.

## R3. The three PENDING vendor config values, and no practice mode (B6)

`CODEX_REASONING_EFFORT`, `GEMINI_THINKING` and `GEMINI_AUTH_SETTING` are each sourced by a static read of the pinned package (no model call, no network), recorded beside the value with the file and line it came from.
No vendor walk runs before `take_config.write` runs on the walk road; there is no practice mode (D8 line 312 expects no web search even in a single walk).

## R4. The O and G pin profiles (B7)

As the plan writes them: codex, per model, `{"permission_mode": "bypass", "version": "0.162.1"}`; gemini `{"permission_mode": "yolo", "version": "0.64.0"}`; each equal to its adapter's `MODE_FLAGS`.
The rate-limit and spend-cap markers follow the T4 plan's R-4 as written; if R-4 lets practice walks run without them, practice walks do, and the freeze adds them.
`test_pin_for_vendor`'s refusal assertion moves by this ruling, named in the commit.

## R5. The gate's order (B8)

1. Javier signs in; `verify_codex_lease.py codex2` prints `RESULT: OK`, and glitch-b5 runs it again.
2. B2 to B7 are reviewed and the athena battery is green.
3. One commit flips `CODEX_SUBSCRIPTION_READY` to True and rewrites its comment to this order; `test_run_take`'s "the gate is closed" assertion moves to "open" by this ruling, named in the commit, and its review checks nothing else moved.
4. The first real Codex walk runs and commits `pending-native-reader`.

B8 is not built before step 1.

Added 18 Oct 2026 by glitch-b5's ruling B7-F4 (vendor-admission round 17, review r17 MINOR 1), an addition to this order, not a rewrite of it: before step 3, Javier confirms that the Codex2 account holds no purchased credits and no automatic top-up.
The reason: a ChatGPT sign-in bills no money per call unless the account holds purchased credits, and a take could draw on them with no error at all; routing.json's codex spend-cap texts refuse only once credits run out.

## R6. Where each piece is built

B1 (the login wrapper, the prepare and verify scripts, their tests and mutants) is built by a local builder on this Mac, because it is deployed to athena and checked against the pinned image there; its files sit only under `lane-reports/codex-login/`, on its own branch from 7f0ae461.
B2 to B7 are the vendor-admission lane's rounds 17 onward, in the cloud, in the plan's order, each red first.
B1 joins the lane at the lane's close; the two share no file.

## R7. The account record

glitch-b5 writes `/home/javier/gap4-secrets/account-emails.json` (mode 600) on athena from the two addresses Javier gives, with a small script that validates through `walk_builders.account_emails`.
No address is ever written into a repository, a record or a commit.

## R8. The Gemini key

Checked by glitch-b5 at 05:30 EDT: `verify_walk_login.py r4-g` on athena prints every line passing and `RESULT: OK`.
Javier owes no Gemini paste; he only confirms the r4-g study key still exists in AI Studio, and the first Gemini walk's first turn would show a dead key anyway.
