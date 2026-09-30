#!/usr/bin/env python3
"""Recompute the deposited-track half of the failed-replicate finding (docs/RESULTS.md, row 3a).

    python3 reproduction/gse58638/recompute.py            # streams 8.8 GB from NCBI, stores nothing
    python3 reproduction/gse58638/recompute.py --from DIR # reads local copies (size and sha256 checked)
    python3 reproduction/gse58638/recompute.py --check-published   # the network-free binding CI runs

It streams the authors' four H3K27me3 z-score bigWigs from GEO GSE58638, hashes every byte, parses
every data block with the standard library alone, and counts, per file, the 10-bp bins above z>1 and
z>2 (base-weighted, strictly greater, on the stored float32) and the 10-kb tiles whose exact mean is
above them. It prints the report, compares it with the committed expected.txt, and checks each
quotation of RESULTS.md it discusses is found there exactly once.

What it reports and binds is fixed by two files beside it: PREREG.md (frozen before any deposit
byte was read) and PREREG-2.md (the dated rule for the binding under the recorded IN KIND verdict).

Exit codes: 0 identical and matching; 1 a science difference (a deposit's size or sha256 changed, a
quotation moved, the report differs), named; 2 refused (short read, bad format, zero records, the
network on the deposits); 3 only a public-metadata context line changed or could not be fetched.

Standard library only; Python 3.9 or later.
"""
import dataclasses
import hashlib
import http.client
import math
import re
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REL_EXPECTED = "reproduction/gse58638/expected.txt"
USER_AGENT = "GARS-recompute/1 (github.com/javrodriguez/genomics-agentic-research-system; reproduction/gse58638)"
CHUNK = 1 << 20
ATTEMPTS = 5
TILE = 10000

# ---- the four deposits (plan §2.1; sizes and sha256 recorded at first read, step1.md §2) ------------


@dataclasses.dataclass(frozen=True)
class Deposit:
    gsm: str
    cell: str
    srx: str
    path: str       # below the URL base
    filename: str
    size: int
    sha256: str


DEPOSITS = (
    Deposit("GSM1415877", "HCT116", "SRX610762", "GSM1415nnn/GSM1415877/suppl/",
            "GSM1415877_HCT116_H3K27me3_D1ALAACXX_7_KEL656A215.male.hg19.fa.mdups.wiggler_norm"
            ".binned_10.minusInput.Z_score.bw",
            2171032113, "9b95fc99b01822e2a824ef6898f0dcdb241c68c4c1d96bfc6d5018b422e86978"),
    Deposit("GSM1420155", "HCT116", "SRX625662", "GSM1420nnn/GSM1420155/suppl/",
            "GSM1420155_HCT116_H3K27me3_Heather_FC64LGK_L6_rep1.male.hg19.fa.mdups.wiggler_norm"
            ".binned_10.minusInput.Z_score.bw",
            2261546285, "1aa3f5403aafd8796936db3aaa5403b10ec8e7e0361a50a3fda9c06be68213ba"),
    Deposit("GSM1415885", "DKO1", "SRX610770", "GSM1415nnn/GSM1415885/suppl/",
            "GSM1415885_DKO1_H3K27me3_D1ALAACXX_5_KEL656A212.male.hg19.fa.mdups.wiggler_norm"
            ".binned_10.minusInput.Z_score.bw",
            2174430755, "1de24e332e4563b83af699406c4ca9ec41fa713c9ae09dbe45a75ec9797cb04f"),
    Deposit("GSM1420162", "DKO1", "SRX625669", "GSM1420nnn/GSM1420162/suppl/",
            "GSM1420162_DKO1_H3K27me3_D2BUFACXX_8_KEL656A296.male.hg19.fa.mdups.wiggler_norm"
            ".sort.binned_10.minusInput.Z_score.bw",
            2220232372, "d0b1e64f28a12d077b893b898abb9b0be34435cff2317d5db72b3c2490ce112e"),
)
FAILED = "GSM1420155"
GEO_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/samples"
GEO_BRIEF = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=%s&targ=self&form=text&view=brief"
SRA_RUNINFO = "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc=%s"

# ---- what the report discusses and binds ---------------------------------------------------------

# PREREG.md P1: the targets and the context line, verbatim from docs/RESULTS.md (U+2013, U+00D7).
QUOTES = {
    "T1": "0.0073 of bins above z>1 against 0.053–0.083 for the others",
    "T2": "**40–100× below them at z>2**",
    "C1": "theirs (z>1 fraction 0.067 vs 0.045)",
}
# The relation step 1 recorded (VERDICT-step1.md), which PREREG-2 R1 keeps.
VERDICT = "IN KIND"
ADOPTED = "B1"
# PREREG-2 R3: step1.md §5's B1 row (z>1, z>2 per deposit) and VERDICT-step1.md's B1 ratios
# (other/GSM1420155, in the order GSM1415877, GSM1415885, GSM1420162), at their printed precision.
STEP1_B1 = {
    "GSM1415877": ("0.1066", "0.0429"),
    "GSM1420155": ("0.0256", "0.00200"),
    "GSM1415885": ("0.1130", "0.0384"),
    "GSM1420162": ("0.1165", "0.0432"),
}
STEP1_B1_RATIOS = (("4.17", "4.42", "4.56"), ("21.4", "19.2", "21.5"))
# The one step-1 figure the exact recompute does not equal at its printed precision, measured by the
# lane on 30 Sep 2026 and raised to the orchestrator: GSM1420155's B1 z>2 fraction is
# 620682/309564635 = 0.0020050..., which is 0.00201 at three figures under any rounding; step 1
# printed 0.00200. libBigWig counts the same bases. Step 1's figure is the same count rounded twice:
# to four figures (0.002005), then half-even to three (review r3). The binding holds this cell to the recompute's
# own figure and the report prints the difference; every other step-1 figure is bound as printed.
# PENDING a PREREG-3: PREREG-2 R3 binds step 1's printed value, and only the orchestrator can change
# that (R6). Asked in the lane session on 30 Sep, the orchestrator chose to keep this named exception,
# visible in the report and in decision 0241, over a binding that fails until PREREG-3 exists.
STEP1_B1_DIFFERS = {("GSM1420155", 1): "0.00201"}
# PREREG-2 R4: the figures it states for B4, as it states them. Its "44" is step 1's 43.5 rounded a
# second time (the exact ratio is 2435/56 = 43.48); the report prints ratios at step 1's three
# significant figures, so it reads 43.5, and the test binds that (test_b4_equals_prereg2_r4).
PREREG2_R4 = {
    "failed_z1": "0.0074", "others_z1": ("0.053", "0.083"), "ratios_z2": ("44", "108"),
    "c1_dko1": "0.068", "c1_hct116_with": "0.045", "c1_hct116_without": "0.083",
}
# The public-metadata section of expected.txt, pinned so a hand edit to it fails the binding on push
# (the monthly regrade re-fetches it; a change there exits 3). Update only from a real run.
METADATA_SHA256 = "bad7aff4a590190399f06969744b8108892494194b757b2610cd628974599b58"
# The exact counts and the four sha256 as the real run recorded them (the "Exact counts" block through
# the "sha256:" lines of expected.txt), pinned so that a planted expected.txt re-rendered from changed
# counts fails on push; the push-time binding otherwise re-renders from the counts it is given.
# Update only from a real run.
COUNTS_SHA256 = "4e989d44c8748edff43380d926397a5a512aed7bae431df8ed4bd7f222b1fedd"
# docs/RESULTS.md at 37a8d94 (LF), the base this was built on: while no row 3a addendum is found, the
# binding requires RESULTS.md unchanged, so an addendum that lands in a form find_addendum() misses
# fails rather than leaving PREREG-2 R5 skipped for good.
RESULTS_MD_SHA256 = "81d517aeb4a9d9f3d91db60c57db7e4f0793da42b42a55b888e152b854ba77ae"
# PREREG.md P6's thresholds, printed and never asserted (PREREG-2 R2).
P6_Z1, P6_Z2 = 5, 20


