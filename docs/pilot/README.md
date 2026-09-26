# Pilot 1 instruments (row 13, step A)

The files in this folder are **templates and definitions**. The real pilot files — the log, the
baseline, the owner inputs, the bring-home file and the sheet — are private and are **never
committed here** ([decision 0140](../decisions/0140-row-13-pilot-instruments.md), D7). Everything
below is the lane's specification, decided under the owner's standing delegation of
23 Sep 2026.

| File | What it is | How it is filled |
|---|---|---|
| `pilot_log_vocabulary.json` | the pilot log's columns, header comment and the stage, actor, action and reason_code vocabularies (D1); the baseline's columns and `basis` values (D2) | not filled; it is the single definition every reader and (step B) the writer use |
| `pilot1_log.template.csv` | the log's shape: `# gars-pilot-log v1 nonce=<32 hex>`, then `ts,stage,actor,action,reason_code,minutes` | never by hand. Step B's writer creates the real log with a fresh 32-hex nonce and appends each row from clock readings; `minutes` is computed, never typed. The template's placeholder nonce is refused as a log. |
| `pilot1_baseline.template.csv` | `stage,action,hours,basis` | by the owner, before the pilot session, one row per stage and action, `basis` = `measured_prior` or `estimate`; stored privately; its SHA-256 is recorded before the session |
| `owner_inputs.template.json` | the closed schema of `owner_inputs.json`: `hourly_value_usd` (number), `hourly_value_source` (string), `project_definition` (string), `liability` (`unpriced` only in this row), `price_usd` (`null` only in this row) | privately, by the owner. No other key is accepted; the placeholders are refused until replaced. The two strings are hashed into the sheet's head, never printed. |

The log has **no free-text column**, so it cannot carry a sample name, a gene or a note.

## The generators

```bash
python3 scripts/unit_economics.py --log pilot1_log.csv --baseline pilot1_baseline.csv \
    --bench backend_bench.csv --inputs owner_inputs.json --quantities bring_home.txt --out <dir>
python3 scripts/rerun_diff.py --comparison <out>/comparison.json
python3 scripts/session_turns.py --transcript <session.jsonl> --log pilot1_log.csv --stage 02_02_de
```

All three are stdlib-only; written for Python 3.6.8 (syntax checked, not executed on 3.6.8). A
refusal exits 2 with `refused: <reason>` on stderr and writes nothing; input that would crash a
parser (a NUL byte, runaway JSON nesting) is refused with a fixed code too, never a traceback, and
so is a number too large to print to the cent or an exponent past the decimal context
(`value_out_of_range`, whichever decimal signal it raises). Refusal codes are required to be
the same on every Python from 3.6 to 3.13, tested by emulating both sides of each known split
(`tests/pilot_emulation.py`); executed on CPython 3.8.2, 3.8.19, 3.9.6, 3.9.21, 3.10.16, 3.12.9,
3.12.14, 3.13.2 and 3.14.7, not on 3.6, 3.7 or 3.11. To that end a NUL byte is refused before the
`csv` module sees it (3.11 and later read one as data), integers are never converted through
`int()` of their text (3.11 and later cap its digits), and every file is read as UTF-8 whatever
the locale. A
refused `unit_economics.py` run leaves any sheet already in `--out` untouched, so a stale sheet
can outlive a refused regeneration: compare its `input … sha256` lines with the inputs before
using it.

The sheet's cost line names every part it does not price, by backend:
`cost total: $<x> + unmetered compute (<backends with a bench row>) + unmeasured compute
(<backends without one>) + unmetered agent + unpriced liability` (either compute part is omitted
when it names no backend). `time saved total` covers the stages that have a baseline row only;
the human hours of the others are printed on their own line,
`human hours without a baseline: <h> (<stages>)`, and never subtracted (ruling L3).

## Interfaces fixed for step B

These are defined here once; `tests/test_unit_economics.py`, `tests/test_rerun_diff.py` and
`tests/test_session_turns.py` hold the scripts to them.

