# B19 design note: a rolling window for batch.py's drives

Lane vendor-b19, round 1, cloud executor, Mon 19 Oct 2026. Rulings B19-1 (the goal), B19-2 (this note), B19-3 (the red
tests) and B19-4 (batch.py unchanged this round). Read at lane/vendor-admission 7dc0cf9e; every line number below is
that commit's. Nothing here has been built. (Round 2, under rulings B19-5 to B19-11, built it: section 10.)

## 1. Where this note lives, and why

`lane-reports/B19-DESIGN-NOTE.md`, beside batch.py's other design notes: the ones its docstring and code cite
(`lane-reports/nightly-stop-rule-2026-10-14.md` for THE NIGHTLY STOP's D-4-1 and D-4-2, `w1b-cp1-routing-batch.md`
for the loop's first build, `w7c-spend-wiring.md` for THE MONEY GATE) and this lane's own B14 and B16 notes. It stays
out of `evals/gap-study-4/` on purpose: everything under that folder is claimed file by file in `COPIED.d/` and bound
into the study tree that freeze.py hashes (`study_tree_sha`, freeze.py 218-229), so a note there would be one more
file of the frozen study. A note about how the loop should change belongs with the notes that record how it came to be.

## 2. Today's loop, and the proposed one

Today (batch.py 904-932): take a block of up to BLOCK = 3 queued (row, attempt) pairs (913), run the money gate on the
block (915), register the block's rows (917), launch each (919), drive all of them at once in a pool sized to the block
(920-924), wait for every drive of the block, commit them one by one in row order (926-929), put the block's re-runs
back at the front of the queue in row order (931), and go round again. A slow drive holds the two lanes beside it
idle until it ends.

Proposed (B19-1). The loop keeps at most BLOCK drives in flight. It holds a list of *open* takes in launch order (each
registered and launched, its outcome not yet committed), and repeats:

1. **Commit.** While the oldest open take's drive has finished, decide its fate and commit it (the same `_commit`),
   and put a re-run at the front of the queue. A drive that has finished behind an unfinished older one waits.
2. **Hold.** If the loop has stopped, or a hold is set (section 4: a pause seen, a stop seen, a nightly count reached
   in prospect, or a half-cell about to close at the queue's head), launch nothing; when nothing is left open, wait
   for the usage window if a pause asks for it, clear the hold, and go on (or return, when stopped).
3. **Fill.** Otherwise take the next queued rows, as many as there are free drive lanes (fewer if the open-take bound
   of section 5.1 is reached), as one *wave*: the money gate on the wave, register its rows in row order, launch each
   in row order. These are exactly today's `_money_gate`, `_register` and `_launch_paid_checked`, called on a wave
   instead of a block.
4. **Wait** until any drive in flight finishes; read its routed state from its finished step (section 4); go to 1.

**The tie rule.** Drives that have finished by the time step 1 runs are all committed before step 3 fills a lane; step
1 runs again after every commit. This is what makes the equal-duration case the block case. "Equal durations" means
drives the loop observes finished at one reading: three drives of one wave seen finished together are committed
together, their re-runs requeued first, and only then is the next wave of three taken, exactly as today's block. The
tests model it so (tests/test_batch_rolling.py, TimedDriver when equal and EqualRepo; test_batch's World): a wave's
other drives end only once its head's commit has begun, and a commit waits until every future the loop holds open is
done (B19-13).

Under that model every wave is three rows (or what the queue has left), every gate, registration, launch, commit,
re-run requeue, window wait, nightly stop and closed-cell drop happens at the place it happens today, and the committed
history is byte-for-byte the block run's. Real drives of equal length may roll: when they end a few milliseconds apart
and the loop reads them inside that skew, it fills the lane one freed, so registration order, re-run placement and
which pauses share a window event can differ from a block run's, while pauses that share one usage reset still count
once. With unequal durations, a wave is mostly one row, filling the lane a finished drive freed.

## 3. Every behaviour that depends on the block

For each: today's text and line; the rolling behaviour proposed; and whether the change can move a committed record's
bytes, an outcome, or a pre-registered element. "Equal durations" means drives the loop observes finished at one
reading, under which the block run is reproduced exactly (section 2; real drives of equal length may roll); the "can
move" column is about unequal durations.

### 3.1 The block itself: BLOCK, `self.block`, the pool

- Today: `BLOCK = 3` (251); `self.block = 1 if serial else BLOCK` (584); `block = [queue.popleft() for _ in
  range(min(self.block, len(queue)))]` (913); `ThreadPoolExecutor(max_workers=len(block))` (920); docstring step 1
  (11) "take a block of up to three slots from the queue".
- Rolling: BLOCK keeps its value and becomes the number of drive lanes; `serial=True` keeps one lane (which is today's
  serial run exactly). One pool of BLOCK workers lives for the whole run; waves are submitted to it as lanes free.
- Can move: no record's bytes (the outcome keys and their values are decided by the same handlers); which takes run
  side by side changes, which is the point. No pre-registered element names the block (section 6).

### 3.2 The money gate before registration (W7C-gap4-1, W7C-R1-3, W7C-close-1)

- Today: docstring 165-177, "Before each block is registered, every row of the block whose harness bills money per
  call ... is put through both, on one reading of the spend ledger ... nothing of the block is registered or launched
  ... (the block's Claude rows wait too)"; `if self._money_gate(block)` (915), `_money_gate` (946-957), the re-check
  of the hold on a fresh clock reading just before each paid launch (`_launch_paid_checked`, 959-976), which commits a
  refused take `failed` with drive_started false and launches no later take of the block.
- Rolling: the gate runs on each wave, before its rows are registered, on one ledger reading, with the same
  `money_gate_problems`; the per-launch re-check is unchanged. A refusal stops the loop as today; the takes already
  open finish and are committed (step 2), and nothing more is registered. With equal durations the waves are the
  blocks, so every gate reading and every refusal falls where it does today.
- Can move: no record's bytes. With unequal durations the ledger is read once per wave (mostly per row) instead of
  once per block, so the gate sees fresher spend; a Claude row that would have shared a block with a refused paid row
  may already be registered and running when the paid row is refused (today it waits with the block). No outcome is
  decided by the gate; it only stops the loop. W7C-gap4-1's "before each block" wording needs re-ruling (section 7).

### 3.3 Registration, and a register failure (W1B2-5)

- Today: `_register(block)` (986-1002), "Register the block's rows, one commit each, in row order. If one fails,
  commit every row already registered as `failed`"; docstring 179-184.
- Rolling: `_register(wave)`, unchanged. Registration stays serial, in row order, before each launch, and never
  overlaps a commit (one thread does both). A register failure commits the wave's already-registered rows `failed`
  (nothing launched) as today, stops the loop, and lets the open takes finish and commit first.
- Can move: no record's bytes. **Outside batch.py, three things refuse a registration made while other takes are open,
  and each must change with it** (section 5).

### 3.4 Commits in row order and the re-run requeue

- Today: "decide each take's fate ... then commit its records ... serially, in row order, for every take of the
  block" (docstring 19-20); the commit loop (926-929); `queue.extendleft(reversed(requeue))  # same slots, first, in
  row order` (931).
- Rolling: commits stay serial and in launch order (step 1); a re-run is put at the front of the queue as soon as its
  take is committed, ahead of every row not yet registered, and re-runs committed in one step 1 keep row order. With
  equal durations the requeue happens exactly where it does today.
- Can move: no record's bytes. With unequal durations a re-run's attempt is registered after whatever rows were
  launched while its first attempt waited behind a slower older take, so attempt numbers are unchanged but the
  interleaving of slots in `takes.json` and `outcomes.json` differs from a block run's.

### 3.5 The usage-window pauses that share one event (W1B3-5)

- Today: THE CELL CAPS (docstring 45-56): "the pauses that share one reset count once ... this loop drives a block of
  up to three and every pause of one block shares the one reset it waits for before the next block"; `window_event`
  (95) "shared by every pause of one block"; `self._block_event = None  # the block's pauses share one window event
  (W1B3-5)` (925); `_window_event` (1104-1109), "a new one at its first pause, shared by the rest"; the pause handler
  sets `self.paused` (1273, and 1222 in a closed half-cell); the wait comes before the next block (909-912).
- Rolling: **the pause is acted on when its drive finishes, not when it is committed.** A finished step whose routed
  state is pause (the drive step routes before it returns, 1154-1176) sets the hold at once, so no new drive starts
  while the window is spent. The takes open at that moment (at most BLOCK drives in flight, plus finished takes waiting
  behind an older one) finish and are committed; then the loop waits (`_wait_window`) and clears the hold. A window
  event is a new number at the first pause committed after the last wait (or the run's start), shared by every pause
  committed before the next wait: `_block_event` is cleared after each wait instead of at each block. Every pause that
  shares an event comes from a drive that was in flight when the first one was seen, so an event still holds at most
  BLOCK pauses, one per slot, as today.
- With equal durations: each wave's pauses are committed together and the wait follows, so the events are today's.
- Can move: no record's bytes beyond the window_event values. With unequal durations, which pauses share an event
  depends on which drives overlapped, so a half-cell's pause count, and so whether and when it closes at
  `events_per_half_cell` = 3, can differ from what a block run of the same takes would have counted. W1B3-5's rule (the
  pauses that share one reset count once) is kept exactly; only its block wording ages. Two readers outside batch.py
  assume the block's span (section 5.3).

### 3.6 restart_waits over the last BLOCK committed outcomes (lane w1b decision 11, W1B3-3)

- Today: `restart_waits` (320-326), "a restart waits for the usage window when a pause, committed or ruled, is among
  the last BLOCK committed outcomes ... or the rulings committed among or after them"; `self.paused =
  restart_waits(history)` (789); docstring 148-151 and 204.
- Rolling: a stop or crash after a pause can leave more than BLOCK outcomes committed after it (every take that was
  open when the pause was seen). The span becomes the open-take bound (section 5.1): a restart waits when a pause,
  committed or ruled, is among the last MAX_OPEN committed outcomes or the rulings among or after them. Waiting too
  often costs nothing: wait_reset returns at once when the window has already reset (THE USAGE WINDOW, 202-210).
- Can move: no record's bytes and no outcome (a wait decides when, never what). W1B3-3's binding to "the last BLOCK"
  needs re-ruling (section 7).

### 3.7 The nightly stop carried by the block's last row (D-4-1, the step-4 review)

- Today: docstring 214-218, "when the count reaches NIGHTLY_HARNESS_ERRORS, the block's last committed outcome carries
  `stop` = NIGHTLY_STOP + why ... and nothing further is registered"; `self._block_last = (block[-1][0]["slot"],
  block[-1][1])  # THE NIGHTLY STOP: carried by the last` (914); `_nightly` (1081-1094), "the block's last outcome
  carries the stop and the loop stops after the block".
- Rolling: when committed harness-errors plus finished-but-uncommitted ones reach NIGHTLY_HARNESS_ERRORS, the hold
  is set (no new launch). The stop is carried by the last open take at the moment the commit that reaches the count
  lands (the take launched last), or by that take itself when nothing else is open; `_block_last` becomes "the last
  open take", updated at each launch. The count, the D-4-1 window, the replay (`_night_walk`) and the night ruling
  are unchanged.
- With equal durations the last open take is the block's last row, as test_batch_rolling's second equal-duration
  scenario pins (the stop on slot 4, the wave's last).
- Can move: which committed record carries the stop text (a reader's marker only: the replay never trusts it,
  docstring 223-224). With unequal durations up to MAX_OPEN - 1 takes may be driven after the take that reached the
  count, where a block allowed at most two; the prospective hold keeps that to the takes already launched.

### 3.8 Stops: blocked, failed, a leak (W1B3-1, W1B2-5)

- Today: "the loop stops launching; the rest of the queue stays unstarted for a human" (docstring 37-38); a leak "the
  loop stops after the block, the stop committed with the record" (104-105); `_stop` (1276-1280); the leak in
  `_commit` (1009-1013); `while self.stopped is None` (905).
- Rolling: a finished step whose state is blocked or failed, or whose container leaked, sets the hold at its finish;
  the open takes finish and are committed in row order; the loop returns. `stopped` and the committed stop text are
  set at the commit, as today.
- Can move: no record's bytes. As in 3.7, more takes may already be open when a stopping take finishes than a block
  held; none is launched after it finishes.

### 3.9 The cap and the closed-cell drops (glitch-f3's cap ruling, 6 Oct 2026)

- Today: `queue = self._drop_closed(queue)` (906) and `_drop_closed` (934-944): a closed half-cell's queued rows and
  re-runs are dropped, each listed in `skipped`; `_decide` (1214-1225): "In a half-cell that has already closed (a
  drive of the same block, running when it closed), never a re-run, and the cell state is carried"; docstring 56-60,
  "A drive of the same block that was already running when its half-cell closed is committed as usual".
- Rolling: `_drop_closed` runs before every wave. A drive of the half-cell that was open when it closed is committed
  carrying the cell state, as today ("of the same block" becomes "open"). New: when the row at the queue's head
  belongs to a half-cell in which a finished, uncommitted rehearsal or pause would bring the count to its cap, the
  hold is set until that take commits (then the row is dropped as today). The queue order is never changed.
- Can move: no record's bytes. Without that head-of-queue hold, more drives of a half-cell could start after the take
  that closes it (any number up to MAX_OPEN - 1, against two today), each a take that is driven and then carries
  `incomplete — mechanical`; with it, only drives already launched when the closing take finished can.

### 3.10 The ledger and history records

- Today: one commit per registration (`takes.json`) and one per outcome (`outcomes.json`), in the order the loop makes
  them; `history()` in commit order (R4-4); every outcome exactly OUTCOME_KEYS (255-259); rulings and night rulings
  committed by people (takes.py); `Batch.history_problems` and `cell_history_problems` replay it.
- Rolling: the same records, the same keys, the same doors. Registrations and outcome commits interleave where
  waves overlap (a registration can land between two outcomes). Every replay reads outcomes in commit order and
  never reads registrations, so `_replay`, `history_problems`, `cell_history_problems` and `_night_walk` need no
  change; window events still rise in commit order and are never reopened (the 'reopened' refusal holds, since an
  event is closed by its wait before any later pause is committed).
- Can move: no key, no record shape. With equal durations, byte-for-byte today's files.

## 4. Reading a drive's state before its commit

Today the routed state is read only at the commit. The drive step already routes before it returns (`_drive_step`,
1154-1176, then `_route`), so the loop can read `state` and `leaked_container` from a finished future without
deciding anything: the fate is still decided by the handlers at the commit, from the committed history in row order.
The holds of 3.5, 3.7, 3.8 and 3.9 read only those two fields. Nothing is committed out of order.

## 5. What outside batch.py depends on the block

### 5.1 takes.py: OPEN_LIMIT and the RegistrationGuard

- `OPEN_LIMIT = batch.BLOCK` (takes.py 43); `guard_registration` refuses "at most {OPEN_LIMIT} open rows (three in one
  live block)" (263-264), and refuses any open row outside this instance's live set (`outside_live_block`, 168-169,
  259-260); `RegistrationGuard.check` clears its live set only when every live row is committed and refuses "a row is
  registered with no committed outcome in the finishing block" when some but not all are (292-298). Production
  registers through it (drive.TakeRepo.register, 1622-1624; TakeRepo.guard, 1587).
- A rolling registration happens while other takes are open, so the guard as written refuses the first one (some of
  the live set committed, not all), and a commit order that waits on a slow head needs more than three open rows to
  gain anything: a model of the run (1,260 takes, about 31% of rows on the Gemini arm so that two thirds of blocks
  hold one, Gemini drives 6.5 to 14 minutes and the rest 1 to 2, three seeds; arithmetic only, no drive) gives about
  52 hours in blocks, 45 hours rolling with at most three open takes, about 29 hours with at most 12, and the same
  29 hours with no bound (the three lanes' total work divided by three).
- Proposed: a new constant beside BLOCK, MAX_OPEN = 12, the most takes open at once (in flight or finished and
  waiting for an older commit); OPEN_LIMIT = batch.MAX_OPEN; the guard keeps a live set that grows at each
  registration and loses each row at its commit, refusing any open row outside it (so a restart still finds stray
  registrations for a human) and more than MAX_OPEN open. test_pipeline's mutants `finishing-block` and `four-open`
  (test_pipeline.py 134-135, 204) are re-pinned to the new rule, never weakened.
- Can move: no record's bytes. A crash can leave up to MAX_OPEN registrations without outcomes for a human to
  reconcile, against three today.

### 5.2 takes.commit_registration: the clean tree

- `if _git_at(repo, "status", "--porcelain"): raise ValueError("registration requires a clean committed repository")`
  (takes.py 372-373). A take writes its folder `takes/<slot>/<k>/` inside the study folder (drive.py TAKES_DIR, 3692;
  mode_binding.py 72) from its launch until its commit, so with any take open the tree is not clean and every rolling
  registration is refused. Today no take is open at a registration, so the check never meets one.
- Proposed: the check refuses anything unclean except the folders of this instance's open takes (the guard's live
  set), each named exactly as `takes/<slot>/<attempt>/`, untracked; anything else still refuses.
- Can move: nothing committed. It is a refusal narrowed by exactly the open takes' folders; it needs its own ruling.

### 5.3 check_results.py: the window event's span and the ruled pause's block

- `window_problems` (84-98): "A window event occupies at most one block's span, with no slot twice", refusing an
  event whose pauses span more than BLOCK consecutive outcomes; `publication` calls it (183) and refuses the history.
  Under the rolling window an event's pauses are at most BLOCK, one per slot, but finished takes of other slots can
  be committed between them, so a sound history can span up to MAX_OPEN outcomes and would be refused.
- `pause_event` (101-150) derives, for a pause a ruling routes, which block it sat in by enumerating "block edges"
  of one to BLOCK outcomes; a rolling run has no block edges.
- Proposed: `window_problems` checks at most BLOCK pauses per event, no slot twice, within at most MAX_OPEN
  consecutive outcomes, with no other event's pause inside; `pause_event` counts a ruled pause as its own event (the
  strict own-event count it already falls back to, with STRICT_PAUSE_NOTE, and the count batch itself uses).
- Can move: publication. A ruled pause that today could share an event in its half-cell's count would count as its
  own; that can close a half-cell one event earlier in the published table. This is the one change here that reaches
  a published count, and it needs glitch-26's ruling before it is built.
- A pause a ruling routes can count as its own event where a block run would have merged it with its block (B19-6).

### 5.4 Prose

`costs.py` 13 ("before a block is registered"), takes.py's docstring (6-8, "only that instance's current block may
have up to three open rows"), drive.py's TakeRepo docstring (1494-1495), and routing.json's pause cap source (the
`caps.pause.source` text: "round 4 drives up to three takes in a block and every pause of one block shares the one
reset the loop waits for before its next block").

## 6. Pre-registered elements

- No `prereg.json` exists at 7dc0cf9e, so nothing is frozen yet; freeze.py binds the whole study tree, batch.py,
  takes.py and check_results.py included, at the freeze (`study_tree_sha`, 218-229), and refuses an edit to it after
  the rehearsal. The change must land before the freeze rehearsal.
- `prereg-draft.json` binds routing.json by its sha256 (build_draft.py 841). The proposal changes no routing.json byte:
  the caps, their values and their unit (W1B3-5) are unchanged. Its pause source prose (5.4) would then describe
  blocks the loop no longer makes; rewording it moves the draft's routing sha, so it is left for glitch-26 (section 7,
  re-ruling 6).
