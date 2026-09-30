#!/usr/bin/env python3
"""Tests for recompute.py: the reader, the counts, the stream, the report and the binding.

Standard library only. Run from anywhere: `python3 reproduction/gse58638/test_recompute.py`.
Nothing here touches the network: the stream tests serve the committed fixtures from a local
HTTP server, and the metadata fetcher is replaced by a function returning fixed lines.

The fixtures are tiny bigWigs written by an independent writer (pyBigWig 0.3.26, libBigWig) from
the committed text sources beside them, and committed as hex text (fixtures/README.md). The text
source is the truth: the reader must return it exactly.
"""
import contextlib
import dataclasses
import hashlib
import http.server
import io
import math
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FIX = HERE / "fixtures"
sys.path.insert(0, str(HERE))

import recompute  # noqa: E402  (red until recompute.py exists)

# The fixtures' own pins: size and sha256 of the decoded bytes, taken when they were written.
FIXPINS = {
    "bedgraph": (11047, "0bb1e859f599da6098e72bb2c2855ea4720dda7bcc3995c711a33c7309d92ab9"),
    "fixedstep": (937, "cbb0887c881f3d7cc2d6be37b388867bc81945ffebee7a82e622d8a465068bb4"),
    "empty": (224, "0de65bc244862849a50b215b9f7d832586a62fa11090e59a854b82f9aefac14a"),
}

# The frozen inputs that ship beside the script, pinned by the lane brief and the step-1 record.
PREREG_SHA256 = "1f1a9d59132e16c815449e7752d29bf1141c2165e87543acf1c3583232eadb12"
PREREG2_SHA256 = "ff779cf98f4084f885559cbe931cd97dfd92992aeda93a70d9867a85c56f28cc"
VERDICT_SHA256 = "059ac970be4d70cb846120b5f2e7df58735c6a5074366b7c0ad2e16e9695daf3"

# The row 3a addendum as glitch-14's plan quotes the approved wording (commit 37b7543, not yet in
# this base). Used only on a temporary copy of RESULTS.md, to exercise PREREG-2 R5's logic now.
ADDENDUM = (
    "Addendum (30 Sep 2026). Re-measured from the deposited z-score tracks (GEO GSE58638) with a "
    "one-command recompute: the deposit-side direction on line 73 (DKO1 0.067 vs HCT116 0.045) "
    "holds only when GSM1420155 is counted; without it the healthy HCT116 deposit scores 0.083 "
    "against DKO1's 0.067. The pipeline-side direction (123 M vs 45.6 M peak bp) is not affected. "
    "GSM1420155 is the second-deepest of the four libraries by raw reads (38.0 M), not the deepest "
    "(lines 89-90 corrected).")

ROLES = (("GSM1415877", "HCT116"), ("GSM1420155", "HCT116"),
         ("GSM1415885", "DKO1"), ("GSM1420162", "DKO1"))


def fixture_bytes(name):
    return bytes.fromhex("".join((FIX / (name + ".bw.hex")).read_text(encoding="ascii").split()))


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def read_source(name):
    """The committed text source: chromosome sizes and records, values through float32."""
    chroms, records = [], []
    for line in (FIX / (name + "_source.tsv")).read_text(encoding="utf-8").splitlines():
        if line.startswith("#chrom\t"):
            _, c, n = line.split("\t")
            chroms.append((c, int(n)))
        elif line and not line.startswith("#"):
            c, s, e, v = line.split("\t")
            records.append((c, int(s), int(e), f32(float(v))))
    return chroms, records


def same_value(a, b):
    return (math.isnan(a) and math.isnan(b)) or a == b


class Oracle(object):
    """A deliberately naive second computation from the text source: per-base expansion and
    exact rationals. It shares no code with recompute.py."""

    def __init__(self, name):
        self.chroms, self.records = read_source(name)
        self.bases = self.above1 = self.above2 = self.nan_bases = 0
        self.nan_records = self.exact1 = self.exact2 = self.not_mult10 = 0
        self.pos_inf = self.neg_inf = 0
        per_base = {c: [None] * n for c, n in self.chroms}
        for c, s, e, v in self.records:
            span = e - s
            if span % 10:
                self.not_mult10 += 1
            if math.isnan(v):
                self.nan_records += 1
                self.nan_bases += span
                continue
            self.bases += span
            self.above1 += span if v > 1.0 else 0
            self.above2 += span if v > 2.0 else 0
            self.exact1 += v == 1.0
            self.exact2 += v == 2.0
            self.pos_inf += v == math.inf
            self.neg_inf += v == -math.inf
            for i in range(s, e):
                per_base[c][i] = v
        self.tiles = self.tiles_above1 = self.tiles_above2 = 0
        for c, n in self.chroms:
            for t in range(0, n, 10000):
                vals = [x for x in per_base[c][t:t + 10000] if x is not None]
                if not vals:
                    continue
                self.tiles += 1
                if math.inf in vals:
                    mean = math.inf
                elif -math.inf in vals:
                    mean = -math.inf
                else:
                    mean = sum(Fraction(x) for x in vals) / len(vals)
                self.tiles_above1 += mean > 1
                self.tiles_above2 += mean > 2


