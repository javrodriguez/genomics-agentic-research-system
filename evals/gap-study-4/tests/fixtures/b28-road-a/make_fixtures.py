#!/usr/bin/env python3
"""Lane vendor-b28 (glitch-f1's ruling O5, 21 Oct 2026): the road (a) fixtures are the RAW stub-model probe records.

Synthetic CLI output only: each session file was written by the pinned gemini-cli 0.64.0 in the locked take-g image
against lane vendor-b27's scripted stub model (box/stub_model_server.py), on synthetic files; never a study take, never
a model's words. Kept raw (not cut), so every byte the reader sees is the CLI's own.

For each scenario the LAST snapshot is stored once as <scenario>-native-last.jsonl; every earlier snapshot is a byte
prefix of the next (checked here), so PROVENANCE.json records each snapshot's byte length and sha256, and the tests
rebuild snapshot k as last[:bytes_k] and check its sha256. PROVENANCE.json also names the probe folder, the B27 head that
produced it, the fetch tar's sha256, the folder's manifest.json sha256 and each source file's sha256 as its manifest
records it (checked against the file here).

    python3 -I -B make_fixtures.py <probe folder> <out folder> --head <sha> --tar-sha256 <hex> [--scenarios A1,A2,...]

Standard library only; reads the probe folder, writes only <out folder>/<scenario>-native-last.jsonl and a PROVENANCE
fragment printed as JSON (the caller merges fragments for more than one probe folder).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def snapshots(folder: Path) -> list:
    return sorted((folder / "session").glob("native-turn-*.jsonl"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("probe")
    p.add_argument("out")
    p.add_argument("--head", required=True)
    p.add_argument("--tar-sha256", required=True)
    p.add_argument("--scenarios", required=True)
    a = p.parse_args(argv)
    probe, out = Path(a.probe), Path(a.out)
    manifest_raw = (probe / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)["files"]
    frag = {"probe_folder": str(probe), "b27_head": a.head, "fetch_tar_sha256": a.tar_sha256,
            "manifest_sha256": sha(manifest_raw), "scenarios": {}}
    for name in a.scenarios.split(","):
        snaps = snapshots(probe / name)
        if not snaps:
            raise SystemExit(f"{name}: no snapshot")
        datas = [s.read_bytes() for s in snaps]
        for k in range(1, len(datas)):
            if not datas[k].startswith(datas[k - 1]):
                raise SystemExit(f"{name}: snapshot {k} is not a byte prefix of snapshot {k + 1}")
        rows = []
        for s, d in zip(snaps, datas):
            rel = f"{name}/session/{s.name}"
            if manifest.get(rel, {}).get("sha256") != sha(d) or manifest[rel].get("bytes") != len(d):
                raise SystemExit(f"{rel}: differs from its manifest entry")
            rows.append({"source": rel, "bytes": len(d), "sha256": sha(d)})
        target = out / f"{name}-native-last.jsonl"
        if target.exists():
            raise SystemExit(f"{target} exists; fixtures are written once")
        target.write_bytes(datas[-1])
        frag["scenarios"][name] = {"file": target.name, "snapshots": rows}
    print(json.dumps(frag, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
