# Repository Guide

## Read First

Start with the root `Readme.md`, then read the nearest subsystem `README.md` before making non-trivial changes.

## Working Rules

- Keep the root `Readme.md` concise. Put subsystem details in the nearest subsystem `README.md`, and only keep repo-level overview, entry points, and security/operations summaries in the root README.
- If you change subsystem behavior, update that subsystem's `README.md` in the same change.
- If you add, remove, or rename files that are documented, update the relevant `README.md` immediately.
- If a change affects high-level repo behavior, also update the root `Readme.md`.
- `Readme.md` is the repo entry point. Subdirectory `README.md` files are the source of truth for subsystem behavior and operational details.

## Verification

- Run the smallest relevant verification for the files you changed.
- Prefer running the same local checks that CI will run for the files you changed instead of relying on the remote pipeline to catch avoidable failures after `git push`.
- Python / Flask / template / navigation / test changes: run containerized `ruff check .`, `ruff format --check .`, and `pytest -q` when practical.
- Shell script changes: run `shellcheck -x scripts/deploy/*.sh articles-sync/*.sh` when practical.
- Compose or deploy changes: run `docker compose -f compose.yml config` and `docker compose -f compose.yml -f compose.dev.yml config` when practical.
- If a touched file fails local formatting or lint, fix it before considering the task complete. Do not leave obvious CI-failing issues for the push pipeline.
- README-only changes do not require full test runs, but they must stay accurate.

## Route Changes

- Treat public URL changes as both app changes and operations changes.
- When a route, language prefix, or public entry path changes, search the repo for old hard-coded paths and update health checks, smoke checks, deploy scripts, monitoring paths, and related docs in the same change.
- After route changes, prefer verifying both app behavior and deploy behavior. When practical, run the relevant `docker compose ... config`, healthcheck-related scripts, and smoke-check scripts in addition to tests.

## Local Working Docs

- `docs/` is reserved for long-lived project documentation that should be committed, such as architecture decisions, deployment notes, and maintainer-facing design docs.
- `docs/superpowers/` is local-only working space for temporary AI-generated specs, plans, and scratch notes.
- Do not commit files under `docs/superpowers/` unless the user explicitly asks to promote that content into a permanent project document.
