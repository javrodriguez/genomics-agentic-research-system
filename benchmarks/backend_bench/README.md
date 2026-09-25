# Backend bench evidence

No measured rows ship with the instrument. W1 is 24 deterministic gzip blobs,
each containing 8 MiB of seeded bytes, generated using SHAKE-256 and explicitly
serialized stored DEFLATE blocks. It exercises GARS full integrity and SHA-256,
not FASTQ analysis. Samples means blobs for this workload.

From the repository root, at each actual venue:

```
python3 scripts/backend_bench.py run --venue local --out bench-run
python3 scripts/backend_bench.py collect --out bench-run --timeout-s 3600
python3 scripts/backend_bench.py append --evidence bench-run/evidence.json
```

Choose the actual venue from local, homelab and slurm. The output directory must
not exist. Homelab uses the local executor and requires the operator's machine
marker. Run submits one prepared job and measures nothing. Collect waits for a
terminal job; timeout writes no evidence. Failed evidence cannot be appended.
Missing measurements for a failed job are null, never invented zeros.

Append retains the exact evidence bytes here under their SHA-256 filename. CSV
rows must regenerate from these files. A replacement requires --supersede with
the prior evidence SHA-256 and appends a new row retaining history. Benchmark
backend labels distinguish all three venues; executor backend names remain
local and slurm. Evidence admits only the fields listed by the instrument and
no host, user, path, partition or IP fields. CSV edits are detected by evidence
regeneration; the truth of source timings still depends on machine clocks.

Costs are unmetered, with owned_hardware for local/homelab and
institutional_allocation for slurm. These are R-193 inputs, not priced economics.

The route and workload rulings were decided under the owner's standing delegation (23 Sep 2026).
