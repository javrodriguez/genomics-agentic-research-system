#!/usr/bin/env python3
"""ops/write_image_lock.py: the one supported lock writer, on a temporary repository only (never the real locks).

Every value is obviously fake. The fixture is a throwaway git repository holding a box/ with the take-a and sidecar
locks (schema 1), their Dockerfiles, sidecar.py, a lock-inputs file and one schema-3 build record with its metadata
file and build log beside it, as lane-reports/build-20261014c/build_candidate_images.py writes them; the record's
build ran in a checkout at another path (an athena-style folder), so the argv mapping is always exercised.

Each refusal is tested alone, with its own message. The lock-writer review's witnesses (LW-1 to LW-6, 14 Oct 2026)
are refusal tests here: L1 (an input changed after the build), L2 (a digest edited in a later commit), L3 (an argv
that is not build_argv's), L4 (no refusal falls through). One positive write fills a schema-1 take-a lock into a
schema-2 lock that image_lock validates and preflight.load_take_lock projects.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from box import image_lock as il  # noqa: E402
from box import preflight as pf  # noqa: E402

SPEC = importlib.util.spec_from_file_location("write_image_lock_test", HERE.parents[1] / "ops/write_image_lock.py")
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)

BASE = "registry.example/fake-base@sha256:" + "a" * 64
INDEX, MANIFEST, CONFIG = "sha256:" + "f" * 64, "sha256:" + "c" * 64, "sha256:" + "d" * 64
ATTESTATION, OTHER = "sha256:" + "b" * 64, "sha256:" + "9" * 64
ATHENA = "/srv/athena-child/clone"          # where the record's build ran: never this repository's path
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "maintenance.auto=false", "-c", "gc.auto=0"]
LOCK_REL = {"take-a": "box/image.lock", "sidecar": "box/sidecar/image.lock"}
SIDECAR_COPY = "COPY sidecar.py /opt/w/sidecar.py\n"


REAL_BOX = il.BOX_DIR


# The fields a fixture's unfilled lock holds PENDING (the locks before the reviewed write).
UNFILLED_PENDING = {"take-a": ("base", "harness.version", "python", "image_id"),
                    "sidecar": ("base", "python", "image_id")}


def committed(image: str) -> dict:
    """The fixture's unfilled (schema-1) lock, made synthetically from the committed lock (now the reviewed schema-2
    pin, glitch-06's post-write ruling): its schema-2 fields removed and UNFILLED_PENDING PENDING again. Never the
    committed lock read as schema 1."""
    with mock.patch.object(il, "BOX_DIR", REAL_BOX):     # the committed lock, even while a fixture box is active
        lock = il.load(os.path.join(REAL_BOX, os.path.dirname(il.DOCKERFILES[image]), "image.lock"))
    lock = {k: v for k, v in copy.deepcopy(lock).items() if k not in il.SCHEMA_2_KEYS}
    lock["schema"] = il.SCHEMA
    for field in UNFILLED_PENDING[image]:
        head, _, tail = field.partition(".")
        if tail:
            lock[head][tail] = il.PENDING
        else:
            lock[head] = il.PENDING
    lock["pending"] = {f: "synthetic: re-PENDINGed from the committed lock" for f in UNFILLED_PENDING[image]}
    return il.validate(lock)


def inputs(lock: dict) -> dict:
    out = {"base": BASE, "python": "3.12.99", "users": copy.deepcopy(lock["users"])}
    out["harness"] = dict(lock["harness"], version="9.8.7") if lock["harness"] is not None else None
    return out


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_log(manifests, configs=(CONFIG,), lists=(INDEX,)) -> str:
    """BuildKit's plain export lines, as measured on athena (14 Oct 03:37 EDT)."""
    lines = ["#1 [internal] load build definition from Dockerfile", "#11 exporting to image",
             "#11 exporting layers done"]
    lines += [f"#11 exporting manifest {m} done" for m in manifests]
    lines += [f"#11 exporting config {c} done" for c in configs]
    lines += [f"#11 exporting attestation manifest {ATTESTATION} 0.0s done",
              *[f"#11 exporting manifest list {i} done" for i in lists], "#11 DONE 0.1s"]
    return "\n".join(lines) + "\n"


