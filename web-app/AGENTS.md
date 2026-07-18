# Web App Agent Notes

## Scope

- These instructions apply only to `website/web-app/`.
- Keep this file focused on agent execution defaults for the Flask app, templates, static assets, and tests.

## Verification Defaults

- Use the containerized `web-app` environment; do not assume host Python dependencies are installed.
- Start with the smallest relevant target, then run the applicable Ruff check, Ruff format check, and pytest commands documented in `README.md`.

## Documentation Fit

- Do not duplicate long command lists or subsystem behavior notes here; keep those in `README.md`.
- Use this file for agent behavior defaults, and use `README.md` for human-facing setup, commands, and background context.
