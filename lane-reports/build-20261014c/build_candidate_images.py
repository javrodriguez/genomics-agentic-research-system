"""(14 Oct, c: the build record ops/write_image_lock.py reads) Build images on athena from a clean checkout.

    python3 -B -I build_candidate_images.py <checkout> <out> <provisional-locks, checkout-relative> [<lock>,...]

<lock> is a lock path relative to <checkout>/evals/gap-study-4 (default box/sidecar/image.lock).

The record is schema 3 (glitch-06's rulings on the lock-writer review, 14 Oct 2026):
  - LW-3: source_commit is `git rev-parse HEAD` of <checkout>, which must be a clean checkout (no change, no
    untracked file) before the first build and again after the last; it is never an argument.
  - LW-1 (ii): every input a build reads is recorded by its checkout-relative path and sha256: the image's
    Dockerfile, every COPY source (parsed by image_lock's own parser), and the provisional-locks file the lock inputs
    come from; each must equal HEAD's blob before the build. `lock_inputs_sha256` is the canonical JSON of the inputs.
  - LW-2: each build adds only --iidfile and --metadata-file to image_lock.build_argv(the unfilled lock); its
    metadata file and its build log (BuildKit plain progress) sit beside build-record.json and are committed with it.
    Measured on athena (14 Oct 03:37 EDT, docker 29.8.1, buildx 0.37.1, containerd store): the metadata file names
    only the image index (containerimage.digest and containerimage.descriptor), never containerimage.config.digest.
    So the index id is bound to the metadata, and the manifest and config digests to the log's one `exporting
    manifest` and one `exporting config` line; the manifest is also read back by `docker image inspect --platform`.
  - LW-4: the image store (`docker info`: Driver and DriverStatus) is recorded.
  - review 2 (R2-1, R2-2): each input's `git ls-tree` mode and blob id are recorded (`tree_entries`); the log's one
    `exporting manifest list` line must be the iidfile's id, and the metadata's provenance must name HEAD.
  - the sidecar's baked /opt/w/sidecar.py is hashed and must equal the recorded sidecar.py input (script b's check).
Nothing is written at any lock path; no push, login, credential or model. It exits 1 on any problem.
"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
CHECKOUT, OUT, PROVISIONAL = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), sys.argv[3]
IMAGES = tuple(sys.argv[4].split(",")) if len(sys.argv) > 4 else ("box/sidecar/image.lock",)
SRC = CHECKOUT / "evals" / "gap-study-4"
sys.path.insert(0, str(SRC))
from box import image_lock as il  # noqa: E402

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": os.environ["HOME"], "BUILDKIT_PROGRESS": "plain",
       "DOCKER_HOST": "unix:///run/user/1000/docker.sock", "XDG_RUNTIME_DIR": "/run/user/1000"}
GIT_ENV = {"PATH": "/usr/bin:/bin", "HOME": os.environ["HOME"], "GIT_CONFIG_NOSYSTEM": "1"}
PLATFORM = "linux/amd64"
INPUTS = ("base", "harness", "python", "users", "squid")
SIDECAR_PROGRAM_SRC = "sidecar.py"


def git(*args) -> str:
    p = subprocess.run(["git", "-C", str(CHECKOUT), *args], env=GIT_ENV, capture_output=True, timeout=120)
    if p.returncode != 0:
        raise SystemExit(f"git {args[0]} failed: {p.stderr.decode(errors='replace').strip()}")
    return p.stdout.decode()


def clean_head() -> str:
    if Path(git("rev-parse", "--show-toplevel").strip()).resolve() != CHECKOUT:
        raise SystemExit("<checkout> is not the top of its git checkout")
    dirty = git("status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise SystemExit("the checkout is not clean:\n" + dirty)
    head = git("rev-parse", "HEAD").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise SystemExit("HEAD is not a 40-hex commit id")
    return head


def sha_of_input(rel: str) -> str:
    """The sha256 of the checkout file `rel`, refused unless its bytes are HEAD's blob."""
    data = (CHECKOUT / rel).read_bytes()
    head = subprocess.run(["git", "-C", str(CHECKOUT), "cat-file", "blob", "HEAD:" + rel], env=GIT_ENV,
                          capture_output=True, timeout=60)
    if head.returncode != 0 or head.stdout != data:
        raise SystemExit(f"{rel} is not HEAD's blob")
    return hashlib.sha256(data).hexdigest()


