"""Evidence (box lane, 15 Oct 2026, glitch-6b's ruling on the outward scan): walk_launch.outward_scan run with the REAL
athena_suite.py functions and the REAL gitleaks on a temporary repository whose "public remote" is a local bare
repository (file:// URL, so fetch_public_refs' own protocol rule applies). Three cases:
  public-only   every commit is on the public remote: nothing is scanned, the ship would pass;
  nonpublic     one commit the public remote does not serve carries a synthetic GitHub-token-shaped string, made at
                run time and never printed: the scan refuses;
  unreadable    the public URL points at no repository: refused (fail closed).
Usage: python3 -I prove_outward_rule.py <athena_suite.py> <gitleaks> <evals/gap-study-4 folder>"""
import json, os, secrets, string, subprocess, sys, tempfile
SUITE, GITLEAKS, STUDY = sys.argv[1:4]
sys.path.insert(0, STUDY)
from box import walk_launch as wl  # noqa: E402
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@invalid", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
       "PATH": os.environ["PATH"], "HOME": tempfile.gettempdir()}
def git(*a):
    return subprocess.run(["git", *a], env=ENV, capture_output=True, text=True, check=True).stdout.strip()
suite = wl.load_suite(SUITE)
out = {"suite": SUITE, "gitleaks": GITLEAKS, "cases": {}}
for case in ("public-only", "nonpublic", "unreadable"):
    with tempfile.TemporaryDirectory() as t:
        repo, pub = os.path.join(t, "repo"), os.path.join(t, "public.git")
        git("init", "-q", "-b", "main", repo)
        open(os.path.join(repo, "a.txt"), "w").write("a\n")
        git("-C", repo, "add", "a.txt"); git("-C", repo, "commit", "-q", "-m", "a")
        git("init", "-q", "--bare", pub)
        git("-C", repo, "push", "-q", pub, "main")              # the synthetic public remote, local only
        if case == "nonpublic":
            fake = "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))
            open(os.path.join(repo, "b.txt"), "w").write(f"token = {fake}\n")
            git("-C", repo, "add", "b.txt"); git("-C", repo, "commit", "-q", "-m", "b")
        head = git("-C", repo, "rev-parse", "HEAD")
        bundle = os.path.join(t, "out.bundle")
        git("-C", repo, "bundle", "create", bundle, "main")
        url = "file://" + (pub if case != "unreadable" else os.path.join(t, "absent.git"))
        suite.PUBLIC_REFERENCE[wl.SUITE_KIND] = url
        try:
            n = wl.outward_scan(suite, repo=repo, bundle=bundle, head=head, gitleaks=GITLEAKS,
                                work=os.path.join(t, "work"))
            out["cases"][case] = {"refused": False, "scanned_commits": n}
        except Exception as e:  # noqa: BLE001
            out["cases"][case] = {"refused": True, "kind": type(e).__name__, "why": str(e)[:200]}
ok = (out["cases"]["public-only"] == {"refused": False, "scanned_commits": 0}
      and out["cases"]["nonpublic"]["refused"] and out["cases"]["unreadable"]["refused"])
out["verdict"] = "PASS" if ok else "FAIL"
print(json.dumps(out, indent=1, sort_keys=True))
sys.exit(0 if ok else 1)
