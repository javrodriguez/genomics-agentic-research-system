"""proxy_conf.py: the egress proxy's configuration for one take, rendered, parsed and checked.

Each take gets its own proxy container and its own internal network (ruling C7). The proxy is squid, because one
file carries the whole policy: a CONNECT to exactly one host, on port 443, chosen by the take's harness (D8 B2
item 8: arm A `api.anthropic.com`, arm O `api.openai.com`, arm G `generativelanguage.googleapis.com`), and
everything else denied. The template `proxy.conf` beside this file holds the one slot @ALLOWED_HOST@.

    render(harness)        the rendered configuration (refuses an unknown harness; never defaults)
    allowed_hosts(text)    every host an `http_access allow` line lets through, over a closed directive grammar
    check(text, harness)   every way `text` is not "exactly one allowed host per take, its arm's"

The shared values (interface 11) live here: HOSTS, ALIAS, PORT, PROXY_URL, CONF_PATH, COMMAND and USER. USER is
squid's package user, which only a built image can tell, so it is PENDING (interface 15): `pending()` names it and
`launch_fields()` raises NotReady while it is.

This module constructs and reads text only; it starts no process. Standard library only (and the seam's own
harness_bookkeeping, for the one harness name it imports rather than types).
"""

from __future__ import annotations

import os
import re

import harness_bookkeeping

PENDING = "PENDING"

CODEX = "codex"
GEMINI = "gemini"
# The one allowed host, by harness (interface 11; the take's harness, never its arm letter).
HOSTS = {
    harness_bookkeeping.CLAUDE_CODE: "api.anthropic.com",
    CODEX: "api.openai.com",
    GEMINI: "generativelanguage.googleapis.com",
}

ALIAS = "proxy"
PORT = 3128
PROXY_URL = f"http://{ALIAS}:{PORT}"
CONF_PATH = "/etc/squid/squid.conf"
COMMAND = ("squid", "-N", "-f", CONF_PATH)
TLS_PORT = 443
USER = PENDING

PENDING_WHY = {
    "USER": "squid's package user (name or uid:gid), which only a built egress image can tell; read from that image "
            "when CP2 builds it on the real box",
}

SLOT = "@ALLOWED_HOST@"
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy.conf")

# The closed directive grammar: each directive with the shape of its arguments.
DIRECTIVES = ("http_port", "acl", "http_access", "cache", "access_log", "pid_filename")
ACL_TYPES = ("port", "method", "dstdomain")
HOST_RE = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+")
ACL_NAME_RE = re.compile(r"[a-z][a-z0-9_]*")
ACCESS_LOG = "stdio:/dev/stdout"


class ProxyConfError(ValueError):
    """A configuration this module does not read, or a harness it does not know."""


class NotReady(RuntimeError):
    """A real use while a value it needs is PENDING."""


def pending() -> dict:
    """Every PENDING value of this module, with why and where it gets measured."""
    return {name: PENDING_WHY[name] for name in PENDING_WHY if globals()[name] == PENDING}


def launch_fields() -> dict:
    """The proxy container's fixed launch values (for run_take.ProxyLaunch); refuses while any is PENDING."""
    held = pending()
    if held:
        raise NotReady("pending: " + ", ".join(sorted(held)))
    return {"conf_target": CONF_PATH, "command": COMMAND, "user": USER, "alias": ALIAS}


def host_for(harness: str) -> str:
    if harness not in HOSTS:
        raise ProxyConfError(f"unknown harness {harness!r}")
    return HOSTS[harness]


def _template_text() -> str:
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        return fh.read()


def render(harness: str) -> str:
    """The configuration for one take of `harness`: the template with its one slot filled."""
    host = host_for(harness)
    text = _template_text()
    if text.count(SLOT) != 1:
        raise ProxyConfError(f"the template must hold the slot {SLOT} exactly once, not {text.count(SLOT)} times")
    out = text.replace(SLOT, host)
    found = check(out, harness)
    if found:
        raise ProxyConfError("the rendered configuration fails its check: " + "; ".join(found))
    return out


