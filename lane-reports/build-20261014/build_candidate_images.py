"""Build the sidecar and take images on athena from one commit's box source (box lane, 14 Oct 2026).

glitch-06 ruling 3: the production CANDIDATE build, for independent review. Build inputs are the provisional
lock values recorded as evidence (lane-reports/provisional-image-locks-20261014.json), handed to
image_lock.build_argv as hand-filled dicts; nothing is written at any lock path. Each argv is build_argv's with
only --iidfile added. After each build: the image id, image_lock's own label check, and for the sidecar the
sha256 of the baked /opt/w/sidecar.py against the commit's. No push, no login, no credential, no model.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SRC, PROVISIONAL, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(SRC))
from box import image_lock as il  # noqa: E402

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": os.environ["HOME"],
       "DOCKER_HOST": "unix:///run/user/1000/docker.sock", "XDG_RUNTIME_DIR": "/run/user/1000"}
IMAGES = ("box/sidecar/image.lock", "box/image.lock", "box/codex/image.lock", "box/gemini/image.lock")


def run(argv, log):
    with open(log, "x") as fh:
        p = subprocess.run(argv, env=ENV, stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return p.returncode


def main():
    OUT.mkdir(mode=0o700)
    prov = json.loads(PROVISIONAL.read_bytes())
    record = {"scope": "production CANDIDATE build for review; provisional lock inputs; no lock written",
              "box_dir": il.BOX_DIR, "images": []}
    sidecar_sha = hashlib.sha256((SRC / "box" / "sidecar.py").read_bytes()).hexdigest()
    try:
        for rel in IMAGES:
            lock = dict(prov["locks"][rel]["content"])
            # build_args never reads image_id; the provisional id stays only so the dict validates as it did.
            name = lock["image"]
            iid = OUT / f"{name}.iid"
            argv = il.build_argv(lock, context=il.BOX_DIR)
            argv = argv[:-1] + ["--iidfile", str(iid), argv[-1]]
            rc = run(argv, OUT / f"{name}.build.log")
            row = {"image": name, "argv": argv, "exit": rc,
                   "image_id": iid.read_text().strip() if iid.exists() else None,
                   "provisional_image_id": prov["locks"][rel]["content"]["image_id"]}
            if row["image_id"]:
                insp = subprocess.run(["docker", "image", "inspect", row["image_id"]], env=ENV,
                                      capture_output=True, text=True, timeout=60)
                doc = json.loads(insp.stdout)[0]
                labels = (doc.get("Config") or {}).get("Labels") or {}
                row["labels"] = labels
                row["label_problems"] = il.check_labels(dict(lock, image_id=row["image_id"]), doc)
                if name == il.SIDECAR_IMAGE:
                    got = subprocess.run(["docker", "run", "--rm", "--pull=never", "--network", "none", row["image_id"],
                                          "python3", "-I", "-c",
                                          "import hashlib;print(hashlib.sha256(open('/opt/w/sidecar.py','rb').read()).hexdigest())"],
                                         env=ENV, capture_output=True, text=True, timeout=120)
                    row["baked_sidecar_sha256"] = got.stdout.strip()
                    row["commit_sidecar_sha256"] = sidecar_sha
                    row["sidecar_bound"] = got.stdout.strip() == sidecar_sha
            record["images"].append(row)
            if rc:
                break
    finally:
        with open(OUT / "build-record.json", "x") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
            fh.write("\n")


if __name__ == "__main__":
    main()
