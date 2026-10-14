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
 ("read follows a link", 'try:f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)', 'try:f=os.open(parts[-1],os.O_RDONLY|os.O_NONBLOCK,dir_fd=fd)'),
 ("read size unchecked", 'if st.st_size>limit:raise SystemExit("refused: larger than the limit")', 'pass'),
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
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(ow.__name__); mod.__file__ = ow.__file__
    exec(compile(SRC.replace(old, new), ow.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
