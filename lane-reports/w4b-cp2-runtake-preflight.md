# Lane w4b-cp2-runtake-preflight: CP2 run_take, take_config and preflight (code with fakes)

_Gap Study round 4, wave 4. Base `48f10056`. Written Thu 8 Oct 2026 (19:06 EDT, read from `date`) by the lane's builder (opus-medium)._

No image or container was built or run.
No model was run.
No login or `.env` file was read.
Nothing was pushed or merged.

## What the lane built

All files are new, under `evals/gap-study-4/`, and claimed in `COPIED.d/w4b-cp2-runtake-preflight.json`.

- `box/run_take.py`: the runtime protocol (`Completed`, `DockerRuntime`, the box's one subprocess call), `TakeSpec` and `create_argv`, the environment per harness and the cross-arm refusal, `read_login`, the config folder's life, `launch` and `teardown`, leaked containers, the agent's leftover processes, the counters, the exit record and `run_turn`.
- `box/preflight.py`: `probes`, `run` and a pure `evaluate` over the closed ordered `PREFLIGHT_CHECKS` (18 checks), `expected_take_inspect`, `inspect_mismatches`, `write` (beside the evidence folder) and `postflight`.
- `box/take_config.py`: the per-take config files per harness, `write` and `config_sha256`.
- `tests/test_run_take.py`, `tests/test_preflight.py`, `tests/test_take_config.py`: fakes only, a module-wide process guard armed after the one leak-word read, and in-memory mutants for every guard, printed red.
- `checks.d/w4b-cp2-runtake-preflight.txt`: the three test files and interface 10's process audit (`test_run_take.py --process-audit`).

## Commits

| commit | what |
|---|---|
| 132021fe | checkpoint, red: tests first, run_take a skeleton |
| 6be8d85b | checkpoint, green |
| b8ff16d9 | preflight |
| c8e3f167 | the rest of run_take tested |
| f933e494 | take_config |
| de939b5f | the process audit reads the lane's test files too |
| 9edb0e47 | fold 1, red tests first (the leak-word fix first) |
| f959711f | fold 1, the fixes |
| fb88e7f3 | the lane report |
| 137ad327 | fold 2, red tests first |
| c46b61fe | fold 2, the fixes |
| 3368cd37 | the lane report's Fold 2 section |
| 44ff12ec | fold 3, red tests first |
| 932f84ad | fold 3, config home isolated, one entry at most, ratified signatures named |
| 4486bc8b | fold 3, the audit's from-imports, module attributes and getattr by construction |
| 355a2031 | the lane report's Fold 3 section |
| 47d653d9 | fold 4, red tests first (gates pending the lift) |
| ddf9e22f | fold 4, the audit binds import-bound names and dynamic builtins (gates pending the lift) |
| (this commit) | the lane report's Fold 4 section (gates pending the lift) |

## The lane's own decisions

1. take_config is its own file and test, so each file stays one owner and small.
2. Memory is exactly three times the reservation.
3. Arms O and G execs raise NotReady while their vendor billing-route list is PENDING (stricter than "until then the set is the list above"); the cross-arm refusal fires first.
4. `exec_argv` accepts only `AGENT_USER`; `read_login` accepts only the three login names, refuses links and requires ASCII; images are `sha256:<id>` and every id is a full 64-hex id.
5. The inspect spellings are a mapping taken from the Docker Engine API, gated by `run_take.INSPECT_STATUS = PENDING`; `container_state` refuses while it is pending.
6. CP5's study folders and leak words are PENDING constants in preflight, never parameters, so no caller can pass an empty list.
7. preflight adds `consequential-paths-readable`: an unreadable consequential path in the sidecar's `begin` reply fails preflight before the first turn (the lane lead's C3 detail). The drive step passes that reply as `run(begin_reply=)`.
8. teardown returns its record and writes only `proxy.log` (stdout, then stderr).
9. The internal network gets a fresh neutral name (`n` + 24 hex); removal is always by id. The proxy joins the default network by the name `bridge`.
10. The keep-alive is pinned as `--entrypoint sleep` with command `infinity`, and both are inspected (fold 1).
11. Postflight also fails on any credential-like name (`CREDENTIAL_LIKE`, which now includes `account`).
12. `memory.low` is checked against the reservation and `cpu.max` against `cpus * 100000 100000`, both derived, not measured.

