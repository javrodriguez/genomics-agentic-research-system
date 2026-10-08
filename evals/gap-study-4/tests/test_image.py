#!/usr/bin/env python3
"""test_image.py: the box images' locks (box/image_lock.py) and their Dockerfiles, driven with no runtime at all.

Nothing here builds an image or runs a container: `build_argv` is only constructed, and a module-level guard
(interface 10) makes every process start and every signal raise for the whole module, armed right after the one
read of round 3's leak words (interface 16).

Every guard is also shown red: each lock clause by a mutated lock (MUTANT_LOCKS), each label rule by a mutated
inspect (MUTANT_INSPECTS). Run alone, the module first prints every mutant with its red run, then runs the tests.
"""

from __future__ import annotations

import copy
import inspect as pyinspect
import json
import os
import re
import subprocess
import sys
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
for _mod, _name in _GUARDED:
    mock.patch.object(_mod, _name, _blocked).start()

from box import image_lock as il  # noqa: E402

LOCK_PATHS = {image: os.path.join(il.BOX_DIR, os.path.dirname(df), "image.lock")
              for image, df in il.DOCKERFILES.items()}
COMMITTED_PENDING = {
    "take-a": ("base", "harness.version", "python", "image_id"),
}

BASE = "registry.example/fake-base@sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


def committed(image: str) -> dict:
    return il.load(LOCK_PATHS[image])


def filled(image: str = "take-a") -> dict:
    """The committed lock with every PENDING value replaced by an obviously fake pinned value."""
    lock = copy.deepcopy(committed(image))
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
    "schema 2": _set(("schema",), 2),
    "schema as a bool": _set(("schema",), True),
    "an unknown image": _set(("image",), "take-z"),
    "the wrong dockerfile": _set(("dockerfile",), "codex/Dockerfile"),
    "a base by tag": _set(("base",), "registry.example/fake-base:latest"),
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
    def test_the_process_guard_is_armed(self):
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
    def test_the_committed_locks_load_with_their_exact_pending_sets(self):
        for image, want in COMMITTED_PENDING.items():
            with self.subTest(image):
                lock = committed(image)
                self.assertEqual(lock["image"], image)
                self.assertEqual(il.pending(lock), want)
                self.assertEqual(tuple(lock["pending"]), want)
                self.assertFalse(il.ready(lock))

    def test_the_committed_users_and_their_names(self):
        for image in COMMITTED_PENDING:
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

    def test_require_ready_names_every_pending_field(self):
        with self.assertRaises(il.NotReady) as cm:
            il.require_ready(committed("take-a"))
        for field in COMMITTED_PENDING["take-a"]:
            self.assertIn(field, str(cm.exception))

    def test_a_dropped_refusal_goes_red(self):
        with mock.patch.object(il, "_pending_fields", lambda lock: []):
            self.assertTrue(il.ready(committed("take-a")))   # the mutant waves the unfilled lock through
        self.assertFalse(il.ready(committed("take-a")))

    def test_the_fixed_ids(self):
        self.assertEqual((il.AGENT_UID, il.WATCHER_UID, il.KEEPALIVE_UID), (10001, 10002, 10003))
        for const, field, role in (("AGENT_UID", "uid", "agent"), ("WATCHER_UID", "uid", "watcher"),
                                   ("KEEPALIVE_UID", "uid", "keepalive")):
            with self.subTest(const), mock.patch.object(il, const, getattr(il, const) + 7):
                self.assertTrue(il.problems(filled("take-a")))


class LabelsTest(unittest.TestCase):
    def test_a_filled_lock_against_its_matching_inspect_passes(self):
        lock = filled("take-a")
        self.assertEqual(il.check_labels(lock, matching_inspect(lock)), [])
        self.assertEqual(set(il.expected_labels(lock)),
                         {il.BASE_NAME_LABEL, il.BASE_DIGEST_LABEL, il.CLI_LABEL, il.PYTHON_LABEL})
        self.assertEqual(il.expected_labels(lock)[il.BASE_DIGEST_LABEL], "sha256:" + "a" * 64)
        self.assertEqual(il.expected_labels(lock)[il.BASE_NAME_LABEL], "registry.example/fake-base")

    def test_the_committed_lock_is_refused_whatever_the_labels_say(self):
        lock = committed("take-a")
        ins = matching_inspect(filled("take-a"))
        found = il.check_labels(lock, ins)
        self.assertEqual(len(found), len(COMMITTED_PENDING["take-a"]))
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
        with mock.patch.object(il, "LABELS", il.LABELS[1:]):
            lock = filled("take-a")
            self.assertTrue(il.check_labels(lock, {"Id": IMAGE_ID, "Config": {"Labels": dict(
                matching_inspect(filled("take-a"))["Config"]["Labels"])}}))

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


def print_mutants() -> None:
    for name in MUTANT_LOCKS:
        lock = mutated(name)
        found = il.problems(lock)
        print(f"mutant lock {name!r}: red ({found[0]})")
    lock = filled("take-a")
    for name in MUTANT_INSPECTS:
        print(f"mutant inspect {name!r}: red ({il.check_labels(lock, inspect_mutated(name))[0]})")


if __name__ == "__main__":
    print_mutants()
    unittest.main()
