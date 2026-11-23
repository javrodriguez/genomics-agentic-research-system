#!/usr/bin/env python3
"""test_image.py: the box images' locks (box/image_lock.py) and their Dockerfiles, driven with no runtime at all.

Nothing here builds an image or runs a container: `build_argv` is only constructed, and a module-level guard
(interface 10) makes every process start and every signal raise for the whole module, armed by setUpModule. Before
it, at import, the module starts git only: the one read of round 3's leak words (interface 16), and the lock writer's
re-derivation of every committed lock from the committed build record (glitch-06's post-write ruling, 14 Oct 2026).

The committed locks are the reviewed pins (schema 2): each must be byte-equal to what ops/write_image_lock.py's
plan() re-derives from lane-reports/build-20261014c/athena-out-20261014/build-record.json at HEAD (PIN_MUTANTS: a
hand-edited digest, another row's pin, an unfilled lock, each red). Every PENDING behaviour is driven on a synthetic
schema-1 lock made from a committed lock with its filled fields re-PENDINGed (`unfilled`).

Every guard is also shown red: each lock clause by a mutated lock (MUTANT_LOCKS), each label rule by a mutated
inspect (MUTANT_INSPECTS). Run alone, the module first prints every mutant with its red run, then runs the tests.
"""

from __future__ import annotations

import copy
import inspect as pyinspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
# Round 3's done commit (copy_manifest.SOURCE_COMMIT), where its leak words are read.
ROUND3 = "e2979b3143081824aadea73523ec41af30c1ddb1"
# The lane lead's additions to round 3's leak words (interface 16).
ADDED_LEAK_WORDS = ("gap4", "round 4", "sidecar", "watcher", "evidence", "holdout", "sealed", "probe", "trap",
                    "grader")


def _round3_leak_words() -> tuple:
    """Round 3's `leak_words`, read once with git show (the only process this module starts), never written down."""
    out = subprocess.run(["git", "-C", REPO, "show", f"{ROUND3}:evals/gap-study-3/prereg.json"],
                         capture_output=True, text=True, check=True).stdout
    words = json.loads(out)["leak_words"]
    if not words or not all(isinstance(w, str) and w for w in words):
        raise AssertionError("round 3's leak_words is not a non-empty list of words")
    return tuple(words)


LEAK_WORDS = _round3_leak_words() + ADDED_LEAK_WORDS


# Interface 10: from here on no test can start a process or signal one.
def _blocked(*_a, **_k):
    raise AssertionError("process start or signal blocked in the box tests")


