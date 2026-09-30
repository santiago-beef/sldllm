# AGENTS.md

Shared instructions for every AI agent working in this repo (Claude Code, Gemini CLI, Ollama-backed tools).
This is the single source of truth. `CLAUDE.md` imports it; Gemini is pointed at it via `.gemini/settings.json`.
Do not duplicate its content into tool-specific files.

## Project

<!-- TODO(user): fill in. Agents cannot guess these. Keep each to 1-3 lines. -->
- **What it is:** TODO (PSP-1001 project, MFA Year 2, SLDLLM)
- **Goal / deliverable:** TODO
- **Stack / languages:** TODO
- **Key models used:** TODO (which Ollama models, which Gemini/Claude models)

## User preferences

- The user is still learning. Explain *why*, not just *what*, and define unfamiliar terms briefly.
- Do not be sycophantic. No praise, no "great question". Give realistic, informative answers, including when an idea is weak or a plan has problems.
- State uncertainty plainly. If you don't know or haven't verified something, say so.
- Give a recommendation, not an exhaustive list of options.
- Keep the repo decluttered. Before creating a new file, check whether an existing file should hold the content. Ask before adding new top-level files or directories.
- Do not create summary, scratch, or "notes to self" files in the repo.

## Environments

Work happens on two machines that sync through GitHub (`origin`, branch `main`).

| Machine | Role | Notes |
|---|---|---|
| macOS laptop | Primary editing | TODO |
| Remote Ubuntu | TODO (e.g. GPU / Ollama host) | TODO |

- Machine-specific paths, hostnames, and secrets never go in tracked files. Use `.env` (gitignored) and document variables in this file.
- Keep code portable across macOS and Ubuntu (no hardcoded `/Users/...` or `/home/...` paths).

## Workflow rules

- `git pull --rebase` before starting work; commit and push before ending a session, so the other machine is never behind.
- Do not commit, push, force-push, or rewrite history unless the user asks.
- Small, single-purpose commits. Imperative subject line.
- Never commit secrets, API keys, model weights, or large data files.
- Before finishing a task, say what was changed and what was *not* verified.

## Memory: where things go

Agents have no memory between sessions beyond the files in this repo. To keep it useful:

- **Stable facts and rules** (stack, conventions, preferences) → this file. Edit in place; keep it short.
- **Current status, decisions, open questions** → `docs/STATE.md`. Update it when a decision is made or the status changes. Record the *reason* for decisions.
- Do not store anything derivable from the code or git history.
- Tool-specific personal memory (e.g. Claude's auto-memory) is per-machine and not synced. Anything that matters on both machines must be written into the repo.

## Multi-agent conventions

- Any agent may pick up where another left off: read `docs/STATE.md` first.
- Note in `docs/STATE.md` when work is left half-done, so the next agent (or the other machine) knows.
- Avoid having two agents edit the same files at once. Use separate branches if running agents in parallel.
