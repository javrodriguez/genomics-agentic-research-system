> Copied unchanged from the owner's private planning repository, `plans/gap-study-4-reader-gap-sensitivity-PREREG-20261108.md` (committed there 2026-11-08 at 14:37 EST), sha256 `dfea5471d9eef1f64306bf295c5541b3a71b905dec579bb4ce8d40f18d172bda`; this line and the blank line after it are the only additions (`tail -n +3` of this file hashes to it).

# Gap Study round 4: reader-gap sensitivity analysis (pre-registered)

Written 2026-11-08T19:37:10Z by glitch-45 under Javier's OD201 (reader-fix-cost a, 2026-11-08T19:35:15Z).
It is written before any measured result has been read.
No grade, route outcome or per-arm count has been seen by the writer.

## Why

Two measured takes (s-3c4f8d, s-0e780d) could not be read by the frozen transcript reader (transcript_view.map_tool ViewError).
One was a Write call with argument key file_text; the other was a Skill tool call, followed by its harness meta record and a command_permissions attachment.
Under the frozen THE RULING RULE they are ruled aborted (OD201).
The gap is in the reader's code, not in the agent's behaviour, and later takes may hit it too.

## Primary analysis

Unchanged: exactly as frozen at freeze/r4-20261021 and its amendments.
Every take the frozen reader cannot read is ruled aborted with a cite starting "end state unreadable: ViewError".

## Secondary analysis (sensitivity, fixed now)

1. After the measured run ends, a reader patched to admit exactly these shapes is built on a separate branch, never on the line: Write.file_text as an alias of content; Skill as OTHER (keys skill, args); the harness's isMeta turnCompanion record whose sourceToolUseID is a Skill call; and the command_permissions attachment (keys type, allowedTools).
2. Every take ruled aborted with "end state unreadable: ViewError" is regraded with that reader. No other take is regraded.
3. A blind check runs first: every take the frozen reader could read gets a byte-identical grade under the patched reader.
4. The report shows the primary result and the secondary result side by side, plus the count of unreadable takes per arm, and which tool shapes caused them.
5. The headline claim rests on the primary analysis. If the secondary analysis changes any conclusion, the write-up says so plainly.

## Disclosure

The write-up names the reader gap, the two takes above, OD200 (fix the reader), and why OD201 reversed it (editing the reader voids the native-reader acceptance records and stales the checker digest).