class Workspace(object):
    """A temporary directory holding four fixture deposits under the real GSM names."""

    def __init__(self, names=("bedgraph", "fixedstep", "bedgraph", "fixedstep"), mutate=None):
        self.dir = Path(tempfile.mkdtemp(prefix="gse58638-test-"))
        self.data = self.dir / "data"
        self.data.mkdir()
        self.deposits = []
        for (gsm, cell), name in zip(ROLES, names):
            size, sha = FIXPINS[name]
            filename = "%s_%s.fixture.bw" % (gsm, name)
            body = fixture_bytes(name)
            if mutate and gsm in mutate:
                body = mutate[gsm](body)
            (self.data / filename).write_bytes(body)
            self.deposits.append(recompute.Deposit(
                gsm=gsm, cell=cell, srx="SRX0", path="",
                filename=filename, size=size, sha256=sha))
        self.expected = self.dir / "expected.txt"

    def config(self, **kw):
        base = dict(deposits=tuple(self.deposits), expected=self.expected,
                    fetch_metadata=lambda: ["  fixture metadata line"])
        base.update(kw)
        return dataclasses.replace(recompute.default_config(), **base)

    def close(self):
        shutil.rmtree(str(self.dir), ignore_errors=True)


def run(config, *argv):
    out, err = io.BytesIO(), io.StringIO()
    config = dataclasses.replace(config, out=out, err=err)
    code = recompute.main(list(argv), config)
    return code, out.getvalue().decode("utf-8"), err.getvalue()