class Refused(Exception):
    """Exit 2: nothing was measured that could be reported."""


class ScienceDifference(Exception):
    """Exit 1: a pinned input or a published figure moved."""


# ---- the bigWig reader ---------------------------------------------------------------------------

BIGWIG_MAGIC = 0x888FFC26
CHROM_TREE_MAGIC = 0x78CA8C91


@dataclasses.dataclass
class ChromCounts:
    records: int = 0
    bases: int = 0
    above1: int = 0
    above2: int = 0


@dataclasses.dataclass
class FileCounts:
    records: int = 0
    bases: int = 0            # bases with data (NaN excluded)
    above1: int = 0           # bases with value > 1.0
    above2: int = 0
    nan_records: int = 0
    nan_bases: int = 0
    pos_inf: int = 0
    neg_inf: int = 0
    exact1: int = 0           # records whose stored value is exactly 1.0
    exact2: int = 0
    not_mult10: int = 0       # records whose span is not a multiple of 10
    tiles: int = 0            # 10-kb tiles with data
    tiles_above1: int = 0
    tiles_above2: int = 0
    tiles_nan: int = 0        # tiles whose mean is undefined (+inf and -inf together)
    blocks: int = 0
    data_count: int = 0
    header_bases_covered: int = 0
    per_chrom: dict = dataclasses.field(default_factory=dict)

    FIELDS = ("records", "bases", "above1", "above2", "nan_records", "nan_bases", "pos_inf", "neg_inf",
              "exact1", "exact2", "not_mult10", "tiles", "tiles_above1", "tiles_above2", "tiles_nan")