class Repo:
    """A throwaway git repository with box/ (take-a and sidecar, schema 1), a lock-inputs file and one build record."""

    def __init__(self, tc, image="take-a"):
        d = Path(tempfile.mkdtemp())
        tc.addCleanup(lambda: shutil.rmtree(d))
        self.image = image
        self.root, self.box = d, d / "box"
        (self.box / "sidecar").mkdir(parents=True)
        (self.box / "Dockerfile").write_text("FROM scratch\n")
        (self.box / "sidecar" / "Dockerfile").write_text("FROM scratch\n" + SIDECAR_COPY)
        (self.box / "sidecar.py").write_text("print('the fixture sidecar')\n")
        self.locks = {}
        for name, rel in LOCK_REL.items():
            self.locks[name] = committed(name)
            (d / rel).write_text(json.dumps(self.locks[name], indent=1) + "\n")
        self.lock = self.locks[image]
        self.lock_path = d / LOCK_REL[image]
        self.prov = {"locks": {rel: {"content": dict(inputs(self.locks[n]), image=n)} for n, rel in LOCK_REL.items()}}
        (d / "prov.json").write_text(json.dumps(self.prov, indent=1) + "\n")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.out = d / "record"
        self.out.mkdir()
        self.record_path = self.out / "build-record.json"
        self.row = self.fresh_row()
        # the metadata file as measured on athena: the image index only, no config digest
        self.meta = {"containerimage.digest": INDEX, "containerimage.descriptor": {
            "mediaType": "application/vnd.oci.image.index.v1+json", "digest": INDEX, "size": 856},
            "buildx.build.provenance": {"invocation": {"parameters": {"root": {"request": {"args": {
                "vcs:revision": self.base, "vcs:localdir:context": "box",
                "vcs:source": "/nonexistent-promisor-never-fetched"}}}}}}}
        self.log = build_log([MANIFEST])
        self.record = {"schema": 3, "source_commit": self.base, "checkout": ATHENA, "box_dir": ATHENA + "/box",
                       "store": {"driver": "overlayfs", "driver_status": [["driver-type", "io.containerd.snapshotter.v1"]]},
                       "lock_inputs_source": {"path": "prov.json", "sha256": self.blob_sha("prov.json")},
                       "clean_after": True, "problems": [], "images": [self.row]}
        self.commit_record()
        p = mock.patch.object(il, "BOX_DIR", str(self.box))
        p.start()
        tc.addCleanup(p.stop)

    def blob_sha(self, rel: str) -> str:
        return sha((self.root / rel).read_bytes())

    def fresh_row(self) -> dict:
        lock = dict(self.lock, **inputs(self.lock), pending={"image_id": "this build makes it"})  # as script c
        name = self.image
        with mock.patch.object(il, "BOX_DIR", ATHENA + "/box"):     # the build ran at athena's path
            argv = il.build_argv(lock, context=il.BOX_DIR)
        argv = argv[:-1] + ["--iidfile", f"/srv/athena-child/out/{name}.iid", "--metadata-file",
                            f"/srv/athena-child/out/{name}.metadata.json", argv[-1]]
        ins = {"box/" + self.lock["dockerfile"]: self.blob_sha("box/" + self.lock["dockerfile"])}
        lock_inputs = {k: v for k, v in inputs(self.lock).items()}
        row = {"image": name, "lock": LOCK_REL[name], "argv": argv, "exit": 0, "inputs": ins,
               "lock_inputs": lock_inputs, "lock_inputs_sha256": sha(w.canonical(lock_inputs)),
               "metadata_file": f"{name}.metadata.json", "build_log": f"{name}.build.log",
               "image_id": INDEX, "manifest_digest": MANIFEST, "config_digest": CONFIG, "label_problems": [],
               "logged_manifests": [MANIFEST]}
        if name == "sidecar":
            ins["box/sidecar.py"] = self.blob_sha("box/sidecar.py")
            row["baked_sidecar_sha256"] = ins["box/sidecar.py"]
        return row

    def entries(self) -> dict:
        """Each recorded input's [mode, blob id] at the build commit, as script c records them (R2-1)."""
        out = {}
        for rel in self.row["inputs"]:
            mode, _, oid = self.git("ls-tree", self.base, "--", rel).split("\t")[0].split(" ")
            out[rel] = [mode, oid]
        return out

    def git(self, *args) -> str:
        return subprocess.run(GIT + ["-C", str(self.root), *args], check=True, capture_output=True,
                              text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(self.root)}).stdout

    def commit_record(self):
        self.record_path.write_text(json.dumps(self.record, indent=1) + "\n")
        (self.out / f"{self.image}.metadata.json").write_text(json.dumps(self.meta) + "\n")
        (self.out / f"{self.image}.build.log").write_text(self.log)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", "record")

    def commit_file(self, rel: str, text: str):
        (self.root / rel).write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"change {rel}")

    def set_inputs(self, edit):
        """Edit the lock inputs in the committed lock-inputs file and the row alike (so only the field rule reads)."""
        edit(self.row["lock_inputs"])
        content = self.prov["locks"][LOCK_REL[self.image]]["content"]
        edit(content)
        content.update(image=self.image)
        (self.root / "prov.json").write_text(json.dumps(self.prov, indent=1) + "\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "inputs")
        self.record["lock_inputs_source"]["sha256"] = self.blob_sha("prov.json")
        self.row["lock_inputs_sha256"] = sha(w.canonical(self.row["lock_inputs"]))
        self.commit_record()

    def plan(self):
        return w.plan(il, self.root, self.record_path, self.lock_path, self.image)


class Positive(unittest.TestCase):
    def test_a_temp_repo_write_fills_a_valid_schema_2_lock(self):
        r = Repo(self)
        new, read = r.plan()
        self.assertEqual(read, r.lock_path.read_bytes())
        w.write(r.lock_path, new, read)
        got = il.load(str(r.lock_path))
        self.assertEqual((got["schema"], got["image_id"], got["manifest_digest"], got["config_digest"],
                          got["source_commit"], got["pending"]), (2, INDEX, MANIFEST, CONFIG, r.base, {}))
        self.assertEqual(il.problems(got), [])
        projected = pf.load_take_lock(str(r.lock_path), harness="claude-code")
        self.assertEqual(projected["manifest_digest"], MANIFEST)
        self.assertFalse(Path(str(r.lock_path) + ".writing").exists())

    def test_the_sidecar_lock_with_its_copied_program(self):
        r = Repo(self, "sidecar")
        new, _ = r.plan()
        self.assertEqual((new["schema"], new["image"], new["manifest_digest"]), (2, "sidecar", MANIFEST))

    def test_without_write_nothing_changes(self):
        r = Repo(self)
        before = r.lock_path.read_bytes()
        r.plan()
        self.assertEqual(r.lock_path.read_bytes(), before)

    def test_main_dry_run_prints_and_writes_nothing(self):
        r = Repo(self)
        before = r.lock_path.read_bytes()
        buf = io.StringIO()
        with mock.patch.object(w, "load_image_lock", lambda repo: il), redirect_stdout(buf):
            rc = w.main(["--repo", str(r.root), "--record", str(r.record_path), "--lock", str(r.lock_path),
                         "--image", "take-a"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue())["manifest_digest"], MANIFEST)
        self.assertEqual(r.lock_path.read_bytes(), before)


class Refusals(unittest.TestCase):
    def refuse(self, r, pattern):
        with self.assertRaisesRegex((w.Refused, il.LockError), pattern):
            r.plan()

    def test_an_uncommitted_record(self):
        r = Repo(self)
        r.record_path.write_text(r.record_path.read_text() + " ")
        self.refuse(r, "differs from its committed bytes")
        untracked = r.root / "other.json"
        untracked.write_text(r.record_path.read_text())
        with self.assertRaisesRegex(w.Refused, "not a file committed"):
            w.plan(il, r.root, untracked, r.lock_path, "take-a")

    def test_a_commit_not_an_ancestor(self):
        r = Repo(self)
        r.git("checkout", "-q", "-b", "side", r.base)
        r.git("commit", "-q", "--allow-empty", "-m", "side")
        side = r.git("rev-parse", "HEAD").strip()
        r.git("checkout", "-q", "-")
        r.record["source_commit"] = side
        r.commit_record()
        self.refuse(r, "not an ancestor")
        r.record["source_commit"] = "main"
        r.commit_record()
        self.refuse(r, "40 hex")

    def test_each_row_condition(self):
        for key, value, pattern in (("exit", 1, "did not exit 0"), ("exit", True, "did not exit 0"),
                                    ("label_problems", ["x"], "labels"), ("manifest_digest", "c" * 64, "manifest"),
                                    ("config_digest", None, "config"), ("image_id", "sha256:x", "image_id"),
                                    ("lock_inputs", None, "lock_inputs")):
            with self.subTest(key=key, value=value):
                r = Repo(self)
                r.row[key] = value
                r.commit_record()
                with self.assertRaisesRegex(w.Refused, pattern):   # the writer's own check, before any validation
                    r.plan()

    def test_zero_or_two_rows(self):
        r = Repo(self)
        r.record["images"] = [r.row, dict(r.row)]
        r.commit_record()
        self.refuse(r, "2 rows")
        r.record["images"] = []
        r.commit_record()
        self.refuse(r, "0 rows")

    def test_an_unresolved_or_changed_input(self):
        for edit, pattern in ((lambda i: i.pop("python"), "does not resolve python"),
                              (lambda i: i.update(python=il.PENDING), "PENDING not resolved|pinned shape"),
                              (lambda i: i["harness"].update(package="@openai/codex"), "harness package"),
                              (lambda i: i["users"]["agent"].update(uid=10009), "users differs"),
                              (lambda i: i.update(squid="6.99-1"), "does not carry")):
            with self.subTest(pattern=pattern):
                r = Repo(self)
                r.set_inputs(edit)
                self.refuse(r, pattern)

    def test_a_filled_or_other_lock(self):
        r = Repo(self)
        new, read = r.plan()
        w.write(r.lock_path, new, read)
        r.git("add", "-A"); r.git("commit", "-q", "-m", "filled")
        self.refuse(r, "not the unfilled schema-1 lock")
        r2 = Repo(self)
        with self.assertRaisesRegex(w.Refused, "0 rows"):
            w.plan(il, r2.root, r2.record_path, r2.lock_path, "take-o")

    def test_a_record_of_another_schema(self):
        for schema in (1, 2):
            with self.subTest(schema=schema):
                r = Repo(self)
                r.record["schema"] = schema
                r.commit_record()
                self.refuse(r, "not schema 3")


class InputsLW1(unittest.TestCase):
    """LW-1 (MAJOR, threat g): the build's inputs must be HEAD's. L1 is the first case."""

    def refuse(self, r, pattern):
        with self.assertRaisesRegex(w.Refused, pattern):
            r.plan()

    def test_L1_the_dockerfile_changed_after_the_build(self):
        r = Repo(self)
        r.commit_file("box/Dockerfile", "FROM scratch\nRUN echo changed after the build\n")
        self.assertTrue(w.is_ancestor(r.root, r.base))           # the stale commit is still an ancestor
        self.refuse(r, "box/Dockerfile at HEAD is not the box/Dockerfile the image was built from")

    def test_the_sidecar_program_changed_after_the_build(self):
        r = Repo(self, "sidecar")
        r.commit_file("box/sidecar.py", "print('changed after the build')\n")
        self.refuse(r, "box/sidecar.py at HEAD is not")

    def test_a_copy_source_not_recorded(self):
        r = Repo(self, "sidecar")
        del r.row["inputs"]["box/sidecar.py"]
        r.commit_record()
        self.refuse(r, "are not the inputs HEAD's Dockerfile reads")

    def test_a_copy_added_at_head(self):
        r = Repo(self)
        r.commit_file("box/Dockerfile", "FROM scratch\nCOPY sidecar.py /opt/x\n")
        self.refuse(r, "are not the inputs HEAD's Dockerfile reads")

    def test_a_context_read_the_writer_does_not_bind(self):
        for line in ("ADD sidecar.py /opt/x\n", "COPY --from=other /x /y\n", "COPY *.py /opt/\n",
                     "COPY ../x /y\n"):
            with self.subTest(line=line):
                r = Repo(self)
                r.commit_file("box/Dockerfile", "FROM scratch\n" + line)
                self.refuse(r, "a context read this writer does not bind")

    def test_no_inputs_recorded(self):
        r = Repo(self)
        r.row["inputs"] = {}
        r.commit_record()
        self.refuse(r, "records no build inputs")

    def test_a_recorded_sha_that_is_not_hex(self):
        r = Repo(self)
        r.row["inputs"]["box/Dockerfile"] = "x" * 64
        r.commit_record()
        self.refuse(r, "is not 64 hex")

    def test_the_lock_inputs_file_changed(self):
        r = Repo(self)
        r.commit_file("prov.json", (r.root / "prov.json").read_text() + " ")
        self.refuse(r, "prov.json at HEAD is not the lock-inputs file")

    def test_no_lock_inputs_file(self):
        r = Repo(self)
        del r.record["lock_inputs_source"]
        r.commit_record()
        self.refuse(r, "names no lock-inputs file")

    def test_lock_inputs_not_the_files(self):
        r = Repo(self)
        r.row["lock_inputs"]["python"] = "3.12.98"
        r.row["lock_inputs_sha256"] = sha(w.canonical(r.row["lock_inputs"]))
        r.commit_record()
        self.refuse(r, "lock_inputs are not prov.json's")

    def test_lock_inputs_sha_not_theirs(self):
        r = Repo(self)
        r.row["lock_inputs_sha256"] = "0" * 64
        r.commit_record()
        self.refuse(r, "lock_inputs_sha256 is not")

    def test_the_row_of_another_lock(self):
        r = Repo(self)
        r.row["lock"] = "box/codex/image.lock"
        r.commit_record()
        self.refuse(r, "is the build of")

    def test_a_baked_sidecar_program_that_differs(self):
        r = Repo(self, "sidecar")
        r.row["baked_sidecar_sha256"] = "0" * 64
        r.commit_record()
        self.refuse(r, "baked program is not its recorded sidecar.py")


class BuildLW2(unittest.TestCase):
    """LW-2: the digests bound to the build's own metadata file and log; the argv is build_argv's. L2 and L3."""

    def refuse(self, r, pattern):
        with self.assertRaisesRegex(w.Refused, pattern):
            r.plan()

    def test_L2_a_manifest_digest_edited_in_a_later_commit(self):
        r = Repo(self)
        r.row["manifest_digest"] = OTHER
        r.commit_record()
        self.refuse(r, "build log exported manifest")

    def test_a_config_digest_edited_in_a_later_commit(self):
        r = Repo(self)
        r.row["config_digest"] = OTHER
        r.commit_record()
        self.refuse(r, "config_digest is not its build log's one exported config")

    def test_a_log_with_two_or_no_configs(self):
        for configs in ((CONFIG, OTHER), ()):
            with self.subTest(configs=configs):
                r = Repo(self)
                r.log = build_log([MANIFEST], configs)
                r.commit_record()
                self.refuse(r, "config_digest is not its build log's one exported config")

    def test_an_image_id_that_is_not_the_metadata_index(self):
        for label, edit in (("row", lambda r: r.row.update(image_id=OTHER)),
                            ("digest", lambda r: r.meta.update({"containerimage.digest": OTHER})),
                            ("descriptor", lambda r: r.meta["containerimage.descriptor"].update(digest=OTHER)),
                            ("no descriptor", lambda r: r.meta.pop("containerimage.descriptor"))):
            with self.subTest(label=label):
                r = Repo(self)
                edit(r)
                r.commit_record()
                self.refuse(r, "image_id is not its metadata file's image index")

    def test_a_metadata_file_or_log_not_committed(self):
        for key in ("metadata_file", "build_log"):
            with self.subTest(key=key):
                r = Repo(self)
                p = r.out / {"metadata_file": "take-a.metadata.json", "build_log": "take-a.build.log"}[key]
                p.write_text(p.read_text() + " ")
                self.refuse(r, "differs from its committed bytes")

    def test_a_side_file_not_named_for_the_image(self):
        for key, name in (("metadata_file", "../x.metadata.json"), ("build_log", "take-o.build.log"),
                          ("build_log", "take-a.txt"), ("metadata_file", None)):
            with self.subTest(key=key, name=name):
                r = Repo(self)
                r.row[key] = name
                r.commit_record()
                self.refuse(r, f"{key} is not a file named for it")

    def test_a_log_with_two_or_no_manifests(self):
        for manifests in ([MANIFEST, OTHER], []):
            with self.subTest(manifests=manifests):
                r = Repo(self)
                r.log = build_log(manifests)
                r.commit_record()
                self.refuse(r, "build log exported manifest")

    def test_L3_an_argv_that_is_not_build_argv(self):
        for label, edit in (
                ("other Dockerfile", lambda a: a.__setitem__(a.index("--file") + 1, ATHENA + "/box/codex/Dockerfile")),
                ("extra flag", lambda a: a.insert(2, "--no-cache")),
                ("other build arg", lambda a: a.__setitem__(a.index("--build-arg") + 1, "BASE=" + BASE + "x")),
                ("no metadata file", lambda a: a.__delitem__(slice(-3, -1))),
                ("dropped label", lambda a: a.__delitem__(slice(a.index("--label"), a.index("--label") + 2))),
                ("other context", lambda a: a.__setitem__(-1, "/elsewhere"))):
            with self.subTest(label=label):
                r = Repo(self)
                edit(r.row["argv"])
                r.commit_record()
                self.refuse(r, "argv is not image_lock.build_argv")

    def test_an_argv_whose_metadata_file_is_another(self):
        r = Repo(self)
        r.row["argv"][-2] = "/srv/athena-child/out/other.metadata.json"
        r.commit_record()
        self.refuse(r, "--metadata-file is not the committed")

    def test_a_box_folder_that_is_not_the_checkouts(self):
        r = Repo(self)
        r.record["checkout"] = "/srv/elsewhere"
        r.commit_record()
        self.refuse(r, "box folder is not its checkout's")


class Review2(unittest.TestCase):
    """Review 2 (gap4-review-box-lockwriter2-20261014): R2-1 the git mode of an input, R2-2 the log's manifest list
    and the provenance revision, R2-3 the record's problems, R2-4 a tree is never a blob."""

    def refuse(self, r, pattern):
        with self.assertRaisesRegex(w.Refused, pattern):
            r.plan()

    def test_R2_1_a_mode_only_change_after_the_build(self):
        r = Repo(self, "sidecar")
        os.chmod(r.box / "sidecar.py", 0o755)
        r.git("add", "-A"); r.git("commit", "-q", "-m", "mode only")
        before, after = (r.git("ls-tree", rev, "--", "box/sidecar.py").split("\t")[0].split(" ") for rev in (r.base, "HEAD"))
        self.assertEqual((before[0], after[0], before[2] == after[2]), ("100644", "100755", True))   # the blob is unchanged
        self.refuse(r, "box/sidecar.py's mode or blob at HEAD is not the build commit's")

    def test_R2_1_recorded_tree_entries_must_be_the_build_commits(self):
        r = Repo(self, "sidecar")
        r.row["tree_entries"] = {k: ["100755", v[1]] for k, v in r.entries().items()}
        r.commit_record()
        self.refuse(r, "recorded tree entries are not the build commit's")
        r.row["tree_entries"] = r.entries()
        r.commit_record()
        self.assertEqual(r.plan()[0]["image"], "sidecar")

    def test_R2_2_a_log_whose_manifest_list_is_not_the_image_id(self):
        for lists in ((OTHER,), (INDEX, OTHER), ()):
            with self.subTest(lists=lists):
                r = Repo(self)
                r.log = build_log([MANIFEST], lists=lists)
                r.commit_record()
                self.refuse(r, "build log exported manifest list")

    def test_R2_2_a_provenance_of_another_revision_or_context(self):
        for label, edit in (("revision", lambda a: a.update({"vcs:revision": "e" * 40})),
                            ("no revision", lambda a: a.pop("vcs:revision")),
                            ("context", lambda a: a.update({"vcs:localdir:context": "elsewhere"}))):
            with self.subTest(label=label):
                r = Repo(self)
                edit(r.meta["buildx.build.provenance"]["invocation"]["parameters"]["root"]["request"]["args"])
                r.commit_record()
                self.refuse(r, "provenance is not the build of")
        r = Repo(self)
        r.meta.pop("buildx.build.provenance")
        r.commit_record()
        self.refuse(r, "provenance is not the build of")

    def test_R2_3_a_record_with_problems(self):
        r = Repo(self)
        r.record["problems"] = ["take-a: something"]
        r.commit_record()
        self.refuse(r, "the record lists problems")
        del r.record["problems"]
        r.commit_record()
        self.refuse(r, "the record lists problems")

    def test_R2_4_a_tree_is_never_a_blob(self):
        r = Repo(self)
        with self.assertRaisesRegex(w.Refused, "is not a file committed at HEAD"):
            w.head_blob(r.root, "box")


class CheckoutLW3StoreLW4(unittest.TestCase):
    def refuse(self, r, pattern):
        with self.assertRaisesRegex(w.Refused, pattern):
            r.plan()

    def test_a_checkout_not_shown_clean_after(self):
        for value in (False, None, "yes"):
            with self.subTest(value=value):
                r = Repo(self)
                r.record["clean_after"] = value
                r.commit_record()
                self.refuse(r, "clean after the builds")

    def test_no_store_named(self):
        for store in (None, {}, {"driver": "", "driver_status": []}, {"driver": "overlayfs"}):
            with self.subTest(store=store):
                r = Repo(self)
                r.record["store"] = store
                r.commit_record()
                self.refuse(r, "does not name its image store")

    def test_a_manifest_digest_equal_to_the_config_digest(self):
        r = Repo(self)
        r.row["manifest_digest"] = CONFIG
        r.log = build_log([CONFIG], [CONFIG])
        r.commit_record()
        self.refuse(r, "classic-store reading")


class RefusalsDoNotFallThroughL4(unittest.TestCase):
    def test_absent_outside_or_dirty_records_refuse_and_write_nothing(self):
        r = Repo(self)
        before = r.lock_path.read_bytes()
        r.record_path.write_text(json.dumps(dict(r.record, extra=1)))
        with self.assertRaises(w.Refused):
            r.plan()
        for bad in (r.root / "missing.json", Path("/nonexistent/build-record.json")):
            with self.assertRaises((w.Refused, OSError, ValueError)):
                w.plan(il, r.root, bad, r.lock_path, "take-a")
        self.assertEqual(r.lock_path.read_bytes(), before)

    def test_main_returns_1_on_a_refusal(self):
        r = Repo(self)
        r.commit_file("box/Dockerfile", "FROM scratch\nRUN echo changed\n")
        before = r.lock_path.read_bytes()
        buf = io.StringIO()
        with mock.patch.object(w, "load_image_lock", lambda repo: il), redirect_stdout(buf):
            rc = w.main(["--repo", str(r.root), "--record", str(r.record_path), "--lock", str(r.lock_path),
                         "--image", "take-a", "--write"])
        self.assertEqual((rc, r.lock_path.read_bytes()), (1, before))
        self.assertIn("REFUSED", buf.getvalue())


class Rederive(unittest.TestCase):
    """rederive(): the bytes a committed lock must hold, re-derived by plan() from the committed record."""

    def test_a_written_lock_rederives_to_its_own_bytes(self):
        r = Repo(self)
        new, read = r.plan()
        w.write(r.lock_path, new, read)
        self.assertEqual(w.rederive(il, r.root, r.record_path, r.lock_path, "take-a"), r.lock_path.read_bytes())

    def test_a_hand_edited_pin_differs(self):
        r = Repo(self)
        new, read = r.plan()
        w.write(r.lock_path, dict(new, manifest_digest=OTHER), read)
        self.assertNotEqual(w.rederive(il, r.root, r.record_path, r.lock_path, "take-a"), r.lock_path.read_bytes())

    def test_an_unfilled_or_other_lock_refuses(self):
        r = Repo(self)
        with self.assertRaisesRegex(w.Refused, "is not take-a's filled schema-2 lock"):
            w.rederive(il, r.root, r.record_path, r.lock_path, "take-a")
        new, read = r.plan()
        w.write(r.lock_path, new, read)
        with self.assertRaisesRegex(w.Refused, "is not sidecar's filled schema-2 lock"):
            w.rederive(il, r.root, r.record_path, r.lock_path, "sidecar")

    def test_a_rederived_plan_is_never_written(self):
        r = Repo(self)
        new, _ = r.plan()
        with self.assertRaisesRegex(w.Refused, "never written"):
            w.write(r.lock_path, new, None)


class WriteLW6(unittest.TestCase):
    def test_a_lock_changed_after_reading_is_not_overwritten(self):
        r = Repo(self)
        new, read = r.plan()
        r.lock_path.write_text(r.lock_path.read_text() + "\n")
        with self.assertRaisesRegex(w.Refused, "changed since it was read"):
            w.write(r.lock_path, new, read)

    def test_another_writer_holding_the_folder_refuses(self):
        import fcntl
        r = Repo(self)
        new, read = r.plan()
        before = r.lock_path.read_bytes()
        held = os.open(str(r.lock_path.parent), os.O_RDONLY)
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(w.Refused, "another writer holds"):
                w.write(r.lock_path, new, read)
        finally:
            os.close(held)
        self.assertEqual(r.lock_path.read_bytes(), before)
        w.write(r.lock_path, new, read)                        # released: the same write now goes through
        self.assertEqual(il.load(str(r.lock_path))["schema"], 2)


if __name__ == "__main__":
    unittest.main()