- No pre-registered value names the block size or the drive concurrency in this tree (prereg-draft.json holds
  neither; the plan file is not in this mirror and was not read).
- The outcomes a rolling run commits differ from a block run's only where durations differ: which pauses share an
  event (3.5), which take carries the nightly stop text (3.7), and how many takes start after a take that stops the
  loop or closes its half-cell (3.7 to 3.9). Section 5.3 is the only change to a published count.

## 7. Rulings that would need re-ruling, with proposed wording for glitch-26

1. **W7C-gap4-1** (THE MONEY GATE, "before each block is registered"). Proposed: "Before each wave of rows is
   registered (the rows that fill the drive lanes free at that moment; with equal drive durations, today's blocks),
   every row of the wave whose harness bills money per call is put through both checks on one reading of the spend
   ledger; when either refuses, nothing of the wave is registered or launched, the takes already open finish and are
   committed, and the loop stops blocked. The per-launch re-check of the hold (W7C-R1-3) is unchanged."
2. **W1B3-5** (pauses that share one reset count once; "every pause of one block"). Proposed: "A window event is the
   set of pauses committed between two waits for the usage window. A pause is acted on when its drive finishes: no new
   drive starts until the open takes are committed and the window has reset. The pauses that share one reset count
   once, as ruled; an event holds at most BLOCK pauses, one per slot."
3. **Lane w1b decision 11, as bound by W1B3-3** (`restart_waits`, "the last BLOCK committed outcomes"). Proposed: "A
   restart waits for the usage window when a pause, committed or ruled, is among the last MAX_OPEN committed outcomes
   or the rulings committed among or after them."
4. **The nightly stop's carrier** (live harness step 4 and its review: "the block's last committed outcome carries
   `stop`"). Proposed: "When the harness-errors committed or finished reach NIGHTLY_HARNESS_ERRORS, no new drive
   starts; the stop is carried by the last take open when the count is committed (that take itself when none other is
   open). D-4-1's window, the replay and the night ruling are unchanged."
5. **glitch-f3's cap ruling** ("a drive of the same block that was already running when its half-cell closed").
   Proposed: "A take of a half-cell that was open when the half-cell closed is committed as usual, never re-run, and
   carries the cell state. No drive of a half-cell starts while a finished, uncommitted rehearsal or pause would bring
   it to its cap."
6. **takes.py's open-row rule** (OPEN_LIMIT = BLOCK, "three in one live block") and **the clean-tree registration**
   (takes.py 372-373). Proposed: "At most MAX_OPEN takes are open at once (registered, outcome not committed); the guard's
   live set gains a row at its registration and loses it at its commit, and a registration refuses an unclean tree
   except the untracked folders of the live set's takes." With a value for MAX_OPEN (proposed 12; section 5.1).
7. **check_results' window span and the ruled pause's block** (5.3). Proposed: "A window event holds at most BLOCK
   pauses, one per slot, within at most MAX_OPEN consecutive outcomes, and no other event's pause between them; a
   pause a ruling routes counts as its own event in its half-cell." This one can change a published count.
8. **routing.json's pause cap source prose** (5.4): reword it (the draft's routing sha moves, and build_draft is run
   again), or leave its bytes and record here that its block wording describes the loop before B19.

