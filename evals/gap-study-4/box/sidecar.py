#!/usr/bin/env python3
"""The take's sidecar (CP2): a stub, so the checkpoint's tests can be committed red first. Built in the next commit."""

REPLY_FIELDS = ("ok", "command", "label", "taken_at", "rearmed_at", "unreadable", "unreadable_consequential",
                "problems")
OVERFLOW_EVENT = "Q_OVERFLOW"


class WatchEvent:
    def __init__(self, *a, **k):
        raise NotImplementedError("the stub sidecar")


class Sidecar:
    def __init__(self, *a, **k):
        raise NotImplementedError("the stub sidecar")


def parse_reply(stdout):
    raise NotImplementedError("the stub sidecar")
