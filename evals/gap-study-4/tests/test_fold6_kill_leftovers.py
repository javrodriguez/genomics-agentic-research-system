#!/usr/bin/env python3
"""Lane fold6/kill-leftovers (Gap Study round 4; glitch-45's ruling (a), Sun 1 Nov 2026, under Javier's standing
delegation): postflight admits the peer-messaging pair a killed claude-code take leaves in its config folder, bound to
the take that produced it, and nothing else.

  K1-admit    given the take's session id and run tree, sessions/N.json plus sessions/N.<64 hex>.key, regular files with
              one link, N.json naming that session and the socket <run tree>/.tmp/cc-socks/N.sock, are admitted and
              recorded (names, sizes, owners; never contents).
  K2-refuse   a .key alone; a pair whose sessionId or socket path is another take's; an extra file in sessions/; a
              symlinked or hard-linked member; a .key anywhere else in the config folder; and any pair when the session
              id and run tree are not given (the old behaviour, unchanged) are each refused.
  K3-drive    drive.TakeDriver._postflight passes the take's own session id and run tree.

Synthetic config folders in temporary directories only; no container, model or network.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from box import preflight  # noqa: E402

SID = "3c1f0e9a-0000-5000-8000-0000000000aa"
TREE = "/tmp/run-0637012b"
KEY = "69." + "ab" * 32 + ".key"


def config(tmp: str, *, key=True, json_doc=None, extra=None, link=None) -> str:
    root = os.path.join(tmp, "cfg")
    os.makedirs(os.path.join(root, "sessions"))
    doc = {"sessionId": SID, "peerProtocol": 1, "messagingSocketPath": f"{TREE}/.tmp/cc-socks/69.sock"} \
        if json_doc is None else json_doc
    Path(root, "sessions", "69.json").write_text(json.dumps(doc))
    if key:
        Path(root, "sessions", KEY).write_bytes(b"k" * 110)
    for rel in extra or ():
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        Path(root, rel).write_text("x")
    if link == "symlink":
        os.unlink(os.path.join(root, "sessions", KEY))
        Path(tmp, "outside.key").write_bytes(b"k" * 110)
        os.symlink(os.path.join(tmp, "outside.key"), os.path.join(root, "sessions", KEY))
    elif link == "hardlink":
        os.link(os.path.join(root, "sessions", KEY), os.path.join(tmp, "second-name.key"))
    return root


def run(root: str, bound: bool = True) -> dict:
    kw = {"session_id": SID, "run_tree": TREE} if bound else {}
    return preflight.postflight(root, "claude-code", **kw)


class K1Admit(unittest.TestCase):
    def test_the_exact_pair_bound_to_the_take_is_admitted_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = run(config(tmp))
        self.assertTrue(got["ok"], got["checks"])
        pair = got["recorded"]["admitted_session_pair"]
        self.assertEqual([p["name"] for p in pair], ["sessions/69.json", f"sessions/{KEY}"], "K1-admit")
        self.assertEqual(pair[1]["size"], 110, "K1-admit")
        self.assertEqual(set(pair[0]), {"name", "size", "uid", "gid"}, "K1-admit: never contents")
        self.assertNotIn(SID, json.dumps(pair), "K1-admit: the record carries no content")


class K2Refuse(unittest.TestCase):
    def refused(self, got, what):
        self.assertFalse(got["ok"], f"K2-refuse: {what} admitted: {got['recorded']}")
        self.assertEqual(got["recorded"].get("admitted_session_pair", []), [], f"K2-refuse: {what}")

    def test_a_key_alone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = config(tmp)
            os.unlink(os.path.join(root, "sessions", "69.json"))
            self.refused(run(root), "a .key alone")

    def test_another_takes_session_or_socket_is_refused(self):
        for doc in ({"sessionId": "another", "messagingSocketPath": f"{TREE}/.tmp/cc-socks/69.sock"},
                    {"sessionId": SID, "messagingSocketPath": "/tmp/run-99999999/.tmp/cc-socks/69.sock"},
                    {"sessionId": SID, "messagingSocketPath": f"{TREE}/.tmp/cc-socks/70.sock"}):
            with self.subTest(doc=doc), tempfile.TemporaryDirectory() as tmp:
                self.refused(run(config(tmp, json_doc=doc)), "another take's pair")

    def test_an_extra_file_in_sessions_is_refused(self):
        for extra in ("sessions/70.json", "sessions/notes.txt"):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as tmp:
                self.refused(run(config(tmp, extra=[extra])), f"an extra {extra}")

    def test_a_linked_member_is_refused(self):
        for link in ("symlink", "hardlink"):
            with self.subTest(link=link), tempfile.TemporaryDirectory() as tmp:
                self.refused(run(config(tmp, link=link)), f"a {link}")

    def test_a_key_elsewhere_still_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = run(config(tmp, extra=["projects/x/peer.key"]))
        self.assertFalse(got["ok"], "K2-refuse: a .key outside sessions/ passed")
        self.assertIn("projects/x/peer.key", got["checks"][0]["detail"], "K2-refuse")

    def test_without_the_take_binding_nothing_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = run(config(tmp), bound=False)
        self.assertFalse(got["ok"], "K2-refuse: the unbound call admitted the pair")
        self.assertNotIn("admitted_session_pair", got["recorded"], "K2-refuse: the unbound record changed shape")


class K3Drive(unittest.TestCase):
    def test_the_driver_passes_the_takes_session_and_run_tree(self):
        import drive
        seen = {}

        def fake(config_dir, harness, **kw):
            seen.update(kw, config_dir=config_dir, harness=harness)
            return {"ok": True}

        take = types.SimpleNamespace(config_dir="/c", identity={"session_id": SID},
                                     spec=types.SimpleNamespace(run_tree=TREE), cleanup=[])
        me = types.SimpleNamespace(_write=lambda *a: None)
        with mock.patch.object(drive._preflight, "postflight", fake):
            drive.TakeDriver._postflight(me, take, {"agent": {"harness": "claude-code"}})
        self.assertEqual(seen, {"config_dir": "/c", "harness": "claude-code", "session_id": SID, "run_tree": TREE},
                         "K3-drive")


if __name__ == "__main__":
    unittest.main()
