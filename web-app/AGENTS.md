# Web App Agent Notes

## Scope

- These instructions apply only to `website/web-app/`.
- Keep this file focused on agent execution defaults for the Flask app, templates, static assets, and tests.

## Verification Defaults

- Do not assume the host Python environment has the project dependencies installed.
- For `web-app` changes, prefer the containerized `web-app` environment first.
- Default Python verification commands should use `docker compose -f compose.yml -f compose.dev.yml run --rm --no-deps -T web-app ...` unless the user explicitly asks for host-based commands.
- Prefer the smallest relevant verification target before running the full suite.

## Documentation Fit

- Do not duplicate long command lists or subsystem behavior notes here; keep those in `README.md`.
- Use this file for agent behavior defaults, and use `README.md` for human-facing setup, commands, and background context.
