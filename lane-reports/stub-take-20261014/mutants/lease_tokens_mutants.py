"""Mutants of the Codex lease's exact-value scan road (glitch-06, 14 Oct 2026): box/scan_record.read_lease_tokens,
walk_builders.lease_secrets, and drive's scan kind for postflight.json, against tests/test_scan_record.TestLeaseTokens
(in memory; nothing on disk changes)."""
import contextlib, io, sys, types, unittest
from pathlib import Path
from unittest import mock
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_scan_record as tt
import box, drive, walk_builders
SR, WB = tt.sr, walk_builders
SRC = {"sr": open(SR.__file__).read(), "wb": open(WB.__file__).read()}
MUTANTS = [
 ("sr", "only the access token searched", 'LEASE_TOKEN_KEYS = ("access_token", "refresh_token")', 'LEASE_TOKEN_KEYS = ("access_token",)'),
 ("sr", "a missing token key admitted", '        if not found:\n            raise LoginError(f"the lease file holds no {key}")', '        if False:\n            raise LoginError(f"the lease file holds no {key}")'),
 ("sr", "a short value admitted", '            if not isinstance(v, str) or len(v) < MIN_LENGTH["token"]:\n                raise LoginError(f"a {key}', '            if not isinstance(v, str):\n                raise LoginError(f"a {key}'),
 ("sr", "a link or special file admitted", '        raise LoginError("the lease file is not a plain file (a link or a special file is refused)")', '        pass'),
 ("sr", "any mode admitted", '        raise LoginError("the lease file\'s mode is not 600")', '        pass'),
 ("sr", "any owner admitted", '        raise LoginError("the lease file is not owned by its reader")', '        pass'),
 ("sr", "an oversize file admitted", '        raise LoginError(f"the lease file is at most {LEASE_MAX_BYTES} bytes")', '        pass'),
 ("sr", "deep nesting crashes", '    except (UnicodeDecodeError, ValueError, RuntimeError):', '    except (UnicodeDecodeError, ValueError):'),
 ("sr", "an unreadable open file crashes", '    except OSError:\n        raise LoginError("the lease file cannot be read") from None', '    except ZeroDivisionError:\n        raise LoginError("the lease file cannot be read") from None'),
 ("wb", "no read at take start", '    seen = list(scan_record.read_lease_tokens(auth_path))', '    seen = []'),
 ("wb", "the take-start values dropped at the scan", '        for v in scan_record.read_lease_tokens(auth_path):\n            if v not in seen:\n                seen.append(v)\n        return [("token", v) for v in seen]', '        return [("token", v) for v in scan_record.read_lease_tokens(auth_path)]'),
 ("kind", "postflight.json masked as agent text", None, None),
]
def load(key, src, name):
    mod = types.ModuleType(name); mod.__file__ = (SR if key == "sr" else WB).__file__
    exec(compile(src, mod.__file__, "exec"), mod.__dict__); return mod
def run(sr=SR, wb=WB, kinds=None):
    stack = contextlib.ExitStack()
    with stack:
        stack.enter_context(mock.patch.object(tt, "sr", sr))
        stack.enter_context(mock.patch.object(box, "scan_record", sr))
        stack.enter_context(mock.patch.dict(sys.modules, {"box.scan_record": sr, "walk_builders": wb}))
        if kinds:
            stack.enter_context(mock.patch.dict(drive.TAKE_FILE_KINDS, kinds))
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestLeaseTokens)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
c = run(); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for key, name, old, new in MUTANTS:
    if key == "kind":
        r = run(kinds={"postflight.json": "transcript"})
    else:
        assert SRC[key].count(old) == 1, name
        src = SRC[key].replace(old, new)
        r = run(sr=load("sr", src, SR.__name__)) if key == "sr" else run(wb=load("wb", src, WB.__name__))
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