### The quantities file (`--quantities`)

A bring-home text file. `unit_economics.py` reads **only** lines of exactly these three shapes
and ignores every other line, printing `quantities: graded <k> of <n> lines` (k matched, n
total) — except that a line starting with the word `quantity`, in any case and after any
leading whitespace, which matches neither quantity shape (an extra space, a capital, a tab, a
sign, an unknown backend) is refused as `quantity_malformed` (rulings L4 and n2), and so is a
line starting `human turns:` (any case, after leading whitespace) that is not the session_turns
shape below (step B, D-vi n2); a word
that only begins with `quantity` (`quantity_notes`) is another line, counted and ignored:

- `quantity samples_in_design <non-negative integer>`
- `quantity cpu_hours <backend> <non-negative decimal>`, backend one of `local`, `homelab`, `slurm`
- the session_turns line exactly as `session_turns.py` prints it:
  `human turns: <t>; inside spans: <i>; outside spans: <o>; outside minutes: <m>; session wall minutes: <w>; agent active minutes: <a>; outside window: <k>; graded <n> of <n> records`

For example (one of each shape):

    quantity samples_in_design 6
    quantity cpu_hours slurm 1.75
    human turns: 6; inside spans: 4; outside spans: 2; outside minutes: 1.50; session wall minutes: 47.00; agent active minutes: 45.50; outside window: 0; graded 14 of 14 records

Values are stored and printed in canonical form (no leading zeros, no trailing fractional
zeros: `01.750` is `1.75`, `0.20` is `0.2`), and a repeated quantity is compared by canonical
value: the same value in another spelling is accepted, a different value is refused
(`quantity_conflict`). A missing
`samples_in_design` makes every per-sample figure `uncomputable`, never zero; a missing CPU-hour
line prints `unmeasured`; a missing session_turns line prints the cross-check as `unmeasured`.
A session line whose inside and outside counts do not sum to its turns is refused.

### The bench CSV (`--bench`)

Row 8B's `benchmarks/backend_bench.csv`, which does not exist at this row's parent. The binding
is to **8B's plan, not 8B's code**, and is re-checked when step B rebases onto 8B. It is read by
header name only, never by column position. Columns used: `backend`, `status`, `samples`,
`cpu_s`, `wall_s`, `cost_usd_per_sample`, `cost_basis`; any other column (`queue_wait_s`,
`workload_sha256`, `measured_at`, …) is carried through unread. Each row must recompute:
`status` is `COMPLETED`; `samples`, `cpu_s`, `wall_s` are non-negative numbers; `cost_basis`
is `owned_hardware` or `institutional_allocation`, and then `cost_usd_per_sample` is exactly
`unmetered`. A numeric cost is a hand-typed cost and is refused (`bench_hand_typed_cost`).
No row for a backend prints that backend's compute as `unmeasured`.

### The comparison file (`--comparison`)

