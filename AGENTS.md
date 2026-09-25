# Repository Guide

## Read First

Start with the root `README.md`. Before planning or making non-trivial changes in a subsystem, read its nearest `README.md`.

## Documentation

- Keep the root `README.md` as a concise repository entry point for repo-level overview and security/operations summaries; use subsystem `README.md` files as the source of truth for subsystem details.
- Write the root `README.md` in Chinese, using English technical terms when clearer; write `AGENTS.md` and subsystem `README.md` files in English by default.
- Update the relevant README files in the same change when their descriptions would otherwise become outdated.

## Verification

Determine verification scope from the affected behavior, including consumers of shared components.

- Run the smallest verification that covers this scope, and resolve related failures before completing the task. When a failure reveals a shared assumption, check other tests that rely on it.
- Shell script changes: run `shellcheck -x scripts/deploy/*.sh articles-sync/*.sh` when practical.
- Compose changes: validate both configurations with `docker compose -f compose.yml config --quiet` and `docker compose -f compose.yml -f compose.dev.yml config --quiet`.

## Git Workflow

- Work directly on `main` by default. Create a branch or PR only when explicitly requested by the user.

## Route Changes

- When changing a public route or language prefix, search for the old path and update affected tests, health checks, smoke checks, deployment scripts, monitoring, and documentation in the same change.
