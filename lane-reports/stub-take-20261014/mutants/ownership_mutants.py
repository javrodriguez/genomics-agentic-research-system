"""Mutants of box/ownership.py against tests/test_ownership.py (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_ownership as tt
ow = tt.ow
SRC = open(ow.__file__).read()
MUTANTS = [
 ("grant to keepalive", '("run_tree", run_take._abs_path(run_tree, "run_tree"), AGENT_UID)', '("run_tree", run_take._abs_path(run_tree, "run_tree"), 10003)'),
 ("evidence to agent", '("evidence_dir", run_take._abs_path(evidence_dir, "evidence_dir"), WATCHER_UID)', '("evidence_dir", run_take._abs_path(evidence_dir, "evidence_dir"), AGENT_UID)'),
 ("grant goes on after a failure", '            raise OwnershipError(f"grant-{name} failed', '            pass\n            if False: raise OwnershipError(f"grant-{name} failed'),
 ("restore ignores present containers", "    if still:\n        raise OwnershipError(\"restore refused", "    if False:\n        raise OwnershipError(\"restore refused"),
 ("restore not verified", "        problems += owner_problems(path, os.getuid())", "        pass"),
 ("restore to the agent", "own_argv(image, path, HOST_UID, strict=False)", "own_argv(image, path, AGENT_UID, strict=False)"),
 ("links followed", "    os.chown(name,uid,uid,dir_fd=fd,follow_symlinks=False)", "    os.chown(name,uid,uid,dir_fd=fd,follow_symlinks=True)"),
 ("specials admitted", 'raise RuntimeError("nonregular refused")', 'pass'),
 ("link check skipped", "        if os.path.islink(p) or not os.path.isdir(p):", "        if not os.path.isdir(p):"),
 ("overlap admitted", "            if run_take._inside(p1, p2) or run_take._inside(p2, p1):", "            if False:"),
 ("cfg repo check off", "    if not run_take.outside_every_repository(out[1][1]):", "    if False:"),
 ("extra capability", 'CAPS = ("CHOWN", "DAC_READ_SEARCH")', 'CAPS = ("CHOWN", "DAC_READ_SEARCH", "SYS_ADMIN")'),
 ("DAC_OVERRIDE back", 'CAPS = ("CHOWN", "DAC_READ_SEARCH")', 'CAPS = ("CHOWN", "DAC_OVERRIDE")'),
 ("network on", '"--network", "none", "--user", "0:0"', '"--network", "bridge", "--user", "0:0"'),
 ("write follows the final link", 'f=os.open(parts[-1],os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o644,dir_fd=fd)', 'f=os.open(parts[-1],os.O_WRONLY|os.O_CREAT|os.O_NONBLOCK,0o644,dir_fd=fd)'),
 ("write nlink unchecked", 'if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:raise SystemExit("refused: not a regular file with one link")', 'if not stat.S_ISREG(st.st_mode):raise SystemExit("refused: not a regular file with one link")'),
 ("write follows a folder link", ' nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd); os.close(fd); fd=nfd', ' nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY,dir_fd=fd); os.close(fd); fd=nfd'),
 ("write reply unchecked", "    if got != want:\n", "    if False:\n"),
 ("read size unchecked", ' if len(data)>limit:raise SystemExit("refused: larger than the limit")', ' pass'),
 ("operator runs as root", '"--network", "none", "--user", run_take.AGENT_USER,', '"--network", "none", "--user", "0:0",'),
 # the reviewer's eleven (gap4-review-ownership-20261014/reviewer_mutants.py), anchors moved to the current source
 ("rv: O_NOFOLLOW dropped on child open", "child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)", "child=os.open(name,os.O_RDONLY|os.O_NONBLOCK,dir_fd=fd)"),
 ("rv: O_NONBLOCK dropped on child open", "child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)", "child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)"),
 ("rv: verify follows links", "os.walk(path, onerror=onerror, followlinks=False)", "os.walk(path, onerror=onerror, followlinks=True)"),
 ("rv: verify ignores unreadable subtrees", "        out.append(f\"{getattr(e, 'filename', path)}: unreadable ({type(e).__name__})\")", "        pass"),
 ("rv: verify top-level owner skipped", "        if os.lstat(path).st_uid != uid:\n            out.append(f\"{path}: owner is not the host user\")", "        if False:\n            out.append(f\"{path}: owner is not the host user\")"),
 ("rv: restore stops at first failed step", "            problems.append(f\"restore-{name} exited {step['returncode']}\")", "            problems.append(f\"restore-{name} exited {step['returncode']}\")\n            break"),
 ("rv: timeout counted ok in restore", "        if step[\"returncode\"] != 0:\n            problems.append", "        if step[\"returncode\"] not in (0, None):\n            problems.append"),
 ("rv: no-new-privileges dropped", '    argv += ["--security-opt", "no-new-privileges",\n             "--mount"', '    argv += [\n             "--mount"'),
 ("rv: leaked checked with no ids", "        still = run_take.leaked(runtime, list(ids), caller_env=caller_env)", "        still = run_take.leaked(runtime, [], caller_env=caller_env)"),
 ("rv: restore folders check skipped", "        folders = _folders(run_tree, config_dir, evidence_dir)\n        _image(image)\n        still", "        folders = [(n, p, 0) for n, p in ((\"run_tree\", run_tree), (\"config_dir\", config_dir), (\"evidence_dir\", evidence_dir))]\n        still"),
 # minors 3, 4 and note 10
 ("restore Refused not wrapped", "    except run_take.Refused as e:\n        raise OwnershipError(f\"restore refused: {e}\"", "    except KeyError as e:\n        raise OwnershipError(f\"restore refused: {e}\""),
 ("timed-out container not removed", "        if step.get(\"timed_out\"):\n            runtime.run(", "        if False:\n            runtime.run("),
 ("left container ignored", "        if left:\n            step[\"returncode\"] = None", "        if False:\n            step[\"returncode\"] = None"),
 ("unreadable id ignored", "            if step[\"returncode\"] is None or step[\"returncode\"] == 0:\n                step[\"returncode\"] = None", "            if False:\n                step[\"returncode\"] = None"),
 ("grant not strict", 'own_argv(image, path, uid, strict=True), env)', 'own_argv(image, path, uid, strict=False), env)'),
 ("strict ignores hard links", 'and st.st_nlink!=1)', 'and st.st_nlink<1)'),
 ("restore leaves 0000", ' if restore:os.fchmod(fd,stat.S_IMODE(os.fstat(fd).st_mode)|(0o700 if stat.S_ISDIR(st.st_mode) else 0o600))', ' pass'),
 ("restore widens to group and other", '|(0o700 if stat.S_ISDIR(st.st_mode) else 0o600))', '|(0o777 if stat.S_ISDIR(st.st_mode) else 0o666))'),
 ("restore runs as grant mode", '"strict" if strict is True else "restore"]', '"strict" if strict is True else "loose"]'),
 # glitch-06, 14 Oct 2026: the config-folder read (native sessions mid-take)

 ("read: a folder link followed", ' try:nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)\n except FileNotFoundError:print(json.dumps({"exists":False}));raise SystemExit(0)\n os.close(fd); fd=nfd\ntry:f=', ' try:nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY,dir_fd=fd)\n except FileNotFoundError:print(json.dumps({"exists":False}));raise SystemExit(0)\n os.close(fd); fd=nfd\ntry:f='),
 ("read: the wrong root mounted", '    argv = operator_argv(image, root, READ_PROGRAM, rel, str(limit), readonly=True)', '    argv = operator_argv(image, os.path.dirname(root), READ_PROGRAM, rel, str(limit), readonly=True)'),
 ("read: a write mount", '    argv = operator_argv(image, root, READ_PROGRAM, rel, str(limit), readonly=True)', '    argv = operator_argv(image, root, READ_PROGRAM, rel, str(limit), readonly=False)'),
 ("read: readonly spelled away", '(",readonly" if readonly is True else "")', '("" if readonly is True else "")'),
 ("read: hard links admitted", 'if st.st_nlink!=1:raise SystemExit("refused: a file with another hard link")', 'pass'),
 ("read: reply hash unchecked", '                    and got["sha256"] == hashlib.sha256(data).hexdigest():', '                    and True:'),
 ("read: reply length unchecked", '            if len(data) <= limit and got["bytes"] == len(data) \\', '            if len(data) <= limit and True \\'),
 ("read: config cap is the run tree's", 'READ_ROOTS = {"run_tree": OPERATOR_READ_MAX_BYTES, "config": CONFIG_READ_MAX_BYTES}', 'READ_ROOTS = {"run_tree": OPERATOR_READ_MAX_BYTES, "config": OPERATOR_READ_MAX_BYTES}'),
 ("read: capability added", '    return [run_take.RUNTIME_CLIENT, "run", "--rm", "--pull=never", "--network", "none", "--user", run_take.AGENT_USER,\n            "--cap-drop", "ALL",', '    return [run_take.RUNTIME_CLIENT, "run", "--rm", "--pull=never", "--network", "none", "--user", run_take.AGENT_USER,\n            "--cap-add", "DAC_READ_SEARCH",'),
 # glitch-06, 14 Oct 2026: operator_list (session discovery, one folder at a time)
 ("list: a link listed as a dir", ' m=os.stat(n,dir_fd=fd,follow_symlinks=False).st_mode', ' m=os.stat(n,dir_fd=fd,follow_symlinks=True).st_mode'),
 ("list: recursion", 'names=os.listdir(fd)\n', 'names=os.listdir(fd)+[a+"/"+b for a in os.listdir(fd) if stat.S_ISDIR(os.stat(a,dir_fd=fd,follow_symlinks=False).st_mode) for b in os.listdir(os.open(a,os.O_RDONLY|os.O_DIRECTORY,dir_fd=fd))]\n'),
 ("list: recursion admitted by the host", '                or b"/" in raw or b"\\0" in raw or raw in seen:', '                or b"\\0" in raw or raw in seen:'),
 ("list: the wrong root mounted", '    argv = operator_argv(image, root, LIST_PROGRAM, rel, str(LIST_MAX_ENTRIES), readonly=True)', '    argv = operator_argv(image, os.path.dirname(root), LIST_PROGRAM, rel, str(LIST_MAX_ENTRIES), readonly=True)'),
 ("list: a write mount", '    argv = operator_argv(image, root, LIST_PROGRAM, rel, str(LIST_MAX_ENTRIES), readonly=True)', '    argv = operator_argv(image, root, LIST_PROGRAM, rel, str(LIST_MAX_ENTRIES), readonly=False)'),
 ("list: listed through a folder link", ' try:nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)\n except FileNotFoundError:print(json.dumps({"exists":False}));raise SystemExit(0)\n os.close(fd); fd=nfd\nnames', ' try:nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY,dir_fd=fd)\n except FileNotFoundError:print(json.dumps({"exists":False}));raise SystemExit(0)\n os.close(fd); fd=nfd\nnames'),
 ("list: entry cap unchecked", 'if len(names)>limit:raise SystemExit("refused: more entries than the limit")', 'pass'),
 ("list: host cap unchecked", 'and isinstance(got["entries"], list) and len(got["entries"]) <= LIST_MAX_ENTRIES):', 'and isinstance(got["entries"], list)):'),
 ("list: reply hash unchecked", '    if got["sha256"] != hashlib.sha256(canon.encode("utf-8")).hexdigest():', '    if False:'),
 ("list: any kind", ' and e[1] in LIST_KINDS)', ')'),
 ("list: duplicates admitted", ' or raw in seen:', ':'),
 # review-operator-read O-1, O-2, O-3 (14 Oct 2026)
 ("O-1: a torn read admitted", '(st.st_ino,st.st_dev,st.st_size,st.st_mtime_ns) or len(data)!=st.st_size:raise', 'False and (st.st_ino,st.st_dev,st.st_size,st.st_mtime_ns) and False:raise'),
 ("W-4: bytes read not compared", ' or len(data)!=st.st_size:raise SystemExit("refused: the file changed during the read")', ':raise SystemExit("refused: the file changed during the read")'),
 ("O-1: only the size compared", '(post.st_ino,post.st_dev,post.st_size,post.st_mtime_ns)!=(st.st_ino,st.st_dev,st.st_size,st.st_mtime_ns)', 'post.st_size!=st.st_size'),
 ("O-1: mtime not compared", '(post.st_ino,post.st_dev,post.st_size,post.st_mtime_ns)!=(st.st_ino,st.st_dev,st.st_size,st.st_mtime_ns)', '(post.st_ino,post.st_dev,post.st_size)!=(st.st_ino,st.st_dev,st.st_size)'),
 ("L-1: a removed name admitted", 'except FileNotFoundError:raise SystemExit("refused: the file changed during the read")', 'except FileNotFoundError:post=st'),
 ("L-1: the name's inode not compared", '(post.st_ino,post.st_dev,post.st_size,post.st_mtime_ns)!=(st.st_ino,st.st_dev,st.st_size,st.st_mtime_ns)', '(post.st_dev,post.st_size,post.st_mtime_ns)!=(st.st_dev,st.st_size,st.st_mtime_ns)'),
 ("L-2: a non-UTF-8 name keeps its kind", '            name, kind = raw.decode("utf-8", "surrogateescape"), "other"', '            name, kind = raw.decode("utf-8", "surrogateescape"), e[1]'),
 ("O-2: credential path admitted", '    if root_kind == "config" and rel != "." and any(credential_name(part) for part in rel.split("/")):', '    if False:'),
 ("O-2: only the last part checked", 'any(credential_name(part) for part in rel.split("/"))', 'credential_name(rel.split("/")[-1])'),
 ("O-2: the backstop dropped", '    return name in names or bool(preflight.CREDENTIAL_LIKE.search(name))', '    return name in names'),
 ("O-2: listed credential readable", '            kind = "other"                  # O-2', '            pass                            # O-2'),
 ("O-3: a link root admitted", '        if os.path.islink(path) or not os.path.isdir(path):\n            raise run_take.Refused(f"{name} must be an existing folder, never a link")\n    if not run_take.outside_every_repository(cfg):', '        if not os.path.isdir(path):\n            raise run_take.Refused(f"{name} must be an existing folder, never a link")\n    if not run_take.outside_every_repository(cfg):'),
 ("O-3: nesting admitted", '    if run_take._inside(tree, cfg) or run_take._inside(cfg, tree):\n        raise run_take.Refused("the run tree and the config folder must not contain each other")', '    if False:\n        raise run_take.Refused("the run tree and the config folder must not contain each other")'),
 ("O-3: config in a repository admitted", '    if not run_take.outside_every_repository(cfg):\n        raise run_take.Refused("the per-take config folder must sit outside every repository")\n    return tree if', '    if False:\n        raise run_take.Refused("the per-take config folder must sit outside every repository")\n    return tree if'),
 ("O-3: any root kind", '    if root_kind not in READ_ROOTS:\n        raise run_take.Refused(f"an operator root is one of {sorted(READ_ROOTS)}")', '    if root_kind not in READ_ROOTS and False:\n        raise run_take.Refused(f"an operator root is one of {sorted(READ_ROOTS)}")'),
 ("O-3: the other root mounted", '    return tree if root_kind == "run_tree" else cfg', '    return cfg if root_kind == "run_tree" else tree'),
 ("operator path escapes", ' or ".." in rel_path.split("/") or rel_path == ".":', ' or rel_path == ".":'),
]
def run(mod):
    tt.ow = mod
    try:
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(tt))
    finally:
        tt.ow = ow
c = run(ow); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
alive = []
PAIRS = [
 # the named pair (box/ownership.py READ_PROGRAM comment): O_NOFOLLOW on the final open and the name's post-read lstat
 # each refuse a final link; removing one alone is masked by the other, so they are killed together.
 ("read: a final link followed (the pair)", (
  ('try:f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)', 'try:f=os.open(parts[-1],os.O_RDONLY|os.O_NONBLOCK,dir_fd=fd)'),
  ('try:post=os.stat(parts[-1],dir_fd=fd,follow_symlinks=False)', 'try:post=os.stat(parts[-1],dir_fd=fd,follow_symlinks=True)'))),
]
for name, swaps in PAIRS:
    src = SRC
    for old, new in swaps:
        assert src.count(old) == 1, name
        src = src.replace(old, new)
    MUTANTS.append((name, SRC, src))
for name, old, new in MUTANTS:
    if old is SRC:
        mod = types.ModuleType(ow.__name__); mod.__file__ = ow.__file__
        exec(compile(new, ow.__file__, "exec"), mod.__dict__)
        r = run(mod); bad = len(r.failures) + len(r.errors)
        print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
        if not bad: alive.append(name)
        continue
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(ow.__name__); mod.__file__ = ow.__file__
    exec(compile(SRC.replace(old, new), ow.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
