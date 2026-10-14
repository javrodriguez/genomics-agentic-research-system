"""Box lane, 14 Oct 2026: source-level in-memory mutants of ops/write_image_lock.py; each must turn
tests/test_write_image_lock.py red. Run: /usr/local/bin/python3.13 -B <this file> after a light gate.

Extended for the lock-writer review fold (LW-1 to LW-7): the pre-fold writer (0c15b12b, as at 0f7cdbfd) is run first
against today's tests (red-first: the review's witnesses L1-L3 were accepted by it), then one mutant per new guard,
then the image_lock and preflight mutants that test_preflight's C2-pending and sidecar-manifest cases must kill.
Each line prints RED (failfast: the first failing test) or ALIVE; the script exits 1 if anything stays ALIVE."""
import io, subprocess, sys, types, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "evals/gap-study-4/tests"
sys.path.insert(0, str(T)); sys.path.insert(0, str(T.parent)); sys.dont_write_bytecode = True
import test_write_image_lock as tw
SRC = (ROOT / "ops/write_image_lock.py").read_text()
PRE_FOLD = subprocess.run(["git", "-C", str(ROOT), "show", "0f7cdbfd:ops/write_image_lock.py"], check=True,
                          capture_output=True, text=True).stdout
mutants = [
 ("committed check off", '_need(data == blob, f"{rel} differs from its committed bytes")', 'pass'),
 ("ancestor check off", '_need(is_ancestor(repo, commit), f"the build commit {commit} is not an ancestor of HEAD")', 'pass'),
 ("exit check off", '_need(row.get("exit") == 0 and type(row.get("exit")) is int, f"{image}\'s build did not exit 0")', 'pass'),
 ("label check off", '_need(row.get("label_problems") == [], f"{image}\'s labels did not check clean")', 'pass'),
 ("digest check off", '_need(isinstance(row.get(k), str) and DIGEST.fullmatch(row[k]) is not None, f"{image}\'s {k} is not a digest")', 'pass'),
 ("one row not required", '_need(len(rows) == 1, f"the record holds {len(rows)} rows for {image}, not one")', 'pass'),
 ("unresolved input allowed", '_need(field in inputs, f"{image}\'s record does not resolve {field}")', 'if field not in inputs: continue'),
 ("changed input allowed", '_need(have == want, f"{image}\'s {field} differs from the record\'s")', 'pass'),
 ("schema-1 lock not required", '_need(lock["schema"] == il.SCHEMA, "the lock is not the unfilled schema-1 lock")', 'pass'),
 ("changed-since-read not checked", '_need(fh.read() == read_bytes, "the lock changed since it was read")', 'pass'),
 ("record schema not checked", '_need(isinstance(record, dict) and record.get("schema") == RECORD_SCHEMA,', '_need(True,'),
 # LW-1
 ("LW-1 input shas not compared with HEAD", '_need(hashlib.sha256(head_blob(repo, rel)).hexdigest() == sha,', '_need(True,'),
 ("LW-1 recorded input set not compared", '_need(sorted(inputs) == sorted(want),', '_need(True,'),
 ("LW-1 inputs check not called", '    check_inputs(il, repo, record, row, lock, Path(lock_path), commit)\n', ''),
 ("LW-1 COPY sources not read", 'out += words[:-1]', 'pass'),
 ("LW-1 unbound context reads allowed", '_need(ins.keyword == "COPY" and len(words) >= 2', '_need(True or len(words) >= 2'),
 ("LW-1 empty inputs allowed", '_need(isinstance(inputs, dict) and inputs,', '_need(isinstance(inputs, dict),'),
 ("LW-1 sha shape not checked", '_need(isinstance(sha, str) and HEX64.fullmatch(sha) is not None,', '_need(True,'),
 ("LW-1 lock-inputs file sha not compared", '_need(hashlib.sha256(blob).hexdigest() == src["sha256"],', '_need(True,'),
 ("LW-1 lock-inputs source not required", '_need(isinstance(src, dict) and set(src) == {"path", "sha256"} and isinstance(src["path"], str),',
  'src = src if isinstance(src, dict) else {"path": "prov.json", "sha256": ""}\n    _need(True,'),
 ("LW-1 lock_inputs not the file's", '_need(row.get("lock_inputs") == {k: entry[k] for k in INPUT_FIELDS if k in entry},', '_need(True,'),
 ("LW-1 lock_inputs sha not checked", '_need(row.get("lock_inputs_sha256") == hashlib.sha256(canonical(row["lock_inputs"])).hexdigest(),', '_need(True,'),
 ("LW-1 row lock path not checked", '_need(row.get("lock") == lock_rel,', '_need(True,'),
 ("LW-3 baked sidecar not checked", '_need(row.get("baked_sidecar_sha256") == inputs[program],', '_need(True,'),
 # LW-2
 ("LW-2 build check not called", '    check_build(il, repo, Path(record_path), record, row, new)\n', ''),
 ("LW-2 metadata index not compared", '_need(isinstance(meta, dict) and meta.get("containerimage.digest") == row["image_id"]', '_need(True'),
 ("LW-2 metadata descriptor not compared", 'and isinstance(desc, dict) and desc.get("digest") == row["image_id"],', ','),
 ("LW-2 log config not compared", '_need(configs == [row["config_digest"]],', '_need(True,'),
 ("LW-2 log manifest not compared", '_need(logged == [row["manifest_digest"]],', '_need(True,'),
 ("LW-2 side files not committed", 'side[key] = committed_bytes(repo, Path(record_path).parent / name)',
  'side[key] = (Path(record_path).parent / name).read_bytes()'),
 ("LW-2 side file names not checked", '_need(isinstance(name, str) and SIDE_FILE.fullmatch(name) is not None and name.startswith(image + "."),',
  '_need(isinstance(name, str),'),
 ("LW-2 argv not compared", '_need(len(mapped) == len(want) + 4 and mapped[-1] == want[-1] and mapped[:len(want) - 1] == want[:-1]',
  '_need(True or len(mapped) == len(want) + 4 and mapped[-1] == want[-1] and mapped[:len(want) - 1] == want[:-1]'),
 ("LW-2 argv context not compared", 'len(mapped) == len(want) + 4 and mapped[-1] == want[-1] and', 'len(mapped) == len(want) + 4 and'),
 ("LW-2 metadata path not the committed file", '_need(os.path.isabs(iid) and os.path.isabs(md) and os.path.basename(md) == row["metadata_file"],',
  '_need(os.path.isabs(iid) and os.path.isabs(md),'),
 ("LW-2 box folder not the checkout's", 'and rbox == checkout.rstrip("/") + "/" + rel_box, "the record', 'and True, "the record'),
 # LW-3, LW-4
 ("LW-3 clean_after not required", '_need(record.get("clean_after") is True,', '_need(True,'),
 ("LW-4 store not required", '_need(isinstance(store, dict) and isinstance(store.get("driver"), str) and store["driver"]',
  '_need(True or isinstance(store, dict) and isinstance(store.get("driver"), str) and store["driver"]'),
 ("LW-4 manifest == config allowed", '_need(row["manifest_digest"] != row["config_digest"],', '_need(True,'),
 # LW-6
 ("LW-6 no flock", 'fcntl.flock(dfd, fcntl.LOCK_EX | fcntl.LOCK_NB)', 'pass'),
 # review 2
 ("R2-1 HEAD mode/blob not compared with the build commit's", '_need(tree_entry(repo, "HEAD", rel) == built[rel],', '_need(True,'),
 ("R2-1 tree entry compares the blob only", '    return [mode, oid]', '    return [oid]'),
 ("R2-1 recorded tree entries not compared", '_need(row["tree_entries"] == built,', '_need(True,'),
 ("R2-2 manifest list not compared", '_need(lists == [row["image_id"]],', '_need(True,'),
 ("R2-2 provenance revision not compared", 'and args.get("vcs:revision") == record["source_commit"]', ''),
 ("R2-2 provenance context not compared", '          and args.get("vcs:localdir:context") == rel_box,', '          ,'),
 ("R2-3 problems not read", '_need(record.get("problems") == [],', '_need(True,'),
 ("rederive schema-2 not required", '_need(lock["schema"] == il.SCHEMA_2 and lock["image"] == image,', '_need(True,'),
 ("rederive plan written", '_need(read_bytes is not None, "a re-derived plan is never written")', 'pass'),
 ("rederive keeps the committed digests", 'unfilled = {k: v for k, v in lock.items() if k not in il.SCHEMA_2_KEYS}', 'unfilled = dict(lock)'),
 ("R2-4 head_blob by git show", '_git(repo, "cat-file", "blob", "HEAD:" + rel)', '_git(repo, "show", "HEAD:" + rel)'),
]