class BigWigCounter(object):
    """A push parser: feed() the file's bytes in order, then finish(). Nothing is seeked, so the
    same code serves a stream and a local file. Each data block is its own zlib stream."""

    def __init__(self, label, sink=None):
        self.label = label
        self.sink = sink              # optional callable(chrom, start, end, value) for tests
        self.pos = 0                  # bytes consumed so far
        self.head = bytearray()       # everything before the first data block
        self.state = "head"
        self.c = FileCounts()
        self.chroms = {}              # id -> (name, size)
        self.inflater = None
        self.block = []
        self.last = None              # (chrom id, end) of the previous record
        self.done = set()             # chromosomes whose records have ended
        self.tile = None              # (chrom id, tile index)
        self.tile_parts = []
        self.tile_bases = 0
        self.tile_inf = [False, False]

    # -- the header, zoom headers, total summary and chromosome tree, all before the data --------

    def _parse_head(self):
        b = bytes(self.head)
        magic = struct.unpack_from("<I", b, 0)[0]
        if magic != BIGWIG_MAGIC:
            raise Refused("%s: not a bigWig (magic %08x)" % (self.label, magic))
        (_, version, zooms, self.tree_off, self.data_off, self.index_off, _, _, _, summary_off,
         self.ubuf) = struct.unpack_from("<IHHQQQHHQQI", b, 0)
        if version < 3:
            raise Refused("%s: bigWig version %d is not supported" % (self.label, version))
        if not (64 <= self.tree_off < self.data_off and 64 <= summary_off < self.data_off):
            raise Refused("%s: header offsets out of order" % self.label)
        self.c.header_bases_covered = struct.unpack_from("<Q", b, summary_off)[0]
        self._parse_tree(b)
        self.c.data_count = struct.unpack_from("<Q", b, self.data_off)[0]
        if self.c.data_count == 0:
            raise Refused("%s: zero records (the data section holds no block)" % self.label)
        if self.index_off <= self.data_off + 8:
            raise Refused("%s: index offset %d does not follow the data" % (self.label, self.index_off))

    def _parse_tree(self, b):
        magic, _, key_size, val_size, count = struct.unpack_from("<IIIIQ", b, self.tree_off)
        if magic != CHROM_TREE_MAGIC or val_size != 8:
            raise Refused("%s: bad chromosome tree" % self.label)
        stack = [self.tree_off + 32]
        while stack:
            off = stack.pop()
            leaf, _, n = struct.unpack_from("<BBH", b, off)
            off += 4
            for _ in range(n):
                key = b[off:off + key_size].rstrip(b"\0").decode("ascii")
                off += key_size
                if leaf:
                    cid, size = struct.unpack_from("<II", b, off)
                    self.chroms[cid] = (key, size)
                    off += 8
                else:
                    stack.append(struct.unpack_from("<Q", b, off)[0])
                    off += 8
        if len(self.chroms) != count:
            raise Refused("%s: chromosome tree lists %d of %d" % (self.label, len(self.chroms), count))

    # -- feeding ---------------------------------------------------------------------------------

    def feed(self, data):
        """Every malformed-structure error surfaces as a refusal naming the file, never as a
        traceback (review r6, F-2)."""
        try:
            self._feed(data)
        except Refused:
            raise
        except (struct.error, UnicodeDecodeError, IndexError, KeyError, ValueError, OverflowError) as exc:
            raise Refused("%s: malformed bigWig (%s: %s)" % (self.label, exc.__class__.__name__, exc))

    def _feed(self, data):
        if self.state == "head":
            need = None
            self.head += data
            if len(self.head) >= 64 and not hasattr(self, "data_off"):
                if struct.unpack_from("<I", self.head, 0)[0] != BIGWIG_MAGIC:
                    raise Refused("%s: not a bigWig (bad magic %s)" % (self.label, bytes(self.head[:4]).hex()))
                self.data_off = struct.unpack_from("<Q", self.head, 16)[0]
            if hasattr(self, "data_off"):
                need = self.data_off + 8
            if need is None or len(self.head) < need:
                self.pos += len(data)
                return
            self._parse_head()
            rest = bytes(self.head[need:])
            self.pos += len(data) - len(rest)
            self.head = None
            self.state = "data"
            self.inflater = zlib.decompressobj()
            if rest:
                self._feed(rest)
            return
        if self.state == "data":
            limit = self.index_off - self.pos
            part, rest = (data, b"") if len(data) <= limit else (data[:limit], data[limit:])
            self.pos += len(part)
            self._inflate(part)
            if self.pos == self.index_off:
                if self.inflater is not None:
                    raise Refused("%s: a data block runs past the index offset" % self.label)
                if self.c.blocks != self.c.data_count:
                    raise Refused("%s: %d blocks decoded where the header counts %d"
                                  % (self.label, self.c.blocks, self.c.data_count))
                self.state = "tail"
            if rest:
                self.pos += len(rest)
            return
        self.pos += len(data)   # index and zoom levels: hashed by the caller, not parsed

    def _inflate(self, data):
        while data:
            if self.inflater is None:
                self.inflater = zlib.decompressobj()
            try:
                out = self.inflater.decompress(data)
            except zlib.error as exc:
                raise Refused("%s: corrupt data block (%s)" % (self.label, exc))
            if out:
                self.block.append(out)
            if not self.inflater.eof:
                return
            data = self.inflater.unused_data
            self.inflater = None
            self._section(b"".join(self.block))
            self.block = []

    # -- one decompressed section ----------------------------------------------------------------

    def _section(self, raw):
        self.c.blocks += 1
        if len(raw) < 24:
            raise Refused("%s: short section" % self.label)
        cid, _, _, step, span, kind, _, count = struct.unpack_from("<IIIIIBBH", raw, 0)
        if cid not in self.chroms:
            raise Refused("%s: section names unknown chromosome id %d" % (self.label, cid))
        body = memoryview(raw)[24:]
        if kind == 1:
            if len(body) != 12 * count:
                raise Refused("%s: bedGraph section length" % self.label)
            items = struct.iter_unpack("<IIf", body)
        elif kind == 2:
            if len(body) != 8 * count:
                raise Refused("%s: variableStep section length" % self.label)
            items = ((s, s + span, v) for s, v in struct.iter_unpack("<If", body))
        elif kind == 3:
            if len(body) != 4 * count:
                raise Refused("%s: fixedStep section length" % self.label)
            first = struct.unpack_from("<I", raw, 4)[0]
            items = ((first + i * step, first + i * step + span, v)
                     for i, (v,) in enumerate(struct.iter_unpack("<f", body)))
        else:
            raise Refused("%s: unknown section type %d" % (self.label, kind))
        self._records(cid, items)

    def _records(self, cid, items):
        c = self.c
        name, size = self.chroms[cid]
        if self.last is not None and self.last[0] != cid:
            self.done.add(self.last[0])
            self._close_tile()
        if cid in self.done:
            raise Refused("%s: chromosome %s revisited after another" % (self.label, name))
        pc = c.per_chrom.setdefault(name, ChromCounts())
        last_end = self.last[1] if self.last is not None and self.last[0] == cid else 0
        sink = self.sink
        n = bases = a1 = a2 = 0
        for s, e, v in items:
            if e <= s or s < last_end or e > size:
                raise Refused("%s: record %s:%d-%d out of order or out of bounds" % (self.label, name, s, e))
            last_end = e
            n += 1
            span = e - s
            if span % 10:
                c.not_mult10 += 1
            if sink is not None:
                sink(name, s, e, v)
            if v != v:
                c.nan_records += 1
                c.nan_bases += span
                continue
            bases += span
            if v > 1.0:
                a1 += span
                if v > 2.0:
                    a2 += span
            elif v == 1.0:
                c.exact1 += 1
            if v == 2.0:
                c.exact2 += 1
            if v == math.inf:
                c.pos_inf += 1
            elif v == -math.inf:
                c.neg_inf += 1
            # 10-kb tiles from the chromosome start; a record across a tile edge is split.
            t = s // TILE
            while True:
                if self.tile != (cid, t):
                    self._close_tile()
                    self.tile = (cid, t)
                edge = (t + 1) * TILE
                if e <= edge:
                    self._tile_add(v, e - s)
                    break
                self._tile_add(v, edge - s)
                s, t = edge, t + 1
        c.records += n
        c.bases += bases
        c.above1 += a1
        c.above2 += a2
        pc.records += n
        pc.bases += bases
        pc.above1 += a1
        pc.above2 += a2
        self.last = (cid, last_end)

    def _tile_add(self, v, b):
        self.tile_bases += b
        if v == math.inf:
            self.tile_inf[0] = True
        elif v == -math.inf:
            self.tile_inf[1] = True
        else:
            self.tile_parts.append(v * b)   # exact: a float32 times b < 2**14 fits a double

    def _close_tile(self):
        if self.tile is None or self.tile_bases == 0:
            self.tile, self.tile_parts, self.tile_bases, self.tile_inf = None, [], 0, [False, False]
            return
        c = self.c
        c.tiles += 1
        pos, neg = self.tile_inf
        if pos and neg:
            c.tiles_nan += 1
        elif pos:
            c.tiles_above1 += 1
            c.tiles_above2 += 1
        elif not neg:
            # mean > T  <=>  sum > T * bases. fsum is correctly rounded, so a strict inequality on
            # it is exact; only equality is ambiguous, and then exact rationals decide.
            total = math.fsum(self.tile_parts)
            for threshold in (1, 2):
                bound = threshold * self.tile_bases
                if total > bound:
                    above = True
                elif total < bound:
                    above = False
                else:
                    above = sum(Fraction(p) for p in self.tile_parts) > bound
                if above:
                    if threshold == 1:
                        c.tiles_above1 += 1
                    else:
                        c.tiles_above2 += 1
        self.tile, self.tile_parts, self.tile_bases, self.tile_inf = None, [], 0, [False, False]

    def finish(self):
        if self.state == "head":
            raise Refused("%s: file ends inside the header (%d bytes)" % (self.label, self.pos))
        if self.state == "data":
            raise Refused("%s: file ends inside the data section, at byte %d of %d"
                          % (self.label, self.pos, self.index_off))
        self._close_tile()
        if self.c.records == 0:
            raise Refused("%s: zero records" % self.label)
        return self.c


def grade_against_seen(c, label):
    """Every base the header's total summary says the file covers was counted (NaN bases counted by
    either writer's convention). The header is the only independent count the file carries."""
    if c.header_bases_covered not in (c.bases, c.bases + c.nan_bases):
        raise Refused("%s: graded %d bases (+%d NaN) but the header covers %d"
                      % (label, c.bases, c.nan_bases, c.header_bases_covered))