def parse(text: str) -> list:
    """The directives of `text` as (line, directive, [tokens]); an unknown directive or acl type is refused."""
    out = []
    for n, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\\" in line:
            raise ProxyConfError(f"line {n}: a continuation is not read here")
        toks = line.split()
        if toks[0] not in DIRECTIVES:
            raise ProxyConfError(f"line {n}: unknown directive {toks[0]!r}")
        if toks[0] == "acl":
            if len(toks) < 4 or toks[2] not in ACL_TYPES:
                raise ProxyConfError(f"line {n}: an acl must be `acl <name> <{'|'.join(ACL_TYPES)}> <value>...`")
            if not ACL_NAME_RE.fullmatch(toks[1]):
                raise ProxyConfError(f"line {n}: acl name {toks[1]!r}")
        out.append((n, toks[0], toks[1:]))
    return out


def _acls(directives) -> dict:
    acls = {}
    for n, d, args in directives:
        if d == "acl":
            name, kind, values = args[0], args[1], args[2:]
            if name in acls:
                raise ProxyConfError(f"line {n}: acl {name!r} defined twice (squid would merge the two)")
            acls[name] = (kind, values)
    return acls


def allowed_hosts(text: str) -> list:
    """Every host an `http_access allow` line lets through; an allow not bounded by one dstdomain acl is refused."""
    directives = parse(text)
    acls = _acls(directives)
    hosts = []
    for n, d, args in directives:
        if d != "http_access" or args[0] != "allow":
            continue
        names = args[1:]
        domains = [a for a in names if a in acls and acls[a][0] == "dstdomain"]
        if len(domains) != 1 or any(a.startswith("!") for a in names) or any(a not in acls for a in names):
            raise ProxyConfError(f"line {n}: an allow line must be bounded by exactly one dstdomain acl")
        hosts.extend(acls[domains[0]][1])
    return hosts


def check(text: str, harness: str) -> list:
    """Every way `text` is not "exactly one allowed host per take, its arm's" ([] when it is)."""
    try:
        host = host_for(harness)
        directives = parse(text)
        acls = _acls(directives)
        hosts = allowed_hosts(text)
    except ProxyConfError as e:
        return [str(e)]
    out = []
    if SLOT in text or "@" in text:
        out.append("an unrendered slot")
    by = {}
    for n, d, args in directives:
        by.setdefault(d, []).append(args)
    if by.get("http_port") != [[str(PORT)]]:
        out.append(f"exactly one `http_port {PORT}` (all addresses, no mode or option)")
    kinds = {}
    for name, (kind, values) in acls.items():
        kinds.setdefault(kind, []).append((name, values))
    ports = kinds.get("port", [])
    if len(ports) != 1 or ports[0][1] != [str(TLS_PORT)]:
        out.append(f"exactly one port acl, holding only {TLS_PORT}")
    methods = kinds.get("method", [])
    if len(methods) != 1 or methods[0][1] != ["CONNECT"]:
        out.append("exactly one method acl, holding only CONNECT")
    domains = kinds.get("dstdomain", [])
    if len(domains) != 1:
        out.append("exactly one dstdomain acl")
    else:
        values = domains[0][1]
        if len(values) != 1:
            out.append(f"the dstdomain acl must hold one host, not {values}")
        for v in values:
            if v.startswith(".") or v.startswith("-") or not HOST_RE.fullmatch(v):
                out.append(f"the dstdomain value {v!r} is not one exact host (no leading dot, no flag)")
    if hosts != [host]:
        out.append(f"the allowed hosts {hosts} are not exactly [{host!r}], {harness}'s own")
    if len(ports) == 1 and len(methods) == 1 and len(domains) == 1:
        p, m, h = ports[0][0], methods[0][0], domains[0][0]
        want = [["deny", f"!{m}"], ["deny", m, f"!{p}"], ["allow", m, h], ["deny", "all"]]
        if by.get("http_access") != want:
            out.append("http_access must be exactly: deny !CONNECT, deny CONNECT !443, allow CONNECT <host>, "
                       "then deny all, last")
    if by.get("cache") != [["deny", "all"]]:
        out.append("exactly one `cache deny all` (no cache)")
    if by.get("access_log") != [[ACCESS_LOG]]:
        out.append(f"exactly one `access_log {ACCESS_LOG}` (the walks read the refused hosts there)")
    if by.get("pid_filename") != [["none"]]:
        out.append("exactly one `pid_filename none`")
    return out
