# Repository Guide

## Read First

Start with the root `README.md`. Before planning or making non-trivial changes in a subsystem, read its nearest `README.md` and any `AGENTS.md` files on the path from the repository root to the target files.

## Documentation

- Keep the root `README.md` as a concise repository entry point for repo-level overview and security/operations summaries; use subsystem `README.md` files as the source of truth for subsystem details.
- Write the root `README.md` in Chinese, using English technical terms when clearer; write `AGENTS.md` and subsystem `README.md` files in English by default.
- In the same change, update the relevant subsystem `README.md` when its behavior or documented files change, and update the root `README.md` when repo-level behavior changes.

## Verification

- Run the smallest relevant verification for the files you changed, and resolve related failures before completing the task.
- Shell script changes: run `shellcheck -x scripts/deploy/*.sh articles-sync/*.sh` when practical.
- Compose changes: validate both configurations with `docker compose -f compose.yml config --quiet` and `docker compose -f compose.yml -f compose.dev.yml config --quiet`.

## Route Changes

- When changing a public route or language prefix, search for the old path and update affected tests, health checks, smoke checks, deployment scripts, monitoring, and documentation in the same change.