def count_path(path, sink=None):
    counter = BigWigCounter(str(path), sink)
    with open(str(path), "rb") as f:
        while True:
            data = f.read(CHUNK)
            if not data:
                break
            counter.feed(data)
    return counter.finish()


def records_of(path):
    out = []
    count_path(path, sink=lambda *r: out.append(r))
    return out


# ---- reading a deposit: a local copy or a resumable stream --------------------------------------

def read_local(dep, folder, err):
    p = Path(folder) / dep.filename
    if not p.is_file():
        raise Refused("%s: %s not found in %s" % (dep.gsm, dep.filename, folder))
    size = p.stat().st_size
    if size < dep.size:
        raise Refused("%s: short read, %s holds %d of %d bytes" % (dep.gsm, dep.filename, size, dep.size))
    if size > dep.size:
        raise ScienceDifference("%s: %s is %d bytes, pinned %d: the deposit changed"
                                % (dep.gsm, dep.filename, size, dep.size))
    counter, h, parse_error = BigWigCounter(dep.filename), hashlib.sha256(), None
    with open(str(p), "rb") as f:
        while True:
            data = f.read(CHUNK)
            if not data:
                break
            h.update(data)
            parse_error = parse_error or feed_guarded(counter, data)
    return finish_deposit(dep, counter, h, size, parse_error)


def feed_guarded(counter, data):
    """Feed the parser; a refusal is kept, not raised, so every byte is still hashed and a changed
    deposit is named as changed (exit 1) before any parse error is reported (exit 2)."""
    try:
        counter.feed(data)
    except Refused as exc:
        return exc
    return None


def read_stream(dep, url_base, err, retry_wait=5.0, opener=urllib.request.urlopen):
    url = "%s/%s%s" % (url_base.rstrip("/"), dep.path, dep.filename)
    counter, h, got, parse_error = BigWigCounter(dep.filename), hashlib.sha256(), 0, None
    failures = []
    for attempt in range(ATTEMPTS):
        headers = {"User-Agent": USER_AGENT}
        if got:
            headers["Range"] = "bytes=%d-" % got
        try:
            resp = opener(urllib.request.Request(url, headers=headers), timeout=120)
        except (urllib.error.URLError, OSError) as exc:
            failures.append(str(exc))
            time.sleep(retry_wait)
            continue
        with resp:
            status = getattr(resp, "status", 200)
            if got:
                crange = resp.headers.get("Content-Range", "")
                if status != 206 or not crange.startswith("bytes %d-" % got):
                    failures.append("resume at byte %d answered %s %s" % (got, status, crange))
                    time.sleep(retry_wait)
                    continue
            else:
                length = resp.headers.get("Content-Length")
                if length is not None and int(length) != dep.size:
                    raise ScienceDifference("%s: %s is %s bytes on GEO, pinned %d: the deposit changed"
                                            % (dep.gsm, dep.filename, length, dep.size))
            try:
                while got < dep.size:
                    data = resp.read(min(CHUNK, dep.size - got))
                    if not data:
                        break
                    h.update(data)
                    got += len(data)
                    parse_error = parse_error or feed_guarded(counter, data)
            except (OSError, ValueError, http.client.HTTPException) as exc:  # IncompleteRead, resets
                failures.append("dropped at byte %d (%s)" % (got, exc.__class__.__name__))
            if got >= dep.size:
                if resp.read(1):
                    raise ScienceDifference("%s: %s is longer than its pinned %d bytes"
                                            % (dep.gsm, dep.filename, dep.size))
                return finish_deposit(dep, counter, h, got, parse_error)
        err.write("  %s: connection ended at byte %d of %d; resuming\n" % (dep.gsm, got, dep.size))
        time.sleep(retry_wait)
    raise Refused("%s: short read, %d of %d bytes after %d attempts (%s)"
                  % (dep.gsm, got, dep.size, ATTEMPTS, "; ".join(failures[-3:])))


def finish_deposit(dep, counter, h, nbytes, parse_error=None):
    digest = h.hexdigest()
    if digest != dep.sha256:
        raise ScienceDifference("%s: %s sha256 %s, pinned %s: the deposit changed"
                                % (dep.gsm, dep.filename, digest, dep.sha256))
    if parse_error is not None:
        raise parse_error
    c = counter.finish()
    grade_against_seen(c, dep.filename)
    return c, nbytes, digest


# ---- arithmetic ---------------------------------------------------------------------------------

def round_sig(x, n):
    """x (a rational) to n significant figures, half-up on the exact value, in fixed notation."""
    x = Fraction(x)
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    x = abs(x)
    e = 0
    while Fraction(10) ** (e + 1) <= x:
        e += 1
    while Fraction(10) ** e > x:
        e -= 1
    scale = n - 1 - e
    q = x * Fraction(10) ** scale
    r = (q + Fraction(1, 2)).numerator // (q + Fraction(1, 2)).denominator
    if r == 10 ** n:
        r //= 10
        scale -= 1
    if scale <= 0:
        return sign + str(r * 10 ** (-scale))
    digits = str(r).rjust(scale + 1, "0")
    return sign + digits[:-scale] + "." + digits[-scale:]


def sig_figs(printed):
    digits = printed.replace(".", "").lstrip("0")
    return len(digits)


def b1_fractions(c):
    return Fraction(c.above1, c.bases), Fraction(c.above2, c.bases)


def b4_fractions(c):
    return Fraction(c.tiles_above1, c.tiles), Fraction(c.tiles_above2, c.tiles)


def others(counts):
    return [g for g in counts if g != FAILED]


def ratios(counts, fractions):
    """other/GSM1420155 at z>1 and z>2; None where GSM1420155's fraction is 0 (P3: undefined)."""
    f = {g: fractions(c) for g, c in counts.items()}
    out = []
    for z in (0, 1):
        out.append(tuple(None if f[FAILED][z] == 0 else f[g][z] / f[FAILED][z] for g in others(counts)))
    return out


def b1_ratios(counts):
    return ratios(counts, b1_fractions)


def step1_differences(counts):
    """Each B1 figure step 1 printed (8 fractions, 6 ratios) that the recompute does not equal at
    that precision, as a sentence."""
    out = []
    for g, printed in STEP1_B1.items():
        for z, want in enumerate(printed):
            got = round_sig(b1_fractions(counts[g])[z], sig_figs(want))
            if got != want:
                out.append("%s z>%d fraction: step 1 printed %s, the exact recompute is %s (%s)"
                           % (g, z + 1, want, got, exact_decimal(b1_fractions(counts[g])[z], 8)))
    for z in (0, 1):
        for value, want in zip(b1_ratios(counts)[z], STEP1_B1_RATIOS[z]):
            got = "inf" if value is None else round_sig(value, sig_figs(want))
            if got != want:
                out.append("a z>%d ratio: step 1 printed %s, the exact recompute is %s" % (z + 1, want, got))
    return out