## Interface: the ratified signatures

glitch-f3 ratified both required additions on Thu 8 Oct, under Javier's delegation (glitch-f3's ruling, not Javier's words), so the merge binds them as interface:
- `exec_argv(container_id, inner, *, user, workdir, harness, run_tree, login_file, caller_env=None)`: the required `login_file` is the file the login is read from at exec time (`read_login`); its value reaches only the client environment.
- `launch(runtime, spec, *, sidecar, proxy, record_dir, caller_env=None)`: the required `record_dir` is the take's record folder, where the launch record and, at teardown, the proxy log are written, beside the evidence folder.

Both are named in the functions' docstrings too.

## Departures from the pinned signatures (W4B1-10; Review A)

- `exec_argv(...)` adds a required `login_file` (the login is read at exec time) and an optional `caller_env` (the client env's seam; since fold 1 it never switches the refusal off).
- `launch(...)` adds a required `record_dir` (launch writes the launch record there) and an optional `caller_env`. `Launched` gains `spec`, the take's spec on the network launch made.
- `teardown`, `leaked`, `refuse_restart_if_leaked`, `agent_processes`, `kill_agent`, `wait_gone`, `container_state` and `run_turn` take an optional `caller_env`.
- `preflight.run(...)` adds `begin_reply` and `caller_env`.
- `agent_exec_argv(...)` adds `config_home` (only a harness's config-home variable at the config mount).

The two required additions, `login_file` and `record_dir`, were ratified by glitch-f3, Thu 8 Oct (see the interface section).
The remaining departures are the optional ones above (`caller_env`, `Launched.spec`, `begin_reply`, `config_home`).

## Fold 1

Two reviews:
- Review A, the lane's own review of `f933e494`. glitch-f3 ruled "fold all of it" under Javier's delegation (glitch-f3's ruling, not Javier's words). The NITs are at the lane lead's discretion, and all are folded.
- Review B, the lane lead's round 1 review of `de939b5f`.

| finding | severity | fix | test and mutant |
|---|---|---|---|
| W4B1-8 / A-10 round 3 leak word committed | MINOR | the read is checked by count and shape; test data draws round 3 words at run time or uses the lane lead's own words | `test_leak_words_read`; no round 3 word is typed as test data (prose and repository paths that contain one are left; see open question 1) |
| W4B1-1 / A take on the stale network | MAJOR | `_on_network(spec, launched.network_id)` before `create_argv` and `expected_take_inspect`; `Launched.spec` | `test_network_is_launchs` (spec network differs from the created one); mutant `stale-spec-network` red |
| W4B1-2 PENDING refused late | MAJOR | `_check_launch_ready` raises NotReady before any runtime call | `test_pending_refused_before_any_call` (zero calls, both cases); mutant `no-ready-gate` red |
| W4B1-3 hollow audit | MAJOR | flags the modules as values, `.os`/`.subprocess`/`.pty`/`.asyncio` on any base, `__dict__`, `sys.modules`, `vars`/`globals`/`locals`/`setattr`/`delattr`, and non-constant `getattr`; the box modules were rewritten to pass it (`pending()` without `globals()`, `os.O_NOFOLLOW`) | 9 new planted positives (30 in all), each caught |
| W4B1-4 login length boundary | MAJOR | (code was right) | 19 characters refused, 20 accepted; Review B's M6 now red |
| W4B1-5 other vendors' names | MAJOR | (code was right) | a literal list per harness, a world where a third vendor's host resolves; M22 now red; mutant `other-vendors-dropped` red |
| W4B1-6 sidecar rules | MAJOR | `_check_sidecar` also pins `security_opt` and the `/srv/ev` mount (Review A) | breaks with a matching inspect: bridge, root, privileged, host pid, no security option, evidence elsewhere; M39 now red |
| W4B1-7 hash ignores paths | MAJOR | (code was right) | a renamed config file changes the hash; M34 now red; mutant `digests-only` red |
| W4B1-9 caller_env switches off the refusal | MINOR | `check_environment` always reads `os.environ` too | `test_own_environ_always_checked`; mutant `caller-env-replaces` red. The tests drop refused names from their own process environment (names only) |
| W4B1-10 signatures | NIT | named above as departures | - |
| W4B1-11 (a) / A credential names unsourced | NIT | only `auth.json` (D8) stays a real value; the three recalled names are in `RECORDED_PENDING["credential_file_names"]`; `CREDENTIAL_LIKE` catches them | postflight test; mutants `no-names`, `no-pattern` red |
| W4B1-11 (b) proxy hardening | NIT | `--cap-drop ALL`, `--security-opt no-new-privileges` on the proxy | mutants `proxy-keeps-caps`, `proxy-new-privileges` red |
| W4B1-11 (c) version probe environment | NIT | the version probe carries only its harness's config home | mutant `version-without-config-home` red |
| W4B1-11 (d) port typed | NIT | `_proxy_port()` derives it from `PROXY_URL` | mutant `port-typed` red |
| W4B1-12 lane report | NIT | this file | - |
| A proxy uid spellings | - | `_proxy_uid` parses `uid[:gid]` numerically; uid 0 refused in every spelling | `0`, `0:0`, `0:5`, `00:00`, `000`, `root`, `root:5` refused; near-misses `1`, `5:0`, `01:00`, `100:100`, `13:13`, `proxy`, `squid` accepted; mutant `uid-string-compare` red |
| A entrypoint not pinned | - | `--entrypoint sleep`, inspected as `Config.Entrypoint` | mutant `no-entrypoint` red; breaks `entrypoint`, `no-entrypoint` |
| A unreadable /proc rows skipped | - | the program records `{"pid", "unreadable"}`; both process checks fail on one | the program run in memory over a fake /proc; mutant `skips-unreadable` red |
| A PROGRAMS read from a dict | - | the checks read each program from the argv each probe builds | mutants patch the program constants the probes use |
| A PENDING-parameter tests without a mutant | - | each of the three tests is now a check with an `override-parameter` mutant | red in all three files |

Review B's 39 whole-file mutants, re-run from a copy (`scratchpad/w4b/fold1/r1/`): 39 of 39 red, each by assertion failures.

## Fold 2

The lane review's round 2 found 1 MAJOR, 1 MINOR and 3 NITs at `fb88e7f3`.
The decisions below are the lane lead's.
The standing rule is glitch-f3's, made under Javier's delegation (Thu 8 Oct): no reviewer or builder writes guard-evasion probes, guards are built and judged by construction, and a missing guard is reported in words.
This fold planted no new evasion form.

| finding | severity | the lane lead's decision | fix | test | mutant (whole-file swap, closing line) |
|---|---|---|---|---|---|
| W4B2-1 config_home guard untested | MAJOR | fold | the rule is its own helper, `_config_home_allowed` | `test_config_home_refusals`: a login name, a name that is not a config home, and a wrong value are each Refused; no refusal carries the value | the guard dropped (`if False:`): `FAILED (failures=1)` |
| W4B2-2 audit not default-deny | MINOR | fold by construction | the audit admits `os` only through `OS_ATTRS`, a dunder only through `DUNDERS_ALLOWED`, and `subprocess` only as a `(name, how)` of `SUBPROCESS_USES` (run as a call, TimeoutExpired in an except); all derived once from the box modules' source and committed | `TestAuditAllowlists`: each list is exactly what the modules use | OS_ATTRS widened `FAILED (failures=1)`, emptied `FAILED (failures=2)`; DUNDERS_ALLOWED widened `FAILED (failures=1)`, emptied `FAILED (failures=2)`; SUBPROCESS_USES widened `FAILED (failures=1)`, emptied `FAILED (failures=2)`; the unchanged control run `OK` |
| W4B2-3 placeholder network | NIT | document it | `check_spec` and `launch` docstrings: the drive step passes a placeholder 64-hex network id, which launch replaces with the network it creates (`Launched.spec` carries the result) | - | - |
| W4B2-4 evidence mount source unbound | NIT | no signature change here | none in this lane | - | - |
| W4B2-5 `/srv/ev` owner and mount `type` | NIT | no change | none in this lane | - | - |

The residual, in words: the process audit is judged by construction, not by adversarial probing.
Its allowlists say what the box modules may use, and the planted list holds only the forms round 1 named.

Open items for the CP2 drive step and the merge (carried by the lane lead):
- W4B2-4: the sidecar's evidence mount source must equal the `evidence_dir` preflight reads. Today evaluate does not bind the two; the drive step passes the same folder to both.
- W4B2-5: merge binding 4 binds preflight's `SIDECAR_EVIDENCE_MOUNT = "/srv/ev"` to `sidecar.EVIDENCE_MOUNT`, and the parsed `sidecar_expect` must leave out the mount `type` key (preflight refuses it, fail-closed).

No interface changed in fold 2.

## Fold 3

The lane review's round 3 found 1 MAJOR, 2 MINOR and 1 NIT at `3368cd37`.
The decisions below are the lane lead's.
glitch-f3's ratification of `login_file` and `record_dir` is in the interface section above.
glitch-f3's standing rule holds: no guard-evasion probes; guards are built and judged by construction; this fold planted no new form.

| finding | severity | the lane lead's decision | fix | test | mutant (whole-file swap, closing line) |
|---|---|---|---|---|---|
| W4B3-1 config-home name clause not isolated | MAJOR | fold | none needed in the guard; the tests now isolate it | the login-name and non-config-home cases carry `/opt/cfg` (`CODEX_API_KEY=/opt/cfg`, `PATH=/opt/cfg`); the wrong-value case stays | "name unchecked" (helper returns `value == CONFIG_MOUNT`): `FAILED (failures=1)` |
| W4B3-2 SUBPROCESS_USES rule bound only by its literal | MINOR | fold | none needed in the rule | `test_subprocess_rule_fires_on_the_real_call`: with ("run", "call") removed, process_audit() on the real run_take.py flags the one real call | the in-test list mutant `run-call-removed` red |
| W4B3-3 audit not default-deny over from-imports, module attributes and getattr | MINOR | extend by construction | `IMPORT_FROM_ALLOWED`, `MODULE_ATTRS` and `GETATTR_ALLOWED`, derived once from the box modules and committed | `TestAuditAllowlists`: each list is exactly what the modules use | emptied: import-from `FAILED (failures=3)` (the whole set replaced by an empty one), module-attrs `FAILED (failures=3)` (the swap emptied one module's list, `secrets`, while the committed in-memory mutant empties every list), getattr `FAILED (failures=3)` (the whole set emptied); widened: red in the committed in-memory mutants (their whole-file swaps are unrun, see below) |
| W4B3-4 more than one config_home entry accepted | NIT | refuse it | `CONFIG_HOME_MAX = 1` in agent_exec_argv | the two-entry case in `test_config_home_refusals` | `CONFIG_HOME_MAX = 2`: `FAILED (failures=1)` |

The residual, in words: the process audit is judged by construction, not by adversarial probing.

Unrun at the 20:45 EDT hold:
- the whole-file swaps of the three widen mutants (import-from, module-attrs, getattr) and of `run-call-removed`;
- every gate on the report-only head. The code is unchanged since 4486bc8b, whose gates all passed.

## Fold 4

Round 4 on `355a2031` returned VERDICT: PASS (no MAJOR), so the review loop stops.
Under the stop rule only the two MINORs that loosen a check are fixed; the lane lead also folds the prose NIT.
The decisions are the lane lead's.
glitch-f3's standing rule holds: no evasion form is written, and the reviewer's alias chain stays in words only.

| finding | severity | the lane lead's decision | fix | test | mutant |
|---|---|---|---|---|---|
| W4B4-1 MODULE_ATTRS keys not bound to the imports | MINOR | fold, by construction | the audit refuses an attribute on an import-bound name with no entry in MODULE_ATTRS (os and subprocess keep their own lists), refuses `asname` on every plain import, and refuses every import-bound module name used as a value | `test_module_keys_bound_to_imports`: the keys equal the import-bound names derived from the box modules, less os and subprocess; with `shutil` dropped, the real `shutil.rmtree` is refused | `module-attrs-key-dropped` |
| W4B4-2 dynamic builtins reachable through another name | MINOR | fold, by construction | each of `DYNAMIC_BUILTINS` (getattr, eval, exec, compile, vars, globals, locals, setattr, delattr, `__import__`) is refused when loaded other than as the func of a direct call | `test_dynamic_builtins`: the list is bound by its literal, and the real modules' own direct calls still pass | `dynamic-builtins-dropped-getattr`, `dynamic-builtins-emptied` |
| W4B4-3 stale ratification prose; the swapped form unstated | NIT | fold | the departures line and open question 2 point at the ratified interface section; the Fold 3 table states which emptied form each swap used | - | - |

The residual, in words: the process audit is judged by construction, not by adversarial probing.
For W4B4-2, the list is bound by its literal and by the real modules passing; no alias form is written, so the rule itself has no planted witness.

Gates pending the lift (the Mac hold was on for all of fold 4; nothing was run):
- the three lane test files alone, `--process-audit`, the checks file and `copy_manifest.py --check`;
- the fold 3 swaps never run (import-from-widened, module-attrs-widened, getattr-widened, run-call-removed);
- one swap per new mutant (module-attrs-key-dropped, dynamic-builtins-dropped-getattr, dynamic-builtins-emptied).

## PENDING values, with reasons

`run_take.pending()`:
- `FALLBACK_ENV`: the refusal-fallback and model-fallback names and values, at the pinned version.
- `VENDOR_BILLING_ROUTE_VARIABLES` for codex and gemini: named from each harness's documentation at the pinned version.
- `TOP_FORMAT`: the column form `docker top` prints under rootless Docker.
- `INSPECT_STATUS`: the inspect spellings, confirmed when the stub take reads one inspect.
- `TakeSpec.resources`: the memory reservation, CPUs and pids limit, measured at the cold-start stub take.

`run_take.CALLER_PENDING` (the caller passes them once measured):
- the container's cgroup folder;
- the runtime's uid map;
- whether the take needs `XDG_RUNTIME_DIR` inside the container;
- the run tree's and config folder's ownership and modes under the uid map, and how uid-mapped files are removed (plain `rmtree`, no chmod invented).

`preflight.pending()`:
- `VERSION_PATTERNS`: every `--version` output form.
- `STUDY_PATHS`: the pre-registered study folders (CP5).
- `LEAK_WORDS`: the round's leak words (CP5).

`preflight.RECORDED_PENDING`:
- `token_visible_to_children`;
- `google_project_tier` (arm G);
- `watcher_holds_capability` (the check passes only when it does);
- `internal_resolver` (the names check measures it);
- `credential_file_names` (the recalled names, confirmed by a walk);
- `cap_add spelling` (`sidecar_expect` carries PENDING until the stub take).

`take_config.pending()`:
- `CLAUDE_BYPASS_KEY`;
- `CODEX_REASONING_EFFORT`;
- `GEMINI_THINKING`;
- `GEMINI_AUTH_SETTING`;
- `GEMINI_SETTINGS_PATH`.

A named gap: until the billing-route lists are filled, arms O and G refuse only the closed list (drive.py's three tuples plus `CODEX_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, less the take's own login).

## Open questions for the lane lead

1. Round 3's leak words still occur in prose and repository paths in the lane's files: "round 3's", "pre-registered", the round 3 path the leak-word helper reads, and `literal_eval` in a test. No test data names one. Should prose be swept too?
2. The required `login_file` and `record_dir` were ratified by glitch-f3, Thu 8 Oct (see the interface section); the optional additions remain departures for the merge to note.
3. `kill_agent` needs a `kill` binary in the take image (w4a).
4. The C3 constants for merge binding 7: run_take holds `QUIESCENCE_CAP_SURVIVORS_KEY` and `QUIESCENCE_CAP_ROW`; preflight holds `UNREADABLE_CONSEQUENTIAL_KEY` and `UNREADABLE_CONSEQUENTIAL_ROW`.
5. Merge binding 4: `sidecar_expect` now also pins `security_opt` as `["no-new-privileges"]` and the evidence mount at `/srv/ev`.
6. A process note: at 18:43 EDT a test run started without its light-ok gate passing (the gate printed a hold and the run was not chained to it). It was a light single-file run, and every later run was gated.

## Lessons

- `mock.patch.object` on a function held in a dispatch dict does not reach the dict; the mutant patches the dict.
- A test that builds its expectation from the module under test lets a mutant pass; type the expectation (W4B1-5).
- A boundary rule needs both sides planted (W4B1-4).
- Gate each test command on light-ok with `&&` in the same line; a separate line runs anyway.
