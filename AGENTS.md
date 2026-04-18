# Repository Guide

## Read First

Start with the root `Readme.md`, then read the nearest subsystem `README.md` before making non-trivial changes.

Examples:

- `web-app/README.md`
- `articles-sync/README.md`
- `scripts/deploy/README.md`
- `nginx-modsecurity/README.md`

## Working Rules

- Keep changes focused. Do not mix unrelated refactors into the same task.
- Keep the root `Readme.md` concise. Put subsystem details in the nearest subsystem `README.md`, and only keep repo-level overview, entry points, and security/operations summaries in the root README.
- If you change subsystem behavior, update that subsystem's `README.md` in the same change.
- If you add, remove, or rename files that are documented, update the relevant `README.md` immediately.
- If a change affects high-level repo behavior, also update the root `Readme.md`.

## Verification

- Run the smallest relevant verification for the files you changed.
- Python / Flask / template / navigation changes: run `pytest -q` when practical.
- Shell script changes: run `shellcheck` when practical.
- README-only changes do not require full test runs, but they must stay accurate.

## Route Changes

- Treat public URL changes as both app changes and operations changes.
- When a route, language prefix, or public entry path changes, search the repo for old hard-coded paths and update health checks, smoke checks, deploy scripts, monitoring paths, and related docs in the same change.
- After route changes, prefer verifying both app behavior and deploy behavior. When practical, run the relevant `docker compose ... config`, healthcheck-related scripts, and smoke-check scripts in addition to tests.

## Workflow Fit

- Do not default to heavy spec / plan / subagent-driven workflows for small copy, polish, or tightly scoped UI changes.
- Prefer direct implementation or a short local checklist unless the work has meaningful scope, ambiguity, or coordination risk.

## Subagent Hygiene

- Close subagents promptly once their task and review role are complete.
- Do not keep finished implementer or reviewer agents open across unrelated tasks.
- Open a fresh subagent for the next task unless continued context is immediately necessary.

## Documentation Priority

`Readme.md` is the repo entry point. Subdirectory `README.md` files are the source of truth for subsystem behavior and operational details.

## Local Working Docs

- `docs/` is reserved for long-lived project documentation that should be committed, such as architecture decisions, deployment notes, and maintainer-facing design docs.
- `docs/superpowers/` is local-only working space for temporary AI-generated specs, plans, and scratch notes.
- Do not commit files under `docs/superpowers/` unless the user explicitly asks to promote that content into a permanent project document.
