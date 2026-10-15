"""Postflight on a case-sensitive filesystem (athena, glitch-06's ask, 14 Oct 2026): the Codex lease home's auth.json
rules when a case variant of the name is present. Run with python3 -I from the folder holding the committed
evals/gap-study-4 subset; no docker, no network, fake values only; prints one JSON record, never file contents."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "evals", "gap-study-4"))
from box import preflight as pf, run_take as rt
FAKE = b'{"tokens": {"access_token": "FAKE-case-probe-0123456789-PLANTED"}}\n'
def write(p, data=FAKE, mode=0o600):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode); os.write(fd, data); os.close(fd); os.chmod(p, mode)
def home(base, name):
    d = tempfile.mkdtemp(prefix=name + "-", dir=base)
    with open(os.path.join(d, "config.toml"), "w") as fh: fh.write('model = "m"\n')
    return d
base = tempfile.mkdtemp(prefix="cases-", dir=HERE)
probe = os.path.join(base, "CaseProbe")
write(probe, b"x")
case_sensitive = not os.path.exists(os.path.join(base, "caseprobe"))
cases = []
def case(label, plant, expect_ok):
    d = home(base, "h")
    for rel, data in plant:
        write(os.path.join(d, rel), data)
    r = pf.postflight(d, rt.CODEX)
    cases.append({"case": label, "ok": r["ok"], "expected_ok": expect_ok, "as_expected": r["ok"] is expect_ok,
                  "detail": r["checks"][0]["detail"], "admitted": r["recorded"]["admitted_credential"],
                  "contents_leaked": "PLANTED" in json.dumps(r)})
case("auth.json alone", [("auth.json", FAKE)], True)
case("auth.json and Auth.json (a second file on this filesystem)", [("auth.json", FAKE), ("Auth.json", b"{}")], False)
case("AUTH.JSON alone (no registered file)", [("AUTH.JSON", FAKE)], False)
case("auth.json and sessions/AUTH.JSON", [("auth.json", FAKE), ("sessions/AUTH.JSON", b"{}")], False)
case("auth.json and a same-bytes Auth.JSON copy", [("auth.json", FAKE), ("Auth.JSON", FAKE)], False)
print(json.dumps({"probe": "postflight-case-sensitivity", "host_uname": os.uname().sysname,
                  "filesystem_case_sensitive": case_sensitive, "python": sys.version.split()[0],
                  "cases": cases, "all_as_expected": all(c["as_expected"] and not c["contents_leaked"] for c in cases)},
                 indent=1, sort_keys=True))