def run(module_src, label):
    mod = types.ModuleType("write_image_lock_mutant")
    exec(compile(module_src, "write_image_lock.py", "exec"), mod.__dict__)
    orig = tw.w; tw.w = mod
    try:
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0, failfast=True).run(
            unittest.defaultTestLoader.loadTestsFromModule(tw))
    finally:
        tw.w = orig
    bad = len(r.failures) + len(r.errors)
    first = (r.failures + r.errors)[0][0].id().split(".", 1)[1] if bad else "-"
    print(("RED  " if bad else "ALIVE"), f"stopped at {first} after {r.testsRun} tests" if bad else f"0/{r.testsRun}",
          "|", label, flush=True)
    return bad


alive = []
if not run(PRE_FOLD, "pre-fold writer (0f7cdbfd): red-first"):
    alive.append("pre-fold")
for name, old, new in mutants:
    assert SRC.count(old) == 1, name
    if not run(SRC.replace(old, new), name):
        alive.append(name)

# LW-5 and LW-7: mutants of image_lock.pending and preflight, killed by test_preflight's own checks.
import test_preflight as tp  # noqa: E402
from box import image_lock as il, preflight as pf  # noqa: E402
IL_SRC = Path(il.__file__).read_text()


def module_from(src, name, real):
    mod = types.ModuleType(real.__name__)
    mod.__file__ = real.__file__
    exec(compile(src, real.__file__, "exec"), mod.__dict__)
    return mod


