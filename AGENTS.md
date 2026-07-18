# Repository Guide

## Read First

Start with the root `README.md`. Before planning or making non-trivial changes in a subsystem, read its nearest `README.md` and any `AGENTS.md` files on the path from the repository root to the target files.

## Working Rules

- Keep the root `README.md` concise. Put subsystem details in the nearest subsystem `README.md`, and only keep repo-level overview, entry points, and security/operations summaries in the root README.
- If you change subsystem behavior, update that subsystem's `README.md` in the same change.
- If you add, remove, or rename files that are documented, update the relevant `README.md` immediately.
- If a change affects high-level repo behavior, also update the root `README.md`.
- `README.md` is the repo entry point. Subdirectory `README.md` files are the source of truth for subsystem behavior and operational details.

## Verification

- Run the smallest relevant verification for the files you changed, and resolve related failures before completing the task.
- Shell script changes: run `shellcheck -x scripts/deploy/*.sh articles-sync/*.sh` when practical.
- Compose changes: validate both configurations with `docker compose -f compose.yml config --quiet` and `docker compose -f compose.yml -f compose.dev.yml config --quiet`.

## Route Changes

- When changing a public route or language prefix, search for the old path and update affected tests, health checks, smoke checks, deployment scripts, monitoring, and documentation in the same change.
