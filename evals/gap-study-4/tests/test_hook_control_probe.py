"""box/hook_control_probe.py and walk_launch's probe-hooks entry (lane hook-control, the D8 hook positive control for
arms O and G; glitch-f1's rulings on lane-reports/hook-control-DESIGN.md, Wed 21 Oct 2026).

Fakes only: no container, CLI, network, login or athena runs here. What is bound (the design's test list):
  - the marker command: its exact text per event, no `$`, no backquote or backslash, no study word; run for real
    through /bin/bash -c it appends exactly its event name;
  - the diff rule: the off twin is the study's bytes plus the planted hook only; the on twin differs from the off twin
    by exactly the switch; flipping another key, flipping the switch in the off twin, dropping the hook from the off
    twin, or a C1 base other than the study plus the dead provider, each refuses;
  - the Codex argv: O-off-study is codex_adapter.argv exactly and passes run_take.check_codex_turn; the hook-trust flag
    is appended after that check, in exactly the two bypass runs;
  - the environment: arm G is B27's three changes; arm O is the Codex row exactly, under the no-login launcher, the
    walk's exec form byte for byte; no key, no lease (ast: place_lease, read_login, exec_argv, run_turn never named);
  - the verdict truth table (PASS, INCONCLUSIVE, FAIL) and the fail-safe pre-run marker check;
  - the dry run prints every argv and runs nothing; full runs on a fake box (honest, switch-ignoring, dead, a broken
    self-test) give PASS, FAIL, INCONCLUSIVE and a stopped unit;
  - walk_launch: probe-hooks starts under the probe's own hold, its refusals, and test_walk_launch's witnesses still
    apply once.
"""
import ast
import base64
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from box import hook_control_probe as hcp  # noqa: E402
from box import ownership, run_take as rt, stub_model_probe as smp, take_config  # noqa: E402
from box import walk_launch as wl  # noqa: E402
import codex_adapter  # noqa: E402
from graders import awareness  # noqa: E402

BOX = str(STUDY / "box")
GEMINI_IMAGE = json.loads((STUDY / "box" / "gemini" / "image.lock").read_text())["image_id"]
CODEX_IMAGE = json.loads((STUDY / "box" / "codex" / "image.lock").read_text())["image_id"]
RESOURCES = {"memory_reservation": 2 * 1024 ** 3, "memory": 6 * 1024 ** 3, "cpus": "8", "pids_limit": 4096}
TREE = "/scratch/hc-x/t"
FIRED = f"{TREE}/.hookctl/fired.log"
ID = "a" * 64
THREAD = "0199aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee"
CHILD = "/home/javier/w-AbCdEf12"


def pairs(argv) -> dict:
    i = argv.index(rt.LAUNCHER[-1])
    n = int(argv[i + 2])
    return dict(p.split("=", 1) for p in argv[i + 3:i + 3 + n])


def study_files(harness, run_tree=TREE):
    if harness == rt.CODEX:
        return take_config.files_for(rt.CODEX, model=hcp.CODEX_MODEL, run_tree=run_tree)
    return take_config.files_for(rt.GEMINI, model=hcp.HG_SCENARIO["model"])


# ------------------------------------------------------------------------------------------------ the marker
class Marker(unittest.TestCase):
    def test_the_exact_text(self):
        self.assertEqual(
            hcp.marker_command(FIRED, "SessionStart"),
            '/usr/bin/python3 -I -S -c "import os,sys;fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_APPEND,'
            '0o644);os.write(fd,(sys.argv[2]+chr(10)).encode());os.close(fd)" ' + FIRED + " SessionStart")

    def test_no_shell_trap_and_no_study_word(self):
        # the planted commands (the self-test's `selftest` is never planted: it runs once, as the operator's exec)
        for event in hcp.GEMINI_EVENTS + hcp.CODEX_EVENTS:
            cmd = hcp.marker_command(FIRED, event)
            with self.subTest(event=event):
                self.assertTrue(cmd.endswith(" " + event))
                for ch in ("$", "`", "\\", "'", ";rm", "&&"):
                    self.assertNotIn(ch, cmd.replace(";fd=", "").replace(";os.", ""))
                self.assertEqual(awareness.scan(cmd), [])
                for word in ("gap", "study", "probe", "stub", "eval", "grader", "test"):
                    self.assertNotIn(word, cmd.lower())
        for text in hcp.HG_SCENARIO["processes"] + list(hcp.CODEX_PROMPTS):
            self.assertEqual(awareness.scan(text), [])

    def test_a_bad_event_or_path_refuses(self):
        for path, event in ((FIRED, "Session Start"), (FIRED, "x;y"), ("relative/fired.log", "SessionStart"),
                            ("/a b/fired.log", "SessionStart"), ("/a/$x/fired.log", "SessionStart")):
            with self.subTest(path=path, event=event), self.assertRaises(hcp.HookRefused):
                hcp.marker_command(path, event)

    def test_run_for_real_it_appends_exactly_its_event(self):
        # the image's python3 is /usr/bin/python3; this Mac and athena both have one, so the command's own quoting is
        # proved through a real bash -c, the way Gemini spawns a command hook (chunk-NR7L3FXV.js:365194-365212)
        # (never a skip: round 4's battery fails a skip whose reason is not in its SKIP_ALLOWED)
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(os.path.realpath(d), "fired.log")
            for ev in (hcp.SELFTEST, "SessionStart"):
                p = subprocess.run(["/bin/bash", "-c", hcp.marker_command(log, ev)], capture_output=True, text=True,
                                   timeout=30, env={"PATH": "/usr/bin:/bin", "HOME": os.path.realpath(d)})
                self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "", ""))
            self.assertEqual(Path(log).read_text(), "selftest\nSessionStart\n")


class HooksDoc(unittest.TestCase):
    def test_gemini_plants_all_eleven_events_each_naming_itself(self):
        doc = hcp.hooks_doc(rt.GEMINI, FIRED)
        self.assertEqual(sorted(doc), sorted(hcp.GEMINI_EVENTS))
        self.assertEqual(len(hcp.GEMINI_EVENTS), 11)
        for ev, defs in doc.items():
            m = "" if ev in ("SessionStart", "SessionEnd", "PreCompress") else ".*"
            self.assertEqual(defs, [{"matcher": m, "hooks": [{"type": "command",
                                                               "command": hcp.marker_command(FIRED, ev)}]}])

    def test_gemini_session_entries_match_every_trigger(self):
        # glitch-f1's ruling after the 22 Oct HG trip: 0.64.0 matches a SessionStart or SessionEnd entry against its
        # trigger by exact string equality (chunk-NR7L3FXV.js:365647-365648, 365666-365668), so a regex such as ".*"
        # matches no trigger; only an empty matcher, none or "*" matches all (365640-365643). Read from the generated
        # settings, the way the probe writes them.
        study = study_files(rt.GEMINI)
        t = hcp.hook_twins(rt.GEMINI, study, fired_path=FIRED)
        for twin in ("off", "on"):
            hooks = json.loads(t[twin][take_config.GEMINI_SETTINGS_PATH])["hooks"]
            for ev in ("SessionStart", "SessionEnd", "PreCompress"):
                with self.subTest(twin=twin, event=ev):
                    self.assertEqual([d.get("matcher") for d in hooks[ev]], [""])
            for ev in set(hcp.GEMINI_EVENTS) - {"SessionStart", "SessionEnd", "PreCompress"}:
                with self.subTest(twin=twin, event=ev):
                    self.assertEqual([d.get("matcher") for d in hooks[ev]], [".*"])

    def test_codex_plants_session_start_and_pre_tool_use_in_gars_shape(self):
        doc = hcp.hooks_doc(rt.CODEX, FIRED)
        self.assertEqual(sorted(doc), ["hooks"])
        self.assertEqual(sorted(doc["hooks"]), ["PreToolUse", "SessionStart"])
        for ev, defs in doc["hooks"].items():
            self.assertEqual(defs, [{"matcher": ".*", "hooks": [{"type": "command",
                                                                  "command": hcp.marker_command(FIRED, ev)}]}])


