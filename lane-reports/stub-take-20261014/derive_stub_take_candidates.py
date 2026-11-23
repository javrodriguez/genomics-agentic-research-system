"""Derive the stub-take candidates from the two athena runs, by the written rules below; write the derivation record,
the candidate patch, and a replay of preflight.evaluate over the recorded raw probes in a throwaway patched copy.

Never writes a module of the checkout: the patch is produced from copies in a temporary folder, and the replay runs
there. Stub-take lane, glitch-06's rulings (14 Oct 2026). Run from anywhere:

    python3 -B lane-reports/stub-take-20261014/derive_stub_take_candidates.py <repo root> <run1.json> <run2.json>

THE RULES (each reads only the recorded runs and the committed locks):
  R-TOP     ps_options is the measured form whose header is exactly PID UID COMMAND with numeric pid and uid columns,
            in every live and after-kill reading of both runs. uid_namespace is "container" when every row's UID
            column equals the container uid whose host uid (read from /proc/<pid>/status on the host) maps through the
            container's own uid_map, and the column differs from that host uid; "host" when it equals the host uid;
            otherwise no candidate.
  R-INSPECT every INSPECT_PATHS key resolves (run_take._path_get) in the take's, the sidecar's and the proxy's inspect
            of both runs; then INSPECT_STATUS is a record naming the engine and API versions and the evidence files.
  R-VERSION per harness, the stdout of `<harness> --version` (the preflight probe's for claude-code, the one-shot
            container's for the other two) with the lock's version replaced by one group ([0-9]+(?:\\.[0-9]+){2}),
            the rest re.escape'd; it must fullmatch every recorded output and its group equal the lock's version.
  R-RES     concurrency C = 3 takes (the plan's fixed scope). Reservation R = floor((MemTotal - 8 GiB) / (3 C)) in
            whole GiB, ceiling 3 R; cpus = floor((nproc - 8) / C); pids = the largest power of two P with
            C P <= floor(user-1000.slice pids.max / 4). Run 2 ran with exactly these; limits-apply read them back.
  R-FALLBACK the identifiers matching [A-Z_]*FALLBACK[A-Z_]* in the pinned Claude Code binary whose names start with
            CLAUDE_CODE_ and govern a model or refusal fallback (their string contexts); values "1" are INFERRED
            from the CLAUDE_CODE_DISABLE_* convention and one message ("... is set: model substitution is disabled"),
            not observed in behaviour (that needs a model turn).
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import hashlib
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
RUNS = [Path(p).resolve() for p in sys.argv[2:4]]
OUT = Path(__file__).resolve().parent
STUDY = ROOT / "evals/gap-study-4"
sys.path.insert(0, str(STUDY))
from box import run_take as rt  # noqa: E402

docs = [json.loads(p.read_text()) for p in RUNS]
for d in docs:
    assert d["record_kind"] == "stub-take-measurement" and d.get("failure") is None, "a run failed or is unlabelled"
sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in RUNS}
rel = {p.name: os.path.relpath(p, ROOT) for p in RUNS}
derivation = {"record_kind": "stub-take-derivation", "runs": [{"file": rel[p.name], "sha256": sha[p.name]}
                                                              for p in RUNS], "rules": {}}


# ---------------------------------------------------------------------------------------------------------- R-TOP
def uid_map(d):
    return [tuple(int(x) for x in ln.split()) for ln in d["cgroup_before"]["uid_map"].splitlines() if ln.strip()]


def top_candidate():
    seen, namespaces = [], set()
    for d in docs:
        um = uid_map(d)
        for reading in ("top_live", "top_after_kill"):
            r = d[reading]["eo-pid-uid-comm"]
            rows = [ln.split() for ln in r["stdout"].splitlines() if ln.strip()]
            assert r["returncode"] == 0 and rows[0] == ["PID", "UID", "COMMAND"], (reading, rows[:1])
            for pid, uid, _cmd in rows[1:]:
                assert pid.isdigit() and uid.isdigit()
                host = int(r["host_proc_uid_by_pid"][pid][0][0])
                mapped = rt.host_uid(int(uid), um)
                ns = "container" if mapped == host and int(uid) != host else "host" if int(uid) == host else None
                namespaces.add(ns)
                seen.append({"run": d["started_at"], "reading": reading, "pid": int(pid), "uid_column": int(uid),
                             "host_uid": host, "uid_map_of_column": mapped, "namespace": ns})
    assert namespaces == {"container"}, namespaces
    return {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID",
            "uid_namespace": "container"}, seen


# ------------------------------------------------------------------------------------------------------ R-INSPECT
def inspect_candidate():
    rows = []
    for d, p in zip(docs, RUNS):
        objs = {"take": [s for s in d["launch"]["steps"] if s["step"] == "take-inspect"][0]["inspect"],
                "sidecar": [s for s in d["launch"]["steps"] if s["step"] == "sidecar-inspect"][0]["inspect"],
                "proxy": json.loads(d["preflight_raw"]["proxy-inspect"]["stdout"])[0],
                "take-running": d["take_inspect_running"]["inspect"]}
        for name, obj in objs.items():
            for key, dotted in rt.INSPECT_PATHS.items():
                rt._path_get(obj, dotted)          # raises KeyError when a spelling does not resolve
            rows.append({"run": rel[p.name], "inspect": name, "resolved": sorted(rt.INSPECT_PATHS)})
    ver = json.loads(docs[-1]["runtime"]["version"])
    return {"confirmed_on": "2026-10-14", "engine": ver["Server"]["Version"],
            "api_version": ver["Server"]["ApiVersion"],
            "evidence": [f"{rel[p.name]} sha256:{sha[p.name]}" for p in RUNS]}, rows


# ------------------------------------------------------------------------------------------------------ R-VERSION
def version_candidate():
    out, rows = {}, []
    for h in (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI):
        outputs = [(d["versions"][h]["stdout"], d["versions"][h]["lock_version"]) for d in docs]
        if h == rt.CLAUDE_CODE:
            outputs += [(d["preflight_raw"]["harness-version"]["stdout"], d["versions"][h]["lock_version"])
                        for d in docs]
        text, lock = outputs[0][0].strip(), outputs[0][1]
        assert text.count(lock) == 1, (h, text)
        a, b = text.split(lock)
        pattern = re.escape(a) + r"([0-9]+(?:\.[0-9]+){2})" + re.escape(b)
        for o, lv in outputs:
            m = re.fullmatch(pattern, o.strip())
            assert m and m.group(1) == lv, (h, o)
            rows.append({"harness": h, "output": o, "lock_version": lv, "group": m.group(1)})
        out[h] = pattern
    return out, rows


# ---------------------------------------------------------------------------------------------------------- R-RES
def resources_candidate():
    d = docs[-1]
    mem_kb = int(re.search(r"MemTotal:\s+([0-9]+) kB", d["runtime"]["meminfo"]).group(1))
    nproc = int(d["runtime"]["nproc"])
    # review finding 3: athena's user slice pids.max, read raw (user-slice-pids-max-20261014.txt, 08:27 EDT 14 Oct)
    raw = (OUT / "user-slice-pids-max-20261014.txt").read_text().splitlines()
    slice_pids = int(raw[raw.index("== /sys/fs/cgroup/user.slice/user-1000.slice/pids.max") + 1])
    C, gib = 3, 1 << 30
    R = math.floor((mem_kb * 1024 - 8 * gib) / (3 * C) / gib) * gib
    cpus = (nproc - 8) // C
    P = 1
    while C * P * 2 <= slice_pids // 4:
        P *= 2
    cand = {"memory_reservation": R, "memory": 3 * R, "cpus": str(cpus), "pids_limit": P}
    ran = d["spec_resources"]
    assert {k: ran[k] for k in cand} == cand, (ran, cand)
    limits = [c for c in d["preflight"]["checks"] if c["id"] == "limits-apply"][0]
    assert limits["ok"], limits
    peaks = [{"run": rel[p.name], "memory.peak": dd["cgroup_after"]["files"]["memory.peak"].strip(),
              "pids.peak": dd["cgroup_after"]["files"]["pids.peak"].strip(),
              "memory.events": dd["cgroup_after"]["files"]["memory.events"], "counters": dd["counters"]}
             for dd, p in zip(docs, RUNS)]
    return cand, {"MemTotal_kB": mem_kb, "nproc": nproc, "user_slice_pids_max": slice_pids, "C": C,
                  "limits_apply_run2": limits, "stub_peaks": peaks,
                  "caveat": "the stub's peaks bound only the box's floor; a real harness turn's footprint is first "
                            "read at the first walk (memory.peak, pids.peak and the oom/pids counters per turn)"}


# ----------------------------------------------------------------------------------------------------- R-FALLBACK
def fallback_candidate():
    probe = json.loads((OUT / "claude-fallback-probe-20261014.json").read_text())
    names = json.loads(probe["stdout"])["names"]
    pick = ("CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK", "CLAUDE_CODE_NO_MODEL_FALLBACK",
            "CLAUDE_CODE_DISABLE_MODEL_ACCESS_FALLBACK")
    for n in pick:
        assert n in names, n
    others = sorted(n for n in names if n.startswith("CLAUDE_CODE_") and n not in pick)
    return {n: "1" for n in pick}, {"found": sorted(names), "picked": list(pick), "not_picked": others,
                                     "why_not_picked": {"CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "a transport "
                                                        "fallback (streaming to non-streaming), not a model or refusal "
                                                        "fallback",
                                                        "CLAUDE_CODE_REFUSAL_FALLBACK_CATCH_ALL": "its documented "
                                                        "string reads it as a switch 'explicitly disabled'; its off "
                                                        "value is not readable from the binary's strings"},
                                     "values": "INFERRED, not observed in behaviour"}


top, top_rows = top_candidate()
inspect, inspect_rows = inspect_candidate()
versions, version_rows = version_candidate()
res, res_basis = resources_candidate()
fallback, fallback_basis = fallback_candidate()
derivation["rules"] = {
    "TOP_FORMAT": {"candidate": top, "observations": top_rows},
    "INSPECT_STATUS": {"candidate": inspect, "observations": inspect_rows},
    "VERSION_PATTERNS": {"candidate": versions, "observations": version_rows},
    "TakeSpec.resources": {"candidate": res, "basis": res_basis,
                           "patch": "values only: TakeSpec's resources are the caller's (walk_builders.take_spec, the "
                                    "integration's consumer); run_take is not patched"},
    "FALLBACK_ENV": {"candidate": fallback, "basis": fallback_basis},
    "rules_scanner": {"measured": {d["started_at"]: d["gitleaks"] for d in docs},
                      "adapter": "box/stub_take.py gitleaks_rules_scanner (gitleaks dir <file> --no-banner --redact "
                                 "--report-format json --report-path <r> --exit-code 0; StartLine, RuleID)",
                      "proof": {"clean": [{k: d["scan_clean"]["result"][k] for k in ("events", "refused", "holdout")}
                                          for d in docs],
                                "rule_probe": [d["scan_rule_probe"]["result"]["refused"] for d in docs]},
                      "patch": "none: scan_record holds no process code and real_rules_scanner returns the adapter "
                               "itself, so where the adapter lives is an interface ruling; RULES_SCANNER stays PENDING"},
}

# ------------------------------------------------------------------------------------------ the candidate patch
tmp = Path(tempfile.mkdtemp(prefix="stub-cand-"))
try:
    edits = {
        "evals/gap-study-4/box/run_take.py": [
            ("FALLBACK_ENV = PENDING", "FALLBACK_ENV = " + json.dumps(fallback) +
             "  # CANDIDATE (stub-take lane, 14 Oct 2026): names read from the pinned 2.1.296 binary; values inferred"),
            ("TOP_FORMAT = PENDING", "TOP_FORMAT = " + json.dumps(top) +
             "  # CANDIDATE (stub-take lane, 14 Oct 2026): measured on athena, docker 29.8.1"),
            ("INSPECT_STATUS = PENDING", "INSPECT_STATUS = " + json.dumps(inspect) + "  # CANDIDATE (stub-take lane)"),
        ],
        "evals/gap-study-4/box/preflight.py": [
            ("VERSION_PATTERNS = {run_take.CLAUDE_CODE: PENDING, run_take.CODEX: PENDING, run_take.GEMINI: PENDING}",
             "VERSION_PATTERNS = {run_take.CLAUDE_CODE: %r, run_take.CODEX: %r,\n                    run_take.GEMINI: %r}"
             "  # CANDIDATE (stub-take lane, 14 Oct 2026)" % (versions[rt.CLAUDE_CODE], versions[rt.CODEX],
                                                              versions[rt.GEMINI])),
        ],
    }
    for relpath, subs in edits.items():
        a, b = tmp / "a" / relpath, tmp / "b" / relpath
        a.parent.mkdir(parents=True, exist_ok=True)
        b.parent.mkdir(parents=True, exist_ok=True)
        src = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{relpath}"], capture_output=True, text=True,
                             check=True).stdout
        a.write_text(src)
        for old, new in subs:
            assert src.count(old) == 1, (relpath, old)
            src = src.replace(old, new)
        b.write_text(src)
    diff = subprocess.run(["diff", "-ru", "a", "b"], cwd=tmp, capture_output=True, text=True).stdout
    patch = OUT / "stub-take-candidates-20261014.patch"
    patch.write_text(diff)
    check = subprocess.run(["git", "-C", str(ROOT), "apply", "-p1", "--check", str(patch)], capture_output=True,
                           text=True)
    derivation["patch"] = {"file": os.path.relpath(patch, ROOT), "sha256": hashlib.sha256(diff.encode()).hexdigest(),
                           "git_apply_check": check.returncode, "stderr": check.stderr}

    # --------------------------------------------------------------------------------------------- the replay
    rep = tmp / "replay"
    arch = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", "HEAD", "evals/gap-study-4/box",
                           "evals/gap-study-4/harness_bookkeeping.py", "evals/gap-study-4/agent_adapter.py",
                           "evals/gap-study-4/scrub.py", "evals/gap-study-4/graders/labels4.py"],
                          capture_output=True, check=True).stdout
    rep.mkdir()
    subprocess.run(["tar", "-xf", "-", "-C", str(rep)], input=arch, check=True)
    subprocess.run(["git", "apply", "-p1", str(patch)], cwd=rep, check=True)
    program = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from box import preflight, run_take as rt, stub_take as st
from box.egress import proxy_conf
d = json.load(open(sys.argv[2]))
sc, r = d["scratch"], d["spec_resources"]
spec = rt.TakeSpec(image=d["images"]["take"], run_tree=sc["run_tree"], config_dir=sc["config"],
                   network=d["launch"]["network_id"], memory_reservation=r["memory_reservation"], memory=r["memory"],
                   cpus=r["cpus"], pids_limit=r["pids_limit"])
sl = st.sidecar_launch(image=d["images"]["sidecar"], run_tree=sc["run_tree"], evidence=sc["evidence"])
out = preflight.evaluate(d["preflight_raw"], spec=spec, lock=d["locks"]["take"], sidecar_expect=sl.expect,
                         harness=rt.CLAUDE_CODE, hosts=dict(proxy_conf.HOSTS), evidence_dir=sc["evidence"],
                         sidecar_lock=d["locks"]["sidecar"], egress_lock=d["locks"]["egress"])
print(json.dumps({"pending_run_take": sorted(rt.pending()), "pending_preflight": sorted(preflight.pending()),
                  "checks": out["checks"], "ok": out["ok"]}))
'''
    derivation["replay"] = {}
    for p in RUNS:
        res_ = subprocess.run([sys.executable, "-B", "-c", program, str(rep / "evals/gap-study-4"), str(p)],
                              capture_output=True, text=True, cwd=tmp)
        assert res_.returncode == 0, res_.stderr[-2000:]
        derivation["replay"][rel[p.name]] = json.loads(res_.stdout)
finally:
    shutil.rmtree(tmp)

(OUT / "stub-take-derivation-20261014.json").write_text(json.dumps(derivation, indent=1, sort_keys=True) + "\n")
for k, v in derivation["replay"].items():
    print(k, "ok" if v["ok"] else "not ok", [(c["id"], c["ok"]) for c in v["checks"] if not c["ok"]])
print("patch", derivation["patch"]["sha256"], "apply-check", derivation["patch"]["git_apply_check"])
