# Review stubs for `_system/` landings (row 11's rule, row 14's ceremony)

The `Review:` trailer of a landing on main's first-parent line that touches `_system/` names a
small committed stub here, `<run_id>.md`, committed in the landing's one evidence child commit
beside its smoke record. The review itself stays outside the repository; the stub binds it.

A stub holds exactly one `session:` line (row 11's rule, checked by the pre-push hook and by
`gars/_system/hooks/audit_trailers.py`: exactly one, and different from the landing's `Session:`
trailer), plus:

```text
session: <reviewer session id>
reviewed: <base sha>..<head sha>
verdict: <the review's verdict>
review_sha256: <sha256 of the private review file>
```

The session id is a label, not an entry in a session registry: nothing here proves which
session wrote the review, only that the stub names a session other than the producer's.
