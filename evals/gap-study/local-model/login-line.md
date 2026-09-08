# The login line

Source: https://code.claude.com/docs/en/llm-gateway
Retrieved: 2026-09-08

> Setting only that variable, without a gateway credential, doesn't replace the subscription.

## Why it is here, and the two sentences that sit around it

This study's local takes must spend no subscription usage, or a "no per-token model fee" statement
beside a local row would be untrue.
The vendor page states the rule in both directions, and both halves are quoted here because only
the pair makes the design sound.

The sentence above is the caveat for setting the base URL alone. Its neighbours on the same page:

> Requests still route through the gateway, but a saved claude.ai login remains the active credential, so its usage limits and billing apply.

> While a [gateway credential variable](/docs/en/llm-gateway-connect#set-the-credential-variable) or `apiKeyHelper` is active, a developer's claude.ai subscription isn't used: the credential replaces the subscription login for that session, and the subscription's usage limits don't apply.

## What this study does about it

The driver sets **both** variables in the child process environment: `ANTHROPIC_BASE_URL` pointing
at the local server, and `ANTHROPIC_AUTH_TOKEN` set to a placeholder.
By the second sentence above, a credential variable being active means the subscription login is
not the credential in play, which is the condition this study needs.

The driver also **removes** `ANTHROPIC_API_KEY` from that environment rather than setting it to an
empty string, which is what the Ollama integration page shows.
An empty API-key variable is still an API-key variable, and every local take records its
environment diff from a stock shell so a reader can check for themselves that no API-key variable
was set.