# ------------------------------------------------------------------------------------------------ the diff rule
class DiffRule(unittest.TestCase):
    def test_gemini_twins(self):
        study = study_files(rt.GEMINI)
        t = hcp.hook_twins(rt.GEMINI, study, fired_path=FIRED)
        rel = take_config.GEMINI_SETTINGS_PATH
        off, on, base = (json.loads(t[k][rel]) for k in ("off", "on", "base"))
        self.assertEqual(t["base"], study)
        self.assertEqual({k: v for k, v in off.items() if k != "hooks"}, json.loads(study[rel]))
        self.assertEqual(off["hooks"], hcp.hooks_doc(rt.GEMINI, FIRED))
        self.assertIs(off["hooksConfig"]["enabled"], False)
        self.assertIs(on["hooksConfig"]["enabled"], True)
        on["hooksConfig"]["enabled"] = False
        self.assertEqual(on, off)
        self.assertEqual(t["off"][rel], take_config._json_bytes(off))
        self.assertEqual(t["diff"]["switch"], "hooksConfig.enabled")

    def test_codex_twins_c0(self):
        study = study_files(rt.CODEX)
        t = hcp.hook_twins(rt.CODEX, study, fired_path=FIRED, road="C0")
        self.assertEqual(t["base"], study)
        self.assertEqual(t["off"]["config.toml"], study["config.toml"])
        self.assertEqual(sorted(t["off"]), ["config.toml", "hooks.json"])
        self.assertEqual(json.loads(t["off"]["hooks.json"]), hcp.hooks_doc(rt.CODEX, FIRED))
        self.assertEqual(t["on"]["hooks.json"], t["off"]["hooks.json"])
        off_lines = t["off"]["config.toml"].decode().split("\n")
        on_lines = t["on"]["config.toml"].decode().split("\n")
        diff = [(a, b) for a, b in zip(off_lines, on_lines) if a != b]
        self.assertEqual(diff, [("hooks = false", "hooks = true")])
        self.assertEqual(len(off_lines), len(on_lines))
        self.assertIn('[projects."' + TREE + '"]', t["off"]["config.toml"].decode())

    def test_codex_c1_base_is_the_study_plus_the_dead_provider_only(self):
        study = study_files(rt.CODEX)
        t = hcp.hook_twins(rt.CODEX, study, fired_path=FIRED, road="C1")
        base = t["base"]["config.toml"].decode()
        self.assertIn('model_provider = "' + hcp.C1_PROVIDER + '"', base)
        self.assertIn("base_url = \"http://127.0.0.1:9\"", base)
        self.assertIn("requires_openai_auth = false", base)
        top, *table = hcp.c1_lines_added()
        self.assertLess(base.index(top), base.index("\n[") + 1)
        self.assertEqual(base.replace(top, "", 1), study["config.toml"].decode() + "".join(table))
        self.assertEqual(t["off"]["config.toml"], t["base"]["config.toml"])

    def _refused(self, harness, study, base, off, on, road=None, words=None):
        with self.assertRaises(hcp.HookRefused) as cm:
            hcp.check_twins(harness, study, base, off, on, hooks=hcp.hooks_doc(harness, FIRED), road=road)
        if words:
            self.assertIn(words, str(cm.exception))

    def test_gemini_mutant_twins_refuse(self):
        study = study_files(rt.GEMINI)
        rel = take_config.GEMINI_SETTINGS_PATH
        t = hcp.hook_twins(rt.GEMINI, study, fired_path=FIRED)
        off, on = json.loads(t["off"][rel]), json.loads(t["on"][rel])

        def b(doc):
            return {rel: take_config._json_bytes(doc)}
        flip_other = json.loads(t["on"][rel])
        flip_other["telemetry"]["enabled"] = True
        switch_in_off = json.loads(t["off"][rel])
        switch_in_off["hooksConfig"]["enabled"] = True
        no_hook_off = {k: v for k, v in off.items() if k != "hooks"}
        no_hook_on = {k: v for k, v in on.items() if k != "hooks"}
        other_in_off = json.loads(t["off"][rel])
        other_in_off["general"]["enableAutoUpdate"] = True
        fewer_events = json.loads(t["off"][rel])
        del fewer_events["hooks"]["SessionEnd"]
        for name, o, n in (("another key flipped in on", off, flip_other), ("the switch on in off", switch_in_off, on),
                           ("the hook dropped from off", no_hook_off, no_hook_on),
                           ("the hook dropped from on", off, no_hook_on),
                           ("another key changed in off", other_in_off, on),
                           ("an event missing", fewer_events, on), ("on equals off", off, off)):
            with self.subTest(name):
                self._refused(rt.GEMINI, study, study, b(o), b(n))

    def test_codex_mutant_twins_refuse(self):
        study = study_files(rt.CODEX)
        t = hcp.hook_twins(rt.CODEX, study, fired_path=FIRED, road="C0")
        off, on = dict(t["off"]), dict(t["on"])
        cfg_on = on["config.toml"].decode()
        cfg_off = off["config.toml"].decode()
        mutants = {
            "another line flipped in on": dict(on, **{"config.toml": cfg_on.replace("plugins = false",
                                                                                  "plugins = true").encode()}),
            "an enable line added in on": dict(on, **{"config.toml": cfg_on.replace(
                "hooks = true", "hooks = true\nhooks_trusted = true").encode()}),
            "another hooks file in on": dict(on, **{"hooks.json": b"{}\n"}),
            "a file added in on": dict(on, **{"requirements.toml": b"x\n"}),
            "the agents key flipped": dict(on, **{"config.toml": cfg_on.replace(
                "[agents]\nenabled = false", "[agents]\nenabled = true").encode()}),
        }
        for name, n in mutants.items():
            with self.subTest(name):
                self._refused(rt.CODEX, study, study, off, n, road="C0")
        for name, o in (("the switch on in off", dict(off, **{"config.toml": cfg_off.replace(
                            "hooks = false", "hooks = true").encode()})),
                        ("the hook dropped from off", {"config.toml": off["config.toml"]}),
                        ("off off the study bytes", dict(off, **{"config.toml": cfg_off.replace(
                            "web_search = \"disabled\"", "web_search = \"live\"").encode()}))):
            with self.subTest(name):
                self._refused(rt.CODEX, study, study, o, on, road="C0")

    def test_a_change_mirrored_into_both_twins_refuses(self):
        # the twins differ by the switch alone, but both left the study's bytes (mutants D2 and D4 of stage 3)
        rel = take_config.GEMINI_SETTINGS_PATH
        study = study_files(rt.GEMINI)
        t = hcp.hook_twins(rt.GEMINI, study, fired_path=FIRED)
        o, n = json.loads(t["off"][rel]), json.loads(t["on"][rel])
        for doc in (o, n):
            doc["telemetry"]["enabled"] = True
        self._refused(rt.GEMINI, study, study, {rel: take_config._json_bytes(o)}, {rel: take_config._json_bytes(n)},
                      words="study's settings")
        study = study_files(rt.CODEX)
        t = hcp.hook_twins(rt.CODEX, study, fired_path=FIRED, road="C0")
        off, on = (dict(t[k], **{"config.toml": t[k]["config.toml"].replace(b'web_search = "disabled"',
                                                                             b'web_search = "live"')})
                   for k in ("off", "on"))
        self._refused(rt.CODEX, study, study, off, on, road="C0", words="base's bytes")

    def test_a_gemini_twin_off_the_study_s_serialisation_refuses(self):
        # REVIEW NIT 2 (mutant R6): the same document in other bytes (compact, or with a duplicate key) refuses
        rel = take_config.GEMINI_SETTINGS_PATH
        study = study_files(rt.GEMINI)
        t = hcp.hook_twins(rt.GEMINI, study, fired_path=FIRED)
        o, n = json.loads(t["off"][rel]), json.loads(t["on"][rel])
        compact = {rel: json.dumps(o, sort_keys=True).encode()}
        self._refused(rt.GEMINI, study, study, compact, t["on"], words="serialisation")
        dup = {rel: t["on"][rel].replace(b'{\n', b'{\n  "hooks": {},\n', 1)}
        self.assertEqual(json.loads(dup[rel]), n)
        self._refused(rt.GEMINI, study, study, t["off"], dup, words="serialisation")

    def test_the_flipped_line_must_sit_under_features(self):
        study = {"config.toml": b'model = "m"\n\n[features]\nhooks = false\n\n[other]\nhooks = false\n'}
        planted = (json.dumps(hcp.hooks_doc(rt.CODEX, FIRED), indent=2, sort_keys=True) + "\n").encode()
        off = dict(study, **{"hooks.json": planted})
        on = dict(off, **{"config.toml": b'model = "m"\n\n[features]\nhooks = false\n\n[other]\nhooks = true\n'})
        self._refused(rt.CODEX, study, study, off, on, road="C0", words="[features]")
        good = dict(off, **{"config.toml": b'model = "m"\n\n[features]\nhooks = true\n\n[other]\nhooks = false\n'})
        self.assertEqual(hcp.check_twins(rt.CODEX, study, study, off, good, hooks=hcp.hooks_doc(rt.CODEX, FIRED),
                                         road="C0")["line"], 4)

    def test_the_on_twin_s_switch_must_be_true(self):
        study = study_files(rt.GEMINI)
        rel = take_config.GEMINI_SETTINGS_PATH
        t = hcp.hook_twins(rt.GEMINI, study, fired_path=FIRED)
        for value in (None, "true", 1):
            on = json.loads(t["on"][rel])
            on["hooksConfig"]["enabled"] = value
            with self.subTest(value=value):
                self._refused(rt.GEMINI, study, study, t["off"], {rel: take_config._json_bytes(on)})

    def test_a_c1_base_with_anything_else_refuses(self):
        study = study_files(rt.CODEX)
        t = hcp.hook_twins(rt.CODEX, study, fired_path=FIRED, road="C1")
        base = t["base"]["config.toml"].decode()
        for bad in (base.replace("requires_openai_auth = false", "requires_openai_auth = true"),
                    base + "\n[features2]\nx = true\n", study["config.toml"].decode()):
            b = {"config.toml": bad.encode()}
            off = dict(b, **{"hooks.json": t["off"]["hooks.json"]})
            on = dict(off, **{"config.toml": bad.replace("hooks = false", "hooks = true").encode()})
            with self.subTest(bad=bad[-60:]):
                self._refused(rt.CODEX, study, b, off, on, road="C1")

    def test_the_study_must_write_the_switch_off(self):
        self.assertIn(("hooks", False), take_config.CODEX_FEATURES)
        self.assertIn(("hooksConfig.enabled", False), take_config.GEMINI_SETTINGS)
        with mock.patch.object(take_config, "CODEX_FEATURES", (("hooks", True), take_config.CODEX_PLUGINS)):
            bad = take_config.files_for(rt.CODEX, model=hcp.CODEX_MODEL, run_tree=TREE)
        with self.assertRaises(hcp.HookRefused):
            hcp.hook_twins(rt.CODEX, bad, fired_path=FIRED, road="C0")

    def test_the_set_hash_is_take_config_s(self):
        for harness in (rt.GEMINI, rt.CODEX):
            files = hcp.hook_twins(harness, study_files(harness), fired_path=FIRED,
                                   road="C0" if harness == rt.CODEX else None)["on"]
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as d:
                hcp.write_twin(d, files)
                self.assertEqual(hcp.files_sha256(files), take_config.config_sha256(d, harness))

    def test_the_walk_census_names_the_planted_codex_file(self):
        # open call 7, descriptive only: the walk road's config-folder census refuses hooks.json by name
        named = hcp.census_names(rt.CODEX, ["config.toml", "hooks.json"])
        self.assertEqual([r for r, _why in named], ["hooks.json"])
        self.assertIn("hook config", named[0][1])