_GUARDED = [(subprocess, "run"), (subprocess, "Popen")]
_GUARDED += [(os, n) for n in ("system", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork") if hasattr(os, n)]
_GUARDED += [(os, n) for n in sorted(dir(os)) if n.startswith(("exec", "spawn")) and callable(getattr(os, n))]
_PATCHERS = [mock.patch.object(_mod, _name, _blocked) for _mod, _name in _GUARDED]


def setUpModule():
    """Arm the guard for every test of this module (the wave 4 merge's fix: never at import, because test_round4
    imports every test module in one process and an import-time guard would trip in the others)."""
    for patcher in _PATCHERS:
        patcher.start()


def tearDownModule():
    for patcher in reversed(_PATCHERS):
        patcher.stop()

import harness_bookkeeping as hb  # noqa: E402
from box import image_lock as il  # noqa: E402
from box.egress import proxy_conf as pc  # noqa: E402

LOCK_PATHS = {image: os.path.join(il.BOX_DIR, os.path.dirname(df), "image.lock")
              for image, df in il.DOCKERFILES.items()}
# The fields an unfilled (schema-1) lock holds PENDING, as the locks did before the reviewed write; `unfilled`
# re-PENDINGs exactly these on a committed lock.
UNFILLED_PENDING = {
    "take-a": ("base", "harness.version", "python", "image_id"),
    "take-o": ("base", "harness.version", "python", "image_id"),
    "take-g": ("base", "harness.version", "python", "image_id"),
    "sidecar": ("base", "python", "image_id"),
    "egress": ("base", "image_id", "squid"),
}
# Each take image's npm package, built from the seam's harness names (imported, never typed here).
PACKAGES = {
    "take-a": "@anthropic-ai/" + hb.CLAUDE_CODE,
    "take-o": "@openai/" + pc.CODEX,
    "take-g": "@google/" + pc.GEMINI + "-cli",
}

BASE = "registry.example/fake-base@sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


def committed(image: str) -> dict:
    return il.load(LOCK_PATHS[image])


def unfilled(image: str) -> dict:
    """A synthetic unfilled (schema-1) lock: the committed lock with its schema-2 fields removed and each field of
    UNFILLED_PENDING PENDING again, each with a reason. Never written to a lock path."""
    lock = {k: v for k, v in copy.deepcopy(committed(image)).items() if k not in il.SCHEMA_2_KEYS}
    lock["schema"] = il.SCHEMA
    for field in UNFILLED_PENDING[image]:
        head, _, tail = field.partition(".")
        if tail:
            lock[head][tail] = il.PENDING
        else:
            lock[head] = il.PENDING
    lock["pending"] = {f: "synthetic: re-PENDINGed from the committed lock" for f in UNFILLED_PENDING[image]}
    return il.validate(lock)


# The reviewed pins (glitch-06's post-write ruling, 14 Oct 2026): the lock writer re-derives each committed lock from
# the committed build record, here at import (git, before the guard), never from a hand-copied value.
import hashlib  # noqa: E402
import importlib.util  # noqa: E402

RECORD = os.path.join(REPO, "lane-reports", "build-20261014c", "athena-out-20261014", "build-record.json")
RECORD_SHA256 = "c55c75cc7bffea5c202a19bc25e1a9f8490e4c22975e6248486008b96bd65914"
_WSPEC = importlib.util.spec_from_file_location("write_image_lock_for_test_image",
                                                os.path.join(REPO, "ops", "write_image_lock.py"))
WRITER = importlib.util.module_from_spec(_WSPEC)
_WSPEC.loader.exec_module(WRITER)


def _rederived() -> dict:
    out = {}
    for image in il.IMAGES:
        try:
            out[image] = WRITER.rederive(il, REPO, RECORD, LOCK_PATHS[image], image)
        except (WRITER.Refused, il.LockError, ValueError, OSError, subprocess.TimeoutExpired) as e:   # closure C-2
            out[image] = f"refused: {type(e).__name__}: {e}"
    return out


REDERIVED = _rederived()


def pin_problems(texts: dict) -> list:
    """Every way the lock files' bytes (`texts`: image -> bytes) are not the reviewed pins ([] when they are)."""
    out = []
    for image in il.IMAGES:
        want, got = REDERIVED.get(image), texts.get(image)
        if not isinstance(want, bytes):
            out.append(f"{image}: the lock writer does not re-derive it ({want})")
            continue
        try:
            schema = json.loads(got).get("schema")
        except (TypeError, ValueError, AttributeError):
            schema = None
        if schema != il.SCHEMA_2:
            out.append(f"{image}: the committed lock is not schema {il.SCHEMA_2}")
        if got != want:
            out.append(f"{image}: the committed lock is not the lock writer's re-derivation from the record")
    return out


def committed_texts() -> dict:
    out = {}
    for image in il.IMAGES:
        with open(LOCK_PATHS[image], "rb") as fh:
            out[image] = fh.read()
    return out


def _another_rows_pin(texts: dict) -> dict:
    """take-a's lock carrying take-o's record row's digests: a pin from another row."""
    with open(RECORD, encoding="utf-8") as fh:
        row = [r for r in json.load(fh)["images"] if r["image"] == "take-o"][0]
    lock = json.loads(texts["take-a"])
    lock.update({k: row[k] for k in ("image_id", "manifest_digest", "config_digest")})
    return dict(texts, **{"take-a": WRITER.lock_text(lock).encode()})


def _one_digest_edited(texts: dict) -> dict:
    lock = json.loads(texts["take-a"])
    d = lock["manifest_digest"]
    lock["manifest_digest"] = d[:-1] + ("0" if d[-1] != "0" else "1")
    return dict(texts, **{"take-a": WRITER.lock_text(lock).encode()})


PIN_MUTANTS = {
    "a lock hand-edited by one digest": _one_digest_edited,
    "a lock from a different record row": _another_rows_pin,
    "a schema-1 PENDING lock where a filled one is required":
        lambda texts: dict(texts, **{"sidecar": WRITER.lock_text(unfilled("sidecar")).encode()}),
}


MANIFEST_DIGEST, CONFIG_DIGEST, SOURCE_COMMIT = "sha256:" + "c" * 64, "sha256:" + "d" * 64, "e" * 40


def filled(image: str = "take-a") -> dict:
    """The committed lock with every PENDING value replaced by an obviously fake pinned value: a schema-2 lock, as
    the lock writer fills it (glitch-06's rulings, 14 Oct 2026)."""
    lock = copy.deepcopy(committed(image))
    lock.update(schema=il.SCHEMA_2, manifest_digest=MANIFEST_DIGEST, config_digest=CONFIG_DIGEST,
                source_commit=SOURCE_COMMIT)
    lock["base"] = BASE
    lock["image_id"] = IMAGE_ID
    if lock["harness"] is not None:
        lock["harness"]["version"] = "9.8.7"
    if lock["python"] is not None:
        lock["python"] = "3.12.99"
    if "squid" in lock:
        lock["squid"] = "6.99-1+fake1"
    lock["pending"] = {}
    return lock


def build_input(image: str = "take-a") -> dict:
    """A build's input: the unfilled schema-1 lock with every build input pinned and image_id still PENDING."""
    lock = filled(image)
    for k in il.SCHEMA_2_KEYS:
        del lock[k]
    lock["schema"] = il.SCHEMA
    lock["image_id"] = il.PENDING
    lock["pending"] = {"image_id": "the build makes it"}
    return lock


def matching_inspect(lock: dict) -> dict:
    return {"Id": lock["image_id"], "Config": {"Labels": il.expected_labels(lock)}}


def _set(path, value):
    def f(lock):
        node = lock
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
    return f


def _drop(path):
    def f(lock):
        node = lock
        for k in path[:-1]:
            node = node[k]
        del node[path[-1]]
    return f


# Each schema clause, mutated on a filled take-a lock: every one must be refused (interface 3).
MUTANT_LOCKS = {
    "an unknown key": _set(("extra",), 1),
    "a missing key (base)": _drop(("base",)),
    "a missing key (pending)": _drop(("pending",)),
    "a missing key (users)": _drop(("users",)),
    "schema 3": _set(("schema",), 3),
    "a filled schema-1 lock": _set(("schema",), 1),
    "schema 2 without its manifest digest": _drop(("manifest_digest",)),
    "schema 2 without its config digest": _drop(("config_digest",)),
    "schema 2 without its source commit": _drop(("source_commit",)),
    "a pending manifest digest": _set(("manifest_digest",), il.PENDING),
    "a manifest digest without its algorithm": _set(("manifest_digest",), "c" * 64),
    "a short config digest": _set(("config_digest",), "sha256:" + "d" * 63),
    "a source commit by branch name": _set(("source_commit",), "main"),
    "a short source commit": _set(("source_commit",), "e" * 7),
    "a schema-2 lock with a pending field": _set(("python",), il.PENDING),
    "schema as a bool": _set(("schema",), True),
    "an unknown image": _set(("image",), "take-z"),
    "the wrong dockerfile": _set(("dockerfile",), "codex/Dockerfile"),
    "a base by tag": _set(("base",), "registry.example/fake-base:latest"),
    "a base with a tag and a digest": _set(("base",), "registry.example/fake-base:9@sha256:" + "a" * 64),
    "a base with a parent-folder name": _set(("base",), "../fake-base@sha256:" + "a" * 64),
    "a base with a leading dash": _set(("base",), "-/fake-base@sha256:" + "a" * 64),
    "another image's harness package": _set(("harness", "package"), "@openai/" + pc.CODEX),
    "a short base digest": _set(("base",), "registry.example/fake-base@sha256:" + "a" * 63),
    "a harness version with a range": _set(("harness", "version"), "^9.8.7"),
    "a harness version with a tag": _set(("harness", "version"), "latest"),
    "a harness with an extra key": _set(("harness", "channel"), "stable"),
    "a harness package not scoped": _set(("harness", "package"), "plainname"),
    "python 3 with two parts": _set(("python",), "3.12"),
    "python under the floor": _set(("python",), "3.10.14"),
    "an image id without its algorithm": _set(("image_id",), "b" * 64),
    "harness null on a take image": _set(("harness",), None),
    "python null on a take image": _set(("python",), None),
    "users null on a take image": _set(("users",), None),
    "a squid key on a take image": _set(("squid",), "6.99-1"),
    "the agent's uid moved": _set(("users", "agent", "uid"), 10004),
    "the agent's gid not its uid": _set(("users", "agent", "gid"), 10002),
    "the watcher's uid moved": _set(("users", "watcher", "uid"), 10001),
    "the watcher's gid not its uid": _set(("users", "watcher", "gid"), 10001),
    "the keep-alive uid moved": _set(("users", "keepalive", "uid"), 10001),
    "the keep-alive gid not its uid": _set(("users", "keepalive", "gid"), 0),
    "a named keep-alive": _set(("users", "keepalive", "name"), "kim"),
    "an agent with no gid": _drop(("users", "agent", "gid")),
    "a uid as a string": _set(("users", "agent", "uid"), "10001"),
    "a user name with a space": _set(("users", "agent", "name"), "da na"),
    "root as a user name": _set(("users", "agent", "name"), "root"),
    "a base's own user name": _set(("users", "watcher", "name"), "node"),
    "one name for both users": _set(("users", "watcher", "name"), "dana"),
    "a fourth user": _set(("users", "other"), {"uid": 10004, "gid": 10004}),
    "a pending field pending does not explain": _set(("base",), il.PENDING),
    "a pending reason for a filled field": _set(("pending", "base"), "still to come"),
    "an empty pending reason": lambda lock: (lock.update(python=il.PENDING), lock["pending"].update(python=" ")),
    "a pending map that is a list": _set(("pending",), []),
}


def mutated(name: str) -> dict:
    lock = filled("take-a")
    MUTANT_LOCKS[name](lock)
    return lock


# Each label rule, mutated on the inspect of a filled lock: every one must be refused.
def _inspect_mutants() -> dict:
    def label(key, value):
        def f(ins):
            ins["Config"]["Labels"][key] = value
        return f

    def drop(key):
        def f(ins):
            del ins["Config"]["Labels"][key]
        return f

    out = {f"label {k} differs": label(k, "0.0.0-other") for k in il.LABELS
           if k in il.expected_labels(filled("take-a"))}
    out.update({f"label {k} missing": drop(k) for k in il.expected_labels(filled("take-a"))})
    out["an extra label"] = label("app.other", "x")
    out["a squid label on a take image"] = label(il.SQUID_LABEL, "6.99-1")
    out["the Id differs"] = lambda ins: ins.update(Id="sha256:" + "c" * 64)
    out["no Id"] = lambda ins: ins.pop("Id")
    out["no labels at all"] = lambda ins: ins["Config"].update(Labels=None)
    out["no Config"] = lambda ins: ins.pop("Config")
    return out


MUTANT_INSPECTS = _inspect_mutants()


def inspect_mutated(name: str) -> dict:
    ins = matching_inspect(filled("take-a"))
    MUTANT_INSPECTS[name](ins)
    return ins


class GuardTest(unittest.TestCase):
    def test_the_guard_starts_no_patch_at_import(self):
        # Recorded at the very end of this module's import: no guarded name was patched then.
        self.assertEqual(_PATCHED_AT_IMPORT, [])
        # And the same record, taken now inside a test, holds every guarded name (setUpModule armed them), so the
        # record can see a patch. The mutant that starts the guard at import is a whole-file swap (lane report).
        self.assertEqual(len(_patched_now()), len(_GUARDED))

    def test_the_process_guard_is_armed(self):
        self.assertEqual(len(_patched_now()), len(_GUARDED))
        with self.assertRaises(AssertionError):
            subprocess.run(["true"])
        with self.assertRaises(AssertionError):
            subprocess.Popen(["true"])
        with self.assertRaises(AssertionError):
            os.kill(0, 0)
        with self.assertRaises(AssertionError):
            os.system("true")
        self.assertIn((os, "execv"), _GUARDED)
        self.assertIn((os, "posix_spawn"), _GUARDED)

    def test_the_leak_words_were_read(self):
        self.assertGreater(len(LEAK_WORDS), len(ADDED_LEAK_WORDS))

    def test_module_is_this_rounds(self):
        self.assertTrue(os.path.abspath(il.__file__).startswith(os.path.join(HERE, "box") + os.sep))
        self.assertFalse(os.path.exists(os.path.join(il.BOX_DIR, "__init__.py")))   # a namespace package


class LockSchemaTest(unittest.TestCase):
    def test_the_committed_locks_are_the_reviewed_pins(self):
        """Every committed lock is schema 2 and byte-equal to the lock writer's re-derivation from the committed
        build record, whose sha256 is the reviewed record's."""
        with open(RECORD, "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), RECORD_SHA256)
        self.assertEqual(pin_problems(committed_texts()), [])
        for image in il.IMAGES:
            with self.subTest(image):
                self.assertTrue(il.ready(committed(image)))

    def test_every_pin_mutant_goes_red(self):
        for name, mutate in PIN_MUTANTS.items():
            with self.subTest(name):
                texts = mutate(committed_texts())
                self.assertNotEqual(texts, committed_texts(), f"{name}: the mutant changed nothing")
                self.assertTrue(pin_problems(texts), name)

    def test_the_unfilled_locks_load_with_their_exact_pending_sets(self):
        for image, want in UNFILLED_PENDING.items():
            with self.subTest(image):
                lock = unfilled(image)
                self.assertEqual(lock["image"], image)
                self.assertEqual(il.pending(lock), want)
                self.assertEqual(tuple(lock["pending"]), want)
                self.assertFalse(il.ready(lock))

    def test_the_committed_users_and_their_names(self):
        for image in UNFILLED_PENDING:
            users = committed(image)["users"]
            if users is None:
                continue
            self.assertEqual(users["agent"], {"name": "dana", "uid": 10001, "gid": 10001})
            self.assertEqual(users["watcher"], {"name": "eli", "uid": 10002, "gid": 10002})
            self.assertEqual(users["keepalive"], {"uid": 10003, "gid": 10003})

    def test_a_filled_lock_is_valid_and_ready(self):
        lock = filled("take-a")
        self.assertEqual(il.problems(lock), [])
        self.assertTrue(il.ready(lock))
        self.assertIs(il.require_ready(lock), lock)

    def test_every_schema_mutant_is_refused(self):
        for name in MUTANT_LOCKS:
            with self.subTest(name):
                lock = mutated(name)
                self.assertTrue(il.problems(lock), name)
                with self.assertRaises(il.LockError):
                    il.validate(lock)
                self.assertTrue(il.check_labels(lock, matching_inspect(filled("take-a"))))

    def test_a_duplicate_key_in_a_lock_file_is_refused(self):
        with self.assertRaises(il.LockError):
            il._no_duplicates([("base", 1), ("base", 2)])
        # Through load (fold 3, W4A1-4 b): the unfilled take-a lock with its `base` line written twice, at a path
        # where it sits beside its Dockerfile (BOX_DIR patched), so only the duplicate can refuse it.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "image.lock")
            text = WRITER.lock_text(unfilled("take-a"))
            text = text.replace('"base": "PENDING",', '"base": "PENDING",\n  "base": "PENDING",', 1)
            self.assertEqual(text.count('"base": "PENDING"'), 2)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            with mock.patch.object(il, "BOX_DIR", tmp):
                with self.assertRaises(il.LockError) as cm:
                    il.load(path)
                self.assertIn("duplicate key 'base'", str(cm.exception))
                # The mutant without the hook loads the file silently.
                with mock.patch.object(il, "_no_duplicates", dict):
                    self.assertEqual(il.load(path)["image"], "take-a")

    def test_a_lock_not_beside_its_dockerfile_is_refused(self):
        # Fold 3, W4A1-4 c: the committed take-a lock, copied byte for byte to a folder with no Dockerfile of its own.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "image.lock")
            shutil.copyfile(LOCK_PATHS["take-a"], path)
            with self.assertRaises(il.LockError) as cm:
                il.load(path)
            self.assertIn("is not the Dockerfile beside", str(cm.exception))
            # The same bytes at their own path load.
            self.assertEqual(il.load(LOCK_PATHS["take-a"]), json.loads(open(path, encoding="utf-8").read()))

    def test_require_ready_names_every_pending_field(self):
        with self.assertRaises(il.NotReady) as cm:
            il.require_ready(unfilled("take-a"))
        for field in UNFILLED_PENDING["take-a"]:
            self.assertIn(field, str(cm.exception))

    def test_a_dropped_refusal_goes_red(self):
        lock = unfilled("take-a")
        with mock.patch.object(il, "_pending_fields", lambda lock: []), \
                mock.patch.object(il, "problems", lambda lock: []):
            self.assertTrue(il.ready(lock))   # the mutant waves the unfilled lock through
        self.assertFalse(il.ready(lock))

    def test_the_fixed_ids(self):
        self.assertEqual((il.AGENT_UID, il.WATCHER_UID, il.KEEPALIVE_UID), (10001, 10002, 10003))
        for const, field, role in (("AGENT_UID", "uid", "agent"), ("WATCHER_UID", "uid", "watcher"),
                                   ("KEEPALIVE_UID", "uid", "keepalive")):
            lock = filled("take-a")
            with self.subTest(const), mock.patch.object(il, const, getattr(il, const) + 7):
                self.assertTrue(il.problems(lock))


class LabelsTest(unittest.TestCase):
    def test_a_filled_lock_against_its_matching_inspect_passes(self):
        lock = filled("take-a")
        self.assertEqual(il.check_labels(lock, matching_inspect(lock)), [])
        self.assertEqual(set(il.expected_labels(lock)),
                         {il.BASE_NAME_LABEL, il.BASE_DIGEST_LABEL, il.CLI_LABEL, il.PYTHON_LABEL})
        self.assertEqual(il.expected_labels(lock)[il.BASE_DIGEST_LABEL], "sha256:" + "a" * 64)
        self.assertEqual(il.expected_labels(lock)[il.BASE_NAME_LABEL], "registry.example/fake-base")

    def test_the_unfilled_lock_is_refused_whatever_the_labels_say(self):
        lock = unfilled("take-a")
        ins = matching_inspect(filled("take-a"))
        found = il.check_labels(lock, ins)
        self.assertEqual(len(found), len(UNFILLED_PENDING["take-a"]))
        self.assertTrue(all(p.startswith("lock refused") for p in found))
        # Even an inspect that carries the literal PENDING values is refused.
        ins = {"Id": il.PENDING, "Config": {"Labels": {k: il.PENDING for k in il.LABELS}}}
        self.assertTrue(il.check_labels(lock, ins))

    def test_every_inspect_mutant_is_refused(self):
        lock = filled("take-a")
        for name in MUTANT_INSPECTS:
            with self.subTest(name):
                self.assertTrue(il.check_labels(lock, inspect_mutated(name)), name)

    def test_the_label_keys_are_a_closed_tuple(self):
        self.assertEqual(il.LABELS, ("org.opencontainers.image.base.name", "org.opencontainers.image.base.digest",
                                     "app.cli.version", "app.python.version", "app.squid.version"))
        self.assertEqual(set(il.LABEL_ARGS), set(il.LABELS))
        lock = filled("take-a")
        ins = matching_inspect(lock)
        for k in il.LABELS:
            with self.subTest(k), mock.patch.object(il, "LABELS", tuple(x for x in il.LABELS if x != k)):
                if k in ins["Config"]["Labels"]:
                    self.assertTrue(il.check_labels(lock, ins))   # a dropped label key goes red

    def test_no_parameter_can_override_a_pending_value(self):
        # The public API takes a lock (validated) and an inspect or a context; no parameter carries a pinned value.
        sigs = {n: list(pyinspect.signature(getattr(il, n)).parameters) for n in
                ("load", "pending", "ready", "require_ready", "expected_labels", "check_labels", "build_argv",
                 "build_args", "validate", "problems")}
        self.assertEqual(sigs["check_labels"], ["lock", "inspect"])
        self.assertEqual(sigs["build_argv"], ["lock", "context"])
        for n in ("pending", "ready", "require_ready", "expected_labels", "build_args", "validate", "problems"):
            self.assertEqual(sigs[n], ["lock"], n)
        self.assertEqual(sigs["load"], ["path"])


def dockerfile(image: str) -> str:
    with open(os.path.join(il.BOX_DIR, il.DOCKERFILES[image]), encoding="utf-8") as fh:
        return fh.read()


# Each Dockerfile rule, mutated in the text of one committed Dockerfile: every one must make check_dockerfile red.
# (image, old text, new text); `old` must occur in that file.
NPM_A = 'npm install -g "' + PACKAGES["take-a"] + '@${HARNESS_VERSION}"'
CHECK_A = il.VERSION_CHECK.format(package=PACKAGES["take-a"])
MUTANT_DOCKERFILES = {
    # 1. the base, by digest from the lock
    "FROM a tag": ("take-a", "FROM ${BASE}", "FROM node:22"),
    "ARG BASE with a default": ("take-a", "ARG BASE\n", "ARG BASE=node:22\n"),
    "a second stage": ("take-a", "ENTRYPOINT []", "FROM ${BASE}\nENTRYPOINT []"),
    "an instruction before FROM": ("take-a", "ARG BASE\nFROM", "ARG BASE\nARG BASE_NAME\nFROM"),
    "an extra build argument": ("take-a", "ARG PYTHON_VERSION\n", "ARG PYTHON_VERSION\nARG EXTRA\n"),
    "a build argument missing": ("take-a", "ARG BASE_DIGEST\n", ""),
    # 2. the harness at the exact version, and the installed-version check
    "the harness unpinned": ("take-a", NPM_A, NPM_A.replace("${HARNESS_VERSION}", "latest")),
    "the harness at a range": ("take-a", NPM_A, NPM_A.replace("@${HARNESS_VERSION}", "@^${HARNESS_VERSION}")),
    "another vendor's harness": ("take-a", NPM_A, NPM_A.replace(PACKAGES["take-a"], PACKAGES["take-o"])),
    "a second npm install": ("take-a", "ENV DISABLE", "RUN npm install -g left-pad\nENV DISABLE"),
    "no installed-version check": ("take-a", "RUN " + CHECK_A + "\n", ""),
    "the version check before the install": ("take-a", "RUN " + NPM_A + "\nRUN " + CHECK_A,
                                              "RUN " + CHECK_A + "\nRUN " + NPM_A),
    "the version check against a literal": ("take-a", "RUN " + CHECK_A, "RUN " + CHECK_A.replace(
        '= "${HARNESS_VERSION}"', '= "9.8.7"')),
    # 3. the recorded Python
    "no Python check": ("take-a", "RUN " + il.PYTHON_CHECK + "\n", ""),
    "a Python check on a prefix": ("take-a", il.PYTHON_CHECK, il.PYTHON_CHECK.replace(" = ", " =~ ")),
    "bytecode writing on": ("take-a", "PYTHONDONTWRITEBYTECODE=1", "PYTHONDONTWRITEBYTECODE=0"),
    "no bytecode switch": ("take-a", "ENV PYTHONDONTWRITEBYTECODE=1\n", ""),
    "no autoupdater switch": ("take-a", "ENV DISABLE_AUTOUPDATER=1\n", ""),
    "the autoupdater switch off": ("take-a", "DISABLE_AUTOUPDATER=1", "DISABLE_AUTOUPDATER=0"),
    "an extra ENV": ("take-o", "LABEL org.opencontainers.image.base.name", "ENV MODE=x\nLABEL "
                     "org.opencontainers.image.base.name"),
    "ENV with two names": ("take-a", "ENV DISABLE_AUTOUPDATER=1", "ENV DISABLE_AUTOUPDATER=1 X=1"),
    # 4. the closed package line
    "curl added": ("take-a", "procps ca-certificates", "procps ca-certificates curl"),
    "a container client added": ("take-g", "procps ca-certificates", "procps ca-certificates docker.io"),
    "a network tool added": ("take-o", "procps ca-certificates", "procps ca-certificates netcat-openbsd"),
    "inotify-tools dropped": ("take-a", " inotify-tools", ""),
    "procps dropped": ("take-a", " procps", ""),
    "recommends allowed": ("take-a", "-y --no-install-recommends", "-y"),
    "a second apt-get install": ("take-a", "ENV DISABLE", "RUN apt-get install -y --no-install-recommends nano\n"
                                 "ENV DISABLE"),
    "apt install": ("take-a", "ENV DISABLE", "RUN apt install -y nano\nENV DISABLE"),
    "a fetch in a RUN": ("take-a", "ENV DISABLE", "RUN wget -q -O /tmp/x http://example.invalid/\nENV DISABLE"),
    "pip in a RUN": ("take-a", "ENV DISABLE", "RUN pip install x\nENV DISABLE"),
    # 5. the two users, no privilege helper
    "sudo": ("take-a", "ENV DISABLE", "RUN apt-get -y remove x && sudo true\nENV DISABLE"),
    "a setuid bit": ("take-a", "ENV DISABLE", "RUN chmod u+s /usr/bin/find\nENV DISABLE"),
    "a setuid mode": ("take-a", "ENV DISABLE", "RUN chmod 4755 /usr/bin/find\nENV DISABLE"),
    "the agent's uid moved": ("take-a", "--uid 10001", "--uid 10004"),
    "the agent's gid moved": ("take-a", "useradd --uid 10001 --gid 10001", "useradd --uid 10001 --gid 10002"),
    "the agent's group moved": ("take-a", "groupadd --gid 10001", "groupadd --gid 10005"),
    "the agent renamed": ("take-a", "/home/dana --shell /bin/bash dana", "/home/dana --shell /bin/bash dan"),
    "the agent's home elsewhere": ("take-a", "--home-dir /home/dana", "--home-dir /root"),
    "the watcher's uid moved": ("take-a", "--uid 10002", "--uid 10003"),
    "no watcher": ("take-a", " \\\n && groupadd --gid 10002 eli \\\n && useradd --uid 10002 --gid 10002 "
                   "--no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin eli", ""),
    "a keep-alive user": ("take-a", "RUN git config", "RUN useradd --uid 10003 --gid 10003 kim\nRUN git config"),
    "a non-unique uid": ("take-a", "useradd --uid 10001", "useradd --non-unique --uid 10001"),
    "a user in an extra group": ("take-a", "useradd --uid 10001", "useradd --groups staff --uid 10001"),
    "the last USER root": ("take-a", "USER 10001:10001", "USER root"),
    "a USER after the agent": ("take-a", "USER 10001:10001", "USER 10001:10001\nUSER 0"),
    "no USER": ("take-a", "USER 10001:10001\n", ""),
    "the last USER the watcher": ("take-o", "USER 10001:10001", "USER 10002:10002"),
    # the reviewer's GREEN probes (review round 1): a RUN outside the closed sequence, each red
    "npm i of another version": ("take-a", "ENV DISABLE", 'RUN npm i -g "' + PACKAGES["take-a"] + '@latest"\nENV DISABLE'),
    "npm update": ("take-a", "ENV DISABLE", "RUN npm update -g " + PACKAGES["take-a"] + "\nENV DISABLE"),
    "npm add": ("take-a", "ENV DISABLE", "RUN npm add -g left-pad\nENV DISABLE"),
    "npx": ("take-a", "ENV DISABLE", "RUN npx -y some-tool\nENV DISABLE"),
    "yarn global add": ("take-a", "ENV DISABLE", "RUN yarn global add left-pad\nENV DISABLE"),
    "npm i in the sidecar": ("sidecar", "ENTRYPOINT []", "RUN npm i -g " + PACKAGES["take-a"] + "\nENTRYPOINT []"),
    "npm i in egress": ("egress", "ENTRYPOINT []", "RUN npm i -g x\nENTRYPOINT []"),
    "apt-get -y install": ("take-a", "ENV DISABLE", "RUN apt-get -y install vim-tiny\nENV DISABLE"),
    "apt-get with options before install": ("take-a", "ENV DISABLE", "RUN apt-get update && apt-get -y "
                                            "--no-install-recommends install perl\nENV DISABLE"),
    "egress apt-get -y install": ("egress", "ENTRYPOINT []", "RUN apt-get -y install perl\nENTRYPOINT []"),
    "usermod to uid 0": ("take-a", "ENV DISABLE", "RUN usermod -o -u 0 dana\nENV DISABLE"),
    "usermod into root's group": ("take-a", "ENV DISABLE", "RUN usermod -aG root dana\nENV DISABLE"),
    "a passwd line appended": ("take-a", "ENV DISABLE", "RUN echo 'x::0:0::/:/bin/sh' >> /etc/passwd\nENV DISABLE"),
    "a sudoers drop-in": ("take-a", "ENV DISABLE", "RUN echo 'dana ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/x\n"
                          "ENV DISABLE"),
    "a setuid mode with a leading zero": ("take-a", "ENV DISABLE", "RUN chmod 04755 /usr/bin/find\nENV DISABLE"),
    "a setuid bit by =": ("take-a", "ENV DISABLE", "RUN chmod u=rwxs /usr/bin/find\nENV DISABLE"),
    "install -m 4755": ("take-a", "ENV DISABLE", "RUN install -m 4755 /usr/bin/find /usr/local/bin/f\nENV DISABLE"),
    "adduser": ("take-a", "ENV DISABLE", "RUN adduser --disabled-password kim\nENV DISABLE"),
    "a world-writable passwd": ("take-a", "ENV DISABLE", "RUN chmod 777 /etc/passwd\nENV DISABLE"),
    "safe.directory unset later": ("take-a", "ENV DISABLE", "RUN git config --system --unset-all safe.directory\n"
                                   "ENV DISABLE"),
    "python3 replaced after its check": ("take-a", "ENV DISABLE", "RUN ln -sf /usr/bin/true /usr/bin/python3\n"
                                         "ENV DISABLE"),
    "a git setting holding a word": ("take-a", "ENV DISABLE", "RUN git config --system user.name kim\nENV DISABLE"),
    "python in egress": ("egress", "ENTRYPOINT []", "RUN python3 -V\nENTRYPOINT []"),
    "the watcher with a login shell": ("take-a", "--shell /usr/sbin/nologin eli", "--shell /bin/bash eli"),
    "the watcher with a home": ("take-a", "--no-create-home --home-dir /nonexistent", "--create-home --home-dir /home/eli"),
    # 6. git's ownership
    "no safe.directory": ("take-a", "RUN " + il.GIT_SAFE + "\n", ""),
    "a narrower safe.directory": ("take-a", "safe.directory '*'", "safe.directory /srv"),
    # 7. nothing of the study in a take image
    "a COPY": ("take-a", "ENTRYPOINT []", "COPY x /x\nENTRYPOINT []"),
    "an ADD": ("take-g", "ENTRYPOINT []", "ADD x /x\nENTRYPOINT []"),
    "no ENTRYPOINT reset": ("take-a", "ENTRYPOINT []\n", ""),
    "an ENTRYPOINT": ("take-a", "ENTRYPOINT []", 'ENTRYPOINT ["sh"]'),
    "a CMD": ("take-a", "ENTRYPOINT []", "ENTRYPOINT []\nCMD [\"sh\"]"),
    "a WORKDIR": ("take-a", "ENTRYPOINT []", "WORKDIR /srv\nENTRYPOINT []"),
    # 9. the labels, from the build arguments
    "a label from a literal": ("take-a", 'app.cli.version="${HARNESS_VERSION}"', 'app.cli.version="9.8.7"'),
    "a label from the wrong argument": ("take-a", 'app.cli.version="${HARNESS_VERSION}"',
                                        'app.cli.version="${PYTHON_VERSION}"'),
    "a label missing": ("take-a", 'LABEL app.python.version="${PYTHON_VERSION}"\n', ""),
    "an extra label": ("take-a", "ENTRYPOINT []", 'LABEL app.extra="${BASE}"\nENTRYPOINT []'),
    "a label key renamed": ("take-g", "org.opencontainers.image.base.digest", "org.example.base.digest"),
    "two keys in one LABEL": ("take-a", 'LABEL app.python.version="${PYTHON_VERSION}"',
                              'LABEL app.python.version="${PYTHON_VERSION}" app.x="${BASE}"'),
    # the parser refuses what it does not read
    "an unknown instruction": ("take-a", "ENTRYPOINT []", "FROB x\nENTRYPOINT []"),
    "a heredoc": ("take-a", "ENTRYPOINT []", "RUN <<EOT\ntrue\nEOT\nENTRYPOINT []"),
    # Fold 3 (W4A1-1): BuildKit joins a continuation with no separator, so a check split as `"$(..)"\` / `=\` /
    # `"${V}"` runs as `test "$(..)"="${V}"`, one non-empty word, always true. Both must be refused.
    "P1a the Python check split around its =": ("take-a", "RUN " + il.PYTHON_CHECK, "RUN " + il.PYTHON_CHECK.replace(
        " = ", "\\\n=\\\n")),
    "P1b the installed-version check split around its =": ("take-a", "RUN " + CHECK_A, "RUN " + CHECK_A.replace(
        " = ", "\\\n=\\\n")),
    "a continuation joined inside a word": ("take-a", "RUN " + il.GIT_SAFE, "RUN " + il.GIT_SAFE.replace(
        "--system", "--sys\\\n  tem")),
    "a parser directive": ("take-a", "# The arm A", "# escape=`\n# The arm A"),
    "a continuation off the end": ("take-a", "USER 10001:10001\n", "USER 10001:10001 \\\n"),
    # the sidecar image
    "the sidecar copies nothing": ("sidecar", "COPY sidecar.py /opt/w/sidecar.py\n", ""),
    "the sidecar program elsewhere": ("sidecar", "COPY sidecar.py /opt/w/sidecar.py", "COPY sidecar.py /opt/w/other.py"),
    "the sidecar copies twice": ("sidecar", "COPY sidecar.py /opt/w/sidecar.py",
                                 "COPY sidecar.py /opt/w/sidecar.py\nCOPY . /opt/w/"),
    "a harness in the sidecar": ("sidecar", "ENTRYPOINT []", "RUN npm install -g x\nENTRYPOINT []"),
    "the sidecar's last USER the agent": ("sidecar", "USER 10002:10002", "USER 10001:10001"),
    "the sidecar's last USER root": ("sidecar", "USER 10002:10002", "USER 0:0"),
    "no inotify-tools in the sidecar": ("sidecar", " inotify-tools", ""),
    # the egress image
    "squid unpinned": ("egress", '"squid=${SQUID_VERSION}"', "squid"),
    "egress FROM a tag": ("egress", "FROM ${BASE}", "FROM debian:13"),
    "egress copies a file": ("egress", "ENTRYPOINT []", "COPY proxy.conf /etc/squid/squid.conf\nENTRYPOINT []"),
    "egress with curl": ("egress", '"squid=${SQUID_VERSION}"', '"squid=${SQUID_VERSION}" curl'),
    "egress sets a USER": ("egress", "ENTRYPOINT []", "ENTRYPOINT []\nUSER proxy"),
    "egress without its squid label": ("egress", 'LABEL app.squid.version="${SQUID_VERSION}"\n', ""),
    "egress with a CMD": ("egress", "ENTRYPOINT []", "ENTRYPOINT []\nCMD [\"squid\"]"),
}


def dockerfile_mutated(name: str) -> tuple:
    image, old, new = MUTANT_DOCKERFILES[name]
    text = dockerfile(image)
    at = text.find(old)
    if at < 0:
        raise AssertionError(f"mutant {name!r}: {old!r} is not in {image}'s Dockerfile")
    line = text[text.rfind("\n", 0, at) + 1:].split("\n", 1)[0]
    if line.lstrip().startswith("#") and name not in COMMENT_MUTANTS:
        raise AssertionError(f"mutant {name!r} edits a comment, not an instruction")
    return image, text[:at] + new + text[at + len(old):]


# The one mutant that is meant to edit a comment line (a parser directive is written as a comment).
COMMENT_MUTANTS = {"a parser directive"}


# Each nullability row of NULLABLE, broken on a filled lock of that image (interface 15 schema, per image).
MUTANT_NULLABLE = {
    "sidecar with a harness": ("sidecar", _set(("harness",), {"package": "@x/y", "version": "1.2.3"})),
    "sidecar with python null": ("sidecar", _set(("python",), None)),
    "sidecar with users null": ("sidecar", _set(("users",), None)),
    "egress with a harness": ("egress", _set(("harness",), {"package": "@x/y", "version": "1.2.3"})),
    "egress with users": ("egress", lambda lock: lock.update(users=copy.deepcopy(committed("take-a")["users"]))),
    "egress without squid": ("egress", _drop(("squid",))),
    "egress with a squid range": ("egress", _set(("squid",), ">=6")),
    "egress with a bare squid major": ("egress", _set(("squid",), "6")),
    "egress with a pinned python": ("egress", _set(("python",), "3.12.1")),
    "take-g with the arm A package": ("take-g", _set(("harness", "package"), PACKAGES["take-a"])),
    "take-o with harness null": ("take-o", _set(("harness",), None)),
    "take-g with users null": ("take-g", _set(("users",), None)),
    "take-o with python null": ("take-o", _set(("python",), None)),
}


def nullable_mutated(name: str) -> dict:
    image, f = MUTANT_NULLABLE[name]
    lock = filled(image)
    f(lock)
    return lock


PATH_RE = re.compile(r"(?<![\w$}])/[A-Za-z0-9_.@*/-]+")


def agent_visible(image: str) -> dict:
    """The strings of a take image the agent can read: every path, label key and ENV line, and its user names."""
    ins = il.parse_dockerfile(dockerfile(image))
    out = {"paths": [], "label keys": [], "env": [], "users": [], "instructions": [i.args for i in ins]}
    for i in ins:
        if i.keyword in ("RUN", "COPY", "USER"):
            out["paths"] += PATH_RE.findall(i.args)
        if i.keyword == "LABEL":
            out["label keys"].append(i.args.split("=", 1)[0])
        if i.keyword == "ENV":
            out["env"] += i.args.split("=", 1)
    out["users"] = user_names(image)
    return out


def user_names(image: str) -> list:
    lock = committed(image)
    names = [] if lock["users"] is None else [lock["users"][r]["name"] for r in ("agent", "watcher")]
    users, _ = il._users([i.args for i in il.parse_dockerfile(dockerfile(image)) if i.keyword == "RUN"])
    return names + [u[0] for u in users]


# The sidecar and egress images' own paths and labels are exempt (never in a take image, never mounted in the take
# container), for example the pinned /opt/w/sidecar.py; their user names are not exempt (interface 16).
NEUTRALITY_EXEMPT = {"sidecar": "paths and labels (never in a take image)", "egress": "paths and labels (never in a "
                     "take image)"}


def leak_hits(strings) -> list:
    hits = []
    for s in strings:
        for w in LEAK_WORDS:
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])", s, re.IGNORECASE):
                hits.append(s)
                break
    return hits


class DockerfileTest(unittest.TestCase):
    def test_every_committed_dockerfile_keeps_its_rules(self):
        for image in il.IMAGES:
            with self.subTest(image):
                self.assertEqual(il.check_dockerfile(dockerfile(image), committed(image)), [])

    def test_each_take_image_installs_its_own_harness(self):
        for image, package in PACKAGES.items():
            with self.subTest(image):
                self.assertEqual(committed(image)["harness"]["package"], package)
                runs = [i.args for i in il.parse_dockerfile(dockerfile(image)) if i.keyword == "RUN"]
                self.assertIn(il.NPM_INSTALL.format(package=package), runs)
                self.assertIn(il.VERSION_CHECK.format(package=package), runs)

    def test_every_dockerfile_mutant_goes_red(self):
        for name in MUTANT_DOCKERFILES:
            with self.subTest(name):
                image, text = dockerfile_mutated(name)
                self.assertTrue(il.check_dockerfile(text, committed(image)), name)

    def test_the_common_block_is_byte_identical(self):
        blocks = {image: il.common_block(dockerfile(image)) for image in il.TAKE_IMAGES + (il.SIDECAR_IMAGE,)}
        self.assertEqual(len(set(blocks.values())), 1, blocks.keys())
        block = blocks["take-a"]
        for want in ("apt-get install", il.PYTHON_CHECK, "ENV PYTHONDONTWRITEBYTECODE=1", "useradd", il.GIT_SAFE):
            self.assertIn(want, block)
        # A one-byte change in one file's block goes red.
        changed = dockerfile("take-o").replace("procps ca-certificates", "procps  ca-certificates")
        self.assertNotEqual(il.common_block(changed), block)
        with self.assertRaises(il.DockerfileError):
            il.common_block(dockerfile("take-a").replace(il.COMMON_END + "\n", ""))
        with self.assertRaises(il.DockerfileError):
            il.common_block(dockerfile("take-a") + il.COMMON_BEGIN + "\n")

    def test_the_parser(self):
        text = "# c\nARG BASE\nFROM ${BASE}\nRUN a \\\n# inside\n  && b\n\nUSER 1:1\n"
        ins = il.parse_dockerfile(text)
        self.assertEqual([(i.line, i.keyword, i.args) for i in ins],
                         [(2, "ARG", "BASE"), (3, "FROM", "${BASE}"), (4, "RUN", "a   && b"), (8, "USER", "1:1")])
        # BuildKit's join (fold 3, W4A1-1): no separator, the continuation's leading whitespace kept, the escape and
        # the spaces or tabs after it dropped, the character before it kept.
        joined = il.parse_dockerfile("RUN te\\\nst \"a\"\\ \t\n=\\\n \"b\"\n")[0].args
        self.assertEqual(joined, 'test "a"= "b"')
        self.assertEqual(il.normalized(" a \t b  "), "a b")
        for bad in ("FROB x\n", "RUN a \\\n", "# syntax=docker/dockerfile:1\nARG BASE\n", "RUN <<X\nX\n",
                    "RUN a\r\n", "RUN a\u00a0b\n", "# \x0b\nRUN a\n"):
            with self.subTest(bad), self.assertRaises(il.DockerfileError):
                il.parse_dockerfile(bad)

    def test_the_package_lists(self):
        self.assertEqual(il.PACKAGES, ("python3", "git", "inotify-tools", "procps", "ca-certificates"))
        self.assertEqual(il.forbidden(il.PACKAGES), [])
        for p in ("docker.io", "docker-ce-cli", "podman", "containerd", "runc", "buildah", "curl", "wget",
                  "netcat-openbsd", "ncat", "nmap", "socat", "openssh-client", "telnet", "dnsutils", "bind9-dnsutils",
                  "iputils-ping", "net-tools", "ftp", "lynx", "aria2"):
            with self.subTest(p):
                self.assertEqual(il.forbidden([p]), [p])
                with mock.patch.object(il, "FORBIDDEN_PACKAGES", tuple(x for x in il.FORBIDDEN_PACKAGES
                                                                       if not __import__("fnmatch").fnmatchcase(p, x))):
                    self.assertEqual(il.forbidden([p]), [])   # the mutant that drops its pattern lets it through

    def test_the_users_and_ids_in_every_dockerfile(self):
        for image in il.TAKE_IMAGES + (il.SIDECAR_IMAGE,):
            users, groups = il._users([i.args for i in il.parse_dockerfile(dockerfile(image)) if i.keyword == "RUN"])
            self.assertEqual([u[:3] for u in users], [("dana", "10001", "10001"), ("eli", "10002", "10002")])
            self.assertEqual(groups, [("dana", "10001"), ("eli", "10002")])
            self.assertEqual(il.parse_dockerfile(dockerfile(image))[-1].args, il.LAST_USER[image])
        self.assertEqual(il.LAST_USER, {"take-a": "10001:10001", "take-o": "10001:10001", "take-g": "10001:10001",
                                        "sidecar": "10002:10002"})

    def test_the_in_container_python_runs_on_the_floor(self):
        snippet = re.search(r"python3 -c '([^']*)'", il.PYTHON_CHECK).group(1)
        ast_parse = __import__("ast").parse
        ast_parse(snippet, feature_version=(3, 11))
        self.assertEqual(snippet, "import platform; print(platform.python_version())")

    def test_the_sidecar_program_path(self):
        # Fold 3 (W4A1-10): the copy target is a named constant (merge binding 6 reads it).
        self.assertEqual(il.SIDECAR_PROGRAM, "/opt/w/sidecar.py")
        self.assertEqual(il.SIDECAR_COPY, "sidecar.py " + il.SIDECAR_PROGRAM)


class LockSetTest(unittest.TestCase):
    def test_the_nullable_table(self):
        R, N, O = il.REQUIRED, il.NULL, il.NULL_OR_PENDING
        self.assertEqual(il.NULLABLE, {
            "take-a": {"harness": R, "python": R, "users": R}, "take-o": {"harness": R, "python": R, "users": R},
            "take-g": {"harness": R, "python": R, "users": R}, "sidecar": {"harness": N, "python": R, "users": R},
            "egress": {"harness": N, "python": O, "users": N}})
        self.assertEqual(il.EXTRA_KEYS, {"egress": ("squid",)})

    def test_every_nullable_row_mutant_is_refused(self):
        for name in MUTANT_NULLABLE:
            with self.subTest(name):
                self.assertTrue(il.problems(nullable_mutated(name)), name)

    def test_egress_python_may_be_null_or_pending(self):
        for v in (None, il.PENDING):
            lock = filled("egress") if v is None else build_input("egress")
            lock["python"] = v
            if v == il.PENDING:
                lock["pending"]["python"] = "measured at the build"
            self.assertEqual(il.problems(lock), [], v)

    def test_the_take_and_sidecar_locks_share_one_base(self):
        locks = [committed(i) for i in il.IMAGES]
        self.assertEqual(il.shared_base_problems(locks), [])
        filled_locks = [filled(i) for i in il.IMAGES]
        self.assertEqual(il.shared_base_problems(filled_locks), [])
        filled_locks[1]["base"] = "registry.example/other@sha256:" + "d" * 64
        self.assertTrue(il.shared_base_problems(filled_locks))
        self.assertTrue(il.shared_base_problems(filled_locks[:2]))

    def test_each_lock_sits_beside_its_dockerfile(self):
        for image in il.IMAGES:
            self.assertEqual(committed(image)["dockerfile"], il.DOCKERFILES[image])
            self.assertTrue(os.path.isfile(os.path.join(il.BOX_DIR, il.DOCKERFILES[image])))


def pull_ok(argv) -> bool:
    """The build never pulls: --pull=false exactly once, right after `build`."""
    return argv.count("--pull=false") == 1 and argv[1:3] == ["build", "--pull=false"]


class BuildArgvTest(unittest.TestCase):
    def test_the_unfilled_locks_build_nothing(self):
        for image in il.IMAGES:
            with self.subTest(image), self.assertRaises(il.NotReady):
                il.build_argv(unfilled(image), context="/srv/ctx")

    def test_each_pending_build_input_alone_refuses(self):
        for image in il.IMAGES:
            for field in UNFILLED_PENDING[image]:
                if field == "image_id":
                    continue
                with self.subTest(image=image, field=field):
                    lock = build_input(image)
                    if "." in field:
                        lock["harness"]["version"] = il.PENDING
                    else:
                        lock[field] = il.PENDING
                    lock["pending"][field] = "measured at the build"
                    with self.assertRaises(il.NotReady) as cm:
                        il.build_argv(lock, context=il.BOX_DIR)
                    self.assertIn(field, str(cm.exception))

    def test_a_pending_image_id_alone_does_not_block_the_build(self):
        lock = filled("take-a")
        for k in il.SCHEMA_2_KEYS:            # a build input is the unfilled schema-1 lock
            del lock[k]
        lock["schema"] = il.SCHEMA
        lock["image_id"] = il.PENDING
        lock["pending"] = {"image_id": "the build makes it"}
        self.assertEqual(il.build_argv(lock, context="/srv/ctx")[:3], ["docker", "build", "--pull=false"])
        self.assertTrue(il.check_labels(lock, matching_inspect(filled("take-a"))))   # still never passes the labels

    def test_the_argv(self):
        for image in il.IMAGES:
            with self.subTest(image):
                lock = filled(image)
                ctx = il.BOX_DIR if image == il.SIDECAR_IMAGE else "/srv/ctx"
                argv = il.build_argv(lock, context=ctx)
                self.assertEqual(argv[:5], ["docker", "build", "--pull=false", "--file",
                                            os.path.join(il.BOX_DIR, il.DOCKERFILES[image])])
                self.assertEqual(argv[-1], ctx)
                pairs = list(zip(argv[5:-1:2], argv[6:-1:2]))
                args = dict(v.split("=", 1) for k, v in pairs if k == "--build-arg")
                labels = dict(v.split("=", 1) for k, v in pairs if k == "--label")
                self.assertEqual(len(pairs) * 2, len(argv) - 6)
                self.assertEqual(args, il.build_args(lock))
                self.assertEqual(labels, il.expected_labels(lock))
                self.assertEqual(args["BASE"], BASE)
                dockerfile_args = [i.args for i in il.parse_dockerfile(dockerfile(image)) if i.keyword == "ARG"]
                self.assertEqual(sorted(args), sorted(dockerfile_args))
                self.assertTrue(pull_ok(argv))
        with self.assertRaises(ValueError):
            il.build_argv(filled("take-a"), context="relative/ctx")
        with self.assertRaises(ValueError):
            il.build_argv(filled("sidecar"), context="/srv/ctx")   # the sidecar's context is box/
        self.assertEqual(il.build_argv(filled("sidecar"), context=il.BOX_DIR)[-1], il.BOX_DIR)

    def test_a_dropped_pull_flag_goes_red(self):
        # Fold 3 (W4A1-6): the flag itself mutated, in a copy of the module's source loaded under its own file name.
        with open(il.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count('"--pull=false", '), 1)
        mutant = types.ModuleType("image_lock_mutant")
        mutant.__file__ = il.__file__
        with mock.patch.dict(sys.modules, {"image_lock_mutant": mutant}):
            exec(compile(src.replace('"--pull=false", ', ""), il.__file__, "exec"), mutant.__dict__)
            argv = mutant.build_argv(filled("take-a"), context="/srv/ctx")
        self.assertNotIn("--pull=false", argv)                    # the mutant builds without it
        self.assertFalse(pull_ok(argv))                           # and the argv check test_the_argv uses goes red
        self.assertTrue(pull_ok(il.build_argv(filled("take-a"), context="/srv/ctx")))


class NeutralityTest(unittest.TestCase):
    def test_the_take_images_strings_carry_no_study_word(self):
        for image in il.TAKE_IMAGES:
            with self.subTest(image):
                seen = agent_visible(image)
                self.assertTrue(all(seen.values()), [k for k, v in seen.items() if not v])
                for kind, strings in seen.items():
                    self.assertEqual(leak_hits(strings), [], kind)

    def test_every_images_user_names_carry_no_study_word(self):
        for image in il.IMAGES:
            with self.subTest(image):
                self.assertEqual(leak_hits(user_names(image)), [])
        self.assertEqual(set(NEUTRALITY_EXEMPT), {il.SIDECAR_IMAGE, il.EGRESS_IMAGE})
        self.assertIn("/opt/w/sidecar.py", dockerfile("sidecar"))   # exempt: never in a take image

    def test_the_user_names_are_not_vendor_or_harness_names(self):
        for name in user_names("take-a"):
            for word in (hb.CLAUDE_CODE, pc.CODEX, pc.GEMINI, "claude", "anthropic", "openai", "google", "agent"):
                self.assertNotIn(word, name)

    def test_a_planted_study_word_goes_red(self):
        for planted in ("/home/probe", "/srv/" + LEAK_WORDS[0].replace(" ", "-"), "app.grader.version",
                        "GAP4_MODE", "Round 4"):
            with self.subTest(n=len(planted)):
                self.assertEqual(leak_hits([planted]), [planted])
        text = dockerfile("take-a").replace("/home/dana", "/home/sealed")
        with mock.patch.object(sys.modules[__name__], "dockerfile", lambda image: text):
            self.assertTrue(leak_hits(agent_visible("take-a")["paths"]))
        # The instruction scan: a study word anywhere in an instruction's text, not only in a path, goes red.
        text = dockerfile("take-a").replace("--shell /bin/bash dana", "--shell /bin/bash dana --comment trap")
        with mock.patch.object(sys.modules[__name__], "dockerfile", lambda image: text):
            seen = agent_visible("take-a")
            self.assertTrue(leak_hits(seen["instructions"]))
            self.assertFalse(leak_hits(seen["paths"] + seen["label keys"] + seen["env"]))


def print_mutants() -> None:
    for name in MUTANT_LOCKS:
        lock = mutated(name)
        found = il.problems(lock)
        print(f"mutant lock {name!r}: {'red' if found else 'GREEN'} ({found[0] if found else '-'})")
    lock = filled("take-a")
    for name in MUTANT_INSPECTS:
        found = il.check_labels(lock, inspect_mutated(name))
        print(f"mutant inspect {name!r}: {'red' if found else 'GREEN'} ({found[0] if found else '-'})")
    for name in MUTANT_NULLABLE:
        found = il.problems(nullable_mutated(name))
        print(f"mutant nullable {name!r}: {'red' if found else 'GREEN'} ({found[0] if found else '-'})")
    for name in MUTANT_DOCKERFILES:
        image, text = dockerfile_mutated(name)
        found = il.check_dockerfile(text, committed(image))
        print(f"mutant dockerfile {name!r} ({image}): {'red' if found else 'GREEN'} ({found[0] if found else '-'})")
    for name, mutate in PIN_MUTANTS.items():
        found = pin_problems(mutate(committed_texts()))
        print(f"mutant pin {name!r}: {'red' if found else 'GREEN'} ({found[0] if found else '-'})")


def _patched_now() -> list:
    """The guarded names that are patched to the guard right now."""
    return [f"{getattr(m, '__name__', m)}.{n}" for m, n in _GUARDED if getattr(m, n) is _blocked]


# Taken last, after every import-time statement of this module: must be empty (setUpModule arms the guard).
_PATCHED_AT_IMPORT = _patched_now()


if __name__ == "__main__":
    print_mutants()
    unittest.main()
