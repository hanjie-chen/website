# AGENTS

## Read First

Start with the root `Readme.md`, then read the nearest subsystem `README.md` before making non-trivial changes.

Examples:

- `web-app/README.md`
- `articles-sync/README.md`
- `scripts/deploy/README.md`
- `nginx-modsecurity/README.md`

## Working Rules

- Keep changes focused. Do not mix unrelated refactors into the same task.
- If you change subsystem behavior, update that subsystem's `README.md` in the same change.
- If you add, remove, or rename files that are documented, update the relevant `README.md` immediately.
- If a change affects high-level repo behavior, also update the root `Readme.md`.

## Verification

- Run the smallest relevant verification for the files you changed.
- Python / Flask / template / navigation changes: run `pytest -q` when practical.
- Shell script changes: run `shellcheck` when practical.
- README-only changes do not require full test runs, but they must stay accurate.

## Documentation Priority

`Readme.md` is the repo entry point. Subdirectory `README.md` files are the source of truth for subsystem behavior and operational details.
