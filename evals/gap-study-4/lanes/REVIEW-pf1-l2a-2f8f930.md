VERDICT: PASS

# Closure review of lane pf1-l2a, commit 2f8f930e (on 5c4ec7c7)

Reviewer: the same fresh reviewer as the 5afd80a and 898e598 reviews, Sat 24 Oct 2026, 20:21-20:25 EDT by `date`.
Read:
- `git show 2f8f930e` (check_results.py, run.py, takes.py, result.py, and the lane test);
- how 5c4ec7c7 wires `batch.door_rule_problems` into the restart and `run.produce`.

Probes, all in /private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/l2a/: the applicable parts of probe.py and probe2.py, plus a new probe3.py.
All ran with python3.12 behind `mac_slot.py light-ok`.
At 2f8f930e, test_pf1_routing_rulings is OK.

## The previous MINOR 1, closed (5c4ec7c7)

`history_problems` still accepts a no-records re-run with no refusal record, and a forged pin block (probe2 a7, c2).
That is now intended: `batch.door_rule_problems`, which restart and publication call, refuses both.
- probe3 g1: "its drive started and left no records, and no refusal record of the driver's was committed with its outcome".
- probe3 g2: "its block names the driver's pin, but the pin is the registered row's own profile".

All earlier results are unchanged: probe.py 1, 2, 2b, 4, 4b, 6, 8, 8b and 9, and probe2 a1-a6, c1, c3, c4, d1, e1 and f1-f7.

## The questions asked

**Is the commit subject a strong enough producer check?**
It is not a producer proof.
Anyone with commit access can write that subject.
probe3 g3: a hand commit whose subject is `TAKE_COMMIT_SUBJECT` reads True from `outcome_committed_by_take_road`.
It is enough here, for two reasons.
1. The only thing it unlocks is an exemption from the identity guard for an outcome that is never counted (next answer).
   It cannot add, drop or re-route a counted take.
2. Forging an outcome commit is a different and larger power than any ruling.
   It sits outside the ruling threat, as with the f4 note in the 898e598 review.
   The real guard on the ruling side still holds: a re-running ruling that passed the rule, plus a later outcome under the registered pin.

Offline, there is no stronger anchor than the commit road short of signed commits.
The lane does not over-claim: the commit message and the docstring say "the take road's commit", never a signature.

**Can an exempt outcome be counted?**
No.
- An exempt outcome needs a re-running ruling and a later outcome of the same slot.
- In `check_results.publication`, a re-run ruling sets `final=False` (check_results.py, the RULE_RERUN branch).
  A route ruling that would make the take final hits "comes after its final effective attempt" as soon as the later outcome is read.
- `run.record_for` returns None for a non-final outcome.
- The lane's PB test asserts exactly one counted record (the re-run's) and the expected harness event.
- A blocked outcome is committed with `final False` (probe3 g4).

**The result.py addition (a merge spot with L2b):**
The addition is small: one key in `from_records` and one line in `render`.
L2b's MAJOR 10 work re-shapes result.py's rendering (the original report, and the follow-up).
See NIT 1.

## Findings

### 1. NIT: nothing tests that result.py renders the harness events

The PB test covers `check_results.render_harness_events` and `run.produce`.
It does not cover `result.from_records` or `result.render`.
An L2b merge that drops the new `render` line, or renders the original report through a new function, would stay green.
Add one check that `result.render(result.from_records(...))` on the PB history shows "Harness events: driver pin blocks".
Or bind it at L6's integration.

### 2. NIT: result.py and produce each compute the harness events

`result.from_records` builds `registered` from the rows without `validate_ledger`, and calls `pin_block_events` with the real git readers.
`produce` passes its own `refusal` and `committed`.
In production both use the defaults, so they agree.
Passing the list produce already returned would leave one source.

### 3. NIT, carried: a pin block that also leaks its container

This is the 898e598 review's NIT 2, unchanged.
The leak rewrites the reason, so such a take is neither an exempt event nor re-runnable.
It stops for an owner, which fails safe.
