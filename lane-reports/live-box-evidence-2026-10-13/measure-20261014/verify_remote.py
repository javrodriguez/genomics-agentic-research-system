import hashlib, json, os, stat, sys
from pathlib import Path
child = Path(sys.argv[1]); want_manifest_sha = sys.argv[2]
mb = (child / "transfer-manifest-20261014.json").read_bytes()
assert hashlib.sha256(mb).hexdigest() == want_manifest_sha, "transfer manifest sha differs"
man = json.loads(mb)
tree = child / "admitted-20261014"
files, dirs = [], []
for p in sorted(tree.rglob("*")):
    st = p.lstat(); rel = p.relative_to(tree).as_posix()
    parts = [x.casefold() for x in rel.split("/")]
    assert parts[-1] not in (".gitleaksignore", ".gitleaks.toml") and ".git" not in parts, "control/.git " + rel
    if stat.S_ISDIR(st.st_mode):
        dirs.append({"path": rel, "mode": stat.S_IMODE(st.st_mode)}); continue
    assert stat.S_ISREG(st.st_mode), "nonregular " + rel
    d = p.read_bytes()
    files.append({"path": rel, "bytes": len(d), "mode": stat.S_IMODE(st.st_mode), "sha256": hashlib.sha256(d).hexdigest()})
inv = {"files": sorted(files, key=lambda r: r["path"]), "directories": sorted(dirs, key=lambda r: r["path"])}
inv_sha = hashlib.sha256(json.dumps(inv, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
side_ok = 0
for r in man["side_files"]:
    d = (child / "side-20261014" / r["path"]).read_bytes()
    side_ok += hashlib.sha256(d).hexdigest() == r["sha256"] and len(d) == r["bytes"]
fdiff = [r["path"] for r in inv["files"] if r not in man["tree_inventory"]["files"]] + \
        [r["path"] for r in man["tree_inventory"]["files"] if r not in inv["files"]]
ddiff = [r for r in inv["directories"] if r not in man["tree_inventory"]["directories"]] + \
        [r for r in man["tree_inventory"]["directories"] if r not in inv["directories"]]
print(json.dumps({"files": len(inv["files"]), "directories": len(inv["directories"]),
                  "bytes": sum(r["bytes"] for r in inv["files"]), "inventory_sha256": inv_sha,
                  "inventory_equal": inv == man["tree_inventory"], "inventory_sha_equal": inv_sha == man["tree_inventory_sha256"],
                  "side_verified": side_ok, "side_total": len(man["side_files"]),
                  "file_diffs": fdiff[:10], "dir_diffs": ddiff[:10], "tree_uid_is_me": tree.stat().st_uid == os.getuid()}))