## 8. The red tests (B19-3)

`evals/gap-study-4/tests/test_batch_rolling.py`, on stub drives built on agent_adapter.ScriptedAdapter and test_batch's
scenarios and fakes (no model, no container, no drive.py). A fast drive is one UNIT (0.1 s); the slow one is ten.

- TestRollingStart (nine rows, slot 1 ten times slower), red on 7dc0cf9e: the next row starts before the slow drive
  ends; both freed lanes are filled (slots 4 and 5 registered and started) while it runs; a third drive runs beside it
  once its block mates end. Green on 7dc0cf9e and pinned: never more than three drives at once (and three reached);
  every row driven once.
- TestRowOrder (the same run), green: commits in row order, a drive that finished first waiting for an older row's
  commit, every commit after its own drive's end; registrations in row order and each before its launch;
  registrations and commits never overlap.
- TestRerunRequeue, green: with slot 1 slow and slot 2 a rehearsal, the next registration after slot 2's commit is
  slot 2's re-run.
- TestEqualDurations, green, the equivalence: two scenarios (re-runs, a pause shared by two slots and an abort; the
  nightly stop carried by the wave's last row) whose registrations, launches, commits (every fate key and the window
  event) and window waits are compared with the block run's, read from 7dc0cf9e and written into the test; and a
  check that the comparison can fail (one lane, serial, moves the waits).

