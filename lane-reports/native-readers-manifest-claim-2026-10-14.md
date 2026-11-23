# native-readers/ pre-declared in the manifest (glitch-06's ruling)

Writer: Claude Code harness lane, 14 Oct 2026 03:52 EDT.

The acceptance record and its review live in `native-readers/`, which no record ledger claimed, so Javier's acceptance commit would have had to edit a manifest fragment.
Ruled: pre-declare the folder now, so his acceptance commit never touches a manifest, and keep `copy_manifest` strict for everything else there.

- `COPIED.d/live-harness-foundation.json` gains one entry: path `native-readers/**`, status `acceptance-records`, reason "acceptance records and their reviews; written only by Javier's acceptance commit".
- `copy_manifest.py` accepts that one entry shape only, path and status exact and a non-blank reason.
  It claims only `native-readers/<gemini|codex>-acceptance.json` and `native-readers/<gemini|codex>-review.md`.
  Anything else under the folder is unclaimed and fails, nested paths and other extensions included.
  A fragment entry naming any path inside the folder is refused, and without the pattern entry nothing there is claimed.
  The W8A record-claim lines are untouched (their witnesses' anchors hold: `test_walk_layout --witnesses` 21/21 red).
- `native_reader_registration` now takes the review file only as `gemini-review.md`, the one review name the manifest claims.

Verification (behind a light gate):
- `test_native_reader_registration` 7/7 (ManifestClaim added).
- `test_pending_walk` 18/18.
- `test_scaffold` 49/49.
- `copy_manifest.py --check` ok.
- Four in-memory mutants killed: the pattern loosened, claims without the entry, the entry shape unchecked, and inside paths sent down the normal road.
