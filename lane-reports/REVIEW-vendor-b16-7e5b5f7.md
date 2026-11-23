VERDICT: CHANGES

# Review of lane vendor-b16, range 0aa493c07c27..7e5b5f75 (rounds 1 and 2)

Fresh cloud reviewer for glitch-26. I did not write this change. I read the range, the design note, and the lane file's
ROUND 1 SUMMARY and Progress lines. The BLOCKED lines are records of refused steps that glitch-26 has settled, so they
are not findings here. As the prompt says, two pieces are deliberately out of this range and are not findings: the
copy-manifest claim for tests/test_gemini_undeclared_args.py, and the plan's section 6 row for R-B16-2.

The verified package: @google/gemini-cli 0.64.0, fetched with `npm pack` into a mktemp folder outside the clone. Its
tarball sha256 is 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6, which matches. bundle/chunk-NR7L3FXV.js
is d566e81b... and bundle/gemini-Q2GRYIAK.js is 7702da31..., both matching. I unpacked it and only read it. Nothing from
it was run or imported.

## Findings

1. MINOR. The per-tool citation leaves out two places where the pinned CLI reads every argument key, including an
   undeclared one. One of them can change what ran. See gemini_tool_sources.py lines 160 and 213-219, and
   transcript_gemini.py lines 282-286.
   - The citation says "the run reads only the keys named in `reads` off the call's arguments" (line 160). Its read
     text says "an undeclared key such as file_path changes nothing the call does" (line 219).
   - The pinned package also reads the whole args dict, undeclared keys included, in two places that are not cited.
   - **The loop detector.** LoopDetectionService.getToolCallKey hashes `${name}:${JSON.stringify(args)}`
     (chunk-NR7L3FXV.js 343947-343950). checkToolCallLoop runs it on every ToolCallRequest (343973, 344041-344069).
     A detected loop aborts the turn with LoopDetected or MaxSessionTurns (348323-348336).
   - Loop detection is on in arm G takes. config 380818 defaults disableLoopDetection to false, and box/take_config.py
     line 186 records that model.disableLoopDetection is not written.
   - So two grep_search calls that differ only in an undeclared key's value count as different calls for loop
     detection. The view shows them as identical searches: the key's value is not kept, and its name is kept only on
     the RawItem. Whether the CLI aborts the turn can therefore depend on a key that OPEN_INPUT reads as ignored.
   - **The policy engine.** PolicyEngine.check stable-stringifies the whole args whenever any rule carries an
     argsPattern (364402-364403). ruleMatches tests every argsPattern against that string (364130-364135).
   - Under the takes' settings, no loaded rule with an argsPattern applies to grep_search. The only one in the
     default tier is plan.toml's invoke_agent rule, which applies in plan mode. The [[rules]] in sandbox-default.toml
     is not loaded, because PolicyFileSchema reads the key `rule` (366840-366843). hooksConfig.enabled is false, and
     Conseca is off by default (380958, 368888).
   - So this read changes nothing today, but the citation neither cites it nor records why it is harmless.
   - The missing check: the OPEN_INPUT citation (and the design note, section 2) should cite the loop detector's and
     the policy engine's whole-args reads. It should then either record why ruling R-B16-2's condition still holds
     for them, or narrow the claim to "the invocation reads only declared keys". The loop detector's effect on the
     turn should go to glitch-26 as a question. It is not something to settle in the reader.
   - Everything the citation does cite is true. `--sources` finds 0 problems over 97 lines.
   - My own reading agrees with it on these points:
     - Both invocations read only declared keys off this.params (321746-322406, 322534-322538).
     - validateToolParamValues reads only declared keys (322156-322199, 322578-322623).
     - The base invocation's extractFilePathFromArgs runs only inside shouldConfirmExecute, which the scheduler
       reaches only on ASK_USER (349472-349499).
     - The taint check that could turn ALLOW into DENY in a non-interactive run exists only on ShellToolInvocation
       (325765). So it never reads a grep call's keys.

2. MINOR. R-B16-2's new test and its witnesses are not in any witness list. See
   evals/gap-study-4/checks.d/vendor-admission.txt lines 99-105 (the range's only addition).
   - The file registers B16-1's test_native_snapshot, its `--witnesses`, and a check_vendor_sources P2 line.
   - It registers nothing for round 2: not `tests/test_gemini_undeclared_args.py`, not its `--witnesses` (3
     mutants), and no P2 line for round 2's non-exception files (gemini_tool_sources.py, tests/test_gemini_adapter.py,
     tests/test_gemini_undeclared_args.py).
   - U1-U3 do run inside test_gemini_adapter through S7, which is registered in checks.d/w11b-gemini-adapter.txt. The
     three R-B16-2 witnesses (citation-removed, closed-schema-assumed, name-dropped-from-view) run in no battery.
   - The lane file's 07:19 Progress line records this as "Not done". It is listed here because the range has no
     check that would fail if those witnesses went green.

3. NIT. transcript_gemini.py lines 309-318 keep the undeclared key's name on the parser's item. It does not reach the
   view's events. See transcript_view.py line 785.
   - CallItem carries undeclared_args, but transcript_view.events builds AgentEvent from tool and args only.
   - Nothing outside transcript_gemini.py and its tests reads undeclared_args. awareness_furniture.py is the only
     other caller of raw_items, and it does not read it.
   - This meets ruling R-B16-2's wording ("kept by name on the view item"). But the design note's reason for it, at
     lane-reports/B16-DESIGN-NOTE.md line 59 ("so graders and the labelling sheet see the model's mistake"), is not
     what the code does.