def exact_decimal(x, n):
    """x to n significant figures, for showing where a value sits against a rounding boundary."""
    return round_sig(x, n)


def c1_on_b4(counts, deposits=DEPOSITS):
    f = {g: b4_fractions(c)[0] for g, c in counts.items()}
    cells = {}
    for d in deposits:
        cells.setdefault(d.cell, []).append(d.gsm)
    dko = [f[g] for g in cells["DKO1"]]
    hct = [f[g] for g in cells["HCT116"]]
    healthy = [f[g] for g in cells["HCT116"] if g != FAILED]
    return {"dko1_mean": sum(dko) / len(dko), "hct116_with": sum(hct) / len(hct),
            "hct116_without": sum(healthy) / len(healthy)}


# ---- RESULTS.md ---------------------------------------------------------------------------------

def read_utf8(path):
    return Path(path).read_bytes().decode("utf-8")


def find_once(text, quote):
    n = text.count(quote)
    if n != 1:
        raise ScienceDifference("docs/RESULTS.md: %r found %d times, expected exactly once" % (quote, n))
    return text[:text.index(quote)].count("\n") + 1


def check_quotes(results_md):
    text = read_utf8(results_md)
    return {k: find_once(text, q) for k, q in QUOTES.items()}


ADDENDUM_RE = re.compile(r"Addendum \(30 Sep 2026\)[^\n]*(?:\n(?!\s*\n)[^\n]*)*")


def find_addendum(text):
    """The row 3a addendum: by its dated heading, or by its content (a paragraph that says the
    deposit-side direction holds only when GSM1420155 is counted), whatever its heading."""
    m = ADDENDUM_RE.search(text)
    if m:
        return m.group(0)
    for paragraph in re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n")):
        flat = " ".join(paragraph.split())
        if "line 73" in flat and "GSM1420155" in flat and re.search(r"\b0\.0\d\d\b", flat):
            return paragraph
    return None


def results_md_sha(text):
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def addendum_failures(text, counts, context=""):
    """PREREG-2 R5: the addendum's 0.083 equals the B4 recompute at that precision, the reversal it
    states holds on B4, and its 0.067 and 0.045 are quotations of line 73, never recompute outputs.
    Every other decimal in it must be line 73's or a public-metadata figure the report prints
    (`context`), so no figure enters the addendum unbound."""
    block = find_addendum(text)
    if block is None:
        return ["no addendum block"]
    flat = " ".join(block.split())
    failures = []
    # Line 73's figures may appear only as quotations of line 73, each exactly once: its deposit-side
    # pair as "line 73 (DKO1 x vs HCT116 y)", DKO1's figure once more as the comparator "DKO1's x",
    # and its pipeline-side pair "(123 M vs 45.6 M peak bp)". Those spans are removed; every decimal
    # left must be the bound B4 figure, or a public-metadata figure the report prints, in its own
    # "<figure> M" form (review r4, F-3).
    line73 = next((l for l in text.split("\n") if QUOTES["C1"] in l), "")
    q = re.search(r"fraction (\d+\.\d+) vs (\d+\.\d+)", line73)
    pipe = re.search(r"\(?(\d+ M vs \d+\.\d+ M) mean peak bp\)?", line73)
    rest = flat
    if q:
        spans = ["line 73 (DKO1 %s vs HCT116 %s)" % q.groups(), "DKO1's %s" % q.group(1)]
        for span in spans:
            n = rest.count(span)
            if n != 1:
                failures.append("the addendum holds %r %d times; line 73's figures may appear once, "
                                "as that quotation" % (span, n))
            rest = rest.replace(span, " ")
    if pipe:
        rest = re.sub(r"\(%s peak bp\)" % re.escape(pipe.group(1)), " ", rest, count=1)
    bound = re.search(r"healthy HCT116 deposit scores (\d+\.\d+)", rest)
    if bound:
        rest = rest.replace(bound.group(0), " ", 1)
    for figure in set(re.findall(r"\d+\.\d+", context)):
        rest = rest.replace("%s M" % figure, " ", 1)
    for figure in re.findall(r"\d+\.\d+", rest):
        failures.append("the addendum's %s is neither the bound B4 figure, a quotation of line 73, "
                        "nor a metadata figure the report prints in its own form" % figure)
    # The addendum must itself state the reversal, not merely be consistent with it.
    stated = re.search(r"healthy HCT116 deposit scores (\d+\.\d+) against DKO1's (\d+\.\d+)", flat)
    if not (stated and Fraction(stated.group(1)) > Fraction(stated.group(2))
            and "only when GSM1420155 is counted" in flat):
        failures.append("the addendum does not state the reversal (healthy HCT116 above DKO1, the "
                        "direction holding only when GSM1420155 is counted)")
    c1 = c1_on_b4(counts)
    m = re.search(r"healthy HCT116 deposit scores (\d+\.\d+)", flat)
    if not m:
        failures.append("the addendum's healthy HCT116 figure was not found")
    elif round_sig(c1["hct116_without"], sig_figs(m.group(1))) != m.group(1):
        failures.append("addendum %s != B4 recompute %s" % (
            m.group(1), round_sig(c1["hct116_without"], sig_figs(m.group(1)))))
    if not c1["hct116_without"] > c1["dko1_mean"]:
        failures.append("the reversal the addendum states does not hold on B4")
    m = re.search(r"\(DKO1 (\d+\.\d+) vs HCT116 (\d+\.\d+)\)", flat)
    if not m:
        failures.append("the addendum's quotation of line 73 was not found")
    else:
        try:
            line = find_once(text, QUOTES["C1"])
        except ScienceDifference as exc:
            failures.append(str(exc))
        else:
            quoted = "theirs (z>1 fraction %s vs %s)" % (m.group(1), m.group(2))
            if quoted != QUOTES["C1"]:
                failures.append("the addendum's %s vs %s is not line %d's quotation"
                                % (m.group(1), m.group(2), line))
    return failures


# ---- the report ---------------------------------------------------------------------------------

METADATA_HEAD = "Public metadata (context, not recomputed science):"


def git_blob(data):
    data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def script_blob():
    return git_blob(Path(__file__).read_bytes())


