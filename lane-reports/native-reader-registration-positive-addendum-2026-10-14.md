# Gemini native-reader registration: a positive registration (addendum)

Parent: `fd4177e0`. Writer: Claude Code harness lane, 14 Oct 2026 02:25 EDT, under glitch-06's order (a gate nothing can pass proves nothing).

`PositiveRegistration` in `tests/test_native_reader_registration.py` builds a throwaway temp git repository with temp copies of the reader's sources.
It commits an unmarked walk through the real `drive.WalkRepo.commit_walk`, then a review and an acceptance record (acceptor `javier`, a different reviewer).
The walk has 2 interactions, 2 tool round trips and 2 retained snapshots.
`production_readers` registers the reader.
Five single mutations, each on a fresh repository, unregister it, each refusal asserted by its reason: a working-tree drift, a committed source edit, the native ref swapped to an earlier ledger snapshot, another acceptor, and a synthetic marker in the review.

The fixture is unmarked on purpose, as its comment says: the synthetic-marker gate refuses every labelled fixture.
It lives only in the temp folder and never touches the study tree.
Its walk folder is still written by the test, not by a driver; the review's finding 2 (no real Gemini walk can reach the gate) is the next fix, and this test moves onto that road then.

Verification: the module 10/10 (behind a light gate).
Twenty in-memory mutants were all killed, including two that make the gate unpassable (the marker matching everything; production_readers never registering), which no test killed before this one.
