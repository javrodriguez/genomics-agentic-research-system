"""The environment-name sweep of the pinned Gemini CLI (glitch-06, 14 Oct 2026), run on athena as javier. The package
folder is copied out of the pinned take-g image (box/gemini/image.lock image_id) with `docker create` + `docker cp`,
never run; the container is removed. Every text file of the package (dependencies included) is read for three kinds of
environment access: `process.env.NAME`, `env["NAME"]` / `env['NAME']` (any object called env, process.env included),
and the vendor-name regex over all text. Prints one JSON record: per name, its count per kind and up to three files.
Usage: python3 -I gemini_env_name_sweep.py <image id> <work folder>"""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK = sys.argv[1], sys.argv[2]
PKG = "/usr/local/lib/node_modules/@google/gemini-cli"
ENV = dict(os.environ, DOCKER_HOST="unix:///run/user/1000/docker.sock")
def run(argv):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=600)
    return {"argv": argv, "rc": p.returncode, "stdout": p.stdout.strip()[:200], "stderr": p.stderr.strip()[:300]}
steps = []
create = run(["docker", "create", "--pull=never", "--network", "none", IMAGE, "true"])
steps.append(create)
cid = create["stdout"]
out = os.path.join(WORK, "pkg")
if create["rc"] == 0 and re.fullmatch(r"[0-9a-f]{64}", cid):
    try:
        steps.append(run(["docker", "cp", f"{cid}:{PKG}", out]))
    finally:
        steps.append(run(["docker", "rm", cid]))
KINDS = {
    "process.env.X": re.compile(rb"process\.env\.([A-Za-z_][A-Za-z0-9_]*)"),
    "env[X]": re.compile(rb"\benv\s*\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"),
    "vendor-regex": re.compile(rb"(?<![A-Za-z0-9_])((?:GEMINI|GOOGLE|CLOUDSDK|VERTEX|GCP|GCLOUD|CLOUD_ML|CODEX|OPENAI|"
                               rb"AWS|AZURE|ANTHROPIC)_[A-Z0-9_]+|[A-Z0-9_]*VERTEX[A-Z0-9_]*)(?![A-Za-z0-9_])"),
}
TEXT = (".js", ".cjs", ".mjs", ".json", ".ts", ".md", ".txt", ".sh", ".toml", ".yaml", ".yml")
names, files_read, digest = {}, 0, hashlib.sha256()
package_version = None
for root, dirs, files in os.walk(out):
    dirs.sort()
    for f in sorted(files):
        p = os.path.join(root, f)
        if not f.endswith(TEXT) or os.path.islink(p):
            continue
        data = open(p, "rb").read()
        rel = os.path.relpath(p, out)
        digest.update(rel.encode() + b"\0" + hashlib.sha256(data).digest())
        files_read += 1
        if rel == "package.json":
            package_version = json.loads(data).get("version")
        for kind, rx in KINDS.items():
            for m in rx.finditer(data):
                n = m.group(1).decode()
                e = names.setdefault(n, {"kinds": {}, "files": []})
                e["kinds"][kind] = e["kinds"].get(kind, 0) + 1
                if rel not in e["files"] and len(e["files"]) < 3:
                    e["files"].append(rel)
print(json.dumps({"probe": "gemini-env-name-sweep", "image": IMAGE, "package_path": PKG,
                  "package_version": package_version, "text_files_read": files_read,
                  "package_text_digest": digest.hexdigest(), "extraction": steps,
                  "patterns": {k: v.pattern.decode() for k, v in KINDS.items()}, "names_found": len(names),
                  "names": names}, indent=1, sort_keys=True))
