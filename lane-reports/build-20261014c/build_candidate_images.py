"""(14 Oct, c: a schema-2 build record for ops/write_image_lock.py) Build images on athena from one commit's box source.

    build_candidate_images.py <src> <provisional-locks.json> <out> <source commit> [<lock path>,...]

As build b, plus what the lock writer needs (glitch-06's lock-writer rulings, 14 Oct 2026): each build input is the
provisional values as an UNFILLED schema-1 lock (image_id PENDING), handed to image_lock.build_argv; each build adds
only --iidfile and --metadata-file (BuildKit's record of the config digest); after it, the platform manifest digest
from `docker image inspect --platform linux/amd64`. The record is schema 2: source_commit, and per image its exit,
image_id, manifest_digest, config_digest, label check and lock_inputs. Nothing is written at any lock path; no push,
login, credential or model. PREPARED, NOT RUN at the time of writing.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SRC, PROVISIONAL, OUT, COMMIT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
IMAGES = tuple(sys.argv[5].split(",")) if len(sys.argv) > 5 else ("box/sidecar/image.lock",)
sys.path.insert(0, str(SRC))
from box import image_lock as il  # noqa: E402

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": os.environ["HOME"],
       "DOCKER_HOST": "unix:///run/user/1000/docker.sock", "XDG_RUNTIME_DIR": "/run/user/1000"}
PLATFORM = "linux/amd64"
INPUTS = ("base", "harness", "python", "users", "squid")


def main():
    if not re.fullmatch(r"[0-9a-f]{40}", COMMIT):
        raise SystemExit("the source commit is a 40-hex id")
    OUT.mkdir(mode=0o700)
    prov = json.loads(PROVISIONAL.read_bytes())
    record = {"schema": 2, "source_commit": COMMIT, "box_dir": il.BOX_DIR, "images": []}
    try:
        for rel in IMAGES:
            lock = dict(prov["locks"][rel]["content"])
            lock.update(schema=il.SCHEMA, image_id=il.PENDING, pending={"image_id": "this build makes it"})
            name = lock["image"]
            iid, meta = OUT / f"{name}.iid", OUT / f"{name}.metadata.json"
            argv = il.build_argv(lock, context=il.BOX_DIR)
            argv = argv[:-1] + ["--iidfile", str(iid), "--metadata-file", str(meta), argv[-1]]
            with open(OUT / f"{name}.build.log", "x") as fh:
                rc = subprocess.run(argv, env=ENV, stdout=fh, stderr=subprocess.STDOUT, timeout=3600).returncode
            row = {"image": name, "argv": argv, "exit": rc, "lock_inputs": {k: lock[k] for k in INPUTS if k in lock}}
            if rc == 0:
                row["image_id"] = iid.read_text().strip()
                md = json.loads(meta.read_text())
                row["config_digest"] = md.get("containerimage.config.digest")
                got = subprocess.run(["docker", "image", "inspect", "--platform", PLATFORM, "--format", "{{json .Id}}",
                                      row["image_id"]], env=ENV, capture_output=True, text=True, timeout=60)
                row["manifest_digest"] = json.loads(got.stdout) if got.returncode == 0 else None
                doc = json.loads(subprocess.run(["docker", "image", "inspect", row["image_id"]], env=ENV,
                                                capture_output=True, text=True, timeout=60).stdout)[0]
                filled = dict(lock, image_id=row["image_id"], pending={})
                row["label_problems"] = il.check_labels(dict(filled, schema=il.SCHEMA_2, **{
                    "manifest_digest": row["manifest_digest"] or "sha256:" + "0" * 64,
                    "config_digest": row["config_digest"] or "sha256:" + "0" * 64, "source_commit": COMMIT}), doc)
            record["images"].append(row)
            if rc:
                break
    finally:
        with open(OUT / "build-record.json", "x") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
            fh.write("\n")


if __name__ == "__main__":
    main()
