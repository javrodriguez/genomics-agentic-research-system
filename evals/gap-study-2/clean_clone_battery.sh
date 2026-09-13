#!/usr/bin/env bash
# The suite and the mutation battery, in a fresh full-history clone, with no harness on PATH.
#
#   bash evals/gap-study-2/clean_clone_battery.sh [--source <path-or-sha>] [--out <file>]
#   bash evals/gap-study-2/clean_clone_battery.sh --check-skips <suite-output-file>
#
# WHY. Round 1's CI went red and stayed unread, and a working copy passes on things a clone does not
# have (structural lessons 4 and 17). Goal item 4 requires a clean clone with no harness on PATH to run
# the suite before the first take, and done-line 12 requires the battery in a fresh clone.
#
# WHAT IT DOES, in order; any step that fails stops the run:
#   1. resolves the interpreter BEFORE the environment is cleared (python3.12, else python3) and prints
#      its version: the system python3 is 3.9 while CI uses 3.12;
#   2. clones the source at full depth into a temp folder: --source <path> clones that repository's
#      checked-out commit; --source <sha> clones the origin and checks the sha out; the default is the
#      pushed main, read with `git ls-remote origin main`. A shallow clone is refused;
#   3. builds a one-file bin folder holding only a link to that interpreter, because the folder the
#      interpreter sits in can also hold `claude` and `gh`; then proves, inside `env -i`, that
#      `command -v claude` and `command -v gh` both fail;
#   4. runs the suite under `env -i HOME=<tmp> PATH=<that bin>:/usr/bin:/bin`, printing every skipped
#      test by name; then `--mutations` in the same environment;
#   5. checks the skips against a closed list: the three live classes (TwoMinuteReadLive,
#      NoRateNoBannedWordLive, ThePublishedAnalysisIsRegeneratedLive), plus exactly one more,
#      TheCopiedFixtureBuildsToItsPin.test_the_fixture_builds_and_hashes_to_its_pin, which skips outside
#      a workspaces folder by design. That one must be present; any other skip fails the run.
#
# Everything printed goes to --out too (default: verification/clean-clone-<sha7>.txt beside this file).
# Exit 0 suite OK, battery exit 0 and skips as expected; 1 a suite, battery or skip failure; 2 usage;
# 3 an environment problem (no interpreter, clone failed, shallow clone, a harness reachable).
set -uo pipefail

HERE="$(dirname "$0")"
STUDY_REL="evals/gap-study-2"
LIVE_CLASSES="TwoMinuteReadLive NoRateNoBannedWordLive ThePublishedAnalysisIsRegeneratedLive"
EXPECTED_SKIP="TheCopiedFixtureBuildsToItsPin.test_the_fixture_builds_and_hashes_to_its_pin"

usage() {
  echo "usage: clean_clone_battery.sh [--source <path-or-sha>] [--out <file>]" >&2
  echo "       clean_clone_battery.sh --check-skips <suite-output-file>" >&2
  exit 2
}

# check_skips <file>: reads `SKIPPED <Class>.<method>: <reason>` lines; exit 0 only on the expected set.
check_skips() {
  local file="$1" bad=0 seen_expected=0 name cls ok
  if [ ! -f "$file" ]; then echo "[no-suite-output] $file does not exist"; return 1; fi
  while IFS= read -r line; do
    name="${line#SKIPPED }"; name="${name%%:*}"
    cls="${name%%.*}"
    ok=0
    for live in $LIVE_CLASSES; do [ "$cls" = "$live" ] && ok=1; done
    if [ "$name" = "$EXPECTED_SKIP" ]; then
      seen_expected=$((seen_expected + 1)); ok=1
      echo "  skip (expected, outside a workspaces folder): $name"
    elif [ "$ok" = 1 ]; then
      echo "  skip (live class, no results file yet): $name"
    else
      echo "  SKIP NOT EXPECTED: $name"; bad=1
    fi
  done < <(grep -E '^SKIPPED ' "$file")
  if [ "$seen_expected" != 1 ]; then
    echo "[expected-skip-count] $EXPECTED_SKIP skipped $seen_expected time(s); exactly once is expected"
    bad=1
  fi
  if [ "$bad" = 0 ]; then echo "skips as expected"; return 0; fi
  echo "[unexpected-skips] the skips differ from the expected set"
  return 1
}

SOURCE="" OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --source) [ $# -ge 2 ] && [ -n "$2" ] || usage; SOURCE="$2"; shift 2 ;;
    --out) [ $# -ge 2 ] && [ -n "$2" ] || usage; OUT="$2"; shift 2 ;;
    --check-skips) [ $# -eq 2 ] || usage; check_skips "$2"; exit $? ;;
    *) usage ;;
  esac
done

# 1. the interpreter, before anything clears the environment
PY="$(command -v python3.12 || command -v python3)" || { echo "[no-python] neither python3.12 nor python3 is on PATH"; exit 3; }

