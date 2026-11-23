"""Evidence (box lane, 15 Oct 2026): the 8 gitleaks findings a full-history bundle of the box branch carries all sit
in commits the PUBLIC GARS remote serves. `git ls-remote` of PUBLIC_REFERENCE["gars"], then athena_suite's own
scratch_clone + fetch_public_refs into a plain clone of the bundle, then `merge-base --is-ancestor <commit> <tip>`
over every public tip; also the count athena_suite's rule would scan (`rev-list --count <head> --not <tips>`).
Usage: python3 -I prove_findings_public.py <athena_suite.py> <bundle> <head> <gitleaks report.json> <work folder>"""
import json, os, subprocess, sys, importlib.util
SUITE, BUNDLE, HEAD, REPORT, WORK = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("athena_suite_proof", SUITE)
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
url = A.PUBLIC_REFERENCE["gars"]
ls = subprocess.run(["git", "ls-remote", "--heads", "--tags", url], capture_output=True, text=True, timeout=300)
os.makedirs(WORK, exist_ok=True)
check = os.path.join(WORK, "check-clone")
A.scratch_clone(BUNDLE, check, WORK)
tips = A.fetch_public_refs(check, url, WORK)
commits = sorted({f["Commit"] for f in json.load(open(REPORT))})
def anc(c, t):
    return subprocess.run(["git", "-C", check, "merge-base", "--is-ancestor", c, t]).returncode == 0
rows = {c: [t for t in tips if anc(c, t)][:1] for c in commits}
nonpublic = int(subprocess.run(["git", "-C", check, "rev-list", "--count", HEAD, "--not", *tips],
                               capture_output=True, text=True).stdout.strip() or -1)
out = {"public_url": url, "ls_remote_rc": ls.returncode, "ls_remote_refs": len(ls.stdout.splitlines()),
       "fetched_public_tips": len(tips), "finding_commits": len(commits),
       "each_finding_commit_reached_by_a_public_tip": {c: bool(v) for c, v in rows.items()},
       "head": HEAD, "commits_athena_suite_would_scan": nonpublic}
out["verdict"] = "PASS" if ls.returncode == 0 and all(out["each_finding_commit_reached_by_a_public_tip"].values()) \
    and len(commits) == 8 else "FAIL"
print(json.dumps(out, indent=1, sort_keys=True))
sys.exit(0 if out["verdict"] == "PASS" else 1)