# ------------------------------------------------------------------------------------------------ argv and environment
class CodexArgv(unittest.TestCase):
    def test_the_study_run_is_the_walk_argv_exactly(self):
        for k, tid in ((1, None), (2, THREAD)):
            want = codex_adapter.argv(hcp.CODEX_PROMPTS[k - 1], model=hcp.CODEX_MODEL, mode="bypass", session_id=tid,
                                      first=k == 1)
            got = hcp.codex_inner(k, tid, bypass_trust=False)
            self.assertEqual(got, want)
            self.assertEqual(rt.check_codex_turn(got), hcp.CODEX_MODEL)

    def test_the_trust_flag_rides_only_the_two_bypass_runs_after_the_check(self):
        flagged = {}
        for run in hcp.RUNS["HO-C0"]:
            flagged[run.name] = [hcp.TRUST_FLAG in hcp.codex_inner(k, None if k == 1 else THREAD,
                                                                   bypass_trust=run.bypass) for k in (1, 2)]
        self.assertEqual(flagged, {"O-on-bypass": [True, True], "O-off-bypass": [True, True],
                                   "O-off-study": [False, False], "O-on-study": [False, False]})
        one = hcp.codex_inner(1, None, bypass_trust=True)
        self.assertEqual(one[-2:], [hcp.TRUST_FLAG, hcp.CODEX_PROMPTS[0]])
        two = hcp.codex_inner(2, THREAD, bypass_trust=True)
        self.assertEqual(two[-4:], ["resume", hcp.TRUST_FLAG, THREAD, hcp.CODEX_PROMPTS[1]])
        for flagged_argv in (one, two):
            with self.assertRaises(rt.Refused):      # check_codex_turn reads the study argv only
                rt.check_codex_turn(flagged_argv)

    def test_the_four_runs_per_road(self):
        for road in ("HO-C0", "HO-C1"):
            self.assertEqual([(r.name, r.twin, r.bypass, r.role) for r in hcp.RUNS[road]],
                             [("O-on-bypass", "on", True, "on"), ("O-off-bypass", "off", True, "off"),
                              ("O-off-study", "off", False, "off"), ("O-on-study", "on", False, "info")])
        self.assertEqual([(r.name, r.twin, r.role) for r in hcp.RUNS["HG"]], [("G-on", "on", "on"),
                                                                              ("G-off", "off", "off")])


class Environment(unittest.TestCase):
    def test_codex_is_the_row_exactly_under_the_no_login_launcher(self):
        argv, client = hcp.codex_process_argv(ID, hcp.codex_inner(1, None, bypass_trust=False), run_tree=TREE,
                                              caller_env={"PATH": "/usr/bin"})
        self.assertEqual(pairs(argv), rt.take_environment(rt.CODEX, TREE))
        i = argv.index(rt.LAUNCHER[-1])
        self.assertEqual(argv[i + 1], rt.NO_LOGIN)
        self.assertEqual(hcp.codex_environment_changes(pairs(argv), TREE), {"added": [], "removed": [], "replaced": []})
        self.assertFalse(set(client) & {"OPENAI_API_KEY", "CODEX_API_KEY"})

    def test_any_codex_difference_refuses(self):
        row = rt.take_environment(rt.CODEX, TREE)
        for bad in (dict(row, OPENAI_API_KEY="x"), {k: v for k, v in row.items() if k != "HTTPS_PROXY"},
                    dict(row, CODEX_HOME="/elsewhere")):
            with self.subTest(diff=sorted(set(bad) ^ set(row))), self.assertRaises(hcp.HookRefused):
                hcp.codex_environment_changes(bad, TREE)

    def test_the_codex_exec_is_the_walk_s_exec_byte_for_byte(self):
        inner = hcp.codex_inner(1, None, bypass_trust=False)
        with mock.patch.object(rt, "check_codex_lease_place", lambda *a, **k: None), \
                mock.patch.object(rt, "check_environment", lambda *a, **k: None):
            prod, prod_env = rt._codex_exec_argv(ID, inner, user=rt.AGENT_USER, workdir=TREE, run_tree=TREE,
                                                 login_file="/nonexistent/auth.json", caller_env={"PATH": "/usr/bin"})
        mine, mine_env = hcp.codex_process_argv(ID, inner, run_tree=TREE, caller_env={"PATH": "/usr/bin"})
        self.assertEqual(mine, prod)
        self.assertEqual(mine_env, prod_env)

    def test_gemini_is_b27_s_three_changes(self):
        inner = smp.cli_inner(hcp.HG_SCENARIO, 1, None)
        argv, client = hcp.gemini_process_argv(ID, inner, run_tree=TREE, port=41234, caller_env={})
        self.assertEqual((argv, client), smp.process_argv(ID, inner, run_tree=TREE, port=41234, caller_env={}))
        self.assertEqual(smp.environment_changes(dict(pairs(argv), GEMINI_API_KEY=client["GEMINI_API_KEY"]), TREE),
                         {"added": ["GOOGLE_GEMINI_BASE_URL"], "removed": ["HTTPS_PROXY"],
                          "replaced": ["GEMINI_API_KEY"]})

    def test_the_selftest_is_the_marker_through_bash_as_the_agent(self):
        argv = hcp.selftest_argv(ID, TREE)
        self.assertEqual(argv, rt.agent_exec_argv(ID, ["/bin/bash", "-c", hcp.marker_command(FIRED, "selftest")],
                                                  workdir=TREE))


