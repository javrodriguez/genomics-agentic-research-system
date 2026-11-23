#!/usr/bin/env python3
"""Lane vendor-b22 (glitch-26's ruling B22-10, Tue 20 Oct 2026): arm O's delegation tools switched off.

    python3 -B -W ignore evals/gap-study-4/tests/test_codex_agents_off.py               the tests
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_agents_off.py --witnesses   each mutant alone

The study refuses delegation on the vendor side: Gemini's invoke_agent is excluded (R-B14-2), and the Claude arm keeps its
Agent tool as a named difference. The pinned Codex CLI (openai/codex 092d3acd, rust-v0.162.1) offered both arm O models
six collaboration tools in every committed practice walk (31 of 31 walks, 76 of 76 rollouts), because the model
catalog sets "multi_agent_version": "v2" for gpt-6.1-sol and gpt-6-luna and `[agents] enabled` defaults to true
(lane-reports/vendor-b22-DESIGN.md section 10). `[agents] enabled = false` makes the config override Disabled ahead of
the catalog's version on every road, so none of the six is registered.

  K1-table   for each arm O model of the draft, take_config.files_for(codex) holds `[agents]` with exactly
             `enabled = false`, placed after `[features]` and before `[otel]`; and the file with that table taken out
             is byte-identical to 34f7340f's (sha256 pinned per model), so nothing else in it moved.
  K2-others  Gemini's files (each model of the draft) and Claude Code's are byte-identical to 34f7340f's (the
             combined sha256 build_draft.config_templates computes, pinned).
  K3-source  take_config.VALUE_SOURCES["CODEX_AGENTS"] is the record of the pinned reads below.
  MUTANTS    --witnesses: the key dropped, the key set true, the table also written into Gemini's settings; each red
             on its own check.

Synthetic inputs only: no walk's record is read.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from box import take_config as tc  # noqa: E402

MODELS = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))["models"]
# Read at 34f7340f (before B22-10): build_draft.config_templates' combined sha256 of each harness's files.
BASE_COMBINED = {
    (tc.CLAUDE_CODE, None): "a2993c9b40b365cd48edd9986e4dc26099e83e8115228f60c004dc24ffbe5ea0",
    (tc.GEMINI, "gemini-3.8-flash"): "c0f0ed6d37cdc2024acaacd3608bd771777f83fed22a337f8dea064bba6227f7",
    (tc.GEMINI, "gemini-3.5-flash-lite"): "03b73140d0cce94a5c577fd304865c48761b0bb1a80b73447c8558848439878f",
}
# config.toml's sha256 per arm O model at 34f7340f (prereg-draft.json's config_templates at that commit).
BASE_CODEX_CONFIG = {
    "gpt-6.1-sol": "6a2c753709cfa8c632b795f77f3662c80b91bf0b72bdb8dd8480c7c450c4984b",
    "gpt-6-luna": "41870f8a35b254944713ce0a5e94118861255f248f4bfd3e862e9ce650931ad3",
}
AGENTS_TABLE = b"\n[agents]\nenabled = false\n"
CODEX_PKG = {"package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"}
B22_SOURCES = {
    "CODEX_AGENTS": dict(CODEX_PKG, file="codex-rs/core/src/config/mod.rs",
                         lines={"multi_agent_version_override: Disabled when agents_enabled is false": 1607,
                                "multi_agent_version_for_model: the override before the model's version": 1629,
                                "agents_enabled defaults to true": 3897},
                         uses={"codex-rs/config/src/config_toml.rs": {"ConfigToml.agents": 481,
                                                                      "AgentsToml.enabled": 756},
                               "codex-rs/models-manager/models.json": {
                                   "gpt-6.1-sol multi_agent_version v2": 194,
                                   "gpt-6-luna multi_agent_version v2": 541},
                               "codex-rs/features/src/lib.rs": {"multi_agent_v2 default_enabled false": 1424},
                               "codex-rs/core/src/session/mod.rs": {
                                   "the session's version: the override first, resumed threads too": 772},
                               "codex-rs/core/src/tools/spec_plan.rs": {
                                   "collab_tools_enabled is false for Disabled": 721,
                                   "the collaboration handlers registered only then": 1376},
                               "codex-rs/core/src/session/multi_agents.rs": {
                                   "the usage hint only for V2": 16, "the mode section only for V2": 80}},
                         read="[agents] enabled (default true) set to false makes the config override Disabled "
                              "ahead of the model catalog's multi_agent_version v2 for both arm O models, on new, "
                              "resumed and per-turn roads; the six collaboration tools (spawn_agent, send_message, "
                              "followup_task, wait_agent, interrupt_agent, list_agents) are then not registered and "
                              "the multi_agent_role and multi_agent_mode developer sections render nothing"),
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def combined(files: dict) -> str:
    return sha("".join(f"{p}\0{sha(b)}\n" for p, b in sorted(files.items())).encode())


# ------------------------------------------------------------------------------------------------------- K1
def table_problems() -> list:
    out = []
    for model in MODELS["O"]:
        try:
            raw = tc.files_for(tc.CODEX, model=model)[tc.CODEX_CONFIG]
            doc = tomllib.loads(raw.decode("ascii"))
        except Exception as e:  # noqa: BLE001 - named
            out.append(f"{model}: no config ({type(e).__name__}: {e})")
            continue
        if doc.get("agents") != {"enabled": False}:
            out.append(f"{model}: agents is {doc.get('agents')!r}, not {{'enabled': False}}")
            continue
        text = raw.decode("ascii")
        at = [text.find(t) for t in ("[features]", "[agents]", "[otel]")]
        if not (0 <= at[0] < at[1] < at[2]):
            out.append(f"{model}: [agents] is not between [features] and [otel] ({at})")
        if raw.count(AGENTS_TABLE) != 1 or sha(raw.replace(AGENTS_TABLE, b"", 1)) != BASE_CODEX_CONFIG[model]:
            out.append(f"{model}: without its [agents] table the config is not 34f7340f's bytes")
    return out


# ------------------------------------------------------------------------------------------------------- K2
def others_problems() -> list:
    out = []
    want = dict(BASE_COMBINED)
    got = {(tc.CLAUDE_CODE, None): combined(tc.files_for(tc.CLAUDE_CODE, model=None))}
    got.update({(tc.GEMINI, m): combined(tc.files_for(tc.GEMINI, model=m)) for m in MODELS["G"]})
    for k in sorted(set(want) | set(got), key=str):
        if got.get(k) != want.get(k):
            out.append(f"{k}: files sha256 {got.get(k)}, not 34f7340f's {want.get(k)}")
    return out


# ------------------------------------------------------------------------------------------------------- K3
def source_problems() -> list:
    got = getattr(tc, "VALUE_SOURCES", {}).get("CODEX_AGENTS")
    return [] if got == B22_SOURCES["CODEX_AGENTS"] else ["VALUE_SOURCES['CODEX_AGENTS'] is not the B22 record"]


# ------------------------------------------------------------------------------------------------------- MUTANTS
@contextmanager
def gemini_gains_agents():
    real = tc.WRITERS[tc.GEMINI]

    def writer(model):
        files = dict(real(model))
        doc = json.loads(files[tc.GEMINI_SETTINGS_PATH])
        doc["agents"] = {"enabled": False}
        files[tc.GEMINI_SETTINGS_PATH] = (json.dumps(doc, indent=2) + "\n").encode()
        return files

    with mock.patch.dict(tc.WRITERS, {tc.GEMINI: writer}):
        yield


MUTANTS = [
    ("key-dropped", lambda: mock.patch.object(tc, "CODEX_AGENTS", ()), "table"),
    ("key-set-true", lambda: mock.patch.object(tc, "CODEX_AGENTS", (("enabled", True),)), "table"),
    ("gemini-gains-the-table", gemini_gains_agents, "others"),
]
CHECKS = {"table": table_problems, "others": others_problems, "source": source_problems}


def witnesses() -> list:
    """Each mutant alone: (name, its check, red?, every check it turns red)."""
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_clean("test_codex_agents_off witnesses",
                                    lambda: [f"{c}: {x}" for c in CHECKS for x in CHECKS[c]()])
    out = []
    for name, mutant, check in MUTANTS:
        with mutant():
            reds = sorted(c for c in CHECKS if CHECKS[c]())
        out.append((name, check, check in reds, reds))
    return out


class K1Table(unittest.TestCase):
    def test_each_arm_o_config_switches_agents_off_and_nothing_else(self):
        self.assertEqual(table_problems(), [])


class K2Others(unittest.TestCase):
    def test_gemini_and_claude_files_byte_identical(self):
        self.assertEqual(others_problems(), [])


class K3Source(unittest.TestCase):
    def test_the_value_is_sourced(self):
        self.assertEqual(source_problems(), [])


class Mutants(unittest.TestCase):
    def test_every_mutant_is_red_on_its_own_check(self):
        got = witnesses()
        self.assertEqual(len(got), 3)
        self.assertEqual([(n, c) for n, c, red, _r in got if not red], [])


if __name__ == "__main__":
    if sys.argv[1:] == ["--witnesses"]:
        got = witnesses()
        for n, c, red, reds in got:
            print(f"{'red  ' if red else 'GREEN'} {n} ({c}); red checks: {', '.join(reds) or 'none'}")
        print(f"witnesses: {sum(r for _, _, r, _x in got)}/{len(got)} red")
        raise SystemExit(0 if all(r for _, _, r, _x in got) else 1)
    unittest.main(verbosity=2)
