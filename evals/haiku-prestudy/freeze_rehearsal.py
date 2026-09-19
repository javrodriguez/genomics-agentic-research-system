#!/usr/bin/env python3
"""Rehearse the freeze and the take path in a throwaway clone, and write the record the freeze requires.

    python3 evals/haiku-prestudy/freeze_rehearsal.py

WHERE. A `--no-local` clone of this repository at HEAD under ~/.haiku-prestudy-rehearsal/<n>/, with its remote
removed: never the Brain, never the OS temp folder, and never a clone that can push. The clone is deleted after
the record is written; the record is written into THIS study's verification/ folder.

WHAT. In the clone: the owner's approval is filled with the literal word REHEARSAL (in the clone only), the draft
is rebuilt and frozen with `freeze.py --rehearsal --write`, then the gate runs on the frozen state: the suite, the
copy manifest, the finding, the language guard, the loader and the ledger plan. Then the take path, with no model:
the frozen state is committed, a local bare repository inside the box stands in for origin, and `take.py --take 1`
runs exactly as a real take will (preflight, row, commit, drive, postflight, attempt commit) with a STUB `claude`
first on PATH. (Rehearsal 1 committed the row by hand, never staged it, and drove nothing; that is why take.py
itself is rehearsed.) The stub answers `--version` with the frozen harness version and, for a turn, writes
a minimal session file for the imposed session id (one user record, one assistant reply that holds no marker) and
exits 0. So the driver builds the run tree and the fixture, writes the environment record, sends turn 1, finds the
marker unheld, copies the session file, runs the take checker in place and routes the attempt by rule. The stub's
bytes are never a take: they exist only in the clone and are deleted with it.

THE RECORD. verification/freeze-rehearsal-<n>.txt: line 1 the sha256 of the draft bytes rehearsed (with the owner's
approval as it stands in THIS study's draft, not the clone's REHEARSAL word, since that is what freeze.py compares),
then each step with its exit code and the tail of its output, then `all green` or `NOT green`.

No model, no network. stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
REL = "evals/haiku-prestudy"
ROOT = Path.home() / ".haiku-prestudy-rehearsal"

STUB = r'''#!/usr/bin/env python3
import json, sys, uuid
from pathlib import Path
a = sys.argv[1:]
if a == ["--version"]:
    print("{version}")
    sys.exit(0)
sid = a[a.index("--session-id") + 1] if "--session-id" in a else a[a.index("--resume") + 1]
line = a[a.index("-p") + 1]
d = Path("{projects}") / "stub-project"
d.mkdir(parents=True, exist_ok=True)
recs = [
    {"type": "user", "sessionId": sid, "uuid": str(uuid.uuid4()), "permissionMode": "default",
     "message": {"role": "user", "content": line}},
    {"type": "assistant", "sessionId": sid, "uuid": str(uuid.uuid4()),
     "message": {"role": "assistant", "model": "{model}", "content": [{"type": "text", "text": "Starting stage 00."}],
                 "stop_reason": "end_turn"}},
]
with (d / f"{sid}.jsonl").open("a") as fh:
    for r in recs:
        fh.write(json.dumps(r) + "\n")
print(json.dumps({"type": "system", "subtype": "init", "session_id": sid, "apiKeySource": "none"}))
print(json.dumps({"type": "assistant", "message": recs[1]["message"]}))
print(json.dumps({"type": "result", "subtype": "success", "result": "Starting stage 00."}))
'''


def _freeze_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("prestudy_freeze_for_rehearsal", HERE / "freeze.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 1800) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def main() -> int:
    draft_bytes = (HERE / "prereg-draft.json").read_bytes()
    draft_sha = hashlib.sha256(draft_bytes).hexdigest()
    draft = json.loads(draft_bytes)
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", REL], capture_output=True,
                           text=True).stdout.strip()
    if dirty:
        print("refusing: the study has uncommitted changes; a rehearsal runs on what is committed:\n" + dirty)
        return 2
    ROOT.mkdir(exist_ok=True)
    n = 1 + max([int(p.stem.rsplit("-", 1)[1]) for p in (HERE / "verification").glob("freeze-rehearsal-*.txt")] or [0])
    box = ROOT / str(n)
    if box.exists():
        shutil.rmtree(box)
    clone = box / "repo"
    steps: list[tuple[str, int, str]] = []
    try:
        subprocess.run(["git", "clone", "-q", "--no-local", str(REPO), str(clone)], check=True)
        subprocess.run(["git", "-C", str(clone), "remote", "remove", "origin"], check=True)
        for k, v in (("user.name", "rehearsal"), ("user.email", "rehearsal@localhost"), ("commit.gpgsign", "false"),
                     ("maintenance.auto", "false")):
            subprocess.run(["git", "-C", str(clone), "config", k, v], check=True)
        study = clone / REL
        py = sys.executable

        def step(name: str, cmd: list[str], env: dict | None = None) -> int:
            code, out = run(cmd, clone, env)
            steps.append((name, code, "\n".join(out.strip().splitlines()[-6:])))
            return code

        step("approve in the clone only",
             [py, f"{REL}/build_draft.py", "--approve", "REHEARSAL", "--approved-at", "rehearsal"])
        step("record a green rehearsal for the clone's draft",
             [py, "-c", "import hashlib,pathlib;p=pathlib.Path('" + REL + "');"
              "import importlib.util as u;sp=u.spec_from_file_location('fz',p/'freeze.py');fz=u.module_from_spec(sp);"
              "sp.loader.exec_module(fz);"
              "(p/'verification'/'freeze-rehearsal-0.txt').write_text(hashlib.sha256((p/'prereg-draft.json')"
              ".read_bytes()).hexdigest()+'\\ncode sha256: '+fz.code_sha256()+'\\nclone-only record\\nall green\\n')"])
        step("freeze --rehearsal --write", [py, f"{REL}/freeze.py", "--rehearsal", "--write"])
        step("suite on the frozen state", [py, "-W", "ignore", f"{REL}/test_prestudy.py"])
        step("copy manifest", [py, f"{REL}/copy_manifest.py", "--check"])
        step("finding re-derives", [py, f"{REL}/finding.py", "--check"])
        step("language guard", [py, f"{REL}/lint_language.py", f"{REL}/"])
        step("loader status", [py, f"{REL}/prereg.py", "--status"])
        step("ledger plan", [py, f"{REL}/takes.py", "--plan"])
        step("stage the frozen state", ["git", "add", "--", REL])
        step("commit the frozen state", ["git", "commit", "-q", "-m", "rehearsal: frozen"])
        # A local bare repository stands in for origin, so take.py's preflight (clean, even with origin) runs as it
        # will for a real take. It is inside the box and deleted with it; nothing leaves this machine.
        step("a local stand-in for origin", ["git", "clone", "-q", "--bare", str(clone), str(box / "origin.git")])
        step("point origin at it", ["git", "remote", "add", "origin", str(box / "origin.git")])
        step("fetch it", ["git", "fetch", "-q", "origin"])
        step("track it", ["git", "branch", "-q", "--set-upstream-to=origin/main", "main"])
        stub_dir = box / "stub-bin"
        stub_dir.mkdir()
        (stub_dir / "claude").write_text(STUB.replace("{version}", draft["harness"]["claude_version"] + " (Claude Code)")
                                         .replace("{projects}", str(box / "claude-config" / "projects"))
                                         .replace("{model}", draft["models"][0]))
        (stub_dir / "claude").chmod(0o755)
        env = {**os.environ, "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}",
               "CLAUDE_CONFIG_DIR": str(box / "claude-config")}
        step("take.py --take 1 against the stub", [py, "-u", f"{REL}/take.py", "--take", "1"], env)
        step("session id for row 0", [py, f"{REL}/takes.py", "--session-id", "0"])
        step("the row and the attempt are two commits", ["git", "log", "--format=%s", "-3"])
        attempts = sorted(str(p.relative_to(study)) for p in study.glob("*/number-fidelity/positive/*/*/driver-ledger.json"))
        routed = [json.loads((study / a).read_text()) for a in attempts]
        steps.append(("attempt routed", 0 if len(routed) == 1 else 1, f"{attempts}"))
        if routed:
            led = routed[0]
            ok = (led.get("allowed_tools") == draft["driver_change"]["allowed_tools"]
                  and led.get("run_tree_built_from") == draft["export_at"]
                  and led.get("attempt", {}).get("kind") in ("graded", "rehearsal"))
            steps.append(("ledger carries the allowlist and the export commit", 0 if ok else 1,
                          json.dumps({k: led.get(k) for k in ("allowed_tools", "run_tree_built_from", "outcome", "attempt")})))
            take_dir = study / Path(attempts[0]).parent
            if (take_dir / "transcript.jsonl").is_file():
                step("take checker on the routed attempt",
                     [py, f"{REL}/check_take.py", str(take_dir / "transcript.jsonl"), "--task", "number-fidelity",
                      "--half", "positive", "--row", "0"])
            step("outcome reader on the routed attempt", [py, f"{REL}/outcome.py", str(take_dir)])
            step("result.py writes from the frozen state", [py, f"{REL}/result.py", "--write"])
            step("result.py re-derives it", [py, f"{REL}/result.py", "--check"])
            step("the result lists the rehearsal", ["grep", "-n", "Attempts that are not takes\\|Row 0: a rehearsal",
                                                    f"{REL}/RESULT.md"])
    finally:
        shutil.rmtree(box, ignore_errors=True)

    # A take-checker refusal of the stub's bytes is expected (they are not a model's), so that step records its
    # output and is not counted against green; every other step must exit 0.
    informational = {"take checker on the routed attempt"}
    green = all(code == 0 for name, code, _ in steps if name not in informational)
    fz = _freeze_module()
    lines = [draft_sha, f"code sha256: {fz.code_sha256()}", f"rehearsal {n}, clone of HEAD {subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()}", ""]
    for name, code, tail in steps:
        lines += [f"## {name}: exit {code}" + ("  (informational)" if name in informational else ""), tail, ""]
    lines.append("all green" if green else "NOT green")
    out = HERE / "verification" / f"freeze-rehearsal-{n}.txt"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out.relative_to(REPO)}: {'all green' if green else 'NOT green'}")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
