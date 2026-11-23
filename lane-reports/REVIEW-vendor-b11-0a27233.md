VERDICT: PASS

# Review of lane vendor-b11, range 39585e27..0a27233d (round 6: rulings R6-1 and R6-2)

Fresh cloud reviewer, Mon 19 Oct 2026. I did not write this change. I read the review of round 5
(lane-reports/REVIEW-vendor-b11-2b609ff.md), the ROUND 6 SUMMARY FOR REVIEW in lane-reports/vendor-b11-LANE.md and
the whole diff of the range (2 files: evals/gap-study-4/tests/test_config_folder.py and the lane file). No code or test
was changed by this review. I ran no walk, take, login, container or vendor call. I ran no Gemini CLI, Codex or Claude
Code. I opened no login, token, lease or account file. R5-5 (the integration merge) is not in this range and is not a
finding.

There are no MAJOR and no MINOR findings. The round 5 review's finding 1 is closed.

## Findings

1. NIT. evals/gap-study-4/box/run_take.py line 2517: the root-kind half of
   `if root is None or root["kind"] != "dir":` has no test that fails without it.
   - My mutant (below) narrows it to `if root is None:`. It survived test_config_folder, test_run_take and
     test_take_config.
   - The check stays closed without it, for two reasons:
     - The census program (box/ownership.py line 544) opens the root with O_DIRECTORY|O_NOFOLLOW, so a real census
       never reports a root that is not a directory.
     - A census whose root has no children fails the placed set with "placed, and missing" (run_take.py line 2526).
   - Missing check: a C13Guards case where config_folder_problems gets a census whose "." entry has kind "file" or
     "link". It must refuse naming "no folder at its root", and it should be registered as a witness.
   - Not this round's scope. R5-1's census of guards (the round 5 review, (1)) did not count this line. It is recorded
     so that the count is complete.

## Threat model

### (1) Is the round 5 review's finding 1 closed

- Yes.
  - Witness device-unchecked-dirs is registered at tests/test_config_folder.py lines 1002-1004. Its old text is the
    device check at run_take.py line 2521, which occurs once. Its new text is the round 5 reviewer's mutant 2 verbatim.
  - The witness is bound to C13Guards.test_an_entry_on_another_device_refuses (line 1050).
- Red first is real. At eac14157 (registry only), `--witnesses device-unchecked-dirs` reports
  "witness device-unchecked-dirs -> C13Guards.test_an_entry_on_another_device_refuses C13.device: FAIL", rc 1. There
  the plain module is 25 OK.
- The witness is red alone at the head. `--mutant device-unchecked-dirs` fails exactly 1 of 25 tests, the bound test,
  with "C13.device: gemini: .gemini on another device than the folder passed". The other 24 stay OK.
- Each new case refuses for the stated reason:
  - Both new cases (line 861) first pass unaltered (`self.none`). They then refuse with the device bumped on that one
    entry only. The needles are the path and "another device", and only the device rule (line 2522) produces
    "another device".
  - The codex `tmp` case is red on its own too. On a scratch copy with the `.gemini` case removed, the mutant fails
    the test with "C13.device: codex: tmp on another device than the folder passed". The unmutated copy is 25 OK.
  - So each directory case, not only the first in the loop, kills the mutant.
- The C13 docstring (lines 38-42) names the directory case and ruling R6-1.

### (2) Scope and weakening

- `git diff --stat 39585e27..0a27233d` touches only tests/test_config_folder.py (+12/-6) and the lane file.
- box/, drive.py, the Codex gate and every other test are untouched.
- In test_config_folder, all changes are additions or rewordings:
  - The tuple of cases grew from 4 to 6.
  - METHOD's `device-unchecked` entry became a dict comprehension that still binds it to the same test.
  - The docstring was reworded.
  - No assertion, case or witness was removed. The registry grew from 36 to 37, and the module stays at 25 tests.
- R6-2: no change, as ruled.
- No commit message in the range carries a link, a home path or a backtick.

### (3) Guards of the check still without a test

- Every guard named by R5-1 and R6-1 has a witness that is red at the head (37 of 37).
- One further guard, line 2517's root kind, is untested. It is backstopped as described in finding 1, so it is a NIT.

## Checks run

- Head 0a27233d.
- Every check ran in the foreground under `env -i` with only PATH, HOME, LANG and TMPDIR set. HOME and TMPDIR were in a
  mktemp directory in the session scratch area, outside the clone.

| check | result |
|---|---|
| test_config_folder | 25 run, 0 failures |
| test_config_folder --witnesses | 37/37 red; registry 37 |
| test_config_folder --mutant device-unchecked-dirs | FAILED (1: C13Guards.test_an_entry_on_another_device_refuses), 24 OK |
| red first, eac14157: --witnesses device-unchecked-dirs | FAIL (bound test OK), rc 1; plain module 25 OK |
| `tmp` case alone (scratch copy, `.gemini` case removed) under the mutant | FAILED on "codex: tmp"; unmutated 25 OK |
| test_run_take | 68 OK |
| test_take_config | 13 OK |
| test_drive_ownership | 48 OK |
| test_box_integration | 61 OK |
| test_pending_walk | 23 OK |

- My own mutant ran on a local clone at 0a27233d, in a mktemp directory outside this clone, left in place.
  - The change: box/run_take.py line 2517, `if root is None or root["kind"] != "dir":` became `if root is None:`.
  - Result: it survived. On the clone, test_config_folder 25, test_run_take 68 and test_take_config 13 stayed OK.
    On a `git archive` copy with the same edit, test_drive_ownership 48, test_box_integration 61 and
    test_pending_walk 23 stayed OK. This is finding 1.
- A first attempt at test_run_take and test_take_config on a `git archive` copy errored. Those modules `git show` a
  round 3 commit, so they need history, which is why the mutant was rerun on a clone.

`gitleaks git --staged` was run before this commit.