def _attrs(tree, base):
    return {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == base}


def _imports(tree) -> set:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(n.module or "")
            out |= {f"{n.module}.{a.name}" for a in n.names}
    return out


class Bindings(unittest.TestCase):
    def setUp(self):
        self.src = Path(hcp.__file__).read_text(encoding="utf-8")
        self.tree = ast.parse(self.src)

    def test_never_a_key_a_lease_the_harness_exec_or_the_turn(self):
        used = _attrs(self.tree, "run_take")
        for name in ("exec_argv", "_codex_exec_argv", "run_turn", "read_login", "place_lease", "check_login_place",
                     "launch", "teardown", "proxy_create_argv", "sidecar_create_argv", "lease_for_take"):
            self.assertNotIn(name, used)
        names = {n.id for n in ast.walk(self.tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {"exec_argv", "run_turn", "read_login", "place_lease"})
        self.assertNotIn("auth.json", self.src)

    def test_the_walks_own_code_is_used(self):
        self.assertTrue({"create_argv", "take_environment", "launcher_argv", "check_codex_turn", "agent_exec_argv",
                         "make_config_dir", "_teardown_partial", "leaked", "network_name"} <= _attrs(self.tree,
                                                                                                    "run_take"))
        self.assertIn("files_for", _attrs(self.tree, "take_config"))
        self.assertIn("argv", _attrs(self.tree, "codex_adapter"))
        self.assertTrue({"grant", "restore", "operator_list", "operator_read"} <= _attrs(self.tree, "ownership"))

    def test_no_production_module_imports_it(self):
        hits = []
        for p in sorted(STUDY.rglob("*.py")):
            rel = p.relative_to(STUDY).as_posix()
            if rel.startswith("tests/") or rel == "box/hook_control_probe.py":
                continue
            src = p.read_text(encoding="utf-8")
            if [n for n in _imports(ast.parse(src)) if n.split(".")[-1] == "hook_control_probe"] \
                    or "box.hook_control_probe" in src:
                hits.append(rel)
        self.assertEqual(hits, [])
        src = (STUDY / "box" / "walk_launch.py").read_text(encoding="utf-8")
        self.assertEqual([ln.strip() for ln in src.splitlines() if "hook_control_probe.py\"" in ln],
                         ['HOOK_PROBE_MODULE = "evals/gap-study-4/box/hook_control_probe.py"'])

    def test_records_carry_the_probe_label_walk_launch_fetches(self):
        doc = hcp.labelled({"a": 1})
        self.assertEqual(doc["record_kind"], smp.RECORD_KIND)
        self.assertIn("never a study take", doc["not_a_study_record"])
        with self.assertRaises(hcp.HookRefused):
            hcp.labelled({"record_kind": "walk"})


# ------------------------------------------------------------------------------------------------ the verdict
GLIVE = {"served": 2}
OLIVE = {"exit_class": "error", "first_type": "thread.started"}


def unit(run, harness, role, *, selftest="selftest\n", reads=("selftest\nSessionStart\n",), scenario=None,
         liveness=None):
    live = GLIVE if harness == rt.GEMINI else OLIVE
    return {"scenario": scenario or ("HG" if harness == rt.GEMINI else "HO-C0"), "run": run, "harness": harness,
            "role": role, "selftest_read": selftest, "reads": list(reads),
            "final_read": list(reads)[-1] if reads else selftest,
            "liveness": list(liveness) if liveness is not None else [dict(live) for _ in reads],
            "cli_version_rc": 0, "failure": None, "resume_skipped": None}


def good_units(roads=("HO-C0",)):
    out = [unit("G-on", rt.GEMINI, "on", reads=("selftest\nSessionStart\nBeforeAgent\n",
                                               "selftest\nSessionStart\nBeforeAgent\nSessionStart\n")),
           unit("G-off", rt.GEMINI, "off", reads=("selftest\n", "selftest\n"))]
    for road in roads:
        out += [unit("O-on-bypass", rt.CODEX, "on", scenario=road),
                unit("O-off-bypass", rt.CODEX, "off", reads=("selftest\n",), scenario=road),
                unit("O-off-study", rt.CODEX, "off", reads=("selftest\n",), scenario=road),
                unit("O-on-study", rt.CODEX, "info", reads=("selftest\n",), scenario=road)]
    return out


def replace(units, run, scenario=None, **kw):
    out = []
    for u in units:
        if u["run"] == run and (scenario is None or u["scenario"] == scenario):
            new = {("selftest_read" if k == "selftest" else k): v for k, v in kw.items()}
            if "reads" in new and "final_read" not in new:      # the host's read after teardown follows the last one
                new["final_read"] = new["reads"][-1] if new["reads"] else new.get("selftest_read", u["selftest_read"])
            u = dict(u, **new)
        out.append(u)
    return out


class Verdict(unittest.TestCase):
    def v(self, units, arms=("G", "O")):
        return hcp.hook_verdict(units, arms)

    def test_all_good_is_pass(self):
        got = self.v(good_units())
        self.assertEqual(got["verdict"], "PASS", got)
        self.assertEqual({a: r["verdict"] for a, r in got["arms"].items()}, {"G": "PASS", "O": "PASS"})
        self.assertEqual(self.v(good_units(("HO-C0", "HO-C1")))["verdict"], "PASS")

    def test_an_on_twin_silent_is_inconclusive(self):
        got = self.v(replace(good_units(), "G-on", reads=("selftest\n", "selftest\n")))
        self.assertEqual((got["verdict"], got["arms"]["G"]["verdict"], got["arms"]["O"]["verdict"]),
                         ("INCONCLUSIVE", "INCONCLUSIVE", "PASS"))
        got = self.v(replace(good_units(), "O-on-bypass", reads=("selftest\n",)))
        self.assertEqual(got["arms"]["O"]["verdict"], "INCONCLUSIVE")

    def test_per_road_reading_one_codex_road_passing_is_enough(self):
        # glitch-f1's ruling m3 (revising "every on twin must fire" once liveness is bound): a road passes when its on
        # twin fires and its live off twins stay silent; the Codex arm passes when one road passes and no off twin fires
        two = good_units(("HO-C0", "HO-C1"))
        units = replace(two, "O-on-bypass", scenario="HO-C0", reads=("selftest\n",))
        got = self.v(units)
        self.assertEqual(got["arms"]["O"]["verdict"], "PASS", got["arms"]["O"]["reasons"])
        self.assertEqual(got["arms"]["O"]["roads"], {"HO-C0": False, "HO-C1": True})
        both = replace(replace(two, "O-on-bypass", scenario="HO-C0", reads=("selftest\n",)), "O-on-bypass",
                       scenario="HO-C1", reads=("selftest\n",))
        self.assertEqual(self.v(both)["arms"]["O"]["verdict"], "INCONCLUSIVE")
        # an off twin firing on the road that did not pass still fails the arm
        fired = replace(units, "O-off-study", scenario="HO-C0", reads=("selftest\nSessionStart\n",))
        self.assertEqual(self.v(fired)["arms"]["O"]["verdict"], "FAIL")
        # a road whose off twin is not live does not pass, even with its on twin firing
        dead = replace(units, "O-off-bypass", scenario="HO-C1",
                       liveness=[{"exit_class": "exec-failed", "first_type": None}])
        self.assertEqual(self.v(dead)["arms"]["O"]["verdict"], "INCONCLUSIVE")

    def test_a_missing_run_on_another_road_still_blocks_a_pass(self):
        # stage 4 mutant V6: C1 passes, but C0's O-off-study never ran
        units = [u for u in good_units(("HO-C0", "HO-C1")) if (u["scenario"], u["run"]) != ("HO-C0", "O-off-study")]
        self.assertEqual(self.v(units)["arms"]["O"]["verdict"], "INCONCLUSIVE")

    def test_a_docker_exec_failure_is_never_live_even_matched(self):
        # stage 4 mutant L3: the off twin's exec failed exactly as its on twin's did
        failed = [{"exit_class": "exec-failed", "first_type": None}]
        units = good_units()
        for run in ("O-on-bypass", "O-off-bypass", "O-off-study"):
            units = replace(units, run, liveness=failed)
        self.assertEqual(self.v(units)["arms"]["O"]["verdict"], "INCONCLUSIVE")

    def test_an_off_twin_counts_as_silent_only_when_live(self):
        # REVIEW M1: an off twin whose CLI never got as far as its on twin is no evidence for the switch
        for run, live in (("O-off-bypass", [{"exit_class": "exec-failed", "first_type": None}]),
                          ("O-off-study", [{"exit_class": "error", "first_type": None}]),
                          ("O-off-study", [{"exit_class": "timeout", "first_type": "thread.started"}]),
                          ("O-off-study", []),
                          ("O-off-study", [dict(OLIVE), dict(OLIVE)])):
            with self.subTest(run=run, live=live):
                got = self.v(replace(good_units(), run, liveness=live))
                self.assertEqual(got["arms"]["O"]["verdict"], "INCONCLUSIVE")
        for live in ([{"served": 0}, {"served": 1}], [{"served": 2}, {"served": None}], [{"served": 2}]):
            with self.subTest(gemini=live):
                got = self.v(replace(good_units(), "G-off", liveness=live))
                self.assertEqual(got["arms"]["G"]["verdict"], "INCONCLUSIVE")
        # both twins equally quiet on the stream with the same exit class is live
        quiet = [{"exit_class": "error", "first_type": None}]
        units = good_units()
        for run in ("O-on-bypass", "O-off-bypass", "O-off-study"):
            units = replace(units, run, liveness=quiet)
        self.assertEqual(self.v(units)["arms"]["O"]["verdict"], "PASS")

    def test_cli_version_must_exit_zero_and_any_unit_failure_blocks_a_pass(self):
        # REVIEW M1 (cli_version) and m1 (every unit's failure is read, the informational run's too)
        for run in ("G-on", "G-off", "O-on-bypass", "O-off-study", "O-on-study"):
            arm = "G" if run.startswith("G") else "O"
            with self.subTest(run=run, what="cli"):
                self.assertEqual(self.v(replace(good_units(), run, cli_version_rc=126))["arms"][arm]["verdict"],
                                 "INCONCLUSIVE")
            with self.subTest(run=run, what="failure"):
                self.assertEqual(self.v(replace(good_units(), run, failure={"type": "RuntimeError"}))["arms"][arm][
                    "verdict"], "INCONCLUSIVE")
        # Gemini always runs two processes (the design's open call 9): a skipped resume is not a pass
        got = self.v(replace(good_units(), "G-off", resume_skipped="no session id"))
        self.assertEqual(got["arms"]["G"]["verdict"], "INCONCLUSIVE")
        # an off twin that fired still fails, whatever else failed
        got = self.v(replace(good_units(), "G-off", failure={"type": "X"}, reads=("selftest\nSessionStart\n",)))
        self.assertEqual(got["arms"]["G"]["verdict"], "FAIL")

    def test_off_twins_are_judged_on_the_host_read_after_teardown(self):
        # REVIEW m2: a write after the last per-process read (a CLI still running after its client's timeout)
        got = self.v(replace(good_units(), "O-off-study", final_read="selftest\nSessionStart\n"))
        self.assertEqual(got["arms"]["O"]["verdict"], "FAIL")
        got = self.v(replace(good_units(), "G-off", final_read="selftest\nSessionEnd\n"))
        self.assertEqual(got["arms"]["G"]["verdict"], "FAIL")
        got = self.v(replace(good_units(), "O-off-bypass", final_read=None))
        self.assertEqual(got["arms"]["O"]["verdict"], "INCONCLUSIVE")
        got = self.v(replace(good_units(), "O-off-bypass", final_read="rewritten\n"))
        self.assertEqual(got["arms"]["O"]["verdict"], "FAIL")

    def test_session_start_in_process_one_is_the_pass_condition(self):
        for reads in (("selftest\nBeforeAgent\n",), ("selftest\n", "selftest\nSessionStart\n"), ()):
            with self.subTest(reads=reads):
                got = self.v(replace(good_units(), "O-on-bypass", reads=reads))
                self.assertEqual(got["arms"]["O"]["verdict"], "INCONCLUSIVE")

    def test_the_selftest_line_is_never_an_event(self):
        # the self-test wrote nothing before the processes, and process 1's read holds only the self-test's line
        got = self.v(replace(good_units(), "O-on-bypass", selftest="", reads=("selftest\n",)))
        self.assertEqual(got["arms"]["O"]["verdict"], "INCONCLUSIVE")
        got = self.v(replace(good_units(), "O-on-bypass", selftest="selftest\n", reads=("selftest\nselftest\n",)))
        self.assertEqual(got["arms"]["O"]["verdict"], "INCONCLUSIVE")

    def test_a_failed_selftest_is_inconclusive(self):
        for run in ("G-on", "G-off"):
            for st in ("", None, "selftest\nselftest\n", "SessionStart\n"):
                with self.subTest(run=run, selftest=st):
                    got = self.v(replace(good_units(), run, selftest=st,
                                         reads=(st or "",) if run == "G-off" else ((st or "") + "SessionStart\n",)))
                    self.assertNotEqual(got["arms"]["G"]["verdict"], "PASS")

    def test_any_off_event_is_fail_and_beats_inconclusive(self):
        for run in ("O-off-bypass", "O-off-study"):
            with self.subTest(run=run):
                got = self.v(replace(good_units(), run, reads=("selftest\nSessionStart\n",)))
                self.assertEqual((got["verdict"], got["arms"]["O"]["verdict"]), ("FAIL", "FAIL"))
                units = replace(replace(good_units(), run, reads=("selftest\nPreToolUse\n",)), "O-on-bypass",
                                reads=("selftest\n",))
                self.assertEqual(self.v(units)["arms"]["O"]["verdict"], "FAIL")
        got = self.v(replace(good_units(), "G-off", reads=("selftest\n", "selftest\nSessionEnd\n")))
        self.assertEqual(got["arms"]["G"]["verdict"], "FAIL")
        # an off twin whose self-test failed and which then logged an event still fails
        got = self.v(replace(good_units(), "G-off", selftest="", reads=("BeforeModel\n", "BeforeModel\n")))
        self.assertEqual(got["arms"]["G"]["verdict"], "FAIL")
        # a rewritten (not appended) log in an off twin is read as an event
        got = self.v(replace(good_units(), "G-off", reads=("selftest\n", "other\n")))
        self.assertEqual(got["arms"]["G"]["verdict"], "FAIL")

    def test_an_off_twin_with_no_process_or_a_lost_log_is_inconclusive(self):
        for reads in ((), (None,)):
            with self.subTest(reads=reads):
                got = self.v(replace(good_units(), "O-off-study", reads=reads))
                self.assertEqual(got["arms"]["O"]["verdict"], "INCONCLUSIVE")

    def test_the_informational_run_never_moves_the_verdict(self):
        for reads in (("selftest\nSessionStart\n",), ("selftest\n",), ()):
            with self.subTest(reads=reads):
                self.assertEqual(self.v(replace(good_units(), "O-on-study", reads=reads))["verdict"], "PASS")

    def test_a_missing_run_or_arm_is_inconclusive(self):
        for run in ("G-off", "O-off-study", "O-on-bypass"):
            with self.subTest(run=run):
                got = self.v([u for u in good_units() if u["run"] != run])
                self.assertEqual(got["verdict"], "INCONCLUSIVE")
        self.assertEqual(self.v([u for u in good_units() if u["harness"] == rt.GEMINI])["verdict"], "INCONCLUSIVE")
        self.assertEqual(self.v([u for u in good_units() if u["harness"] == rt.GEMINI], ("G",))["verdict"], "PASS")


class Precheck(unittest.TestCase):
    def test_only_exactly_the_selftest_line_passes(self):
        self.assertEqual(hcp.marker_precheck(b"selftest\n"), [])
        for bad in (None, b"", b"selftest", b"selftest\nselftest\n", b"SessionStart\n", b"selftest\nSessionStart\n",
                    b" selftest\n", b"\xff"):
            with self.subTest(raw=bad):
                self.assertTrue(hcp.marker_precheck(bad))


# ------------------------------------------------------------------------------------------------ the dry run
class DryRun(unittest.TestCase):
    def test_the_dry_run_prints_every_argv_and_runs_nothing(self):
        buf = io.StringIO()
        with mock.patch.object(rt, "DockerRuntime", side_effect=AssertionError("a runtime was built")), \
                mock.patch.object(subprocess, "run", side_effect=AssertionError("a process was run")), \
                mock.patch.object(hcp, "take_resources", lambda: dict(RESOURCES)), redirect_stdout(buf):
            rc = hcp.main(["--box", BOX, "--scratch-parent", "/nonexistent", "--output", "/nonexistent/stub-probe-h",
                           "--gemini-image", GEMINI_IMAGE, "--codex-image", CODEX_IMAGE, "--scenarios",
                           "HG,HO-C0,HO-C1", "--dry-run"])
        self.assertEqual(rc, 0)
        rows = [json.loads(x) for x in buf.getvalue().splitlines()]
        steps = {}
        for r in rows:
            steps.setdefault((r["scenario"], r["run"]), []).append(r["step"])
        self.assertEqual(sorted(steps), sorted([("HG", "G-on"), ("HG", "G-off")] + [
            (s, r) for s in ("HO-C0", "HO-C1") for r in ("O-on-bypass", "O-off-bypass", "O-off-study", "O-on-study")]))
        self.assertEqual(steps[("HG", "G-on")],
                         ["twins", "grant-run_tree", "grant-config_dir", "grant-evidence_dir", "network-create",
                          "take-create", "take-inspect", "take-start", "stub-start", "selftest", "cli-version",
                          "process-1", "process-2", "take-rm", "network-rm", "environment"])
        self.assertEqual(steps[("HO-C0", "O-off-study")],
                         ["twins", "git-init", "git-commit", "grant-run_tree", "grant-config_dir", "grant-evidence_dir",
                          "network-create", "take-create", "take-inspect", "take-start", "selftest", "cli-version",
                          "process-1", "process-2", "take-rm", "network-rm", "environment"])
        by = {(r["scenario"], r["run"], r["step"]): r for r in rows}
        self.assertIn(CODEX_IMAGE, by[("HO-C0", "O-on-bypass", "take-create")]["argv"])
        self.assertIn(GEMINI_IMAGE, by[("HG", "G-off", "take-create")]["argv"])
        self.assertIn("--internal", by[("HO-C1", "O-off-study", "network-create")]["argv"])
        self.assertIn(hcp.TRUST_FLAG, by[("HO-C0", "O-on-bypass", "process-1")]["argv"])
        self.assertNotIn(hcp.TRUST_FLAG, by[("HO-C0", "O-off-study", "process-1")]["argv"])
        self.assertNotIn(hcp.TRUST_FLAG, by[("HO-C0", "O-on-study", "process-2")]["argv"])
        tw = by[("HO-C1", "O-on-bypass", "twins")]
        self.assertEqual(tw["diff"]["switch"], "features.hooks")
        self.assertRegex(tw["study_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(tw["twin_sha256"], tw["study_sha256"])
        self.assertEqual(by[("HO-C0", "O-on-study", "environment")]["changes"],
                         {"added": [], "removed": [], "replaced": []})
        self.assertFalse([r for r in rows if "argv" in r and "connect" in r["argv"]])

    def test_an_image_off_its_lock_or_missing_refuses(self):
        for argv in (["--gemini-image", "sha256:" + "0" * 64, "--scenarios", "HG"],
                     ["--codex-image", GEMINI_IMAGE, "--scenarios", "HO-C0"],
                     ["--scenarios", "HO-C0"], ["--scenarios", "HG"],
                     ["--gemini-image", GEMINI_IMAGE, "--scenarios", "HG,HG"],
                     ["--gemini-image", GEMINI_IMAGE, "--scenarios", "A1"]):
            with self.subTest(argv=argv), self.assertRaises(hcp.HookRefused), redirect_stdout(io.StringIO()):
                hcp.main(["--box", BOX, "--scratch-parent", "/x", "--output", "/x/stub-probe-h", "--dry-run", *argv])

    def test_the_real_run_refuses_off_linux(self):
        with mock.patch.object(hcp.sys, "platform", "darwin"), self.assertRaises(hcp.HookRefused):
            hcp.run_probe(mock.Mock(scratch_parent="/x", output="/y/stub-probe-z"), ["HG"])


# ------------------------------------------------------------------------------------------------ the fake box
SESSION = "sess0001-aaaa"
GEMINI_FIRES = {1: ["SessionStart", "BeforeAgent", "BeforeModel", "AfterModel", "BeforeTool", "AfterTool",
                    "BeforeModel", "AfterModel", "AfterAgent", "SessionEnd"],
                2: ["SessionStart", "BeforeAgent", "BeforeModel", "AfterModel", "AfterAgent", "SessionEnd"]}


class FakeBox:
    """A fake Docker client: ids for creates, the operator programs answered from the host folders, the self-test
    run on the host, and CLIs that honour (or, by mode, ignore) the twin's switch.
    mode: "honest" (the switch gates the hook; Codex also needs the trust flag), "ignores-switch" (every hook fires),
    "dead" (nothing fires), "selftest-broken" (the self-test writes nothing)."""

    def __init__(self, mode="honest", *, thread=True):
        self.calls, self.n, self.mode, self.thread = [], 0, mode, thread
        self.cfg = self.tree = None
        self.process = 0

    def _id(self):
        self.n += 1
        return f"{self.n:064x}"

    def _fire(self, events):
        with open(os.path.join(self.tree, ".hookctl", "fired.log"), "a") as fh:
            for e in events:
                fh.write(e + "\n")

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append((list(argv), dict(env or {})))
        a = list(argv)
        if a[:2] == ["docker", "run"]:
            cid = self._id()
            Path(a[a.index("--cidfile") + 1]).write_text(cid)
            mount = a[a.index("--mount") + 1]
            src = mount.split("source=", 1)[1].split(",", 1)[0]
            if ownership.READ_PROGRAM in a:
                p = os.path.join(src, a[a.index(ownership.READ_PROGRAM) + 1])
                if not os.path.exists(p):
                    return rt.Completed(0, json.dumps({"exists": False}), "")
                data = Path(p).read_bytes()
                return rt.Completed(0, json.dumps({"exists": True, "b64": base64.b64encode(data).decode(),
                                                   "sha256": hashlib.sha256(data).hexdigest(),
                                                   "bytes": len(data)}), "")
            if ownership.LIST_PROGRAM in a:
                rel = a[a.index(ownership.LIST_PROGRAM) + 1]
                p = src if rel == "." else os.path.join(src, rel)
                if not os.path.isdir(p):
                    return rt.Completed(0, json.dumps({"exists": False}), "")
                ents = sorted([base64.b64encode(n.encode()).decode(), "dir" if os.path.isdir(os.path.join(p, n))
                               else "file"] for n in os.listdir(p))
                canon = json.dumps(ents, separators=(",", ":"))
                return rt.Completed(0, json.dumps({"exists": True, "entries": ents,
                                                   "sha256": hashlib.sha256(canon.encode()).hexdigest()}), "")
            return rt.Completed(0, "", "")
        if a[1:3] == ["network", "create"]:
            return rt.Completed(0, self._id() + "\n", "")
        if a[1] == "create":
            self.cfg = [m for m in a if m.endswith(f"target={rt.CONFIG_MOUNT}")][0].split("source=")[1].split(",")[0]
            self.tree = a[a.index("--workdir") + 1]
            return rt.Completed(0, self._id() + "\n", "")
        if a[1:3] == ["container", "inspect"]:
            return rt.Completed(0, json.dumps([{"Id": a[3]}]), "")
        if a[1] == "exec":
            joined = " ".join(a)
            if "/bin/bash" in a and a[-1].endswith(" selftest"):
                if self.mode != "selftest-broken":
                    self._fire(["selftest"])
                return rt.Completed(0, "", "")
            if smp.STUB_FILE in joined:
                return rt.Completed(0, json.dumps({"ready": True, "port": 41234, "pid": 77}) + "\n", "")
            if a[-1] == "--version":
                return rt.Completed(0, "0.0.0\n", "")
            self.process += 1
            if "gemini" in a and "-p" in a:
                k = 1 if "-r" not in a else 2
                doc = json.loads(Path(self.cfg, take_config.GEMINI_SETTINGS_PATH).read_text())
                on = doc.get("hooksConfig", {}).get("enabled") is True
                if self.mode == "ignores-switch" or (self.mode == "honest" and on):
                    if doc.get("hooks"):
                        self._fire(GEMINI_FIRES[k])
                self.served = getattr(self, "served", 0) + (2 if k == 1 else 1)
                Path(self.tree, smp.STUB_OUT, "state.json").write_text(json.dumps({"held": None, "done": False,
                                                                                    "requests": self.served}))
                out = json.dumps({"type": "init", "session_id": SESSION}) + "\n" if k == 1 else "{}\n"
                return rt.Completed(0, out, "")
            if "codex" in a and "exec" in a:
                k = 2 if "resume" in a else 1
                cfg = Path(self.cfg, "config.toml").read_text()
                on = "\nhooks = true\n" in cfg
                trusted = hcp.TRUST_FLAG in a
                if os.path.exists(os.path.join(self.cfg, "hooks.json")) and (
                        self.mode == "ignores-switch" or (self.mode == "honest" and on and trusted)):
                    self._fire(["SessionStart"])
                out = json.dumps({"type": "thread.started", "thread_id": THREAD}) + "\n" if self.thread and k == 1 \
                    else ""
                return rt.Completed(1, out, "request failed")
            return rt.Completed(0, "", "")
        if a[1:3] == ["ps", "--all"]:
            return rt.Completed(0, "", "")
        return rt.Completed(0, "", "")


class OffDies(FakeBox):
    """REVIEW M1's reproduction (its gaps.py): the honest box, except every off-switch CLI process dies at once
    (a docker exec error: 126, no stream)."""

    def run(self, argv, *, env=None, timeout=None):
        a = list(argv)
        if a[1:2] == ["exec"] and a[-1] != "--version" and not ("/bin/bash" in a and a[-1].endswith(" selftest")) \
                and smp.STUB_FILE not in " ".join(a) and (("gemini" in a and "-p" in a)
                                                         or ("codex" in a and "exec" in a[2:])):
            if "gemini" in a:
                off = json.loads(Path(self.cfg, take_config.GEMINI_SETTINGS_PATH).read_text())["hooksConfig"][
                    "enabled"] is False
            else:
                off = "\nhooks = false\n" in Path(self.cfg, "config.toml").read_text()
            if off:
                self.calls.append((a, dict(env or {})))
                return rt.Completed(126, "", "OCI runtime exec failed: unable to start container process")
        return super().run(argv, env=env, timeout=timeout)


class Off2Raises(FakeBox):
    """REVIEW m1's reproduction: G-off's resume raises in the docker client."""

    def run(self, argv, *, env=None, timeout=None):
        a = list(argv)
        if a[1:2] == ["exec"] and "-r" in a and "gemini" in a:
            if json.loads(Path(self.cfg, take_config.GEMINI_SETTINGS_PATH).read_text())["hooksConfig"]["enabled"] \
                    is False:
                raise RuntimeError("docker client lost the daemon")
        return super().run(argv, env=env, timeout=timeout)


class LateWriter(FakeBox):
    """REVIEW m2: an off Codex process that times out in the client and writes SessionStart afterwards (the write
    lands before teardown, after the per-process read)."""

    def run(self, argv, *, env=None, timeout=None):
        a = list(argv)
        if a[1:3] == ["rm", "--force"]:
            if getattr(self, "pending", None):
                self._fire(self.pending)
                self.pending = None
        if a[1:2] == ["exec"] and "codex" in a and "exec" in a[2:] and "resume" not in a \
                and "\nhooks = false\n" in Path(self.cfg, "config.toml").read_text():
            self.calls.append((a, dict(env or {})))
            self.pending = ["SessionStart"]
            e = TimeoutError("client timed out")
            e.stdout = json.dumps({"type": "thread.started", "thread_id": THREAD}) + "\n"
            raise e
        return super().run(argv, env=env, timeout=timeout)


def run_fake(names, mode="honest", box_class=None, **kw):
    d = os.path.realpath(tempfile.mkdtemp(prefix="hc-"))
    parent = os.path.join(d, "parent")
    os.mkdir(parent, 0o700)
    out = os.path.join(d, "stub-probe-t")
    box = (box_class or FakeBox)(mode, **kw)
    a = mock.Mock(scratch_parent=parent, output=out, gemini_image=GEMINI_IMAGE, codex_image=CODEX_IMAGE, reason="r")
    with mock.patch.object(hcp.sys, "platform", "linux"), mock.patch.object(hcp, "take_resources",
                                                                            lambda: dict(RESOURCES)):
        summary = hcp.run_probe(a, names, runtime=box, env={"PATH": "/usr/bin"})
    return d, out, box, summary


class FullRunOnFakes(unittest.TestCase):
    def test_an_honest_box_passes_both_arms(self):
        d, out, box, s = run_fake(["HG", "HO-C0", "HO-C1"])
        try:
            self.assertEqual(s["verdict"]["verdict"], "PASS", json.dumps(s["verdict"], indent=1))
            self.assertEqual(s["problems"], {})
            u = {(x["scenario"], x["run"]): x for x in s["units"]}
            self.assertEqual(u[("HG", "G-on")]["events"][0][:2], ["SessionStart", "BeforeAgent"])
            self.assertEqual(u[("HG", "G-off")]["events"], [[], []])
            self.assertEqual(u[("HO-C0", "O-on-study")]["events"], [[], []])
            self.assertEqual(u[("HO-C1", "O-on-bypass")]["events"], [["SessionStart"], ["SessionStart"]])
            # the records: each unit's folder, its twin's files, the reads, the manifest walk_launch checks
            unit_dir = os.path.join(out, "HO-C0", "O-off-study")
            names = sorted(os.listdir(unit_dir))
            for want in ("probe.json", "fired-after-selftest.log", "fired-after-process-1.log", "turn-1.jsonl",
                         "turn-2.stderr.txt", "twin"):
                self.assertIn(want, names)
            self.assertEqual(sorted(os.listdir(os.path.join(unit_dir, "twin"))), ["config.toml", "hooks.json"])
            rec = json.loads(Path(unit_dir, "probe.json").read_text())
            self.assertEqual(rec["record_kind"], "stub-model-probe")
            self.assertEqual(rec["inner"][0], codex_adapter.argv(hcp.CODEX_PROMPTS[0], model=hcp.CODEX_MODEL,
                                                                 mode="bypass", session_id=None, first=True))
            self.assertTrue(rec["git"]["head"])
            self.assertTrue(rec["scratch_removed"])
            self.assertEqual(wl.probe_manifest_problems(out), [])
            self.assertEqual(json.loads(Path(out, "summary.json").read_text())["verdict"]["verdict"], "PASS")
            # every container argv ran on a fresh --internal network, never a proxy or a connect
            argvs = [x for x, _e in box.calls]
            self.assertTrue(all(x[3] == "--internal" for x in argvs if x[1:3] == ["network", "create"]))
            self.assertFalse([x for x in argvs if x[1:3] == ["network", "connect"]])
            # a process never ran before its unit's self-test read
            self.assertTrue(all(x["precheck"] == [] for x in s["units"]))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_box_that_ignores_the_switch_fails(self):
        d, out, box, s = run_fake(["HG", "HO-C0"], "ignores-switch")
        try:
            self.assertEqual(s["verdict"]["verdict"], "FAIL")
            self.assertEqual({a: r["verdict"] for a, r in s["verdict"]["arms"].items()}, {"G": "FAIL", "O": "FAIL"})
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_dead_box_is_inconclusive_never_a_pass(self):
        d, out, box, s = run_fake(["HG", "HO-C0"], "dead")
        try:
            self.assertEqual(s["verdict"]["verdict"], "INCONCLUSIVE")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_broken_selftest_stops_the_unit_before_any_cli_process(self):
        d, out, box, s = run_fake(["HO-C0"], "selftest-broken")
        try:
            self.assertEqual(s["verdict"]["verdict"], "INCONCLUSIVE")
            self.assertFalse([x for x, _e in box.calls if x[1] == "exec" and "codex" in x and x.count("exec") >= 2])
            self.assertTrue([x for x, _e in box.calls if x[1] == "exec" and "/bin/bash" in x])
            self.assertTrue(all(x["precheck"] for x in s["units"]))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_an_off_twin_that_never_starts_is_never_a_pass(self):
        # REVIEW M1, red on d9d9b79e ("OffDies verdict PASS problems []")
        d, out, box, s = run_fake(["HG", "HO-C0", "HO-C1"], box_class=OffDies)
        try:
            self.assertEqual(s["verdict"]["verdict"], "INCONCLUSIVE", json.dumps(s["verdict"]["arms"], indent=1)[:2000])
            self.assertEqual({a: r["verdict"] for a, r in s["verdict"]["arms"].items()},
                             {"G": "INCONCLUSIVE", "O": "INCONCLUSIVE"})
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_unit_that_failed_is_never_a_pass(self):
        # REVIEW m1, red on d9d9b79e ("Off2Raises verdict PASS problems ['HG/G-off']")
        d, out, box, s = run_fake(["HG"], box_class=Off2Raises)
        try:
            self.assertEqual(s["verdict"]["verdict"], "INCONCLUSIVE")
            self.assertIn("HG/G-off", s["problems"])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_late_write_in_an_off_twin_fails(self):
        # REVIEW m2: the host's read after teardown sees what the per-process read missed
        d, out, box, s = run_fake(["HO-C0"], box_class=LateWriter)
        try:
            self.assertEqual(s["verdict"]["verdict"], "FAIL", json.dumps(s["verdict"]["arms"], indent=1)[:2000])
            unit_dir = os.path.join(out, "HO-C0", "O-off-study")
            self.assertEqual(Path(unit_dir, "fired-after-teardown.log").read_text(), "selftest\nSessionStart\n")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_no_thread_id_means_no_resume(self):
        d, out, box, s = run_fake(["HO-C0"], thread=False)
        try:
            self.assertFalse([x for x, _e in box.calls if "resume" in x])
            self.assertEqual(s["verdict"]["verdict"], "PASS")
            self.assertTrue(all(len(x["events"]) == 1 for x in s["units"]))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_probe_exits_zero_only_on_pass(self):
        for verdict, problems, rc in (("PASS", {}, 0), ("INCONCLUSIVE", {}, 1), ("FAIL", {}, 1),
                                      ("PASS", {"HG/G-on": ["the scratch is kept"]}, 1)):
            with self.subTest(verdict=verdict, problems=problems), tempfile.TemporaryDirectory() as d:
                summary = {"verdict": {"verdict": verdict}, "problems": problems}
                with mock.patch.object(hcp, "run_probe", lambda a, names: summary), redirect_stdout(io.StringIO()):
                    got = hcp.main(["--box", BOX, "--scratch-parent", d, "--output", os.path.join(d, "stub-probe-q"),
                                    "--gemini-image", GEMINI_IMAGE, "--scenarios", "HG"])
                self.assertEqual(got, rc)


# ------------------------------------------------------------------------------------------------ walk_launch
_tw = importlib.util.spec_from_file_location("hookctl_test_walk_launch", STUDY / "tests" / "test_walk_launch.py")
twl = importlib.util.module_from_spec(_tw)
_tw.loader.exec_module(twl)


class WalkLaunchProbeHooks(unittest.TestCase):
    OK = dict(child=CHILD, probe="hookctl1", scenarios="HG,HO-C0,HO-C1", gemini_image=GEMINI_IMAGE,
              codex_image=CODEX_IMAGE, reason="the D8 hook control")

    def test_it_starts_under_the_probe_s_own_hold(self):
        cmd = wl.hook_probe_command(**self.OK)
        self.assertTrue(cmd.startswith(wl.fresh_child_guard(CHILD)))
        self.assertIn("athena-reserve hold --by gap4-probe-hookctl1 -- ", cmd)
        self.assertIn(f"{CHILD}/repo/evals/gap-study-4/box/hook_control_probe.py", cmd)
        self.assertIn(f"--output {CHILD}/stub-probe-hookctl1", cmd)
        self.assertIn(f"--gemini-image {GEMINI_IMAGE}", cmd)
        self.assertIn(f"--codex-image {CODEX_IMAGE}", cmd)
        self.assertIn("--scenarios HG,HO-C0,HO-C1", cmd)
        self.assertIn("machine_gate.py athena-check", cmd)
        self.assertIn(f"echo $? > {CHILD}/walk.exit", cmd)
        self.assertNotIn("stub_model_probe.py", cmd)
        self.assertNotIn("GIT_AUTHOR_NAME", cmd)
        only_g = wl.hook_probe_command(**dict(self.OK, scenarios="HG", codex_image=None))
        self.assertNotIn("--codex-image", only_g)

    def test_its_refusals(self):
        for k, v in (("probe", "../x"), ("scenarios", "HG;rm -rf"), ("scenarios", "A1"), ("gemini_image", "x:latest"),
                     ("codex_image", "sha256:" + "0" * 63), ("reason", " "), ("child", "/tmp/x")):
            with self.subTest(**{k: v}), self.assertRaises(wl.LaunchRefused):
                wl.hook_probe_command(**dict(self.OK, **{k: v}))
        for k in ("gemini_image", "codex_image"):
            with self.subTest(missing=k), self.assertRaises(wl.LaunchRefused):
                wl.hook_probe_command(**dict(self.OK, **{k: None}))

    def test_the_pid_is_read_from_the_start(self):
        class R(wl.Runner):
            def __init__(self, out):
                self.out, self.cmds = out, []

            def remote(self, cmd, *, timeout=3600):
                self.cmds.append(cmd)
                return 0, self.out, ""
        r = R("4242\n")
        self.assertEqual(wl.probe_hooks(r, **{("probe_id" if k == "probe" else k): v for k, v in self.OK.items()}),
                         4242)
        self.assertEqual(r.cmds, [wl.hook_probe_command(**self.OK)])
        with self.assertRaises(wl.LaunchRefused):
            wl.probe_hooks(R("x\n"), **{("probe_id" if k == "probe" else k): v for k, v in self.OK.items()})

    def test_the_verb_parses(self):
        seen = {}

        def fake(runner, **kw):
            seen.update(kw)
            return 7
        with mock.patch.object(wl, "probe_hooks", fake), redirect_stdout(io.StringIO()) as buf:
            rc = wl.main(["probe-hooks", "--child", CHILD, "--probe", "hookctl1", "--scenarios", "HG",
                          "--gemini-image", GEMINI_IMAGE, "--reason", "r"])
        self.assertEqual((rc, json.loads(buf.getvalue())), (0, {"pid": 7}))
        self.assertEqual(seen["codex_image"], None)

    def test_every_walk_launch_witness_edit_still_applies_once(self):
        src = Path(wl.__file__).read_text(encoding="utf-8")
        bad = [f"{name}: {src.count(old)}" for name, (edits, _c) in twl.WITNESSES.items() for old, _n in edits
               if src.count(old) != 1]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
