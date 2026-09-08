# The context-window line

Source: https://docs.ollama.com/integrations/claude-code
Retrieved: 2026-09-08

> For larger repositories, set the [context length](/context-length) to 64k or higher.

## What this study calls it, and the correction

Every local row in this study states the context window it ran at, and says
"below Ollama's stated floor for Claude Code" whenever that window is under 64k.

**Read the sentence above before the phrase.**
The source states 64k as guidance for larger repositories.
It does not state a hard floor, and it does not say a smaller window will refuse to run.
The study keeps the disclosure phrase because a reader deciding whether to trust a small-window
result needs the flag, and it prints the sentence verbatim beside the phrase so nobody has to take
our wording for what the vendor said.

This correction is recorded here rather than folded away, because the study's own rule is that a
criterion which stops serving an honest record gets flagged rather than quietly optimised.

## The same page also fixes the endpoint

The integration page gives the configuration as:

```
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL=http://localhost:11434
```

This study's driver departs from it in one way, deliberately: it removes `ANTHROPIC_API_KEY` from
the child environment instead of setting it to an empty string, so that each take's recorded
environment diff shows no API-key variable at all.
The reason is written up in `login-line.md`.

## What the 8 September probe measured

`fit/2026-09-08-llama3.1-64k.log` is the last block of an Ollama server log from a probe of
`llama3.1:8b` at a 64k window with a full-precision cache on this machine (Apple M1 Pro, 16 GB).
It is committed because it is the reason the fit proof exists as a step at all:

- the fit line reports 25 of 33 layers placed on the GPU, not the whole model;
- prompt processing ran at 3.85 tokens a second;
- the server stopped during the prompt, and did not answer afterwards.

A window is only used by this study once its load line shows the whole model on the GPU.
Nothing below 32k is tried.
