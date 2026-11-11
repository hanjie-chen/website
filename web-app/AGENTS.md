# Web App Guide

## Verification

- Run applicable Ruff and pytest checks using the containerized `web-app` commands documented in `README.md`; do not assume host Python dependencies are installed.

## Interface Design

**Less, but better. Say it once. Make it count.**

This site favors calm, content-first interfaces.

- Within a view, give each fact and action one clear home.
- Build hierarchy with typography, spacing, and alignment before adding labels, numbering, badges, cards, or other chrome.
- Repeat only to preserve context, prevent error, or improve accessibility.
- Never simplify by hiding useful content or weakening semantics, focus states, or feedback.
- Take the Genshin event art's colors and their roles (see "Color and Themes" in `README.md`), not its ornaments. Clouds, medallions, glows and background gradients were tried on the notes pages and lost their appeal at interface scale. Shapes follow Apple-style restraint: thin lines, one chevron, structure that closes itself.