TMP="$(mktemp -d)" || exit 3
trap 'rm -rf "$TMP"' EXIT
LOG="$TMP/run.txt"
: > "$LOG"
say() { echo "$*" | tee -a "$LOG"; }
finish() {  # finish <exit>: copy the log to its output file and exit
  local sha7="${SHA:-unknown}"; sha7="${sha7:0:7}"
  local out="${OUT:-$HERE/verification/clean-clone-$sha7.txt}"
  mkdir -p "$(dirname "$out")" && cp "$LOG" "$out" && echo "output: $out"
  exit "$1"
}

say "interpreter: $PY ($("$PY" --version 2>&1))"

# 2. the clone
if [ ! -d "$SOURCE" ]; then  # a default or sha source reads this repository's origin; a path source does not
  REPO="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null)" || { say "[no-repository] $HERE is not inside a git repository"; finish 3; }
fi
if [ -z "$SOURCE" ]; then
  SOURCE="$(git -C "$REPO" ls-remote origin main | awk '{print $1}')"
  [ -n "$SOURCE" ] || { say "[no-pushed-main] git ls-remote origin main returned nothing"; finish 3; }
  say "source: the pushed main, $SOURCE"
fi
CLONE="$TMP/repo"
if [ -d "$SOURCE" ]; then
  say "source: the repository at a path, its checked-out commit"
  git clone -q --no-local "$SOURCE" "$CLONE" 2>>"$LOG" || { say "[clone-failed] cloning the path failed"; finish 3; }
else
  URL="$(git -C "$REPO" remote get-url origin)" || { say "[no-origin] no origin to clone a sha from"; finish 3; }
  git clone -q "$URL" "$CLONE" 2>>"$LOG" || { say "[clone-failed] cloning the origin failed"; finish 3; }
  git -C "$CLONE" checkout -q --detach "$SOURCE" 2>>"$LOG" || { say "[no-such-commit] $SOURCE is not in the clone"; finish 3; }
fi
SHA="$(git -C "$CLONE" rev-parse --verify @)"
if [ "$(git -C "$CLONE" rev-parse --is-shallow-repository)" != "false" ]; then
  say "[shallow-clone] the clone of $SHA is shallow; a history check passes hollow there, so nothing runs"
  finish 3
fi
say "clone: $SHA, full depth, $(git -C "$CLONE" rev-list --count @) commits"

# 3. no harness on PATH
BIN="$TMP/bin"
mkdir -p "$BIN" && ln -s "$PY" "$BIN/python3"
CLEAN_PATH="$BIN:/usr/bin:/bin"
run_clean() { env -i HOME="$TMP/home" PATH="$CLEAN_PATH" "$@"; }
mkdir -p "$TMP/home"
for tool in claude gh; do
  if found="$(run_clean /bin/sh -c "command -v $tool")"; then
    say "[harness-on-path] command -v $tool found $found inside the cleared environment"
    finish 3
  fi
  say "command -v $tool inside the cleared environment: not found (exit non-zero), as required"
done
say "environment: env -i HOME=<tmp>/home PATH=<tmp>/bin:/usr/bin:/bin"

# 4. the suite, with every skip printed by name, then the battery
SUITE_WRAPPER='
import runpy, sys, unittest
path = sys.argv[1]
_Runner = unittest.TextTestRunner
class NamingRunner(_Runner):
    def run(self, test):
        result = super().run(test)
        for t, why in result.skipped:
            name = f"{type(t).__name__}.{t._testMethodName}" if hasattr(t, "_testMethodName") else str(t)
            print(f"SKIPPED {name}: {why}", file=sys.stderr, flush=True)
        return result
unittest.TextTestRunner = NamingRunner
sys.argv = [path]
runpy.run_path(path, run_name="__main__")
'
SUITE_OUT="$TMP/suite.txt"
say ""
say "== suite"
run_clean python3 -c "$SUITE_WRAPPER" "$CLONE/$STUDY_REL/test_harness.py" >"$SUITE_OUT" 2>&1
SUITE_EXIT=$?
tail -n 25 "$SUITE_OUT" | tee -a "$LOG"
grep -E '^SKIPPED ' "$SUITE_OUT" | tee -a "$LOG" >/dev/null
say "suite exit: $SUITE_EXIT"

say ""
say "== skips"
check_skips "$SUITE_OUT" | tee -a "$LOG"
SKIPS_EXIT=${PIPESTATUS[0]}

say ""
say "== battery"
BATTERY_OUT="$TMP/battery.txt"
run_clean python3 "$CLONE/$STUDY_REL/test_harness.py" --mutations >"$BATTERY_OUT" 2>&1
BATTERY_EXIT=$?
grep -vE '^  (red |n/a )' "$BATTERY_OUT" | tail -n 40 | tee -a "$LOG" >/dev/null
say "battery exit: $BATTERY_EXIT"

say ""
if [ "$SUITE_EXIT" = 0 ] && [ "$SKIPS_EXIT" = 0 ] && [ "$BATTERY_EXIT" = 0 ]; then
  say "clean clone of $SHA: suite OK, skips as expected, battery green"
  finish 0
fi
say "clean clone of $SHA: NOT green (suite $SUITE_EXIT, skips $SKIPS_EXIT, battery $BATTERY_EXIT)"
finish 1
