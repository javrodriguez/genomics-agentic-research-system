#!/usr/bin/env python3
"""File-integrity verification, shared by stages 00 and 01.

One home for the rule, because two stages check the same thing at different moments:

    stage 00  every registered file, cheaply -- links resolve, non-empty, gzip magic
    stage 01  the INCLUDED subset, deeply -- full decompression, before hours of compute

Splitting it that way is the point. Stage 00 registers everything the user pointed at; the user
does not choose which samples to analyse until the 00 -> 01 gate. Deep-verifying 48 GB at
registration spends the cost on files that are about to be excluded.

Measured on this cluster (48 GB, 152 files, GPFS): the work is I/O-bound, not CPU-bound. A pass
reading two bytes per file still took 3m51s wall at 0.1 s of CPU. A full pass sustains ~130 MB/s
and is throughput-limited -- 4 and 16 workers measure identically -- so concurrency past 4 buys
nothing. Peak RSS is ~70 MB; it does not leak.

**Deep verification is scheduled work, not login-node work.** Above LOGIN_NODE_BYTES the calling
contract submits it with sbatch rather than running it inline, for the same reason sub-stage 02.02
must: a login node is shared, and its user cgroup here is a 4 GB budget across every process you
own. Exceeding it kills whatever is running, which may not even be the process at fault.
"""

import gzip
import sys

# Above this, a contract submits the check to Slurm instead of running it inline. 10 GB is about
# 80 seconds of reading at the measured rate -- comfortably interactive below, antisocial above.
LOGIN_NODE_BYTES = 10 * 1000 ** 3

THROUGHPUT_BYTES_PER_S = 130e6
DEFAULT_JOBS = 4


def estimate_minutes(total_bytes):
    return max(1, int(round(total_bytes / THROUGHPUT_BYTES_PER_S / 60)))


def needs_scheduling(total_bytes):
    return total_bytes > LOGIN_NODE_BYTES


def check_one(path, mode="full"):
    """Verify one file. Returns a problem string, or None.

    full   resolves, non-empty, and decompresses completely
    quick  resolves, non-empty, and carries the gzip magic bytes. Catches a broken link, an empty
           file and a not-actually-gzip file; does NOT catch truncation or corruption, which are
           the failures `full` exists for.
    skip   resolves and non-empty only
    """
    if not path.is_file():
        return "does not resolve"
    if path.stat().st_size == 0:
        return "is empty"
    if mode == "skip" or not str(path).endswith(".gz"):
        return None
    if mode == "quick":
        try:
            with open(str(path), "rb") as fh:
                if fh.read(2) != b"\x1f\x8b":
                    return "is not gzip (bad magic)"
        except OSError as exc:
            return "cannot be read: %s" % exc
        return None
    try:
        # Python's gzip measured FASTER than the system `gzip -t` binary here (15.6 s vs 26.0 s on
        # a 666 MB file), so there is nothing to gain by shelling out.
        with gzip.open(str(path), "rb") as fh:
            while fh.read(1 << 20):
                pass
    except Exception as exc:
        return "fails integrity check: %s" % exc
    return None


def check_many(paths, mode, jobs=DEFAULT_JOBS, log=sys.stderr):
    """Verify many (label, path) pairs in parallel. Returns [(label, problem), ...].

    Threads, not processes: zlib releases the GIL during decompression. Progress goes to stderr
    because stdout carries JSON -- a silent multi-minute process reads as a hang, and three runs
    were abandoned before that was fixed.
    """
    import concurrent.futures

    problems, done, total = [], [0], len(paths)

    def one(item):
        label, path = item
        problem = check_one(path, mode)
        done[0] += 1
        if total >= 20 and done[0] % max(1, total // 10) == 0:
            log.write("[integrity] %d/%d checked\n" % (done[0], total))
            log.flush()
        return label, problem

    if total and mode != "skip":
        log.write("[integrity] %s check of %d files, %d worker(s)\n" % (mode, total, jobs))
        log.flush()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for label, problem in ex.map(one, paths):
            if problem:
                problems.append((label, problem))
    return problems
