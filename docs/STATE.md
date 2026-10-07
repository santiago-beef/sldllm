# Project State

Living log. Agents: read this first, update it when status or decisions change. Keep it short; prune what is no longer true.

## Current status

- Imported PSP uClinux / hacking codebase into `psp/` (kernel sources, uClinux patches, ring tests, decoder, pscol, and tooling). Build artifacts, dumps, and ancient toolchains excluded.

## Decisions

<!-- Format: YYYY-MM-DD: decision. Why. -->
- 2026-10-07: Imported PSP workspace under `psp/` in `sldllm`. Excluded compiled binaries (ELF/bFLT), large dumps, intermediate logs, and toolchain (`staging_dir`) to keep repo size clean (~320MB).
- 2026-09-30: `AGENTS.md` is the single instruction file; `CLAUDE.md` imports it and Gemini is configured to read it. Why: one file to maintain across three tools.

## Open questions

- TODO

## Handoff

<!-- Anything half-done that the next agent or machine needs to know. Clear when resolved. -->
- None.