Not yet pinned (for round 2, with the rulings): the holds of section 4 (a pause, a stop, a nightly count or a closing
half-cell seen at a drive's finish), the money gate per wave, the restart window of 3.6, and takes.py's and
check_results.py's rules of section 5.

## 9. Open points

- MAX_OPEN's value (12 proposed from the model in 5.1; three keeps most of today's two days).
- Whether 5.3's change to the published count of ruled pauses is acceptable, or whether a rolling run should commit
  something more (a wait marker) so a ruled pause's event can still be derived; that would add a record kind, which
  this note does not propose.
- tests/test_batch_rolling.py is not yet claimed in COPIED.d (copy_manifest --check names it), and it turns
  test_round4's discovered battery red until the green lands, by design of B19-3.

## 10. Rulings

glitch-26's rulings on this note, Mon 19 Oct 2026 (round 2), and what each changed. Commits are on lane/vendor-b19.

- **B19-5**: section 7's proposals 1 to 6 accepted as worded, with MAX_OPEN = 12: at most three drives at once
  (BLOCK), at most twelve takes open (registered, outcome not committed). Changed in f477832f: batch.MAX_OPEN; the loop
  of section 2 (waves, the tie rule, the holds of section 4, the closing half-cell hold of 3.9); the money gate per wave
  (3.2); a register failure committing the open takes first (3.3); the window event as the pauses between two waits
  (3.5); restart_waits over the last MAX_OPEN outcomes (3.6); the nightly stop carried by the last take launched (3.7);
  takes.OPEN_LIMIT = MAX_OPEN, the live set that loses a row at its commit, and clean-tree registration but for the
  open takes' folders (5.1, 5.2); batch.py's and takes.py's prose.
