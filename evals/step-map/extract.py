#!/usr/bin/env python3
"""GARS step-map extractor (skeleton; red-first: every rule is still unimplemented)."""

import subprocess


class Source:
    def __init__(self, repo, sha):
        self.repo = repo
        self.sha = subprocess.run(["git", "-C", repo, "rev-parse", sha], stdout=subprocess.PIPE,
                                  check=True, universal_newlines=True).stdout.strip()


def parse_markdown(text):
    return {"lines": text.split("\n"), "sections": []}


def parse_steps(doc):
    return []


def exit_codes(text):
    return []


def key_vocabulary(src, module_paths):
    return set()


def bind_placeholder(text, line, vocab):
    return {"binding": None}


def extract_text(path, text, src):
    return {"path": path, "steps": [], "findings": []}


def extract(src):
    return {"sha": src.sha, "contracts": [], "helpers": {}, "summary": {}}


class GuardHarness:
    def __init__(self, src, tmp):
        pass

    def bash(self, scenario, command):
        return {"allow": None, "reason": ""}

    def edit(self, scenario, relpath):
        return {"allow": None, "reason": ""}