def file_sha(name):
    return hashlib.sha256((HERE / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def fmt(x, n=4):
    return "inf" if x is None else round_sig(x, n)


def render_science(counts, sizes, digests, blob, deposits=DEPOSITS):
    """The compared report's science part: a pure function of the counts and the pins."""
    order = [d.gsm for d in deposits]
    cell = {d.gsm: d.cell for d in deposits}
    L = []
    L.append("GARS recompute: the deposited-track half of the failed-replicate finding (docs/RESULTS.md, 3a)")
    L.append("Source: GEO GSE58638, the authors' four H3K27me3 z-score tracks (hg19, 10-bp bins), from NCBI")
    L.append("Script: reproduction/gse58638/recompute.py, git blob %s" % blob)
    L.append("Pre-registration: PREREG.md sha256 %s" % file_sha("PREREG.md"))
    L.append("                  PREREG-2.md sha256 %s" % file_sha("PREREG-2.md"))
    L.append("Verdict recorded at step 1 (VERDICT-step1.md, sha256 %s): %s, adopted basis %s"
             % (file_sha("VERDICT-step1.md"), VERDICT, ADOPTED))
    L.append("")
    L.append("B1, the adopted basis: 10-bp bins with data, base-weighted, strictly above the threshold")
    L.append("sample      cell    bins with data  bins z>1    bins z>2    z>1 fraction  z>2 fraction")
    for g in order:
        c = counts[g]
        f1, f2 = b1_fractions(c)
        L.append("%-11s %-7s %-15s %-11s %-11s %-13s %s" % (
            g, cell[g], bins(c.bases), bins(c.above1), bins(c.above2), fmt(f1), fmt(f2)))
    L.append("B4, the nearest exact basis (PREREG-2 R4): 10-kb tiles from each chromosome start, exact mean over bases with data")
    L.append("sample      cell    tiles with data tiles z>1   tiles z>2   z>1 fraction  z>2 fraction")
    for g in order:
        c = counts[g]
        f1, f2 = b4_fractions(c)
        L.append("%-11s %-7s %-15d %-11d %-11d %-13s %s" % (
            g, cell[g], c.tiles, c.tiles_above1, c.tiles_above2, fmt(f1), fmt(f2)))
    L.append("Exact counts (bases; one bin is 10 bases):")
    for g in order:
        c = counts[g]
        L.append("  %s bytes=%d %s" % (g, sizes[g], " ".join("%s=%d" % (k, getattr(c, k)) for k in FileCounts.FIELDS)))
    L.append("sha256:")
    for g in order:
        L.append("  %s %s" % (g, digests[g]))
    tot = lambda k: sum(getattr(counts[g], k) for g in order)  # noqa: E731
    nbytes = sum(sizes[g] for g in order)
    L.append("Graded against seen: %d files, %d of %d bytes, %d records, %d NaN, %d +inf, %d -inf, "
             "%d records exactly 1.0, %d exactly 2.0, %d spans not a multiple of 10, 0 refused"
             % (len(order), nbytes, sum(d.size for d in deposits), tot("records"),
                tot("nan_records"), tot("pos_inf"), tot("neg_inf"), tot("exact1"), tot("exact2"),
                tot("not_mult10")))
    L.append("")
    oth = [g for g in order if g != FAILED]
    b1 = {g: b1_fractions(counts[g]) for g in order}
    b4 = {g: b4_fractions(counts[g]) for g in order}
    r1, r4 = b1_ratios(counts), ratios(counts, b4_fractions)
    L.append("Against docs/RESULTS.md (each quotation found exactly once; the relation step 1 recorded: %s, never a match):" % VERDICT)
    L.append("  \"%s\"" % QUOTES["T1"])
    L.append("    %s  B1: %s against %s–%s   B4: %s against %s–%s" % (
        VERDICT, fmt(b1[FAILED][0], 2), fmt(min(b1[g][0] for g in oth), 2), fmt(max(b1[g][0] for g in oth), 2),
        fmt(b4[FAILED][0], 2), fmt(min(b4[g][0] for g in oth), 2), fmt(max(b4[g][0] for g in oth), 2)))
    L.append("  \"%s\"" % QUOTES["T2"])
    L.append("    %s  B1: %s–%s×   B4: %s–%s×" % (
        VERDICT, span_lo(r1[1]), span_hi(r1[1]), span_lo(r4[1]), span_hi(r4[1])))
    defined = all(r is not None for r in r4[1])
    lo1 = round_sig(min(r4[1]), 1) if defined else "inf"
    hi1 = round_sig(max(r4[1]), 1) if defined else "inf"
    L.append("  Recomputed: T2's range %s under B4 at its printed precision (%s\u2013%s\u00d7 at one figure)." % (
        "reproduces" if (lo1, hi1) == ("40", "100") else "does not reproduce", lo1, hi1))
    L.append("  Quoted from step 1, not recomputed: T1's figures reproduce exactly only under pyBigWig's")
    L.append("  approximate 10-kb tile mean (B6), which this script does not implement (PREREG.md P4).")
    lowest = all(min(order, key=lambda g: b1[g][z]) == FAILED and
                 sum(1 for g in order if b1[g][z] == b1[FAILED][z]) == 1 for z in (0, 1))
    L.append("  Under B1, %s has the lowest z>1 and the lowest z>2 fraction of the four: %s" % (FAILED, "yes" if lowest else "NO"))
    diffs = step1_differences(counts)
    L.append("  Against step 1's B1 figures (step1.md, PREREG-2 R3): %d of %d equal at step 1's printed precision%s"
             % (14 - len(diffs), 14, "" if not diffs else "; differs:"))
    for d in diffs:
        L.append("    %s" % d)
    L.append("")
    met = all(r is not None and r >= P6_Z1 for r in r1[0]) and all(r is None or r >= P6_Z2 for r in r1[1])
    L.append("P6 (PREREG.md), stated, never asserted (PREREG-2 R2): IN KIND asked every other/%s ratio" % FAILED)
    L.append("  to be at least %d at z>1 and at least %d at z>2 under B1. Measured (%s):" % (P6_Z1, P6_Z2, " / ".join(oth)))
    L.append("  z>1 %s; z>2 %s. P6's thresholds are %s under B1." % (
        " / ".join(fmt(r, 3) for r in r1[0]), " / ".join(fmt(r, 3) for r in r1[1]), "met" if met else "not met"))
    L.append("")
    c1 = c1_on_b4(counts, deposits)
    L.append("Line 73, context, never a gate (PREREG.md P8; PREREG-2 R4): \"%s\"" % QUOTES["C1"])
    L.append("  B4: DKO1 mean %s; HCT116 mean %s with %s, %s without it." % (
        fmt(c1["dko1_mean"], 2), fmt(c1["hct116_with"], 2), FAILED, fmt(c1["hct116_without"], 2)))
    L.append("  Without %s the deposit-side direction %s on B4 (HCT116 %s against DKO1 %s)." % (
        FAILED, "reverses" if c1["hct116_without"] > c1["dko1_mean"] else "holds",
        fmt(c1["hct116_without"], 2), fmt(c1["dko1_mean"], 2)))
    L.append("  Quoted from step 1, not recomputed: line 73's figures reproduce only under B6, and the direction")
    L.append("  reverses without %s under every tile basis step 1 measured (B4-B7)." % FAILED)
    L.append("")
    L.append("Not recomputed (our pipeline's per-library outputs, not public): FRiP 0.032, peaks per million reads,")
    L.append("28.8 M filtered reads, 2.6% duplication, binned Spearman 0.464. Quoted from docs/RESULTS.md.")
    L.append("")
    return "\n".join(L) + "\n"


def bins(bases):
    return str(bases // 10) if bases % 10 == 0 else "%d.%d" % (bases // 10, bases % 10)


def span_lo(rs):
    # Three significant figures, the precision step 1 printed its ratios at; rounding those again
    # to whole numbers would round twice (43.48 -> 43.5 -> 44).
    return "inf" if any(r is None for r in rs) else round_sig(min(rs), 3)


def span_hi(rs):
    return "inf" if any(r is None for r in rs) else round_sig(max(rs), 3)


def render(counts, sizes, digests, blob, metadata_lines, deposits=DEPOSITS):
    return render_science(counts, sizes, digests, blob, deposits) + \
        METADATA_HEAD + "\n" + "".join(l + "\n" for l in metadata_lines)


def split_report(text):
    text = text.replace("\r\n", "\n")
    i = text.find(METADATA_HEAD + "\n")
    return (text, "") if i < 0 else (text[:i], text[i:])


def parse_counts(report):
    counts = {}
    for m in re.finditer(r"^  (GSM\d+) bytes=\d+ (.*)$", report.replace("\r\n", "\n"), re.M):
        fields = dict(kv.split("=") for kv in m.group(2).split())
        counts[m.group(1)] = FileCounts(**{k: int(fields[k]) for k in FileCounts.FIELDS})
    return counts


def counts_block(report):
    """The report's "Exact counts" line through its last sha256 line, LF."""
    text = report.replace("\r\n", "\n")
    m = re.search(r"^Exact counts .*?^sha256:\n(?:  GSM\d+ [0-9a-f]{64}\n)+", text, re.M | re.S)
    return m.group(0) if m else ""


def parse_pins(report):
    text = report.replace("\r\n", "\n")
    sizes = {m.group(1): int(m.group(2)) for m in re.finditer(r"^  (GSM\d+) bytes=(\d+) ", text, re.M)}
    digests = {m.group(1): m.group(2) for m in re.finditer(r"^  (GSM\d+) ([0-9a-f]{64})$", text, re.M)}
    return sizes, digests


# ---- public metadata (context only; its drift exits 3, never 1) ---------------------------------

def fetch_text(url, opener=urllib.request.urlopen):
    with opener(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def fetch_metadata():
    lines = []
    try:
        rows = fetch_text(SRA_RUNINFO % ",".join(d.srx for d in DEPOSITS)).strip().splitlines()
        head = rows[0].split(",")
        by_gsm = {}
        for row in rows[1:]:
            rec = dict(zip(head, row.split(",")))
            by_gsm[rec["SampleName"]] = rec
        order = sorted(DEPOSITS, key=lambda d: -int(by_gsm[d.gsm]["spots"]))
        rank = [d.gsm for d in order].index(FAILED) + 1
        words = {1: "first", 2: "second", 3: "third", 4: "fourth"}
        lines.append("  raw reads, SRA run info: %s (%s %s of four)" % (
            ", ".join("%s %.1f M" % (d.gsm, int(by_gsm[d.gsm]["spots"]) / 1e6) for d in order),
            FAILED, words[rank]))
        groups = {}
        for d in DEPOSITS:
            rec = by_gsm[d.gsm]
            groups.setdefault((rec["Model"], rec["avgLength"]), []).append(d.gsm)
        lines.append("  instruments, SRA run info: " + "; ".join(
            "%s %s (%s-bp reads)" % (", ".join(g), model, length)
            for (model, length), g in sorted(groups.items(), key=lambda kv: len(kv[1]))))
    except Exception as exc:  # any failure here is context, never science
        lines.append("  SRA run info: could not be fetched (%s)" % exc.__class__.__name__)
    titles, processing = [], None
    for d in DEPOSITS:
        try:
            text = fetch_text(GEO_BRIEF % d.gsm)
            title = re.search(r"^!Sample_title = (.*)$", text, re.M).group(1).strip()
            note = ""
            rep_title = re.search(r"Rep(\d)", title)
            rep_file = re.search(r"_rep(\d)\.", d.filename)
            if rep_file and (not rep_title or rep_title.group(1) != rep_file.group(1)):
                note = " (its file name says rep%s)" % rep_file.group(1)
            titles.append('%s "%s"%s' % (d.gsm, title, note))
            if d.gsm == FAILED:
                for m in re.finditer(r"^!Sample_data_processing = (.*ENCODE.*)$", text, re.M):
                    processing = m.group(1).strip()
        except Exception as exc:
            titles.append("%s could not be fetched (%s)" % (d.gsm, exc.__class__.__name__))
    lines.append("  GEO titles: " + "; ".join(titles))
    if processing is not None:
        lines.append('  GEO, %s data processing: "%s"' % (FAILED, processing))
    else:
        lines.append("  GEO, %s data processing: could not be fetched" % FAILED)
    return lines


# ---- running ------------------------------------------------------------------------------------

@dataclasses.dataclass
class Config:
    deposits: tuple = DEPOSITS
    url_base: str = GEO_BASE
    results_md: Path = ROOT / "docs" / "RESULTS.md"
    expected: Path = HERE / "expected.txt"
    fetch_metadata: object = fetch_metadata
    retry_wait: float = 5.0
    out: object = None
    err: object = None


def default_config():
    return Config()


USAGE = "usage: recompute.py [--from DIR | --check-published]\n"


def main(argv=None, config=None):
    config = config or default_config()
    out = config.out if config.out is not None else sys.stdout.buffer
    err = config.err if config.err is not None else sys.stderr
    argv = sys.argv[1:] if argv is None else argv
    local = None
    if argv == ["--check-published"]:
        return check_published(config, out, err)
    if len(argv) == 2 and argv[0] == "--from":
        local = argv[1]
    elif argv:
        err.write(USAGE)
        return 2
    try:
        quote_lines = check_quotes(config.results_md)
        started = time.time()
        metadata = config.fetch_metadata()
        counts, sizes, digests = {}, {}, {}
        for dep in config.deposits:
            t0 = time.time()
            if local is not None:
                c, n, digest = read_local(dep, local, err)
            else:
                c, n, digest = read_stream(dep, config.url_base, err, config.retry_wait)
            counts[dep.gsm], sizes[dep.gsm], digests[dep.gsm] = c, n, digest
            dt = max(time.time() - t0, 1e-9)
            err.write("  %s: %d bytes, %d records in %.1f s (%.1f MB/s)\n"
                      % (dep.gsm, n, c.records, dt, n / dt / 1e6))
        report = render(counts, sizes, digests, script_blob(), metadata, tuple(config.deposits))
    except Refused as exc:
        err.write("REFUSED: %s\n" % exc)
        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
            err.write("HTTPS certificates are not installed for this Python. On macOS with a python.org "
                      "build, run 'Install Certificates.command' from its Applications folder.\n")
        return 2
    except ScienceDifference as exc:
        err.write("SCIENCE DIFFERENCE: %s\n" % exc)
        return 1
    err.write("  total %.1f s\n" % (time.time() - started))
    out.write(report.encode("utf-8"))
    expected = Path(config.expected)
    if not expected.exists():
        expected.write_bytes(report.encode("utf-8"))
        out.write(("Identical to %s: written by this run (no committed copy was found)\n" % REL_EXPECTED).encode("utf-8"))
        return 0
    want = expected.read_bytes().decode("utf-8").replace("\r\n", "\n")
    if want == report:
        out.write(("Identical to %s: yes\n" % REL_EXPECTED).encode("utf-8"))
        return 0
    got_sci, got_meta = split_report(report)
    want_sci, want_meta = split_report(want)
    if got_sci == want_sci:
        out.write(("Identical to %s: no; only the public-metadata context lines differ, and the "
                   "recomputed science above is unaffected\n" % REL_EXPECTED).encode("utf-8"))
        return 3
    a, b = got_sci.split("\n"), want_sci.split("\n")
    first = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
    out.write(("Identical to %s: no; the recomputed science differs from line %d\n"
               % (REL_EXPECTED, first + 1)).encode("utf-8"))
    return 1


def check_published(config, out, err):
    """The network-free binding: expected.txt is exactly what this committed script renders from the
    counts it records, it names this script's blob, each quotation is in RESULTS.md exactly once, and
    PREREG-2 R1-R4 hold; R5 once the addendum is in RESULTS.md."""
    failures = []
    try:
        expected = Path(config.expected).read_bytes().decode("utf-8").replace("\r\n", "\n")
        quote_lines = check_quotes(config.results_md)
    except (OSError, ScienceDifference) as exc:
        err.write("BINDING FAILED: %s\n" % exc)
        return 1
    counts = parse_counts(expected)
    sizes, digests = parse_pins(expected)
    pins = {d.gsm: d for d in config.deposits}
    if sorted(counts) != sorted(pins) or sorted(sizes) != sorted(pins) or sorted(digests) != sorted(pins):
        err.write("BINDING FAILED: expected.txt does not record all four deposits\n")
        return 1
    for g, d in pins.items():
        if (sizes[g], digests[g]) != (d.size, d.sha256):
            failures.append("%s: expected.txt records %d bytes / %s, pinned %d / %s"
                            % (g, sizes[g], digests[g], d.size, d.sha256))
        if counts[g].records == 0 or counts[g].bases == 0 or counts[g].tiles == 0:
            failures.append("%s: expected.txt records zero records, bases or tiles" % g)
    if failures:
        err.write("".join("BINDING FAILED: %s\n" % f for f in failures))
        return 1
    blob = script_blob()
    if ("git blob %s" % blob) not in expected:
        failures.append("expected.txt does not name this script's blob %s: re-run the command" % blob)
    sci, meta = split_report(expected)
    if hashlib.sha256(counts_block(expected).encode("utf-8")).hexdigest() != COUNTS_SHA256:
        failures.append("the exact counts and sha256 in expected.txt are not the pinned ones "
                        "(COUNTS_SHA256); they are written only by a real run")
    if hashlib.sha256(meta.encode("utf-8")).hexdigest() != METADATA_SHA256:
        failures.append("the public-metadata section of expected.txt is not the pinned one "
                        "(METADATA_SHA256); it is written only by a real run")
    rendered = render_science(counts, sizes, digests, blob, tuple(config.deposits))
    if sci != rendered:
        a, b = rendered.split("\n"), sci.split("\n")
        first = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
        failures.append("expected.txt is not what this script renders from its own counts (line %d)" % (first + 1))
    if "MATCH" in expected or VERDICT not in expected:
        failures.append("the report must state %s and never MATCH (PREREG-2 R1)" % VERDICT)
    # PREREG-2 R3
    b1 = {g: b1_fractions(c) for g, c in counts.items()}
    for z in (0, 1):
        low = min(b1, key=lambda g: b1[g][z])
        if low != FAILED or sum(1 for g in b1 if b1[g][z] == b1[FAILED][z]) != 1:
            failures.append("R3: %s is not alone lowest at z>%d under B1" % (FAILED, z + 1))
    for g, printed in STEP1_B1.items():
        for z, (value, want) in enumerate(zip(b1[g], printed)):
            want = STEP1_B1_DIFFERS.get((g, z), want)
            if round_sig(value, sig_figs(want)) != want:
                failures.append("R3: %s B1 %s != %s" % (g, round_sig(value, sig_figs(want)), want))
    for z in (0, 1):
        for value, want in zip(b1_ratios(counts)[z], STEP1_B1_RATIOS[z]):
            if value is None or round_sig(value, sig_figs(want)) != want:
                failures.append("R3: a B1 ratio at z>%d is not step 1's %s" % (z + 1, want))
    text = read_utf8(config.results_md)
    if find_addendum(text) is not None:
        failures += ["R5: " + f for f in addendum_failures(text, counts, meta)]
        r5 = "bound"
    elif results_md_sha(text) == RESULTS_MD_SHA256:
        r5 = "not applicable: docs/RESULTS.md is as at 37a8d94, before the row 3a addendum"
    else:
        failures.append("R5: docs/RESULTS.md changed since 37a8d94 and no row 3a addendum was found; "
                        "bind the addendum (find_addendum) or, if it has not landed, re-pin RESULTS_MD_SHA256")
        r5 = "unbound"
    if failures:
        err.write("".join("BINDING FAILED: %s\n" % f for f in failures))
        return 1
    out.write(("binding: expected.txt names blob %s and is exactly what it renders from its counts; "
               "quotations T1, T2, C1 found once each (lines %d, %d, %d); relation %s; PREREG-2 R3 holds%s "
               "(graded 4 deposits, %d records); R5 %s\n"
               % (blob, quote_lines["T1"], quote_lines["T2"], quote_lines["C1"], VERDICT,
                  "" if not STEP1_B1_DIFFERS else " except %d named cell%s awaiting a PREREG-3 (%s)" % (
                      len(STEP1_B1_DIFFERS), "" if len(STEP1_B1_DIFFERS) == 1 else "s",
                      ", ".join("%s z>%d" % (g, z + 1) for g, z in sorted(STEP1_B1_DIFFERS))),
                  sum(c.records for c in counts.values()), r5)).encode("utf-8"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
    except urllib.error.URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
            sys.stderr.write("REFUSED: HTTPS certificates are not installed for this Python. On macOS with a "
                             "python.org build, run 'Install Certificates.command' from its Applications folder.\n")
        else:
            sys.stderr.write("REFUSED: network: %s\n" % exc)
        sys.exit(2)
