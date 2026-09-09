#!/usr/bin/env python3
"""Remove the operator's private context from a published transcript, and nothing else.

    python3 evals/scrub_transcripts.py --check           report, change nothing
    python3 evals/scrub_transcripts.py --write           redact in place

WHY THIS EXISTS. These transcripts are published so a stranger can regrade every take. They were
recorded by a headless agent whose working directory sat inside the operator's personal assistant
tree, so Claude Code loaded that tree's CLAUDE.md and its two imports -- the operator's own profile
and long-term memory -- into the agent's context, and the session file recorded them. That content
is the operator's private material. It has nothing to do with what the agent did, and it was never
meant to be part of the evidence.

WHAT IS REMOVED, AND WHAT IS DELIBERATELY KEPT.

  removed   any instructions file whose path is OUTSIDE this repository, plus the flattened copy of
            it in the same record's `rendered` field. Each removal is replaced by a notice naming
            the file and the sha256 of the content that was taken out, so a reader can see exactly
            what the agent was given without being shown it.
  removed   `session_context.userEmail`, which Claude Code injects into every session.
  KEPT      this repository's OWN CLAUDE.md. The agent's instructions are material to reading its
            behaviour, and that file is public in this repository already.
  KEPT      every operator turn and every agent turn, byte for byte. The script asserts this rather
            than trusting it: a scrub that altered a graded turn would change a published result.

WHY REDACT RATHER THAN REWRITE HISTORY. The commit that introduced the first study's transcripts is
cited in this repository's own verification reports, because GitHub's server-side timestamps on it
cannot be backdated -- which is the strongest integrity claim the published record has. Rewriting
history to remove the content would change that commit's sha and destroy the evidence. So the
history is left exactly as it is and the working tree is corrected in a new commit, which is stated
plainly here rather than implied.

No model is called. stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTICE = ("[redacted: the operator's private context, outside this repository. "
          "path={path} sha256={sha} bytes={n}]")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def in_repo(path: str) -> bool:
    """Is this instructions file part of the published repository?

    Matched on the repository's own directory NAME rather than on this machine's absolute path, so
    the check gives the same answer from a fresh clone at any location.
    """
    return f"/{REPO.name}/" in (path or "")


def replace_in_rendered(rec: dict, needle: str, note: str) -> None:
    """`rendered` is the flattened text actually sent to the model, and it is not a string.

    It is a list of {"content": ...} parts. The first version of this file tested `isinstance(str)`
    and so silently replaced nothing while reporting success -- the whole private payload stayed in
    the transcript and every count said it had gone. That is why nothing here is trusted: the
    caller re-reads the finished bytes and refuses if any removed text survives.
    """
    r = rec.get("rendered")
    if isinstance(r, str):
        if needle in r:
            rec["rendered"] = r.replace(needle, note)
        return
    if isinstance(r, list):
        for part in r:
            if isinstance(part, dict) and isinstance(part.get("content"), str):
                if needle in part["content"]:
                    part["content"] = part["content"].replace(needle, note)


def scrub_record(rec: dict, secrets: list[str]) -> tuple[dict, list[str]]:
    """Return the record with private context removed, and what was removed."""
    removed: list[str] = []
    att = rec.get("attachment")
    if not isinstance(att, dict):
        return rec, removed

    if att.get("type") == "instructions" and isinstance(att.get("files"), list):
        kept = []
        for f in att["files"]:
            if not isinstance(f, dict):
                kept.append(f)
                continue
            path = f.get("path", "")
            if in_repo(path):
                kept.append(f)
                continue
            content = f.get("content") or ""
            note = NOTICE.format(path=Path(path).name, sha=sha(content)[:16], n=len(content))
            kept.append({"path": path, "type": f.get("type"), "content": note})
            removed.append(path)
            # THE SAME CONTENT LIVES TWICE. `rendered` is the flattened text actually sent to the
            # model. Filtering `files` alone would leave every removed byte in `rendered`, which is
            # the shape of a fix that closes one of two routes.
            if content:
                replace_in_rendered(rec, content, note)
                secrets.append(content)
        att["files"] = kept

    if att.get("type") == "session_context" and isinstance(att.get("context"), dict):
        ctx = att["context"]
        if "userEmail" in ctx:
            email = ctx.pop("userEmail")
            removed.append("session_context.userEmail")
            if isinstance(email, str) and email:
                replace_in_rendered(rec, email, "[redacted: operator email]")
                secrets.append(email)
    return rec, removed


def graded_turns(lines: list[str]) -> list[str]:
    """Every record a grader reads. These must come out of the scrub unchanged."""
    out = []
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") in ("user", "assistant"):
            out.append(line)
    return out


def scrub_file(path: Path, write: bool) -> tuple[int, list[str]]:
    lines = path.read_text(errors="replace").splitlines()
    before = graded_turns(lines)
    out: list[str] = []
    removed_all: list[str] = []
    secrets: list[str] = []

    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            out.append(line)
            continue
        rec, removed = scrub_record(rec, secrets)
        removed_all += removed
        # A RECORD THIS SCRUB DID NOT TOUCH IS WRITTEN BACK VERBATIM. Re-serialising every line
        # would rewrite the bytes of turns nobody edited -- which the graded-turn guard correctly
        # refused on its first run, because a published result is bound to those bytes.
        out.append(json.dumps(rec, ensure_ascii=False) if removed else line)

    after = graded_turns(out)
    if before != after:
        raise SystemExit(f"REFUSING: the scrub changed a graded turn in {path}. Nothing written.")

    # THE CHECK THAT MATTERS. Everything above is an intention; this reads the bytes that would be
    # written and refuses if any removed text is still in them. The first version of this file had
    # no such check, reported 56 items removed, and removed none of them.
    body = "\n".join(out)
    survived = [t for t in secrets if t and t in body]
    if survived:
        raise SystemExit(
            f"REFUSING: {len(survived)} removed item(s) are still present in {path.name} after the "
            f"scrub. Nothing written. The first survivor starts: {survived[0][:70]!r}")

    if write and removed_all:
        path.write_text(body + "\n")
    return len(removed_all), removed_all


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove the operator's private context from transcripts.")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not (args.write or args.check):
        print("give --check or --write")
        return 2

    files = sorted(REPO.glob("evals/**/transcript.jsonl"))
    if not files:
        print("no transcript was found. That is not a pass.")
        return 2

    total = 0
    for f in files:
        n, removed = scrub_file(f, args.write)
        total += n
        tag = "would remove" if args.check else "removed"
        print(f"  {tag} {n:2}  {f.relative_to(REPO)}")
        for r in dict.fromkeys(removed):
            print(f"        - {r}")

    print(f"\n{len(files)} transcript(s); {total} private item(s) {'found' if args.check else 'removed'}")
    if args.write:
        print("graded turns were compared before and after in every file, and none changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
