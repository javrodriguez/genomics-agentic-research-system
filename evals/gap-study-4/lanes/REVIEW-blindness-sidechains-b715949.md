VERDICT: PASS

# Closure review: lane blindness-sidechains at b7159493

Same reviewer as the reviews of 5a6dc21 and fff7e0d, Sat 24 Oct 2026 22:38 EDT.
Candidate: `lane/blindness-sidechains` b71594931c93c377f2cd4bade1eab64e6fd6e9cf (one fold on fff7e0d3).
All runs were behind `mac_slot.py light-ok --tests --work gap-study-r4` (light ok, CPU speed limit 89 and 100).
No code changed; the round 1 and smoke folders and the session files were only read.

## Verified

- Suite in the clone: `Ran 55 tests ... OK`; `--witnesses`: `107/107 red; registry 107`; `copy_manifest.py --check`: `ok: 729 files from 73 fragment(s)`; working tree clean after the runs.
- `rounds.py --check` reads one FAIL, `prefreeze round 1 is OPEN: ... prefreeze-1.md is not committed`. That is round 1's real state, not this fold.
- Committed rows untouched:
  - `review_kit/rounds.json` is not in the diff, so row 1's `input_sha256` 85b5b15f... is unchanged.
  - `check()` never recomputes `input_sha256`, so no row can be reinterpreted by it.
  - The binding it does enforce (the committed report and blindness record name the session id the row's commit derives) is unchanged.
- folder_sha256 unchanged:
  - I extracted fff7e0d3's `folder_sha256` and compared it with the new manifest-derived one on the real round 1 and smoke folders: `equal: True` on both.
  - Also equal on a fixture with a two-space file name, a nested `.git` outside `study/`, a link and a non-ASCII name.
  - So a row added with the new `--add` means what an old row meant.
- launch.py refuses a folder that no longer matches `<folder>-launch/folder-manifest.txt`, or one with no manifest. The check runs before anything is written to the launch folder.
- Round 1 re-run, read-only: byte-identical to the builder's `round1-rerun-v4.txt` except one trailing newline.
- Every earlier probe holds:
  - P1 to P11 as at fff7e0d.
  - B1 (brief text the author read outside) now reads UNEXPLAINED, so the brief route is corpus-only.
  - B2, B3 and B5 are UNEXPLAINED; B4 (in the corpus) traces via brief.
  - M1 to M3 are voided.
  - S1, S2, S3, S5, S6, S8 (relative `cp -p`, `rsync -a`, `tar -x`, here-doc, `tee`, `&>`) now leave the corpus.
  - S4 traces only because my fixture records carry no `cwd`; with the record's cwd (shell probe below) the same command is recorded inside.
- Shell splitter (`shellprobe.py`, record cwd set to the folder) records these inside the folder:
  - `cd <folder>/study && cat > x.md <<'EOF'` with an apostrophe in the body;
  - `| tee x.md`, and a bare `cat > x.md`;
  - `cp -p /tmp/brain.md .` after a `cd`, and the relative `cp -p ... study/x.md`;
  - a quoted `cd "<folder>/study"` followed by a write to `'my file.md'`;
  - `echo a;\necho b > ...`;
  - `>path` with no space, `1>path`, `>>path`, a subshell `( cd ...; echo > sub.md )`, and `curl -o`.
  A `>` or `|` inside quotes is text, and `&>` and the `tar -x` destination are listed outside.
  An unbalanced quote (`echo it's > ...`) yields no steps, which is harmless: bash refuses that command too.

## Findings

1. MINOR. A here-document whose delimiter is not a plain word drops the whole command.
   `HEREDOC` only matches `\w+` delimiters, so `cat > <folder>/study/h.md <<'PY-END'` with `it's` in the body is left for shlex, which sees an open quote: 0 steps, nothing recorded.
   Bash runs that command.
   The corpus is still safe:
   - on a manifest round, the hash voids the file;
   - on the stamp rule, the new mtime does.
   What is lost is section 6's listing of such a write outside the folder. Fix: widen the delimiter to `[^\s'"<>;|&]+`.

2. NIT. Writes a program makes from inside its own code are not seen: `python3 -c "open('<folder>/...','w')"` and `dd of=<folder>/...` record nothing. The manifest or the stamp still voids those files.

3. NIT. A file name with a newline makes `manifest_digest` raise (`ValueError`) where the old `folder_sha256` hashed it. Git allows such names. The failure is loud rather than a quiet reinterpretation, and no current folder has one.

4. NIT. A manifest whose digest matches no round row is still used as the corpus. The record prints "binds nothing" beside it, but falling back to the stamp rule would be the safer default.

5. NIT. A Bash record with no `cwd` field leaves a relative write unrecorded. Every real record read here carries `cwd`.

## Stop rule

The rounds.py change cannot move or reinterpret a committed row.
launch.py binds the folder to the row's manifest.
The brief route is corpus-only.
The shell splitter catches every shape asked about.
One minor and four nits remain, none of which changes a binding count. Stop.
