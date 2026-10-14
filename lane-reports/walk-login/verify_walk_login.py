#!/usr/bin/env python3
"""Verify one account's walk-token file after Javier pastes the token (box lane, 14 Oct 2026).

    python3 -I verify_walk_login.py claude1

Prints only: present, mode ok, owner ok, folder ok, one line, format ok, three paste checks (the value contains '=',
was pasted twice, or starts with the variable name: each must be "no"), and a coarse length (empty, under 20, 20 or
more). Never the value, any part of it, or a hash of it. Exits 0 when every check passes, else 1. The rules are box/run_take.read_login's and
check_login_place's: a regular file (never a link) with one link, mode 600, owned by you, in a folder of its own that
is mode 700 and owned by you; exactly one newline-terminated line `CLAUDE_CODE_OAUTH_TOKEN=<value>`, the value at
least 20 characters, ASCII, with no whitespace and no double quote.
"""
import os
import re
import stat
import sys


def main(argv):
    if len(argv) != 2 or not re.fullmatch(r"[a-z][a-z0-9]{0,15}", argv[1]):
        print("usage: verify_walk_login.py <account>, e.g. claude1")
        return 1
    folder = os.path.join(os.path.expanduser("~"), "gap4-secrets", argv[1])
    path = os.path.join(folder, "claude-walk-token")
    out, ok = {}, True
    try:
        st, fst = os.lstat(path), os.lstat(folder)
    except OSError:
        print(f"present: no ({path})")
        return 1
    out["present"] = stat.S_ISREG(st.st_mode) and st.st_nlink == 1
    out["mode ok (600)"] = stat.S_IMODE(st.st_mode) == 0o600
    out["owner ok"] = st.st_uid == os.getuid()
    out["folder ok (700, yours, not a link)"] = (stat.S_ISDIR(fst.st_mode) and stat.S_IMODE(fst.st_mode) == 0o700
                                                 and fst.st_uid == os.getuid())
    length = "not checked"
    one_line = form = False
    bad = {"value contains '='": True, "value pasted twice": True, "value starts with the variable name": True}
    if out["present"] and st.st_size <= 4096:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as fh:
            raw = fh.read(4097)
        one_line = raw.count(b"\n") == 1 and raw.endswith(b"\n")
        prefix = b"CLAUDE_CODE_OAUTH_TOKEN="
        value = raw[len(prefix):].rstrip(b"\n") if raw.startswith(prefix) else b""
        form = (raw.startswith(prefix) and all(0x21 <= c <= 0x7e and c != 0x22 for c in value))
        n = len(value)
        length = "empty" if n == 0 else "under 20 (too short)" if n < 20 else "20 or more"
        # review-walk-token W-2: the shapes a wrong paste leaves (each a yes/no only, never the value)
        bad["value contains '='"] = b"=" in value
        bad["value pasted twice"] = n > 0 and n % 2 == 0 and value[:n // 2] == value[n // 2:]
        bad["value starts with the variable name"] = value.startswith(b"CLAUDE_CODE_OAUTH_TOKEN")
        del raw, value
    out["one line"] = one_line
    out["format ok (CLAUDE_CODE_OAUTH_TOKEN=..., no spaces or quotes)"] = form
    for k, v in out.items():
        print(f"{k}: {'yes' if v else 'NO'}")
        ok = ok and v
    for k, v in bad.items():
        print(f"{k}: {'YES' if v else 'no'}")
        ok = ok and not v
    print(f"length: {length}")
    ok = ok and length not in ("not checked", "empty", "under 20 (too short)")
    print("RESULT: OK" if ok else "RESULT: NOT OK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