def copy_sources(dockerfile_text: str) -> list:
    """Every COPY source of the Dockerfile, relative to the build context (no flag, no glob, no parent step)."""
    out = []
    for ins in il.parse_dockerfile(dockerfile_text):
        if ins.keyword in ("COPY", "ADD"):
            words = shlex.split(ins.args)
            if ins.keyword == "ADD" or len(words) < 2 or any(w.startswith("-") for w in words) \
                    or any(set(w) & set("*?[") or ".." in w.split("/") or w.startswith("/") for w in words[:-1]):
                raise SystemExit(f"line {ins.line}: a COPY this script does not read: {ins.args!r}")
            out += words[:-1]
    return out


def tree_entry(rel: str) -> list:
    """[mode, blob id] of `rel` in HEAD's tree."""
    line = git("ls-tree", "--full-tree", "HEAD", "--", rel).splitlines()
    if len(line) != 1 or line[0].split("\t")[0].split(" ")[1] != "blob":
        raise SystemExit(f"{rel} is not one blob in HEAD's tree")
    mode, _, oid = line[0].split("\t")[0].split(" ")
    return [mode, oid]


def canonical(doc) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def rel_to_checkout(path: str) -> str:
    return Path(path).resolve().relative_to(CHECKOUT).as_posix()


def main() -> int:
    head = clean_head()
    if OUT.resolve().is_relative_to(CHECKOUT):
        raise SystemExit("<out> must be outside the checkout")
    OUT.mkdir(mode=0o700)
    info = json.loads(subprocess.run(["docker", "info", "--format", "{{json .}}"], env=ENV, capture_output=True,
                                     text=True, timeout=60, check=True).stdout)
    prov_sha = sha_of_input(PROVISIONAL)
    prov = json.loads((CHECKOUT / PROVISIONAL).read_bytes())
    record = {"schema": 3, "source_commit": head, "checkout": str(CHECKOUT), "box_dir": il.BOX_DIR,
              "store": {"driver": info.get("Driver"), "driver_status": info.get("DriverStatus")},
              "lock_inputs_source": {"path": PROVISIONAL, "sha256": prov_sha}, "images": []}
    problems = []
    try:
        for rel in IMAGES:
            lock = {k: v for k, v in prov["locks"][rel]["content"].items()}
            lock.update(schema=il.SCHEMA, image_id=il.PENDING, pending={"image_id": "this build makes it"})
            name = lock["image"]
            dockerfile = os.path.join(il.BOX_DIR, lock["dockerfile"])
            inputs = {rel_to_checkout(dockerfile): sha_of_input(rel_to_checkout(dockerfile))}
            for src in copy_sources((CHECKOUT / rel_to_checkout(dockerfile)).read_text(encoding="utf-8")):
                r = rel_to_checkout(os.path.join(il.BOX_DIR, src))
                inputs[r] = sha_of_input(r)
            lock_inputs = {k: lock[k] for k in INPUTS if k in lock}
            iid, meta, log = OUT / f"{name}.iid", OUT / f"{name}.metadata.json", OUT / f"{name}.build.log"
            argv = il.build_argv(lock, context=il.BOX_DIR)
            argv = argv[:-1] + ["--iidfile", str(iid), "--metadata-file", str(meta), argv[-1]]
            with open(log, "x") as fh:
                rc = subprocess.run(argv, env=ENV, stdout=fh, stderr=subprocess.STDOUT, timeout=3600).returncode
            row = {"image": name, "lock": rel, "argv": argv, "exit": rc, "inputs": inputs,
                   "tree_entries": {r: tree_entry(r) for r in sorted(inputs)},
                   "lock_inputs": lock_inputs, "lock_inputs_sha256": hashlib.sha256(canonical(lock_inputs)).hexdigest(),
                   "metadata_file": meta.name, "build_log": log.name}
            if rc == 0:
                row["image_id"] = iid.read_text().strip()
                md = json.loads(meta.read_text())
                desc = md.get("containerimage.descriptor") or {}
                if md.get("containerimage.digest") != row["image_id"] or desc.get("digest") != row["image_id"]:
                    problems.append(f"{name}: the metadata file's index is not the iidfile's {row['image_id']}")
                text = log.read_text()
                configs = sorted(set(re.findall(r"^#\d+ exporting config (sha256:[0-9a-f]{64})(?: |$)", text, re.MULTILINE)))
                row["config_digest"] = configs[0] if len(configs) == 1 else None
                if row["config_digest"] is None:
                    problems.append(f"{name}: the build log exported configs {configs}, not one")
                got = subprocess.run(["docker", "image", "inspect", "--platform", PLATFORM, "--format", "{{json .Id}}",
                                      row["image_id"]], env=ENV, capture_output=True, text=True, timeout=60)
                row["manifest_digest"] = json.loads(got.stdout) if got.returncode == 0 else None
                logged = re.findall(r"^#\d+ exporting manifest (sha256:[0-9a-f]{64})(?: |$)", text, re.MULTILINE)
                row["logged_manifests"] = sorted(set(logged))
                lists = sorted(set(re.findall(r"^#\d+ exporting manifest list (sha256:[0-9a-f]{64})(?: |$)", text,
                                              re.MULTILINE)))
                if lists != [row["image_id"]]:
                    problems.append(f"{name}: the build log's manifest list {lists} is not the iidfile's")
                prov = (((md.get("buildx.build.provenance") or {}).get("invocation") or {}).get("parameters") or {})
                if ((prov.get("root") or {}).get("request") or {}).get("args", {}).get("vcs:revision") != head:
                    problems.append(f"{name}: the provenance does not name {head}")
                if row["logged_manifests"] != [row["manifest_digest"]]:
                    problems.append(f"{name}: the build log's manifest {row['logged_manifests']} is not the inspected "
                                    f"{row['manifest_digest']}")
                doc = json.loads(subprocess.run(["docker", "image", "inspect", row["image_id"]], env=ENV,
                                                capture_output=True, text=True, timeout=60).stdout)[0]
                filled = dict(lock, image_id=row["image_id"], pending={})
                row["label_problems"] = il.check_labels(dict(filled, schema=il.SCHEMA_2, **{
                    "manifest_digest": row["manifest_digest"] or "sha256:" + "0" * 64,
                    "config_digest": row["config_digest"] or "sha256:" + "0" * 64, "source_commit": head}), doc)
                if row["label_problems"]:
                    problems.append(f"{name}: labels {row['label_problems']}")
                if name == il.SIDECAR_IMAGE:
                    baked = subprocess.run(["docker", "run", "--rm", "--pull=never", "--network", "none", row["image_id"],
                                            "python3", "-I", "-c", "import hashlib;print(hashlib.sha256(open("
                                            f"{il.SIDECAR_PROGRAM!r},'rb').read()).hexdigest())"],
                                           env=ENV, capture_output=True, text=True, timeout=120)
                    row["baked_sidecar_sha256"] = baked.stdout.strip() if baked.returncode == 0 else None
                    want = inputs.get(rel_to_checkout(os.path.join(il.BOX_DIR, SIDECAR_PROGRAM_SRC)))
                    if row["baked_sidecar_sha256"] != want:
                        problems.append(f"sidecar: the baked program {row['baked_sidecar_sha256']} is not {want}")
            else:
                problems.append(f"{name}: build exit {rc}")
            record["images"].append(row)
            if rc:
                break
        record["clean_after"] = clean_head() == head
        if not record["clean_after"]:
            problems.append("HEAD moved during the builds")
    finally:
        record["problems"] = problems
        with open(OUT / "build-record.json", "x") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
            fh.write("\n")
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
