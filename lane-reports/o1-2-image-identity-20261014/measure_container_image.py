"""O1-2 (review-box-o1.md): does `docker container inspect`'s .Image equal the image id a container was created from?

Run on athena, fed over ssh stdin (python3 - <args>), against the committed record's three image ids. For each: one
`docker create` by the id (no start, no network, no model, no mount), inspect, remove by the new container's id.
Prints one JSON object. Writes nothing on athena; touches no lock, credential or login.
    python3 - <take-a id> <sidecar id> <egress id>
"""
import json
import subprocess
import sys

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
       "XDG_RUNTIME_DIR": "/run/user/1000", "HOME": "/nonexistent"}


def run(argv):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=120)
    return {"argv": argv, "rc": p.returncode, "out": p.stdout.strip(), "err": p.stderr.strip()[:300]}


out = {"docker": run(["docker", "version", "--format", "{{.Server.Version}}"])["out"],
       "driver_status": run(["docker", "info", "--format", "{{json .DriverStatus}}"])["out"], "rows": []}
for role, image in zip(("take-a", "sidecar", "egress"), sys.argv[1:4]):
    row = {"role": role, "created_from": image}
    row["image_inspect_id"] = run(["docker", "image", "inspect", "--format", "{{json .Id}}", image])["out"]
    row["platform_manifest"] = run(["docker", "image", "inspect", "--platform", "linux/amd64", "--format",
                                    "{{json .Id}}", image])["out"]
    c = run(["docker", "create", "--pull=never", "--network", "none", image, "sleep", "1"])
    row["create"] = {"argv": c["argv"], "rc": c["rc"], "err": c["err"]}
    cid = c["out"]
    if c["rc"] == 0 and len(cid) == 64:
        ins = run(["docker", "container", "inspect", "--format", "{{json .Image}} {{json .Config.Image}}", cid])
        row["container_image"], row["config_image"] = (json.loads(x) for x in ins["out"].split(" ", 1))
        row["rm_rc"] = run(["docker", "rm", "--force", cid])["rc"]
        row["left_after_rm"] = run(["docker", "ps", "-a", "-q", "--no-trunc", "--filter", f"id={cid}"])["out"]
        row["image_equals_created_from"] = row["container_image"] == image
    out["rows"].append(row)
print(json.dumps(out, indent=1, sort_keys=True))
