"""Count the folders each task half's fixture adds to a run tree (box lane, 14 Oct; term D of the watch bound)."""
import json, os, shutil, sys, tempfile, io, contextlib
from pathlib import Path
G = Path("/Users/javrodher/aegis-builds/gap4-live-box-20261013/evals/gap-study-4")
BASE = Path("/Users/javrodher/aegis-builds/gap4-export-20261014/admitted-20261014")
sys.path.insert(0, str(G)); sys.dont_write_bytecode = True
import drive
out = []
for tf in sorted((G / "tasks").glob("*.json")):
    task = json.loads(tf.read_text())
    for half, h in sorted(task.get("halves", {}).items()):
        fx = h.get("fixture")
        if not fx:
            continue
        work = Path(tempfile.mkdtemp(dir=sys.argv[1]))
        tree = work / "tree"; shutil.copytree(BASE, tree, symlinks=True)
        before = sum(1 for p in tree.rglob("*") if p.is_dir() and not p.is_symlink())
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rec, src = drive.build_take_fixture(fx, tree, "run-0000abcd")
            ok = rec is not None
        except BaseException as e:  # noqa
            ok, rec = False, f"{type(e).__name__}: {str(e)[:200]}"
        after = sum(1 for p in tree.rglob("*") if p.is_dir() and not p.is_symlink())
        out.append({"task": tf.stem, "half": half, "kind": fx.get("kind"), "built": ok,
                    "dirs_before": before, "dirs_after": after, "added": after - before,
                    "note": None if ok else str(rec)[:200]})
        shutil.rmtree(work)
print(json.dumps(out, indent=1))
