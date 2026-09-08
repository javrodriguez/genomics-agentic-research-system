# The unsupported-configuration line

This sentence appears beside every local-tier result in this study, byte-identical to the text below.

Source: https://code.claude.com/docs/en/llm-gateway
Retrieved: 2026-09-08

> Anthropic doesn't endorse, maintain, or audit third-party gateway products, and doesn't support routing Claude Code to non-Claude models through any gateway.

## Why it is here

The local tier of this study points Claude Code, unmodified, at a local Ollama server through
`ANTHROPIC_BASE_URL`.
That is a gateway configuration, and the vendor states plainly that it is not a supported one.
A reader deciding whether to run this setup should read that from the vendor, not from us.

The sentence is committed as a file rather than typed into a page so that a test can assert the
published text is byte-identical to it, and so a change to the source page is visible as a diff
here rather than as a quiet rewording somewhere downstream.
