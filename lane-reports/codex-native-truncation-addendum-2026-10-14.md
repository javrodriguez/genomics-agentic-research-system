# Codex 0.162.1 reader: the writer's truncation, reproduced exactly (addendum)

Parent: `154293616`. Writer: Claude Code harness lane, 14 Oct 2026 03:17 EDT, under glitch-06's order once the truncation source was retained (Addendum A of `gap4-codex-rollout-audit-20261014/codex-0.162.1-rollout-audit.md`).
This supersedes the refusal of over-64-KiB outputs in `codex-native-reader-review-fold-2026-10-14.md`; that report stays as written.

Re-checked on the retained copy before relying on it: `codex-rs/utils/string/src/truncate.rs` has sha256 `2f00b330…c99333` and git blob `075d78fd7ac6202d91edf1c409413b4506b26feb`, as the addendum lists; `rollout/src/policy.rs` has sha256 `65ce50e8…11dcbc`.

`codex_native.truncate_middle_with_marker` reimplements `truncate.rs:20-33` in UTF-8 bytes:
- an output at or under the limit is returned unchanged (`:21-23`);
- a marker longer than the limit keeps the longest prefix that fits (`:25-27`; unreachable with the 50-byte marker);
- the budget is the limit minus the marker; `split_budget` gives the head `budget // 2` and the tail the rest, so the tail takes any odd byte (`:156-159`);
- the head ends at `floor_char_boundary(left)`, the tail starts at `ceil_char_boundary(len - right)` (`:29-30`), reimplemented on UTF-8 continuation bytes;
- head, marker and tail are joined (`:177-183`).

The join admits an exec output over 64 KiB only when the rollout's output equals exactly `truncate_middle_with_marker(exec_output, 65536, marker)`; every other output must equal the rollout's exactly.
MCP results use another, unaudited function and stay unprojected (an `McpToolCall` item refuses).

Verification (behind a light gate):
- The new tests against the parent's `codex_native.py`, in a scratch copy: 14 tests, 6 errors.
- Green: 14/14.
  The positive cases are spelled from the source's rule, never read from the module: 70000 single-byte characters, distinct first and last bytes, 2-byte characters and 3-byte characters (each with both cuts rounding inward).
  Each is followed by four wrong rollouts: a byte short at each end, another marker text, and a split off by one.
- Mutants (13): 12 killed, among them a split off by one at the head and at the tail, the head rounded up, the tail rounded down, no char boundary, the marker text, characters instead of bytes, and the reviewer's witness.
  One is equivalent: the caller's size check as `>=` instead of `>`; at exactly 65536 bytes the function returns the output unchanged, so the comparison is the same.