Row 6's `comparison.json`, written by row 6's `scripts/rerun_check.py`, which does not exist at
this row's parent. Shape as the lane read it at row 6's build head: one JSON object with `runs`
(a list of `{run, job, match, reason, artifacts, code}`), `requested`, `original` (the absolute
path of the original stage's `reproducibility/manifest.json`), `tolerances_sha256`,
`wrappers_root`, `wrapper_sha256`. Each artifact is `{path, mode, match, metric, value,
original_sha256, replay_sha256}`, `path` relative to its stage folder.

- The original stage folder is the parent of the parent of `original`.
- Run n's re-run stage folder is `<the folder holding comparison.json>/run-<n>/02_bioinformatics/<assay>/<substage>/`,
  `<assay>/<substage>` being the original stage folder's last two path parts.
- An empty `runs` list (`comparison_runs_empty`) and a run number listed twice
  (`comparison_run_duplicate`) are refused (ruling L5).
- Per run, the one artifact whose path ends in `de_results.csv` is compared (none or more than
  one: refused). Each table must hash to `original_sha256` / `replay_sha256` (else refused).
- One block per run, in `runs` order: `rows original/re-run`, `genes matched`, `genes only in
  original`, `genes only in re-run`, `byte_equal yes|no`, `max_abs_delta log2FoldChange`,
  `max_rel_delta padj`, `spearman log2FoldChange`, `crossings padj<0.05 (gained/lost)`,
  `sign flips`, `na_padj original/re-run`, `na_log2FoldChange original/re-run`, and
  `graded <k> of <n> rows`.

`rerun_diff.py` never prints a gene identifier, a sample name, a path or any `reason` text,
and it changes no tolerance.

### The DE table

`rnaseq_de`'s `de_results.csv`: `gene,baseMean,log2FoldChange,pvalue,padj` (the header comment
of `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`). `NA`, empty or NaN `padj` is counted as
`na_padj`, never dropped silently. The table has no Wald `stat` column, so D4's `spearman stat`
is computed as Spearman's rank correlation of `log2FoldChange` over the matched genes and is
printed as `spearman log2FoldChange`. `max_rel_delta padj` is max |a−b| / max(|a|,|b|) over
matched genes with both values present (0 when both are 0). Crossings count only genes with
both `padj` values present: a gene whose `padj` moves between `NA` and a value below 0.05 is not
a crossing and shows only as a change in `na_padj`. Genes are matched by `gene`; genes in only
one table are counted, never printed.

### The session transcript (`--transcript`)

A Claude Code session JSONL, one record per line. The type is checked first (ruling L7, narrowed
by ruling 0150): a line that is not a JSON object, or a record whose `type` is missing, null,
empty or not a string, is unclassifiable and exits 2 whatever its flags (`isSidechain`,
`isMeta`, `isCompactSummary`). Only `user` and `assistant` are message types. A record of any
other type is a harness record (ruling 0150, decision 0150): a real session writes many of them
(`attachment`, `system`, `queue-operation`, `ai-title`, `file-history-snapshot` and more). It is
graded, never a human turn, never the predecessor that starts an outside turn's attention
interval, never agent activity and never part of the session's window; its content, flags and
timestamp are not examined, so it needs no timestamp and an unparseable one does not refuse it.
It is counted in `graded <n> of <n> records` and in nothing else, not in `outside window`. A
message record classifies as a human turn (`type == "user"`, none of the three flags, content not
all `tool_result`), a tool result, meta or harness record (non-human), or an assistant record
(`type == "assistant"`, none of the three flags). A record with `isCompactSummary` true is
written by Claude Code itself (ruling L2), a record with `isSidechain` true is subagent traffic
the human does not see (ruling L6), and a record with `isMeta` true is meta: each is graded but
never counts as a human turn, never starts an outside turn's attention interval (so it cannot
change `outside minutes`) and is never part of the agent-active span; either flag is enough
(ruling m2). Their content is not examined.

The session's window (ruling L7) runs from the timestamp of the first main-thread record in file
order to that of the last, a main-thread record being a `user` or `assistant` record carrying
none of the three flags; a start later than the end is refused `session_window_inverted`.
`session wall minutes` is the window's length. A message record whose timestamp lies outside the
window is graded, counted in `outside window: <k>`, and never used in session wall minutes,
agent-active minutes, outside minutes or as a predecessor; a human turn outside it still counts
as a turn. A transcript with no main-thread record has an empty window, and every message record
lies outside it. So `graded` = message records inside the window + `outside window` +
non-message (harness) records.

An extra key on an otherwise known record does not change its class; each message record needs
an ISO-8601 `timestamp` with `Z` or a numeric offset. A message record with a missing or
unparseable timestamp or with main-thread `user` content mixing `tool_result` with other blocks,
and a blank line, are unclassifiable and exit 2. `outside minutes` follows ruling L1 (decision 0140) and is a lower
bound on unlogged human attention; it never changes a logged minute.