il_mutants = [
 ("LW-5 pending() ignores base", "    return tuple(_pending_fields(validate(lock)))",
  '    return tuple(f for f in _pending_fields(validate(lock)) if f != "base")'),
 ("LW-5 pending() ignores python", "    return tuple(_pending_fields(validate(lock)))",
  '    return tuple(f for f in _pending_fields(validate(lock)) if f != "python")'),
 ("LW-5 pending() ignores harness.version", "    return tuple(_pending_fields(validate(lock)))",
  '    return tuple(f for f in _pending_fields(validate(lock)) if f != "harness.version")'),
]
for name, old, new in [("control: image_lock unmutated", "", "")] + il_mutants:
    assert name.startswith("control") or IL_SRC.count(old) == 1, name
    m = module_from(IL_SRC.replace(old, new) if old else IL_SRC, "box.image_lock", il)
    m.NotReady, m.LockError = il.NotReady, il.LockError     # the real classes, so only behaviour differs
    real = {k: getattr(il, k) for k in ("pending", "require_ready")}
    il.pending, il.require_ready = m.pending, m.require_ready
    try:
        found = tp.LockSeam.c2_pending(pf)
    finally:
        il.pending, il.require_ready = real["pending"], real["require_ready"]
    if name.startswith("control"):
        print(("ok   " if not found else "BROKEN"), len(found), name, found[:2], flush=True)
        if found:
            alive.append(name)
        continue
    print(("RED  " if found else "ALIVE"), len(found), name, flush=True)
    if not found:
        alive.append(name)

# LW-7 and O-1: test_preflight's own witnesses (in-memory copies of box/preflight.py), killed by c7_sidecar's or
# c8_egress's lines.
for name in getattr(tp, "LW7_WITNESSES", ()) + getattr(tp, "O1_WITNESSES", ()):
    edits, check, prefix, extra = tp.WITNESSES[name]
    got = check(tp.witness_module(edits, extra))
    own = [g for g in got if g.startswith(prefix + " ")]
    errors = [g for g in got if g.startswith("ERROR")]
    ok = bool(own) and not errors
    print(("RED  " if ok else "ALIVE"), f"{len(own)} own, {len(errors)} errors", "|", name, flush=True)
    if not ok:
        alive.append(name)
if not getattr(tp, "LW7_WITNESSES", ()):
    print("NOTE: test_preflight has no LW7_WITNESSES yet (pre-fold run)")
print("ALIVE:", alive if alive else "none")
sys.exit(1 if alive else 0)
