#!/usr/bin/env python3
"""box/scan_record.scan_with_witness: the per-file transformation witness, on planted fake values only.

The witness binds each scanned file's original bytes to its published (masked) bytes: {schema, original_sha256,
published_sha256, original_bytes, published_bytes, replacements: [{start, end, kind, replacement_id}]}. Offsets are
absolute bytes in the original, end exclusive; spans are nonempty, disjoint and increasing; replacement_id is fixed by
the pinned marker map for the kind; an unchanged file carries an empty list. The existing scan result (masked events,
counts, refusals, file hashes) is unchanged. No real login, no process start: every value below is obviously fake.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDY)

from box import scan_record as sr  # noqa: E402

TOKEN = "FAKEVALUE-0123456789abcdef-PLANTED"
KEY = "FAKEKEY-fedcba9876543210-PLANTED-TOO"
EMAIL = "planted.person@example.invalid"
INNER = "FAKEVALUE-0123456789abcdef"            # a token value that sits inside TOKEN (longest-needle selection)
SECRETS = [("token", TOKEN), ("key", KEY), ("email", EMAIL)]
WITNESS_FIELDS = {"schema", "original_sha256", "published_sha256", "original_bytes", "published_bytes",
                  "replacements"}


def no_findings(paths):
    return []


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def rebuild(original: bytes, replacements) -> bytes:
    """An independent verifier: the published bytes from the original and the witness alone."""
    out, at = [], 0
    for r in replacements:
        out += [original[at:r["start"]], sr.replacement_marker(r["replacement_id"])]
        at = r["end"]
    out.append(original[at:])
    return b"".join(out)


def check_witness(tc, w, original: bytes, published: bytes):
    tc.assertEqual(set(w), WITNESS_FIELDS)
    tc.assertEqual(w["schema"], 1)
    tc.assertEqual(w["original_sha256"], sha(original))
    tc.assertEqual(w["published_sha256"], sha(published))
    tc.assertEqual(w["original_bytes"], len(original))
    tc.assertEqual(w["published_bytes"], len(published))
    prev_end = 0
    for r in w["replacements"]:
        tc.assertEqual(set(r), {"start", "end", "kind", "replacement_id"})
        tc.assertLess(r["start"], r["end"])                       # nonempty
        tc.assertGreaterEqual(r["start"], prev_end)               # disjoint and increasing
        tc.assertEqual(r["replacement_id"], sr.REPLACEMENT_IDS[r["kind"]])
        prev_end = r["end"]
    tc.assertEqual(rebuild(original, w["replacements"]), published)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def put(self, name: str, data: bytes) -> str:
        p = os.path.join(self.tmp.name, name)
        with open(p, "wb") as fh:
            fh.write(data)
        return p


class WitnessShape(Base):
    def test_masked_file_spans_are_absolute_original_offsets(self):
        original = (b"first line, nothing here\n"
                    + json.dumps({"t": TOKEN, "e": EMAIL}).encode() + b"\n"
                    + b"tail " + KEY.encode() + b" and " + TOKEN.encode())
        p = self.put("t.jsonl", original)
        result, witness = sr.scan_with_witness([(p, "stream")], SECRETS, rules_scanner=no_findings)
        with open(p, "rb") as fh:
            published = fh.read()
        w = witness[p]
        check_witness(self, w, original, published)
        self.assertEqual(len(w["replacements"]), 4)
        for r in w["replacements"]:
            value = {"token": TOKEN, "key": KEY, "email": EMAIL}[r["kind"]].encode()
            self.assertEqual(original[r["start"]:r["end"]], value)
        self.assertEqual(result["events"], 4)
        self.assertEqual(len(result["masked"]), result["events"])

    def test_unchanged_and_refused_files_have_empty_replacements(self):
        clean = self.put("clean.jsonl", b"nothing to see\n")
        refused_data = b"ledger " + TOKEN.encode() + b"\n"
        ledger = self.put("ledger.json", refused_data)
        session_file = self.put("s.jsonl", b'{"a": "' + TOKEN.encode() + b'"}\n')   # stays valid: masked
        result, witness = sr.scan_with_witness([(clean, "transcript"), (ledger, "ledger"), (session_file, "session")],
                                               SECRETS, rules_scanner=no_findings)
        self.assertEqual(set(witness), {clean, ledger, session_file})
        self.assertEqual(witness[clean]["replacements"], [])
        self.assertEqual(witness[ledger]["replacements"], [])
        check_witness(self, witness[ledger], refused_data, refused_data)
        self.assertEqual(witness[clean]["original_sha256"], witness[clean]["published_sha256"])
        self.assertTrue(result["refused"])

    def test_json_invalidating_mask_records_no_span(self):
        # A JSON line whose masking would make it invalid is refused, unmasked: no replacement is recorded.
        original = b'"' + TOKEN.encode() + b'"\n'
        with mock.patch.dict(sr.MARKERS, {"token": '"'}):
            p = self.put("x.jsonl", original)
            result, witness = sr.scan_with_witness([(p, "stream")], SECRETS, rules_scanner=no_findings)
        self.assertTrue(any("JSON" in r["why"] for r in result["refused"]))
        self.assertEqual(witness[p]["replacements"], [])
        check_witness(self, witness[p], original, original)

    def test_longest_needle_selection_is_unchanged(self):
        secrets = SECRETS + [("token", INNER)]
        original = b"a " + TOKEN.encode() + b" b " + INNER.encode() + b"-x\n"
        p = self.put("l.jsonl", original)
        result, witness = sr.scan_with_witness([(p, "transcript")], secrets, rules_scanner=no_findings)
        spans = [(r["start"], r["end"]) for r in witness[p]["replacements"]]
        a = original.index(TOKEN.encode())
        b = original.index(INNER.encode(), a + len(TOKEN))
        self.assertEqual(spans, [(a, a + len(TOKEN)), (b, b + len(INNER))])
        self.assertEqual(result["events"], 2)

    def test_witness_carries_no_secret_value(self):
        original = b"x " + TOKEN.encode() + b" " + EMAIL.encode() + b" " + KEY.encode() + b"\n"
        p = self.put("n.jsonl", original)
        _, witness = sr.scan_with_witness([(p, "transcript")], SECRETS, rules_scanner=no_findings)
        text = json.dumps(witness)
        for v in (TOKEN, KEY, EMAIL):
            self.assertNotIn(v, text)
            self.assertNotIn(sha(v.encode()), text)

    def test_replacement_ids_are_fixed_and_closed(self):
        # Pinned literally: the ids are a published contract a verifier checks against, not derived at run time.
        self.assertEqual(sr.REPLACEMENT_IDS, {"token": "mask-token-v1", "key": "mask-key-v1",
                                              "email": "mask-email-v1"})
        self.assertEqual(set(sr.REPLACEMENT_IDS), set(sr.SECRET_KINDS))
        self.assertEqual(len(set(sr.REPLACEMENT_IDS.values())), len(sr.SECRET_KINDS))
        for kind, rid in sr.REPLACEMENT_IDS.items():
            self.assertEqual(sr.replacement_marker(rid), sr.MARKERS[kind].encode("utf-8"))
        with self.assertRaises(sr.ScanError):
            sr.replacement_marker("arbitrary-bytes")


class SharedCore(Base):
    def _pair(self, data: bytes, kind: str):
        a, b = self.put("a.jsonl", data), self.put("b.jsonl", data)
        r1 = sr.scan([(a, kind)], SECRETS, rules_scanner=no_findings)
        r2, _ = sr.scan_with_witness([(b, kind)], SECRETS, rules_scanner=no_findings)
        for r in (r1, r2):
            for item in r["masked"] + r["refused"]:
                item["path"] = os.path.basename(item["path"])
            for item in r["files"]:
                item["path"] = os.path.basename(item["path"])
        r1["files"][0]["path"] = r2["files"][0]["path"] = "f"
        for item in r1["masked"] + r1["refused"] + r2["masked"] + r2["refused"]:
            item["path"] = "f"
        return r1, r2

    def test_scan_result_identical_with_and_without_witness(self):
        data = (b"one " + TOKEN.encode() + b"\n" + json.dumps({"k": KEY}).encode() + b"\nlast " + EMAIL.encode())
        for kind in ("transcript", "stream", "session", "ledger"):
            r1, r2 = self._pair(data, kind)
            self.assertEqual(r1, r2, kind)
            self.assertEqual(set(r1), set(sr.RESULT_FIELDS))

    def test_scan_error_writes_nothing_and_returns_no_witness(self):
        original = b"z " + TOKEN.encode() + b"\n"
        p = self.put("e.jsonl", original)
        with mock.patch.object(sr, "_survived", lambda after, needles: True):
            with self.assertRaises(sr.ScanError):
                sr.scan_with_witness([(p, "transcript")], SECRETS, rules_scanner=no_findings)
        with open(p, "rb") as fh:
            self.assertEqual(fh.read(), original)

    def test_core_refuses_a_witness_that_does_not_rebuild(self):
        # Fail closed: if the recorded spans would not rebuild the published bytes, nothing is written.
        original = b"q " + TOKEN.encode() + b"\n"
        p = self.put("r.jsonl", original)
        real = sr._line_offsets
        with mock.patch.object(sr, "_line_offsets", lambda data: [o + 1 for o in real(data)]):
            with self.assertRaises(sr.ScanError):
                sr.scan_with_witness([(p, "transcript")], SECRETS, rules_scanner=no_findings)
        with open(p, "rb") as fh:
            self.assertEqual(fh.read(), original)

    def test_witness_guard_alone_stops_a_surviving_value(self):
        # With the survival check removed, a mask that leaves the value in place is still refused by the rebuild
        # check, and nothing is written.
        original = b"s " + TOKEN.encode() + b"\n"
        p = self.put("v.jsonl", original)
        with mock.patch.object(sr, "_mask", lambda line, spans: line + b" "), \
                mock.patch.object(sr, "_survived", lambda after, needles: False):
            with self.assertRaisesRegex(sr.ScanError, "rebuild"):
                sr.scan([(p, "transcript")], SECRETS, rules_scanner=no_findings)
        with open(p, "rb") as fh:
            self.assertEqual(fh.read(), original)


if __name__ == "__main__":
    unittest.main()