# ------------------------------------------------------------------------------------------------
class ReaderTests(unittest.TestCase):

    def check_equals_source(self, name):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / (name + ".bw")
            p.write_bytes(fixture_bytes(name))
            got = recompute.records_of(p)
        _, want = read_source(name)
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            self.assertEqual(g[:3], w[:3])
            self.assertTrue(same_value(g[3], w[3]), (g, w))

    def test_bedgraph_fixture_equals_text_source(self):
        self.check_equals_source("bedgraph")

    def test_fixedstep_fixture_equals_text_source(self):
        self.check_equals_source("fixedstep")

    def test_fixture_spans_several_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.bw"
            p.write_bytes(fixture_bytes("bedgraph"))
            c = recompute.count_path(p)
        self.assertGreaterEqual(c.blocks, 3)
        self.assertEqual(c.blocks, c.data_count)

    def test_last_block_ends_at_index_offset(self):
        # The header's index offset moved one byte past the data: the data section no longer
        # ends exactly where the header says, and the reader refuses rather than guess.
        body = bytearray(fixture_bytes("bedgraph"))
        index = struct.unpack_from("<Q", body, 24)[0]
        struct.pack_into("<Q", body, 24, index + 1)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.bw"
            p.write_bytes(bytes(body))
            with self.assertRaises(recompute.Refused):
                recompute.count_path(p)

    def test_truncated_copy_refuses_exit_2(self):
        ws = Workspace(mutate={"GSM1420155": lambda b: b[:len(b) // 2]})
        try:
            code, out, err = run(ws.config(), "--from", str(ws.data))
        finally:
            ws.close()
        self.assertEqual(code, 2, err)
        self.assertIn("GSM1420155", err)

    def test_bad_magic_refuses_exit_2(self):
        ws = Workspace(mutate={"GSM1415885": lambda b: b"\0\0\0\0" + b[4:]})
        try:
            code, out, err = run(ws.config(), "--from", str(ws.data))
        finally:
            ws.close()
        self.assertEqual(code, 2, err)
        self.assertIn("magic", err)

    def test_zero_records_refuses_exit_2(self):
        ws = Workspace(names=("bedgraph", "fixedstep", "empty", "fixedstep"))
        try:
            code, out, err = run(ws.config(), "--from", str(ws.data))
        finally:
            ws.close()
        self.assertEqual(code, 2, err)
        self.assertIn("zero records", err)


class CountTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.counts, cls.oracle = {}, {}
        for name in ("bedgraph", "fixedstep"):
            p = Path(cls.tmp.name) / (name + ".bw")
            p.write_bytes(fixture_bytes(name))
            cls.counts[name] = recompute.count_path(p)
            cls.oracle[name] = Oracle(name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def both(self):
        for name in ("bedgraph", "fixedstep"):
            yield name, self.counts[name], self.oracle[name]

    def test_thresholds_are_strict(self):
        for name, c, o in self.both():
            self.assertGreater(o.exact1 + o.exact2, 0, "the fixture must hold boundary values")
            self.assertEqual((c.above1, c.above2), (o.above1, o.above2), name)
            self.assertEqual((c.exact1, c.exact2), (o.exact1, o.exact2), name)

    def test_counts_are_base_weighted(self):
        for name, c, o in self.both():
            self.assertEqual(c.bases, o.bases, name)
            self.assertEqual(c.records, len(o.records), name)
        # A record-weighted count would differ on this fixture: chrB's records span 5,000 bases.
        c, o = self.counts["bedgraph"], self.oracle["bedgraph"]
        self.assertNotEqual(c.above1, sum(1 for r in o.records if r[3] > 1.0))

    def test_nan_excluded_and_counted(self):
        for name, c, o in self.both():
            self.assertGreater(o.nan_records, 0)
            self.assertEqual((c.nan_records, c.nan_bases), (o.nan_records, o.nan_bases), name)

    def test_inf_counts_above(self):
        c, o = self.counts["bedgraph"], self.oracle["bedgraph"]
        self.assertEqual((c.pos_inf, c.neg_inf), (o.pos_inf, o.neg_inf))
        self.assertEqual(c.pos_inf, 1)

    def test_spans_not_multiple_of_10_counted(self):
        for name, c, o in self.both():
            self.assertEqual(c.not_mult10, o.not_mult10, name)
        self.assertGreater(self.counts["fixedstep"].not_mult10, 0)

    def test_tiles_equal_the_exact_oracle(self):
        for name, c, o in self.both():
            self.assertEqual((c.tiles, c.tiles_above1, c.tiles_above2),
                             (o.tiles, o.tiles_above1, o.tiles_above2), name)

    def test_graded_against_seen_matches_header(self):
        for name, c, o in self.both():
            self.assertIn(c.header_bases_covered, (c.bases, c.bases + c.nan_bases), name)
            self.assertEqual(sorted(c.per_chrom), sorted(n for n, _ in o.chroms), name)
            self.assertEqual(sum(x.bases for x in c.per_chrom.values()), c.bases, name)
        # A dropped chromosome is caught by the header's own count.
        c = self.counts["bedgraph"]
        dropped = dataclasses.replace(c, bases=c.bases - c.per_chrom["chrB"].bases)
        with self.assertRaises(recompute.Refused):
            recompute.grade_against_seen(dropped, "fixture")


class RefusalTests(unittest.TestCase):
    """Refusals that only a malformed file can reach, driven directly (review r1, F-8)."""

    def counter(self):
        c = recompute.BigWigCounter("synthetic")
        c.chroms = {0: ("chrA", 100), 1: ("chrB", 50)}
        return c

    def test_header_bases_covered_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.bw"
            p.write_bytes(fixture_bytes("bedgraph"))
            c = recompute.count_path(p)
        recompute.grade_against_seen(c, "fixture")          # consistent: passes
        off = dataclasses.replace(c, header_bases_covered=c.header_bases_covered + 10)
        with self.assertRaises(recompute.Refused):
            recompute.grade_against_seen(off, "fixture")     # per-chromosome sum still consistent

    def test_out_of_order_record_refuses(self):
        with self.assertRaises(recompute.Refused):
            self.counter()._records(0, [(0, 10, 1.0), (5, 15, 1.0)])

    def test_record_past_chromosome_end_refuses(self):
        with self.assertRaises(recompute.Refused):
            self.counter()._records(0, [(90, 110, 1.0)])

    def test_empty_record_refuses(self):
        with self.assertRaises(recompute.Refused):
            self.counter()._records(0, [(10, 10, 1.0)])

    def test_chromosome_revisited_refuses(self):
        c = self.counter()
        c._records(0, [(0, 10, 1.0)])
        c._records(1, [(0, 10, 1.0)])
        with self.assertRaises(recompute.Refused):
            c._records(0, [(20, 30, 1.0)])


class RoundingTests(unittest.TestCase):

    def test_round_half_up_on_exact_rational_boundary(self):
        self.assertEqual(recompute.round_sig(Fraction(725, 100000), 2), "0.0073")
        self.assertEqual(recompute.round_sig(Fraction(745, 100000), 2), "0.0075")
        self.assertEqual(recompute.round_sig(Fraction(215, 10), 2), "22")
        self.assertEqual(recompute.round_sig(Fraction(995, 10000), 2), "0.10")
        self.assertEqual(recompute.round_sig(Fraction(2, 1000), 3), "0.00200")
        self.assertEqual(recompute.round_sig(Fraction(10825, 100), 3), "108")
        self.assertEqual(recompute.round_sig(Fraction(724999, 100000000), 2), "0.0072")

    def test_precision_of_a_printed_figure(self):
        self.assertEqual(recompute.sig_figs("0.00200"), 3)
        self.assertEqual(recompute.sig_figs("0.1066"), 4)
        self.assertEqual(recompute.sig_figs("108"), 3)
        self.assertEqual(recompute.sig_figs("21.4"), 3)


class StreamServer(object):
    """Serves a folder over HTTP with Range support; can drop a response mid-body."""

    def __init__(self, folder, drop_after=None, drop_times=1, honour_range=True):
        state = {"drops": 0}
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                p = folder / self.path.lstrip("/").split("/", 1)[-1]
                if not p.is_file():
                    self.send_error(404)
                    return
                body = p.read_bytes()
                start = 0
                rng = self.headers.get("Range")
                if rng and honour_range:
                    start = int(re.match(r"bytes=(\d+)-", rng).group(1))
                    self.send_response(206)
                    self.send_header("Content-Range", "bytes %d-%d/%d" % (start, len(body) - 1, len(body)))
                else:
                    self.send_response(200)
                self.send_header("Content-Length", str(len(body) - start))
                self.end_headers()
                chunk = body[start:]
                if drop_after is not None and state["drops"] < drop_times and len(chunk) > drop_after:
                    state["drops"] += 1
                    self.wfile.write(chunk[:drop_after])
                    self.wfile.flush()
                    self.close_connection = True
                    with contextlib.suppress(OSError):
                        self.connection.shutdown(socket.SHUT_RDWR)
                    return
                self.wfile.write(chunk)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/files" % self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        outer.state = state

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class StreamTests(unittest.TestCase):

    def streamed(self, ws, **server_kw):
        server = StreamServer(ws.data, **server_kw)
        try:
            return run(ws.config(url_base=server.url, retry_wait=0)), server.state
        finally:
            server.close()

    def test_stream_resumes_after_drop(self):
        ws = Workspace()
        try:
            local = run(ws.config(), "--from", str(ws.data))
            ws.expected.unlink()
            (code, out, err), state = self.streamed(ws, drop_after=3001, drop_times=2)
        finally:
            ws.close()
        self.assertEqual(state["drops"], 2)
        self.assertEqual(local[0], 0, local[2])
        self.assertEqual(code, 0, err)
        self.assertEqual(out, local[1], "a resumed stream must give the local report, byte for byte")

    def test_short_read_refuses_exit_2(self):
        ws = Workspace()
        try:
            (code, out, err), state = self.streamed(ws, drop_after=500, drop_times=99, honour_range=False)
        finally:
            ws.close()
        self.assertEqual(code, 2, err)
        self.assertIn("short read", err)
        self.assertNotIn("Identical", out)

    def test_sha_mismatch_exits_1_naming_file(self):
        # One byte flipped in the zoom data after the index: the parse still succeeds, so only
        # the sha256 pin can catch it.
        def flip(b):
            return b[:-1] + bytes([b[-1] ^ 0xFF])
        ws = Workspace(mutate={"GSM1415877": flip})
        try:
            code, out, err = run(ws.config(), "--from", str(ws.data))
        finally:
            ws.close()
        self.assertEqual(code, 1, err)
        self.assertIn("GSM1415877_bedgraph.fixture.bw", err)
        self.assertIn("sha256", err)

    def test_changed_size_exits_1(self):
        ws = Workspace(mutate={"GSM1415885": lambda b: b + b"\0"})
        try:
            code, out, err = run(ws.config(), "--from", str(ws.data))
        finally:
            ws.close()
        self.assertEqual(code, 1, err)
        self.assertIn("GSM1415885", err)


class ReportTests(unittest.TestCase):

    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def test_two_runs_give_identical_reports(self):
        first = run(self.ws.config(), "--from", str(self.ws.data))
        second = run(self.ws.config(), "--from", str(self.ws.data))
        self.assertEqual(first[0], 0, first[2])
        self.assertEqual(second[0], 0, second[2])
        self.assertEqual(first[1].splitlines()[:-1], second[1].splitlines()[:-1])
        self.assertIn("Identical to reproduction/gse58638/expected.txt: yes", second[1])

    def test_expected_is_written_only_by_the_script(self):
        self.assertFalse(self.ws.expected.exists())
        code, out, err = run(self.ws.config(), "--from", str(self.ws.data))
        self.assertEqual(code, 0, err)
        self.assertEqual(self.ws.expected.read_text(encoding="utf-8"),
                         out[:out.rindex("Identical to")])

    def test_report_difference_exits_1(self):
        run(self.ws.config(), "--from", str(self.ws.data))
        text = self.ws.expected.read_text(encoding="utf-8")
        self.ws.expected.write_text(text.replace("records=", "records=1", 1), encoding="utf-8")
        code, out, err = run(self.ws.config(), "--from", str(self.ws.data))
        self.assertEqual(code, 1, err)
        self.assertIn("Identical to reproduction/gse58638/expected.txt: no", out)

    def test_metadata_only_change_exits_3(self):
        run(self.ws.config(), "--from", str(self.ws.data))
        code, out, err = run(self.ws.config(fetch_metadata=lambda: ["  a moved metadata line"]),
                             "--from", str(self.ws.data))
        self.assertEqual(code, 3, err)
        self.assertIn("unaffected", out)

    def test_report_crlf_insensitive(self):
        run(self.ws.config(), "--from", str(self.ws.data))
        text = self.ws.expected.read_bytes()
        self.ws.expected.write_bytes(text.replace(b"\n", b"\r\n"))
        code, out, err = run(self.ws.config(), "--from", str(self.ws.data))
        self.assertEqual(code, 0, err)

    def test_report_says_in_kind_never_match(self):
        code, out, err = run(self.ws.config(), "--from", str(self.ws.data))
        self.assertEqual(code, 0, err)
        self.assertIn("IN KIND", out)
        self.assertNotIn("MATCH", out)
        self.assertIn("adopted basis B1", out)

    def test_unknown_option_refused(self):
        code, out, err = run(self.ws.config(), "--write")
        self.assertEqual(code, 2)


class QuotationTests(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="gse58638-results-"))
        self.text = (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(str(self.dir), ignore_errors=True)

    def copy(self, text):
        p = self.dir / "RESULTS.md"
        p.write_bytes(text.encode("utf-8"))
        return p

    def test_quotations_found_exactly_once(self):
        for q in recompute.QUOTES.values():
            self.assertEqual(self.text.count(q), 1, q)
            recompute.find_once(self.text, q)

    def test_quotation_found_twice_fails(self):
        doubled = self.text + "\n" + recompute.QUOTES["T1"] + "\n"
        with self.assertRaises(recompute.ScienceDifference):
            recompute.check_quotes(self.copy(doubled))

    def test_changed_figure_in_results_md_fails(self):
        moved = self.text.replace("0.0073 of bins", "0.0072 of bins")
        self.assertNotEqual(moved, self.text)
        with self.assertRaises(recompute.ScienceDifference):
            recompute.check_quotes(self.copy(moved))
        moved = self.text.replace("**40–100× below", "**40–90× below")
        with self.assertRaises(recompute.ScienceDifference):
            recompute.check_quotes(self.copy(moved))

    def test_quotes_are_byte_exact_pre_registered_targets(self):
        prereg = (HERE / "PREREG.md").read_text(encoding="utf-8")
        self.assertIn("`%s`" % recompute.QUOTES["T1"], prereg)
        self.assertIn("`%s`" % recompute.QUOTES["T2"], prereg)
        self.assertIn("`%s`" % recompute.QUOTES["C1"], prereg)

    @unittest.skipIf(os.name == "nt", "the C locale is a POSIX device; Windows CI reads cp1252 anyway")
    def test_results_md_read_as_utf8(self):
        env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONCOERCECLOCALE="0", PYTHONUTF8="0")
        env.pop("PYTHONIOENCODING", None)
        r = subprocess.run([sys.executable, "-X", "utf8=0", str(HERE / "recompute.py"), "--check-published"],
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))


class FrozenInputTests(unittest.TestCase):

    def sha(self, name):
        return hashlib.sha256((HERE / name).read_bytes()).hexdigest()

    def test_prereg_is_the_frozen_file(self):
        self.assertEqual(self.sha("PREREG.md"), PREREG_SHA256)

    def test_prereg2_is_the_dated_rule(self):
        self.assertEqual(self.sha("PREREG-2.md"), PREREG2_SHA256)

    def test_step1_verdict_is_the_frozen_record(self):
        self.assertEqual(self.sha("VERDICT-step1.md"), VERDICT_SHA256)

    def test_fixture_pins(self):
        for name, (size, sha) in FIXPINS.items():
            b = fixture_bytes(name)
            self.assertEqual((len(b), hashlib.sha256(b).hexdigest()), (size, sha), name)

    def test_folder_gitattributes_keep_lf(self):
        text = (HERE / ".gitattributes").read_text(encoding="utf-8")
        for rule in ("*.py text eol=lf", "*.md text eol=lf", "*.txt text eol=lf", "*.tsv text eol=lf",
                     "*.hex text eol=lf"):
            self.assertIn(rule, text)


class PublishedBindingTests(unittest.TestCase):
    """The binding CI runs on every push: network-free, against the committed expected.txt."""

    @classmethod
    def setUpClass(cls):
        cls.expected = (HERE / "expected.txt").read_text(encoding="utf-8")
        cls.counts = recompute.parse_counts(cls.expected)

    def test_results_md_figures_equal_the_recompute(self):
        # The site's claim test. Never skips: under the recorded IN KIND verdict it asserts that
        # each quotation is found exactly once, the report is exactly what the committed script
        # renders from its own counts, and the relation printed is IN KIND (PREREG-2 R1, R3).
        code, out, err = run(recompute.default_config(), "--check-published")
        self.assertEqual(code, 0, err + out)
        self.assertIn("IN KIND", self.expected)
        self.assertNotIn("MATCH", self.expected)

    def test_expected_names_the_committed_script(self):
        m = re.search(r"git blob ([0-9a-f]{40})", self.expected)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), recompute.script_blob())
        if shutil.which("git"):
            r = subprocess.run(["git", "hash-object", "--path", "reproduction/gse58638/recompute.py",
                                str(HERE / "recompute.py")], cwd=str(ROOT),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if r.returncode == 0:
                self.assertEqual(r.stdout.decode().strip(), m.group(1))

    def test_failed_library_lowest_on_b1(self):
        # PREREG-2 R3, first half.
        f = {g: recompute.b1_fractions(c) for g, c in self.counts.items()}
        for z in (0, 1):
            low = min(f, key=lambda g: f[g][z])
            self.assertEqual(low, "GSM1420155")
            self.assertEqual(sum(1 for g in f if f[g][z] == f[low][z]), 1)

    def test_b1_equals_step1_at_its_printed_precision(self):
        # PREREG-2 R3, second half: step1.md §5's B1 row and the VERDICT's ratios. One cell is held
        # to the recompute's own figure and named (STEP1_B1_DIFFERS): step 1 printed 0.00200 for a
        # value of 0.0020050; the report prints that difference, and this test requires it printed.
        self.assertEqual(recompute.STEP1_B1_DIFFERS, {("GSM1420155", 1): "0.00201"})
        for gsm, printed in recompute.STEP1_B1.items():
            got = recompute.b1_fractions(self.counts[gsm])
            for z, (value, want) in enumerate(zip(got, printed)):
                want = recompute.STEP1_B1_DIFFERS.get((gsm, z), want)
                self.assertEqual(recompute.round_sig(value, recompute.sig_figs(want)), want, gsm)
        self.assertIn("13 of 14 equal at step 1's printed precision; differs:", self.expected)
        self.assertIn("GSM1420155 z>2 fraction: step 1 printed 0.00200, the exact recompute is 0.00201",
                      self.expected)
        ratios = recompute.b1_ratios(self.counts)
        for z, printed in ((0, recompute.STEP1_B1_RATIOS[0]), (1, recompute.STEP1_B1_RATIOS[1])):
            for value, want in zip(ratios[z], printed):
                self.assertEqual(recompute.round_sig(value, recompute.sig_figs(want)), want)

    def test_b4_equals_prereg2_r4(self):
        # PREREG-2 R4's B4 figures at their printed precision. Its z>2 ratio range "44-108x" is
        # step 1's 43.5 rounded a second time; the exact ratio is 2435/56 = 43.48, so the lower
        # end is bound at step 1's three figures (43.5) and never at a twice-rounded 44.
        want = recompute.PREREG2_R4
        f = {g: recompute.b4_fractions(c) for g, c in self.counts.items()}
        others = [g for g in f if g != "GSM1420155"]
        self.assertEqual(recompute.round_sig(f["GSM1420155"][0], 2), want["failed_z1"])
        self.assertEqual(recompute.round_sig(min(f[g][0] for g in others), 2), want["others_z1"][0])
        self.assertEqual(recompute.round_sig(max(f[g][0] for g in others), 2), want["others_z1"][1])
        r = [f[g][1] / f["GSM1420155"][1] for g in others]
        self.assertEqual(recompute.round_sig(min(r), 3), "43.5")
        self.assertEqual(recompute.round_sig(max(r), 3), want["ratios_z2"][1])
        self.assertIn("B4: 43.5\u2013108\u00d7", self.expected)
        c1 = recompute.c1_on_b4(self.counts)
        self.assertEqual(recompute.round_sig(c1["dko1_mean"], 2), want["c1_dko1"])
        self.assertEqual(recompute.round_sig(c1["hct116_with"], 2), want["c1_hct116_with"])
        self.assertEqual(recompute.round_sig(c1["hct116_without"], 2), want["c1_hct116_without"])

    def check_copy(self, expected=None, results=None):
        d = Path(tempfile.mkdtemp(prefix="gse58638-bind-"))
        try:
            e, r = d / "expected.txt", d / "RESULTS.md"
            e.write_bytes((expected if expected is not None else self.expected).encode("utf-8"))
            r.write_bytes((results if results is not None else
                           (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")).encode("utf-8"))
            return run(dataclasses.replace(recompute.default_config(), expected=e, results_md=r),
                       "--check-published")
        finally:
            shutil.rmtree(str(d), ignore_errors=True)

    def test_unplanted_copy_binds(self):
        code, out, err = self.check_copy()
        self.assertEqual(code, 0, err)

    def test_planted_metadata_line_fails(self):
        # Review r1, F-1: the metadata section is pinned too.
        moved = self.expected.replace("GSM1420155 38.0 M", "GSM1420155 99.9 M")
        self.assertNotEqual(moved, self.expected)
        code, out, err = self.check_copy(expected=moved)
        self.assertEqual(code, 1)
        self.assertIn("public-metadata section", err)

    def test_consistent_forgery_of_the_counts_fails(self):
        # Review r3, F-1: counts changed and the report re-rendered by the script's own renderer,
        # metadata kept, so the forgery is internally consistent; the counts pin still catches it.
        counts = dict(self.counts)
        c = counts["GSM1415877"]
        counts["GSM1415877"] = dataclasses.replace(c, tiles_above2=c.tiles_above2 + 1)
        sizes, digests = recompute.parse_pins(self.expected)
        meta = recompute.split_report(self.expected)[1]
        forged = recompute.render_science(counts, sizes, digests, recompute.script_blob()) + meta
        self.assertNotEqual(forged, self.expected)
        code, out, err = self.check_copy(expected=forged)
        self.assertEqual(code, 1)
        self.assertIn("COUNTS_SHA256", err)
        self.assertNotIn("not what this script renders", err)

    def test_changed_results_md_without_addendum_fails(self):
        # Review r1, F-5: an addendum the detector misses must not leave R5 skipped for good.
        text = (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")
        code, out, err = self.check_copy(results=text + "\nAn unrelated added line.\n")
        self.assertEqual(code, 1)
        self.assertIn("RESULTS_MD_SHA256", err)

    def test_p6_is_printed_not_asserted(self):
        # PREREG-2 R2: stated, with the measured ratios, and said plainly not to be met.
        self.assertIn("P6", self.expected)
        self.assertIn("not met under B1", self.expected)

    def test_addendum_binding(self):
        # PREREG-2 R5 on the real RESULTS.md. Skips, with its reason, only until the addendum
        # is in the base; the logic itself runs now in AddendumLogicTests.
        text = (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")
        if recompute.find_addendum(text) is None:
            # Skips only while RESULTS.md is exactly as at 37a8d94; any other RESULTS.md without a
            # detected addendum fails the binding (test_changed_results_md_without_addendum_fails).
            self.assertEqual(recompute.results_md_sha(text), recompute.RESULTS_MD_SHA256)
            self.skipTest("PREREG-2 R5: the row 3a addendum (37b7543) is not in docs/RESULTS.md at "
                          "this base (37a8d94); the orchestrator rebases onto it at home")
        meta = recompute.split_report(self.expected)[1]
        self.assertEqual(recompute.addendum_failures(text, self.counts, meta), [])


class AddendumLogicTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")
        expected = (HERE / "expected.txt").read_text(encoding="utf-8")
        cls.counts = recompute.parse_counts(expected)
        cls.meta = recompute.split_report(expected)[1]

    def failures(self, addendum, counts=None):
        return recompute.addendum_failures(self.with_addendum(addendum), counts or self.counts, self.meta)

    def with_addendum(self, addendum):
        lines = self.text.split("\n")
        return "\n".join(lines[:94] + ["", addendum, ""] + lines[94:])

    def test_addendum_as_approved_binds(self):
        self.assertEqual(self.failures(ADDENDUM), [])

    def test_addendum_with_a_moved_figure_fails(self):
        moved = ADDENDUM.replace("scores 0.083", "scores 0.084")
        self.assertNotEqual(self.failures(moved), [])

    def test_addendum_quoting_other_than_line_73_fails(self):
        moved = ADDENDUM.replace("(DKO1 0.067 vs HCT116 0.045)", "(DKO1 0.068 vs HCT116 0.045)")
        self.assertNotEqual(self.failures(moved), [])

    def test_addendum_with_an_unbound_figure_fails(self):
        # Review r1, F-6: every decimal is the bound B4 figure, line 73's, or printed metadata.
        moved = ADDENDUM.replace("against DKO1's 0.067", "against DKO1's 0.099")
        self.assertNotEqual(self.failures(moved), [])

    def test_addendum_denying_the_reversal_fails(self):
        # Review r2, F-3: the addendum must state the reversal, not merely coexist with it.
        moved = ADDENDUM.replace(
            "holds only when GSM1420155 is counted; without it the healthy HCT116 deposit scores 0.083 "
            "against DKO1's 0.067",
            "holds with or without GSM1420155; without it the healthy HCT116 deposit scores 0.083, "
            "still below DKO1")
        self.assertNotEqual(moved, ADDENDUM)
        self.assertNotEqual(self.failures(moved), [])

    def test_line_73_figure_as_a_recompute_output_fails(self):
        # Review r2, F-4: 0.067 and 0.045 only as quotations of line 73, never as recompute outputs.
        moved = ADDENDUM.replace("against DKO1's 0.067.",
                                 "against DKO1's 0.067, and the recompute reproduces line 73's 0.067 exactly.")
        self.assertNotEqual(moved, ADDENDUM)
        self.assertNotEqual(self.failures(moved), [])

    def test_line_73_figures_restated_as_recompute_outputs_fail(self):
        # Review r4, F-3: the three wordings that bound green before.
        for extra in ("The recompute reproduces DKO1's 0.067 on exact tiles.",
                      "The recompute gives (DKO1 0.067 vs HCT116 0.045) exactly.",
                      "GSM1420155's z>1 fraction is 38.0 times lower."):
            moved = ADDENDUM + " " + extra
            self.assertNotEqual(self.failures(moved), [], extra)

    def test_addendum_found_whatever_its_heading(self):
        for head in ("Addendum, 30 Sep 2026.", "**Addendum (1 Oct 2026).**"):
            body = ADDENDUM.replace("Addendum (30 Sep 2026).", head)
            self.assertIsNotNone(recompute.find_addendum(self.with_addendum(body)), head)
        self.assertIsNone(recompute.find_addendum(self.text))

    def test_addendum_reversal_must_hold_on_b4(self):
        # DKO1's mean raised above the healthy HCT116 deposit; the addendum's 0.083 still equals
        # the recompute, so only the reversal can make this fail.
        c = dict(self.counts)
        dko = c["GSM1415885"]
        c["GSM1415885"] = dataclasses.replace(dko, tiles_above1=dko.tiles // 5)
        self.assertNotEqual(self.failures(ADDENDUM, c), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
