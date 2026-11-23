#!/usr/bin/env python3
"""Lane vendor-admission round 17, glitch-b5's ruling B7-F4 (18 Oct 2026; review r17 MINOR 1): the codex rate-limit
and spend-cap text markers against the error texts the pinned Codex CLI prints.

Source: openai/codex tag rust-v0.162.1, commit 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d, read statically (no model
call). The codex adapter records an error with status None and the stream record's own type (codex_adapter.py 150 and
152), so on this road only the text markers can match. Each text below is quoted as the source states it, with its file
and line; a format placeholder is filled with a sample value (named beside it), and each retry suffix is the one the
source line appends, with no reset time: retry_suffix's " Try again later." (error.rs:813) after :795 and :799, and
retry_suffix_after_or's " or try again later." (error.rs:822) after :716, :756, :763, :776, :782 and :788 (B7-F9).

  F4.pause   every usage-limit and rate-limit text matches a codex rate-limit text marker and no codex spend-cap
             marker: these pause (the plan usage-limit texts that mention purchasing credits among them)
  F4.spend   every out-of-credits, spend-cap and quota-exceeded text matches a codex spend-cap text marker: these
             refuse the take for a human ruling (spend-cap-reached)
  F4.lists   codex's spend-cap list is text only (status and type empty) and codex is no longer in
             routing.EMPTY_SPEND_LIST_HARNESSES, which is claude-code alone; NO_MONEY_HARNESSES is unchanged

Fixtures only: no take, model, container or network.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import routing  # noqa: E402

CODEX, CLAUDE = "codex", "claude-code"
AGAIN = " Try again later."            # error.rs:813, retry_suffix with no reset time (after :795 and :799)
OR_AGAIN = " or try again later."      # error.rs:822, retry_suffix_after_or with no reset time (B7-F9)
ERR = "codex-rs/protocol/src/error.rs"

# Texts that pause (rate limits and plan usage limits). (file:line, the text as printed)
PAUSE_TEXTS = (
    (f"{ERR}:109", "rate limit exceeded: Rate limit reached for requests"),           # {0}: a sample stream message
    (f"{ERR}:680", "exceeded retry limit, last status: 429 Too Many Requests"),      # {}: the 429 status, no request id
    (f"{ERR}:716", "You’ve hit your usage limit for gpt-6.1-sol. Switch to another model now," + OR_AGAIN),
    (f"{ERR}:756", "You’ve hit your usage limit. Sample promo message," + OR_AGAIN),  # {promo_message}: a sample
    (f"{ERR}:763", "You’ve hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), visit "
                   "https://chatgpt.com/settings/usage to purchase more credits" + OR_AGAIN),
    (f"{ERR}:776", "You’ve hit your usage limit. To get more access now, send a request to your admin" + OR_AGAIN),
    (f"{ERR}:782", "You’ve hit your usage limit. Upgrade to Plus to continue using Codex "
                   "(https://chatgpt.com/explore/plus)," + OR_AGAIN),
    (f"{ERR}:788", "You’ve hit your usage limit. Visit https://chatgpt.com/settings/usage to purchase more credits"
                   + OR_AGAIN),
    (f"{ERR}:795", "You’ve hit your usage limit." + AGAIN),
    (f"{ERR}:799", "You’ve hit your usage limit." + AGAIN),
)

# Texts that refuse for a human ruling (credits, spend caps, quota). (file:line, the text as printed)
SPEND_TEXTS = (
    (f"{ERR}:726", "Your workspace is out of credits. Add credits to continue."),
    (f"{ERR}:732", "Your workspace is out of credits. Ask your workspace owner to refill in order to continue."),
    (f"{ERR}:738", "You hit your spend cap set in your workspace. Increase your spend cap to continue."),
    (f"{ERR}:744", "You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap "
                   "to continue."),
    # CodexErr::QuotaExceeded, which codex-rs/codex-api/src/api_bridge.rs:221-233 maps insufficient_quota,
    # credit_balance_exhausted, organization_spend_limit_exceeded, project_spend_limit_exceeded and
    # organization_usage_limit_exceeded to
    (f"{ERR}:168", "Quota exceeded. Check your plan and billing details."),
)


def markers(key: str) -> list:
    return routing.load_table()[key][CODEX]["text"]


def text_problems(rate: list, spend: list) -> list[str]:
    p = []
    for where, text in PAUSE_TEXTS:
        if routing.rate_limit_text_marker(text, rate) is None:
            p.append(f"F4.pause: {where} matches no codex rate-limit marker: {text!r}")
        hit = routing.rate_limit_text_marker(text, spend)
        if hit is not None:
            p.append(f"F4.pause: {where} matches the codex spend marker {hit!r}, so a usage limit would stop the take")
    for where, text in SPEND_TEXTS:
        if routing.rate_limit_text_marker(text, spend) is None:
            p.append(f"F4.spend: {where} matches no codex spend-cap marker: {text!r}")
    return p


class CodexSpendTexts(unittest.TestCase):
    def test_f4_usage_limits_pause_and_spend_texts_refuse(self):
        self.assertEqual(text_problems(markers("rate_limit_markers"), markers("spend_cap_markers")), [])

    def test_f4_the_spend_list_is_text_only_and_not_exempt(self):
        entry = routing.load_table()["spend_cap_markers"][CODEX]
        self.assertEqual((entry["status"], entry["type"]), ([], []), "F4.lists")
        self.assertTrue(entry["text"], "F4.lists: codex's spend-cap list is empty")
        self.assertEqual(tuple(routing.EMPTY_SPEND_LIST_HARNESSES), (CLAUDE,), "F4.lists")
        self.assertEqual(tuple(routing.NO_MONEY_HARNESSES), (CLAUDE,), "F4.lists")

    def test_f4_the_check_can_fail(self):
        """The two mutants the ruling names: a usage-limit text added to codex's spend list is red here (the plan
        usage-limit texts would stop the take), and with the spend list emptied no spend text matches."""
        rate, spend = markers("rate_limit_markers"), markers("spend_cap_markers")
        self.assertTrue(any(x.startswith("F4.pause:") for x in text_problems(rate, spend + ["purchase more credits"])))
        self.assertTrue(any(x.startswith("F4.spend:") for x in text_problems(rate, [])))


if __name__ == "__main__":
    unittest.main()