- **B19-6** (proposal 7): accepted. The equal-duration equivalence also compares check_results' window problems,
  window events and pause counts per half-cell with the block run's, read from 94963ea7; equal (22838d85). In f477832f
  check_results.window_problems takes at most BLOCK pauses within at most MAX_OPEN consecutive outcomes (no slot twice,
  no other event between), and pause_event counts a ruled pause as its own event, with STRICT_PAUSE_NOTE when another
  pause of its half-cell carries a window event. 5.3 gains the sentence this ruling asks for. Equal durations means
  drives the loop observes finished at one reading (B19-13, section 2); real drives of equal length may roll, so
  registration order, re-run placement and which pauses share a window event can differ from a block run's, while
  pauses that share one usage reset still count once.
- **B19-7** (proposal 8): routing.json's pause-cap source prose describes the rolling window; build_draft.py run
  again (996e767a). routing.json sha256 eccbb54d7bee09d3c10688c12bd33e9bee28b0e8b29c412c77f32a26d55f0c9b becomes
  e69f468e94fd283defda9a7d535eced3b502be29f6363c46d4908c2754e43387; prereg-draft.json sha256
  1a1aa53f37960a54fba61baedee7426bcf9c8f409d98709de70be0cd69a3a0d5 becomes
  0aed2a2cd124266d2464f8d5d4a9181a66c81ddc56230ca8287859144b0257ae. No cap, value or unit moved.
