#!/usr/bin/env python3
"""Prepare one account's walk-token file on athena, ready for Javier to paste into (box lane, 14 Oct 2026).

    python3 -I prepare_walk_token.py claude1

Creates /home/<you>/gap4-secrets (mode 700) and /home/<you>/gap4-secrets/<account> (mode 700), and in it the file
claude-walk-token (mode 600) holding only the variable's name and the equals sign, `CLAUDE_CODE_OAUTH_TOKEN=`, with no
value and no newline: Javier pastes the token right after the `=` and saves (the editor ends the line). This matches
box/run_take.read_login's format and WALK_LOGIN_FILES. It refuses to run as root, through a link, inside a git
repository, or over a file that already holds more than the name (it never reads or prints a file's content; it reads
only its size). Prints the paths, modes, owner and size as JSON.
"""
import json
import os
import re
import stat
import sys

PREFIX = b"CLAUDE_CODE_OAUTH_TOKEN="
NAME = "claude-walk-token"


def fail(msg):
    print(json.dumps({"ok": False, "refused": msg}))
    raise SystemExit(1)


def entry(path):
    st = os.lstat(path)
    return {"path": path, "type": "link" if stat.S_ISLNK(st.st_mode) else "dir" if stat.S_ISDIR(st.st_mode)
            else "file" if stat.S_ISREG(st.st_mode) else "other", "mode": oct(stat.S_IMODE(st.st_mode)),
            "uid": st.st_uid, "size": st.st_size if stat.S_ISREG(st.st_mode) else None}


def main(argv):
    if len(argv) != 2 or not re.fullmatch(r"[a-z][a-z0-9]{0,15}", argv[1]):
        fail("usage: prepare_walk_token.py <account>, e.g. claude1")
    if os.getuid() == 0:
        fail("never as root")
    home = os.path.expanduser("~")
    base = os.path.join(home, "gap4-secrets")
    folder = os.path.join(base, argv[1])
    path = os.path.join(folder, NAME)
    probe = home
    while True:                                      # outside every git repository
        if os.path.lexists(os.path.join(probe, ".git")):
            fail(f"{probe} is inside a git repository")
        if probe == "/":
            break
        probe = os.path.dirname(probe)
    os.umask(0o077)
    for d in (base, folder):
        if os.path.islink(d):
            fail(f"{d} is a link")
        if not os.path.exists(d):
            os.mkdir(d, 0o700)
        if not os.path.isdir(d):
            fail(f"{d} is not a folder")
        os.chmod(d, 0o700)
    if os.path.lexists(path):
        st = os.lstat(path)
        if not stat.S_ISREG(st.st_mode):
            fail(f"{path} exists and is not a regular file")
        if st.st_size > len(PREFIX):
            fail(f"{path} already holds more than the variable name; left unchanged (a pasted token is never "
                 f"overwritten)")
        os.chmod(path, 0o600)
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.write(fd, PREFIX)
        os.close(fd)
    print(json.dumps({"ok": True, "entries": [entry(base), entry(folder), entry(path)],
                      "expected": {"folders": "0o700", "file": "0o600", "file_bytes_before_paste": len(PREFIX)}},
                     indent=1))


if __name__ == "__main__":
    main(sys.argv)
