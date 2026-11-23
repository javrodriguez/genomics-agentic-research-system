"""The pinned Claude Code 2.1.296 binary's refuse-if-present names, v2 (box lane, 15 Oct 2026; the review of ad71ca07,
MINOR 4: the refuse list must be complete over the sweep, so it cannot shrink and stay green). Supersedes
classify_claude_env_names.py (v1, kept as the record of 116d83e8's list). From the committed records of box ba6d7f14 only:
claude-2.1.296-binary-sweep-20261015.json (every name drive.py's credential and route patterns match),
claude-2.1.296-route-names-20261015.json (CLAUDE_CODE_USE_*, *_BASE_URL, *PROVIDER*, CLAUDE_CODE_SKIP_* and named
credentials) and claude-2.1.296-provider-tables-20261015.json (read only to place names by their bytes).

THE RULE. Every name either record carries is refused if present (refusing more fails closed), EXCEPT a name in
EXEMPT, each with its reason. RULED names (glitch-6b's rulings and the review's named three) are placed by class and
must each be carried by a record's bytes, else the run stops; CONTEXT names are env names seen only inside the records'
recorded contexts (outside every pattern and the route read), refused too and likewise required in the bytes.
Usage: python3 -I classify_claude_env_names_v2.py <binary-sweep json> <route-names json> -> classification JSON."""
import hashlib, json, sys
SWEEP, ROUTE = sys.argv[1], sys.argv[2]
PROVIDER = SWEEP.replace("binary-sweep", "provider-tables")


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


raw_s, raw_r, raw_p = _read(SWEEP), _read(ROUTE), _read(PROVIDER)
s, r, pt = json.loads(raw_s), json.loads(raw_r), json.loads(raw_p)
if not (s["binary_sha256"] == r["binary_sha256"] == pt["binary_sha256"]):
    sys.exit("the records are not of one binary")
if s["image"] != r["image"]:
    sys.exit("the records are not of one image")
RULED = {
    "route-outside": ("CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD", "CLAUDE_CODE_USE_MANTLE",
                      "CLAUDE_CODE_USE_GATEWAY", "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"),
    "credential-outside": ("CLAUDE_CODE_HOST_CREDS_FILE",),
    "route-unlisted": ("ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_BASE_URL", "ANTHROPIC_FOUNDRY_BASE_URL",
                       "ANTHROPIC_FOUNDRY_RESOURCE", "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_GOOGLE_CLOUD_BASE_URL",
                       "ANTHROPIC_BEDROCK_MANTLE_BASE_URL", "ANTHROPIC_UNIX_SOCKET", "CLAUDE_CODE_CUSTOM_OAUTH_URL",
                       "AWS_ENDPOINT_URL_BEDROCK_RUNTIME"),
    "credential-unlisted": ("ANTHROPIC_FOUNDRY_AUTH_TOKEN", "ANTHROPIC_IDENTITY_TOKEN", "ANTHROPIC_IDENTITY_TOKEN_FILE",
                            "ANTHROPIC_ENVIRONMENT_KEY", "ANTHROPIC_WORK_SECRET",
                            "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR", "CLAUDE_CODE_GATEWAY_TOKEN",
                            "CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR"),
}
# Env names seen only in the records' contexts (beside a swept name), outside every pattern and the route read.
CONTEXT = {"CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR": "credential-context",
           "CLAUDE_LOCAL_OAUTH_API_BASE": "route-context"}
EXEMPT = {"CLAUDE_CODE_OAUTH_TOKEN": "the Claude row's own login (run_take.LOGIN_VARIABLE[claude-code]); refused for "
                                    "every other arm by SUBSCRIPTION_TOKEN_VARIABLES"}
carried = set(s["names"]) | set(r["names"])
everything = raw_s + raw_r + raw_p
ruled = {n: c for c, names in RULED.items() for n in names}
for n in list(ruled) + list(CONTEXT):
    if n not in carried and n.encode() not in everything:
        sys.exit(f"{n} is in no record's bytes: the table names only what the binary carries")
rows = []
for n in sorted(carried | set(ruled) | set(CONTEXT)):
    if n in EXEMPT:
        cls = "exempt"
    elif n in ruled:
        cls = ruled[n]
    elif n in CONTEXT:
        cls = CONTEXT[n]
    else:
        cls = "pattern-matched" if n in s["names"] else "route-read"
    src = ("binary-sweep" if n in s["names"] else "route-names" if n in r["names"] else "record-bytes")
    rows.append({"name": n, "class": cls, "record": src, **({"reason": EXEMPT[n]} if n in EXEMPT else {})})
out = {"version": 2, "binary_sha256": s["binary_sha256"], "image": s["image"], "binary_path": s["binary_path"],
       "sweep_sha256": hashlib.sha256(raw_s).hexdigest(), "route_names_sha256": hashlib.sha256(raw_r).hexdigest(),
       "provider_tables_sha256": hashlib.sha256(raw_p).hexdigest(), "ruled": sorted(ruled), "exempt": EXEMPT,
       "rows": rows, "refuse_if_present": sorted(x["name"] for x in rows if x["class"] != "exempt")}
print(json.dumps(out, indent=1, sort_keys=True))
