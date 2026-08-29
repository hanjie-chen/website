#!/usr/bin/env python3
"""Select pinned third-party images changed by the current revision."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from container_remediation import RemediationError, load_policy, parse_image_reference


IMAGE_PATTERN = re.compile(
    r"^\s*image:\s*(?:\"(?P<double>[^\"]+)\"|'(?P<single>[^']+)'|(?P<plain>[^\s#]+))"
)


class GateError(RuntimeError):
    """Raised when the comparison inputs cannot produce a safe gate decision."""


def image_repository(reference: str) -> str:
    """Return the repository portion of a tag-and/or-digest image reference."""
    without_digest = reference.partition("@")[0]
    last_slash = without_digest.rfind("/")
    last_colon = without_digest.rfind(":")
    if last_colon > last_slash:
        repository = without_digest[:last_colon]
    else:
        repository = without_digest
    if not repository:
        raise GateError(f"Invalid image reference: {reference!r}")
    return repository


def load_tracked_policies(config_path: Path) -> dict[str, dict[str, str]]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GateError(f"Unable to read {config_path}: {error}") from error

    if not isinstance(config, dict):
        raise GateError(f"{config_path} must contain a JSON object")
    images = config.get("images")
    if not isinstance(images, dict) or not images:
        raise GateError(f"{config_path} must contain a non-empty 'images' object")
    if not all(isinstance(repository, str) and repository for repository in images):
        raise GateError(f"{config_path} contains an invalid image repository")
    try:
        return {
            repository: load_policy(config_path, repository) for repository in images
        }
    except RemediationError as error:
        raise GateError(str(error)) from error


def read_tracked_images(
    compose_path: Path, policies: dict[str, dict[str, str]]
) -> dict[str, str]:
    try:
        content = compose_path.read_text(encoding="utf-8")
    except OSError as error:
        raise GateError(f"Unable to read {compose_path}: {error}") from error

    tracked = set(policies)
    resolved: dict[str, str] = {}
    for line in content.splitlines():
        match = IMAGE_PATTERN.match(line)
        if match is None:
            continue
        reference = next(
            value for value in match.groupdict().values() if value is not None
        )
        repository = image_repository(reference)
        if repository not in tracked:
            continue
        try:
            parsed = parse_image_reference(reference)
        except RemediationError as error:
            raise GateError(
                f"Invalid tracked image in {compose_path}: {error}"
            ) from error
        if parsed.digest is None:
            raise GateError(
                f"Tracked image {reference!r} in {compose_path} must pin a sha256 digest"
            )
        if re.fullmatch(policies[repository]["tag_regex"], parsed.tag) is None:
            raise GateError(
                f"Tracked image tag {parsed.tag!r} in {compose_path} does not match "
                f"the configured policy for {repository!r}"
            )
        if repository in resolved:
            raise GateError(
                f"Expected one {repository!r} image in {compose_path}, found more than one"
            )
        resolved[repository] = reference

    missing = [repository for repository in policies if repository not in resolved]
    if missing:
        raise GateError(
            f"Missing tracked images in {compose_path}: {', '.join(missing)}"
        )
    return resolved


def select_changed_images(
    base_images: dict[str, str] | None,
    head_images: dict[str, str],
    repositories: list[str],
) -> list[str]:
    if base_images is None:
        return [head_images[repository] for repository in repositories]
    return [
        head_images[repository]
        for repository in repositories
        if head_images[repository] != base_images.get(repository)
    ]


def policies_require_full_scan(
    base_policies: dict[str, dict[str, str]],
    head_policies: dict[str, dict[str, str]],
) -> bool:
    """Reject silent repository removal and detect policy changes."""
    removed = [
        repository for repository in base_policies if repository not in head_policies
    ]
    if removed:
        raise GateError(
            "Tracked image repositories cannot be removed silently: "
            + ", ".join(removed)
        )
    return base_policies != head_policies


def changed_command(args: argparse.Namespace) -> None:
    head_policies = load_tracked_policies(args.config)
    head_images = read_tracked_images(args.head, head_policies)
    base_images = None

    if args.base_config is not None and args.base is None:
        raise GateError("--base-config requires --base")
    if args.base is not None:
        base_policies = (
            load_tracked_policies(args.base_config)
            if args.base_config is not None
            else head_policies
        )
        policy_changed = policies_require_full_scan(base_policies, head_policies)
        if not args.force_all and not policy_changed:
            base_images = read_tracked_images(args.base, base_policies)

    for image in select_changed_images(base_images, head_images, list(head_policies)):
        print(image)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    changed = subparsers.add_parser(
        "changed", help="print changed head image references, one per line"
    )
    changed.add_argument("--config", type=Path, required=True)
    changed.add_argument("--base", type=Path)
    changed.add_argument("--base-config", type=Path)
    changed.add_argument("--force-all", action="store_true")
    changed.add_argument("--head", type=Path, required=True)
    changed.set_defaults(handler=changed_command)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except GateError as error:
        print(f"container CI gate error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