4. NIT. The R-B16-2 test's case "a key the run reads (wait_for_previous)" (tests/test_gemini_undeclared_args.py line
   135) is refused already by the GEMINI_TOOLS entry, without OPEN_INPUT's read-key check, because wait_for_previous
   is not among _GREP_KEYS.
   - The read-key guard (transcript_gemini.py lines 297-298) is still covered, by the patched entry that adds
     file_path to the read keys (lines 148-150).
   - My mutant 1 below confirms U2 goes red without the guard.

## B16-1 (threat 1)

No finding.

- Both locators now ask "." first (native_snapshot.py 166, 194). Every later listing and the located file path is a
  normalised relative path, which `_rel` admits.
- check_take.vendor_native_rel's synthetic lister (check_take.py 4999) reads "." as the root. "" now yields [] there,
  so a locator naming it refuses.
- test_box_integration's FakeOwnership lists the root for "." only.
- test_drive_ownership's stub adapter asks ".".
- No other `lister("")` or `rel_dir == ""` remains under evals/gap-study-4 outside the witnesses' anchors.
- box/ownership.py and drive.py are unchanged in the range.
- BoxRootNaming puts the real `ownership._rel_dir` and `_no_credential_path` in front of the fake listing. It wraps a
  failure as TakeDriver.config_view does (drive.py 2574-2581), so it drives the real path rule.
- operator_list's remaining checks act on the container's reply, not on rel_dir.
- The comment added above the locators shifts native_snapshot.py from line 137 on. Every line-keyed citation of that
  file (harness_bookkeeping.py 119-153, test_harness_bookkeeping.py 307-362) names lines 9-84, which do not move.

## Threat 3 (weakened refusals, tests, witnesses, recorded bytes)

None found.

- The re-anchored `tool-refusal-untyped` witness is still red: test_gemini_adapter --witnesses gave 114/114.
- An unknown tool, a declared mapped key off its type, a tool with no OPEN_INPUT entry, a closed schema, and a read
  key all still refuse (U2).
- A call with no undeclared key is still the plain RawItem.
- transcript_gemini.py changes in place only at line 183 (tool_kind) and line 258 (the parser's call). Its new code is
  appended at the end of the file.
- check_vendor_sources P2 refuses transcript_gemini.py and native_snapshot.py, the two named exceptions, as expected.

## Threat 4 (new guards without a failing test)

None found.

- Each new guard is red without it:
  - native_snapshot "." root: witnesses 2/2.
  - OPEN_INPUT closed-schema check: witness closed-schema-assumed.
  - Read-key intersection: my mutant 1.
  - check_take's "." root: my mutant 2.
  - The undeclared key's name on the item: witness name-dropped-from-view.
  - The citation table: witness citation-removed.
- The gaps in finding 2 are about registration, not about the guards.

## Checks run

Each check ran in the foreground under `env -i PATH HOME LANG=C.UTF-8 TMPDIR=<mktemp outside the clone>`, on
lane/vendor-b16 at 7e5b5f75.

- test_native_snapshot: 15 OK. `--witnesses`: 2/2 red (codex-root-empty, gemini-root-empty).
- test_gemini_undeclared_args: 3 OK.
  - `--witnesses`: 3/3 red (citation-removed, closed-schema-assumed, name-dropped-from-view).
  - `--sources <unpacked verified bundle>`: 0 problems over 97 cited lines.
- test_gemini_adapter: 144 OK. `--witnesses`: 114/114 red.
- test_gemini_tool_registry: 4 OK. `--witnesses`: 115/115 red.
- test_box_integration: 61 OK.
- test_drive_ownership: 44 OK.
- test_run_take: 68 OK.
- test_walk_builders: 95 OK.
- test_vendor_session: 5 OK. This is the battery that exercises check_take.vendor_native_rel.
- build_draft --check: ok, the committed draft is what build_draft.py builds.
- Witness run, every non-comment line of checks.d/vendor-admission.txt: 56 lines, 53 exit 0 and 3 exit 1. All 3
  failures have the same cause, the out-of-range manifest claim: "tests/test_gemini_undeclared_args.py is under
  evals/gap-study-4/ and no fragment in COPIED.d/ claims it". The 3 lines are:
  - line 3: test_freeze_shapes, test_fs_check_mode_is_unchanged
  - line 42: freeze.py --check
  - line 43: copy_manifest.py --check
- Note for glitch-26: the prompt expected only copy_manifest --check to be red. freeze --check and test_freeze_shapes
  are red for the same unclaimed file and should go green with the same claim.
- check_vendor_sources P2 transcript_gemini.py and P2 native_snapshot.py: both REFUSE (the named exceptions, as
  expected).
- My mutants, each on a scratch copy of evals/ made with mktemp outside the clone:
  - Mutant 1: transcript_gemini.ignored_args with the read-key intersection removed (`if set(extra) &
    set(entry[1]): return ()`). test_gemini_undeclared_args: 1 failure, killed. U2 reports "a key the run reads
    (wait_for_previous) is accepted" and "grep_search with file_path is accepted under an entry whose run reads
    file_path".
  - Mutant 2: check_take.vendor_native_rel's lister put back to `rel_dir.split("/") if rel_dir else []`.
    test_vendor_session: errors=15, killed.

Not run, per the prompt: no walk, take, login, container or vendor call; the Gemini CLI, Codex and Claude Code were
never run. No code, test or lane file was changed. The scratch folders /tmp/tmp.lldVYPuTbi (the package),
/tmp/tmp.TtJTeFM5kP (TMPDIR and logs), /tmp/tmp.Soym1lQjY8 and /tmp/tmp.7YPOtPJQUa (the mutants) are left in place.