- **B19-8**: the green, f477832f. The three round 1 red tests are green and both equivalence tests stay green. Tests
  re-pinned to the rulings: test_batch's fakes model equal durations (a wave's drives end together, its head first, and
  a commit waits until none is in flight and SETTLE more), and its one unequal-ordering test checks row order over the
  run, not per block; test_pipeline's live-set, MAX_OPEN and ruled-pause tests, and the mutants finishing-block,
  past-max-open (was four-open), pause-count-refusal, pause-event-identity and pause-note-other-cell (was
  pause-candidate-edges), each red under its mutant; test_spend_wiring's gate-never-called and gate-after-register
  witnesses re-anchored on the wave.
- **B19-9**: a run stopped with twelve takes open restarts owing exactly those takes, in row order, and waits for the
  window (the old BLOCK span of restart_waits as a mutant, red); the open takes reach MAX_OPEN and never pass it while
  three drives run (22838d85: red on 94963ea7, green at f477832f).
- **B19-10**: tests/test_batch_rolling.py claimed in COPIED.d/vendor-admission.json (d8b9d8b9); copy_manifest's rules
  ask no owner's word for a claim.
- **B19-11**: this section.

Where the build differs from sections 2 to 5 as first written (each within the rulings): a re-run joins the queue's
front behind the re-runs already there, so re-runs keep commit order (3.4); the closing half-cell hold stops a wave
before any row of such a half-cell, not only at the queue's head (3.9); the holds and the free lanes are counted from
one reading of the finished drives, so a drive that ends between them frees no lane (an event keeps at most BLOCK
pauses); and a register failure waits for the open takes and commits them before the wave's registered rows (3.3).
Prose naming the block outside the three files is left as it was: costs.py line 13 and drive.py's TakeRepo docstring.
