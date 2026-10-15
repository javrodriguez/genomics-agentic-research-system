#!/usr/bin/env python3
"""Verify one account's walk-login file after Javier pastes the value (box lane, 14 Oct 2026).

    python3 -I verify_walk_login.py claude1      (Claude Code's walk token)
    python3 -I verify_walk_login.py r4-g         (the Gemini arm's study key, glitch-06, 14 Oct 2026)

Prints only: present, mode ok, owner ok, folder ok, one line, format ok, three paste checks (the value contains '=',
was pasted twice, or starts with the variable name: each must be "no"), and a coarse length (empty, under 20, 20 or
more), a quote check (any ' or " in the value: "no"), and the stray non-ASCII check, which names the first such character
by its Unicode name only (a Mac's Option key types them: U+2248 ALMOST EQUAL TO from Option-X). Never the value, any part
of it, or a hash of it. Exits 0 when every check passes, else 1. The rules are box/run_take.read_login's and
check_login_place's: a regular file (never a link) with one link, mode 600, owned by you, in a folder of its own that
is mode 700 and owned by you; exactly one newline-terminated line `<VARIABLE>=<value>` (ACCOUNTS), the value at
least 20 characters, ASCII, with no whitespace and no double quote. The single-quote refusal is this script's own,
stricter than read_login, which refuses only `"`; so are the paste checks and the stray-character check.
"""
import os
import re
import stat
import sys
import unicodedata

# box/run_take.WALK_LOGIN_FILES: each account, its file's name and the one variable it holds
ACCOUNTS = {"claude1": ("claude-walk-token", b"CLAUDE_CODE_OAUTH_TOKEN="),
            "r4-g": ("gemini-walk-login", b"GEMINI_API_KEY=")}


def main(argv):
    if len(argv) != 2 or not re.fullmatch(r"[a-z][a-z0-9-]{0,15}", argv[1]) or argv[1] not in ACCOUNTS:
        print(f"usage: verify_walk_login.py <account>, one of {sorted(ACCOUNTS)}")
        return 1
    name, prefix = ACCOUNTS[argv[1]]
    folder = os.path.join(os.path.expanduser("~"), "gap4-secrets", argv[1])
    path = os.path.join(folder, name)
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
    bad = {"value contains '='": True, "value pasted twice": True, "value starts with the variable name": True,
           "quote in the value": True}
    stray = "not checked"
    if out["present"] and st.st_size <= 4096:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as fh:
            raw = fh.read(4097)
        one_line = raw.count(b"\n") == 1 and raw.endswith(b"\n")
        value = raw[len(prefix):].rstrip(b"\n") if raw.startswith(prefix) else b""
        form = (raw.startswith(prefix) and all(0x21 <= c <= 0x7e and c != 0x22 for c in value))   # read_login's rule
        # glitch-06 (14 Oct 2026): a stray non-ASCII character, named by its Unicode name only, never shown
        stray = "none"
        for ch in raw.decode("utf-8", "replace"):
            if ord(ch) > 0x7e:
                stray = unicodedata.name(ch, f"U+{ord(ch):04X}") if ch != "\ufffd" else "a byte that is not UTF-8"
                break
        n = len(value)
        length = "empty" if n == 0 else "under 20 (too short)" if n < 20 else "20 or more"
        # review-walk-token W-2: the shapes a wrong paste leaves (each a yes/no only, never the value)
        bad["value contains '='"] = b"=" in value
        bad["value pasted twice"] = n > 0 and n % 2 == 0 and value[:n // 2] == value[n // 2:]
        bad["value starts with the variable name"] = value.startswith(prefix[:-1])
        bad["quote in the value"] = b'"' in value or b"'" in value
        del raw, value
    out["one line"] = one_line
    out[f"format ok ({prefix.decode()}..., no spaces or quotes)"] = form
    for k, v in out.items():
        print(f"{k}: {'yes' if v else 'NO'}")
        ok = ok and v
    for k, v in bad.items():
        print(f"{k}: {'YES' if v else 'no'}")
        ok = ok and not v
    print(f"stray non-ASCII character: {stray}")
    ok = ok and stray == "none"
    print(f"length: {length}")
    ok = ok and length not in ("not checked", "empty", "under 20 (too short)")
    print("RESULT: OK" if ok else "RESULT: NOT OK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
