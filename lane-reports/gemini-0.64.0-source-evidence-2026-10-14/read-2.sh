#!/bin/bash
# Read-only source read of the pinned Gemini CLI 0.64.0 bundle on athena: create (never start) a container from the
# pinned image, copy the bundle out, remove the container by its id, hash and extract text. Gemini is never executed.
set -euo pipefail
export DOCKER_HOST=unix:///run/user/1000/docker.sock
IMAGE=sha256:4294b1ce3fc0f3c0a9ca7b789f73c613c2baa56e4e0381229a8db3301a707216
TMP=$(mktemp -d "$HOME/gap4-harness-srcread-XXXXXX")
CID=$(docker create --pull=never --network none "$IMAGE" /bin/true)
echo "container_created=$CID" >&2
set +e
docker cp "$CID:/usr/local/lib/node_modules/@google/gemini-cli/bundle" "$TMP/bundle" >&2
CP1=$?
docker cp "$CID:/usr/local/lib/node_modules/@google/gemini-cli/package.json" "$TMP/package.json" >&2
CP2=$?
docker rm "$CID" >&2
RM=$?
set -e
echo "cp_bundle=$CP1 cp_package=$CP2 rm=$RM" >&2
python3 -I -S - "$TMP" <<'PY'
import hashlib, json, pathlib, sys
tmp = pathlib.Path(sys.argv[1])
pkg = json.loads((tmp / "package.json").read_text())
out = {"package_version": pkg.get("version"), "pinned_chunk_ok": None, "files": {}, "extracts": []}
RANGES = [(12563400, 12568600), (14255400, 14261000), (14287000, 14292300)]
p = tmp / "bundle" / "chunk-J7SXW2FI.js"
b = p.read_bytes(); t = b.decode("utf-8")
out["pinned_chunk_ok"] = hashlib.sha256(b).hexdigest() == "e2aca15290b02dc9845704f3fed44c577919652508624f340974f0ff588f206e" and len(b) == 16755387
out["extracts"] = [{"file": p.name, "start": a, "end": z, "text": t[a:z]} for a, z in RANGES]
print(json.dumps(out))
PY
rm -rf "$TMP"
echo "cleaned=$TMP" >&2
