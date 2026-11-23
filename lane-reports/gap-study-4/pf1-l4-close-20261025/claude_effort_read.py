"""Read-only static read of the pinned Claude Code 2.1.296 binary in the take-a image (lane pf1-l4-close, 25 Oct 2026).

No container is created, nothing is copied, nothing is written on athena: `docker image inspect` (a read) names the
image's overlay layer folders, and the binary is read in place from the layer that holds it. Prints one JSON record:
the layer it was read from, the binary's sha256 and size, and bounded contexts around the effort fields.
argv: IMAGE_ID PATTERN_SET (discover | <comma-separated regex keys>) [MAX_CONTEXTS] [HALF_WIDTH]
"""
import hashlib, json, os, re, subprocess, sys

IMAGE = sys.argv[1]
MODE = sys.argv[2] if len(sys.argv) > 2 else "discover"
MAXC = int(sys.argv[3]) if len(sys.argv) > 3 else 6
HALF = int(sys.argv[4]) if len(sys.argv) > 4 else 300
REL = "usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
       "XDG_RUNTIME_DIR": "/run/user/1000", "HOME": os.environ.get("HOME", "/nonexistent")}

p = subprocess.run(["docker", "image", "inspect", "--format", "{{json .GraphDriver}}", IMAGE], env=ENV,
                   capture_output=True, text=True, timeout=120)
graph = json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else None
dirs = []
if graph and isinstance(graph.get("Data"), dict):
    data_ = graph["Data"]
    for key in ("UpperDir", "LowerDir"):
        dirs += [d for d in (data_.get(key) or "").split(":") if d]
found = next((d for d in dirs if os.path.isfile(os.path.join(d, REL))), None)
blob = open(os.path.join(found, REL), "rb").read() if found else b""
entries = []
if not found:
    # containerd image store: no layer folder. `docker save` streams the image (a read) to this process's stdin pipe;
    # each layer tar is read in memory, and the last layer's version of each candidate wins.
    import tarfile
    PKG = "usr/local/lib/node_modules/@anthropic-ai/claude-code/"
    cand = {}
    save = subprocess.Popen(["docker", "save", IMAGE], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outer = tarfile.open(fileobj=save.stdout, mode="r|")
    for m in outer:
        if not m.isfile() or m.size < 1024:
            continue
        f = outer.extractfile(m)
        try:
            inner = tarfile.open(fileobj=f, mode="r|*")
        except tarfile.TarError:
            continue
        try:
            for im in inner:
                name = im.name.lstrip("./")
                if name.startswith(PKG):
                    rec = {"layer": m.name, "name": name, "type": im.type.decode("latin-1"), "size": im.size,
                           "link": im.linkname or None}
                    entries.append(rec)
                    if im.isfile() and (name == REL or im.size > 50_000_000):
                        cand[name] = (m.name, inner.extractfile(im).read())
        except tarfile.TarError as e:
            entries.append({"layer": m.name, "error": str(e)[:200]})
    save.wait(timeout=600)
    bin_entry = [e for e in entries if e.get("name") == REL]
    target = REL
    if bin_entry and bin_entry[-1]["link"]:
        link = bin_entry[-1]["link"]
        target = link.lstrip("/") if link.startswith("/") else os.path.normpath(os.path.join(os.path.dirname(REL), link))
    if target in cand:
        found = "docker save: layer " + cand[target][0] + " member " + target
        blob = cand[target][1]
    entries = [e for e in entries if e.get("size", 0) > 1_000_000 or e.get("name") == REL or e.get("link")][:40]

PATTERNS = {
    "perTurnEffort": rb"perTurnEffort",
    "per_turn_effort_active": rb"per_turn_effort_active",
    "effort_medium": rb"effort[A-Za-z_]{0,20}[:=]\s{0,2}\"medium\"",
    "supportsEffort": rb"[sS]upports?Effort|effortSupported|EffortSupport",
    "opus55": rb"claude-opus-5-5",
    "sonnet55": rb"claude-sonnet-5-5",
    "haiku45": rb"claude-haiku-4-5",
    "defaultEffort": rb"[dD]efaultEffort|DEFAULT_EFFORT|defaultEffortLevel",
    # one whole model-catalog entry per registered model (the entry opens on its id and closes on advisor_rank)
    "catalog_opus55": rb"\{id:\"claude-opus-5-5\",family:[^{}]{0,400}(?:\{[^{}]{0,800}\}[^{}]{0,800}){0,6}advisor_rank:\d+\}",
    "catalog_sonnet55": rb"\{id:\"claude-sonnet-5-5\",family:[^{}]{0,400}(?:\{[^{}]{0,800}\}[^{}]{0,800}){0,6}advisor_rank:\d+\}",
    "catalog_haiku45": rb"\{id:\"claude-haiku-4-5\",family:[^{}]{0,400}(?:\{[^{}]{0,800}\}[^{}]{0,800}){0,6}advisor_rank:\d+\}",
    "catalog_any_haiku45": rb"\{id:\"claude-haiku-4-5[^\"]{0,20}\",family:",
}
keys = list(PATTERNS) if MODE == "discover" else MODE.split(",")


def text(i, j):
    return "".join(ch if 32 <= ord(ch) < 127 else "." for ch in blob[max(0, i):j].decode("latin-1"))


out = {"image": IMAGE, "inspect_rc": p.returncode, "graph_driver": (graph or {}).get("Name"),
       "layer_dirs": len(dirs), "read_from": found, "binary_path_in_image": "/" + REL,
       "binary_sha256": hashlib.sha256(blob).hexdigest() if blob else None, "binary_bytes": len(blob),
       "package_entries": entries, "hits": {}}
for k in keys:
    rx = PATTERNS.get(k, k.encode())
    ms = list(re.finditer(rx, blob))
    out["hits"][k] = {"count": len(ms), "offsets": [m.start() for m in ms[:50]],
                      "contexts": [text(m.start() - HALF, m.end() + HALF) for m in ms[:MAXC]]}
print(json.dumps(out, indent=1, sort_keys=True))
