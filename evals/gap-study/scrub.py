#!/usr/bin/env python3
"""Take the operator's email address out of a transcript this study publishes, and nothing else.

    python3 evals/gap-study/scrub.py <transcript> ...           report, change nothing
    python3 evals/gap-study/scrub.py <transcript> ... --write   redact, and write scrub.json beside it

WHY THIS EXISTS. Claude Code injects the signed-in account's email address into every session as
`session_context.userEmail` (2.1.267, the version these runs were driven under), and no documented
setting removes it. It says nothing about this study and nothing about what the agent did. It is
the operator's personal address, and this repository is public. The study's own test already
refuses any published walk carrying it.

WHY NOT THE FIRST STUDY'S SCRUB. `evals/scrub_transcripts.py` belongs to that study and is never
edited. It also replaces every instruction file whose path does not contain this repository's
folder name -- right for transcripts driven inside this repository, and wrong for this study's, which
run in a checkout under a temporary directory. It would replace the checkout's own CLAUDE.md, which
is this repository's public file, with a notice saying it came from outside the repository. So this
removes one field, and proves it removed nothing else.

WHAT IT GUARANTEES, READ FROM THE BYTES IT WOULD WRITE RATHER THAN INTENDED:

  every record other than a session context carrying the field is written back byte for byte
  every record a grader reads (`user`, `assistant`) is identical before and after
  the address itself appears nowhere in the written bytes
  scrub.json beside the transcript records the sha256 before and after, and what was removed

WHERE IT APPLIES. The walks and the checkout smokes. Whether a GRADED TAKE's published transcript may
carry this redaction is the repository owner's decision, because the pre-registration's rule for a
take is that its transcript is the session file copied verbatim. This file does not decide that.

No model is called. stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

NOTE = "[redacted: operator email]"
ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _replace_in_rendered(rec: dict, needle: str) -> None:
    """`rendered` is the text actually sent to the model: a string, or a list of content parts."""
    r = rec.get("rendered")
    if isinstance(r, str):
        rec["rendered"] = r.replace(needle, NOTE)
    elif isinstance(r, list):
        for part in r:
            if isinstance(part, dict) and isinstance(part.get("content"), str):
                part["content"] = part["content"].replace(needle, NOTE)


def graded(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("type") in ("user", "assistant"):
            out.append(line)
    return out


def scrub_text(raw: str) -> tuple[str, list[str]]:
    """The scrubbed text and what was removed. Raises SystemExit rather than write a bad result."""
    lines = raw.splitlines()
    out: list[str] = []
    removed: list[str] = []
    addresses: set[str] = set()
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            out.append(line)
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        ctx = att.get("context") if isinstance(att, dict) else None
        if (isinstance(att, dict) and att.get("type") == "session_context"
                and isinstance(ctx, dict) and "userEmail" in ctx):
            sentence = ctx.pop("userEmail")
            removed.append("session_context.userEmail")
            if isinstance(sentence, str) and sentence:
                _replace_in_rendered(rec, sentence)
                addresses.update(ADDRESS.findall(sentence))
            out.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
        else:
            out.append(line)

    if graded(lines) != graded(out):
        raise SystemExit("REFUSING: the scrub would change a record a grader reads. Nothing written.")
    body = "\n".join(out) + ("\n" if raw.endswith("\n") else "")
    survived = [a for a in addresses if a in body]
    if survived:
        raise SystemExit(f"REFUSING: the address removed from the session context is still present "
                         f"elsewhere in the transcript ({len(survived)} address(es)). Nothing "
                         f"written; a record that carries it is not this file's to change.")
    return body, removed


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove the injected account email from transcripts.")
    ap.add_argument("transcripts", nargs="+")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    for t in args.transcripts:
        path = Path(t)
        raw = path.read_text(errors="strict")
        body, removed = scrub_text(raw)
        if not removed:
            print(f"  nothing to remove  {path}")
            continue
        record = {"transcript": path.name, "sha256_before": sha256(raw), "sha256_after": sha256(body),
                  "removed": removed, "records_a_grader_reads": "identical before and after",
                  "why": "Claude Code injects the signed-in account's email address into every "
                         "session; it is the operator's personal address and says nothing about "
                         "the agent. See scrub.py."}
        if args.write:
            path.write_text(body)
            (path.parent / "scrub.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"  {'removed' if args.write else 'would remove'} {len(removed)}  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
