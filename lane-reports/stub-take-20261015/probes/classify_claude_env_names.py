"""The pinned Claude Code 2.1.296 binary's refuse-if-present names (box lane, 15 Oct 2026; glitch-6b's ruling 4(i)),
from the committed sweep records only (ba6d7f14): claude-2.1.296-binary-sweep-20261015.json (drive.py's patterns) and
claude-2.1.296-route-names-20261015.json (CLAUDE_CODE_USE_*, *_BASE_URL, *PROVIDER*, CLAUDE_CODE_SKIP_* and the named
credentials). Deterministic: an explicit table; a table name either record does not carry stops the run, and both
records must be of the same binary and the same image. Classes refused: route-outside (a provider or gateway switch no
drive.py pattern matches), credential-outside, route-unlisted (a provider endpoint or socket the patterns record but no
list stops), credential-unlisted (an inference credential the patterns record but no list stops). Recorded, never
refused: service (product-feature tokens, no inference route on the static read).
Usage: python3 -I classify_claude_env_names.py <binary-sweep json> <route-names json> -> classification JSON."""
import hashlib, json, sys
SWEEP, ROUTE = sys.argv[1], sys.argv[2]
def _read(path):
    with open(path, "rb") as fh:
        return fh.read()
raw_s, raw_r = _read(SWEEP), _read(ROUTE)
s, r = json.loads(raw_s), json.loads(raw_r)
TABLE = {
    "route-outside": ("CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD", "CLAUDE_CODE_USE_MANTLE",
                      "CLAUDE_CODE_USE_GATEWAY", "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"),
    "credential-outside": ("CLAUDE_CODE_HOST_CREDS_FILE",),
    "route-unlisted": ("ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_BASE_URL", "ANTHROPIC_FOUNDRY_BASE_URL",
                       "ANTHROPIC_FOUNDRY_RESOURCE", "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_GOOGLE_CLOUD_BASE_URL",
                       "ANTHROPIC_BEDROCK_MANTLE_BASE_URL", "ANTHROPIC_UNIX_SOCKET"),
    "credential-unlisted": ("ANTHROPIC_FOUNDRY_AUTH_TOKEN", "ANTHROPIC_IDENTITY_TOKEN", "ANTHROPIC_IDENTITY_TOKEN_FILE",
                            "ANTHROPIC_ENVIRONMENT_KEY", "ANTHROPIC_WORK_SECRET",
                            "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR", "CLAUDE_CODE_GATEWAY_TOKEN"),
    "service": ("CLAUDE_BRIDGE_OAUTH_TOKEN", "CCR_OAUTH_TOKEN_FILE", "CLAUDE_TRUSTED_DEVICE_TOKEN",
                "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_MEMORY_API_TOKEN", "CLAUDE_CODE_ARTIFACTS_API_TOKEN",
                "CLAUDE_CODE_HFI_BEARER_TOKEN", "CLAUDE_CODE_SLACK_TAG_TOKEN", "CLAUDE_CODE_MCP_SERVE_AUTH_TOKEN"),
}
REFUSED_CLASSES = ("route-outside", "credential-outside", "route-unlisted", "credential-unlisted")
# CLAUDE_CODE_HOST_CREDS_FILE is read beside CLAUDE_CODE_HOST_GATEWAY_LINEAGE (provider-tables record): it matches no
# sweep pattern, so it is placed by its env-access context in the provider-tables record, read below by name.
PROVIDER = SWEEP.replace("binary-sweep", "provider-tables")
raw_p = _read(PROVIDER)
if s["binary_sha256"] != r["binary_sha256"] or s["binary_sha256"] != json.loads(raw_p)["binary_sha256"]:
    sys.exit("the records are not of one binary")
if s["image"] != r["image"]:
    sys.exit("the records are not of one image")
seen = set(s["names"]) | set(r["names"])
rows = []
for cls, names in TABLE.items():
    for n in names:
        if n not in seen and not (n == "CLAUDE_CODE_HOST_CREDS_FILE" and ("a." + n).encode() in raw_p):
            sys.exit(f"{n} is in neither record: the table names only what the binary carries")
        src = "binary-sweep" if n in s["names"] else ("route-names" if n in r["names"] else "provider-tables")
        rows.append({"name": n, "class": cls, "record": src})
out = {"binary_sha256": s["binary_sha256"], "image": s["image"], "binary_path": s["binary_path"],
       "sweep_sha256": hashlib.sha256(raw_s).hexdigest(), "route_names_sha256": hashlib.sha256(raw_r).hexdigest(),
       "provider_tables_sha256": hashlib.sha256(raw_p).hexdigest(),
       "rows": rows, "refuse_if_present": sorted(x["name"] for x in rows if x["class"] in REFUSED_CLASSES),
       "recorded_not_refused": sorted(x["name"] for x in rows if x["class"] not in REFUSED_CLASSES)}
print(json.dumps(out, indent=1, sort_keys=True))
