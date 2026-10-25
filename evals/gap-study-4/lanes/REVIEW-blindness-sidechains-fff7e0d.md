VERDICT: PASS

# Closure review: lane blindness-sidechains at fff7e0d3

Same reviewer as REVIEW-blindness-sidechains-5a6dc21.md, Sat 24 Oct 2026 17:22 EDT.
Candidate: `lane/blindness-sidechains` fff7e0d3d0000ffe5adc3c685e6ba3c93f984c77 (folds 97a1bd29 and fff7e0d3 on 5a6dc215).
Every run was behind `mac_slot.py light-ok --tests --work gap-study-r4` (it held twice for CPU speed limit below 80; runs started at 17:18 and 17:21, light ok at 81).
No code changed; the round 1 folder, its `-launch` folder and the session files were only read.

## Verified

- Suite in the clone: `Ran 53 tests ... OK`; `--witnesses`: `90/90 red; registry 90`; `copy_manifest.py --check`: `ok: 728 files from 73 fragment(s)`; working tree clean after the runs.
- My first review is committed unedited: the committed file and my file match (no diff in the working tree), and its four allowlist rows are line-exact `ratio-slash` rulings.
- Round 1 re-run, read-only (`report()`, never `main()`): byte-identical to the builder's `round1-rerun-v3.txt` except one trailing newline. Corpus by the launch stamp: 11,766 files, less 68 newer than the stamp; section 4: 37 hits, 34 direct, 2 via brief, 2 UNEXPLAINED (both agent aa07ac8b's own wording, which the orchestrator rules on).
- First-review probes re-run (`probes_old.py`, the same fixtures with the folder files dated before the launch stamp, so the new stamp rule does not hide the result):
  - P1 tail without the marker: (1, 0, 1) UNEXPLAINED, fixed.
  - P2 shell write inside: UNEXPLAINED, fixed.
  - P5b reflowed rendered: 1 hit, read once, fixed.
  - P7 nested relay: (2, 2, 0), both traced through the child, fixed.
  - P8 Agent result with no id, and P9 report read by TaskOutput: each hit counted once and UNEXPLAINED, the operator marker included, fixed.
  - P10 inline plus file copy: 1, fixed.
  - P3 shared study word: traced by design; the docstring and section 4 now say so.
  - Held as before: P4 symlink, P5 prompt-only, P6 no session file, P11 Brain path row.
- Brief route (`probes2.py`):
  - B2: an operator marker in the brief, which the author read in the folder, is UNEXPLAINED.
  - B3: brief text the author never received and the folder lacks is UNEXPLAINED.
  - B5: text the author got only from a sibling's hand-back is UNEXPLAINED.
  - B4: brief text in the launch corpus traces via brief, which is the ruling.
- Manifest (`probes2.py` M1 to M3):
  - M1: a listed file changed after launch, and a new unlisted file, are both out of the corpus.
  - M2: a listed file swapped for a link is out.
  - M3: a listed directory swapped for a link to an outside copy with identical bytes is out, because the path resolves outside the folder.
  - `write_manifest` runs after `folder-at-launch.txt` and before the session starts, skips `.git` and links the same way `regular_files` does, and hashes every regular file.

## Findings

1. MINOR. The shell rule records nothing for a relative write into the folder.
   `note_writes` probe: `cd <folder>/study && cat > x.md <<'EOF'`, `cd <folder>/study && echo hi | tee x.md`, and a bare `cat > x.md` (the session's own cwd is the folder) each give `inside: [] outside: []`.
   This does not hide the write from the corpus on its own:
   - on a manifest round, M1 voids it;
   - on the stamp rule, a plain redirect or `tee` gives the file a new mtime, so the stamp voids it.
   It does hide a relative copy that keeps the source's mtime, on the stamp rule only (`cd <folder>/study && cp -p <outside>/brain.md .`, `rsync -a`, `tar -x`, or `cp -p <outside> study/x` with no `cd`). S1 to S4 each trace an outside text as explained.
   Round 1 is the only round on the stamp rule. A grep of its 7 session files finds no `cp`, `rsync`, `tar`, `unzip`, `mv` or `ln` into the folder, so round 1's reading stands.
   Fix: when the `cd` target is inside the folder, add the target joined to that `cd` path to `written_inside`; take the default cwd from the record's own `cwd` field.

2. MINOR. Section 6 now misses some writes outside the folder, and lists a source as a write.
   - The redirect narrowing drops the paths a program is told to write: `python3 /tmp/w.py --out /tmp/res.json > /tmp/log.txt` lists only `/tmp/log.txt`.
   - `cd /tmp/w && tar -xf <folder>/a.tar` records the archive (a read) as written and misses `/tmp/w`.
   - `&>` is not a redirect to the rule: `cat /tmp/a &> /tmp/b` lists nothing.
   Section 6 is listed, not ruled, so this lowers what the reader sees and voids nothing. Fix: let a step's absolute paths count again when the program is not a known reader, and treat `tar -x`/`unzip` destinations as `-C`/cwd.

3. MINOR, for the orchestrator. The brief route's "the author received it" clause admits only text the folder lacks.
   Text that is in the folder already passes by the corpus clause, so the received clause only ever adds text the author read outside the folder.
   B1: the reviewer runs `cat <outside>/notes.md`, puts its line in the brief, and the sub-agent's echo traces via brief, (1, 1, 1, 0). The builder's own test asserts the same for `cat notes`.
   Read directly, the same text is UNEXPLAINED for a sub-agent (the direct route needs the folder too), so the brief route is the wider of the two.
   It is what the ruling's words say ("from what it received"), and it matches section 1, where the reviewer's own writing is never counted against it; the outside read still shows in section 5.
   If "received" was meant as "received from the folder", the fix is one clause (require `c in in_folder`, which drops the traffic clause). If not, the reader of section 4 should see the via-brief hits whose text is not in the folder marked apart.

4. NIT. `folder-manifest.txt` is not bound to the committed round row: rounds.py's `input_sha256` is taken before launch and the manifest after, in the `-launch` folder, with no digest of the manifest recorded anywhere committed. A later edit to it would go unseen (a session writing there would show in section 6).

## Stop rule

Every finding of the first review is fixed and witnessed.
The brief route cannot explain an operator marker or text the author never received.
The manifest road voids changed, new and linked files correctly.
What remains is three minors and a nit, none of which changes round 1's reading. Stop.
