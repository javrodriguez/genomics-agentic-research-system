# Integration lane checkpoint, 14 Oct 2026 15:03 EDT

Writer: the integration lane (sole writer), under orchestrator glitch-06.
This supersedes `integration-checkpoint-2026-10-14-1422.md`, which is left as written.
Nothing is active, and nothing was pushed.

## Repository state

- Merges: `7225f22d` (box `03180228`) and `9783d584` (harness `573b5a61`), both with no conflict marker.
- On `9783d584`:
  - `build_draft.py --check`: ok, so the draft was not regenerated.
  - `batch.py --check`: exit 0, `batch: routing.json ready`.
  - `copy_manifest.py --check`: ok, 414 files.
  - `freeze.py --check`: ok, 415 paths.
  - The watcher-stop search is unchanged: one lenient hit, at `tests/test_box_integration.py:1887`.

## Blocker: the athena road refuses the merged head by file name

`athena_suite.py run --repo <clone> --rev 9783d584… --label gap4-merge --kind gars-gap4 --solo` printed:

```
athena_suite: refused, nothing left the Mac: the bundle would carry secret-shaped files:
  lane-reports/stub-take-20261014/runs/73-credential-files-mutants.txt  (credential-name)
  lane-reports/stub-take-20261014/runs/79-redfirst-walk-token-at-161d038d.txt  (token-name)
  lane-reports/stub-take-20261014/runs/80-test_walk_token_scripts.txt  (token-name)
  lane-reports/walk-token/prepare_walk_token.py  (token-name)
  lane-reports/walk-token/test_walk_token_scripts.py  (token-name)
  lane-reports/walk-token/verify_walk_token.py  (token-name)
  lane-reports/walk-token/walk-login-prepared-20261014.json  (token-name)
```

- Box `161d038d` added the first of these; box `1eb02a9e` added the other six. None was in the last battery's head (`6e965d12`).
- The road admits such a path only by `--allow-path`, after the operator has read it, or through the committed `athena_suite_allowlist.json`.
- This lane did not read files named for tokens or credentials, so no battery ran this round.

## Finding: the real rules scanner is refused on the merged head

- `walk_builders.walk_rules_scanner` (harness `786be12c`) checks `scan_record.RealRulesScanner`, but box `8ad2978a` moved that class to `box/rules_scanner.py`.
- Reproduced: a real `rules_scanner.RealRulesScanner` gets `BuilderRefused: a real walk scans only with the pinned scanner (scan_record.RealRulesScanner), never RealRulesScanner`.
- test_walk_builders hides it, because it patches `scan_record.RealRulesScanner` with `create=True`.
- The fix is the harness lane's to make: a production change plus its test.
