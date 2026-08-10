#!/usr/bin/env python3
"""Discover and pin safe container update candidates for security remediation."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DOCKER_HUB_API = "https://hub.docker.com/v2/repositories"
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class RemediationError(RuntimeError):
    """Raised when an image or remediation configuration is invalid."""


@dataclass(frozen=True)
class ImageReference:
    repository: str
    tag: str
    digest: str | None

    @property
    def docker_hub_repository(self) -> str:
        repository = self.repository
        for prefix in ("docker.io/", "index.docker.io/"):
            if repository.startswith(prefix):
                repository = repository.removeprefix(prefix)
                break
        if "." in repository.split("/", 1)[0] or ":" in repository.split("/", 1)[0]:
            raise RemediationError(
                f"Only Docker Hub repositories are supported, got {self.repository!r}"
            )
        if "/" not in repository:
            repository = f"library/{repository}"
        return repository


def parse_image_reference(value: str) -> ImageReference:
    """Parse repository:tag@digest while preserving an unqualified repository."""
    reference, separator, digest = value.partition("@")
    if separator and not DIGEST_PATTERN.fullmatch(digest):
        raise RemediationError(f"Invalid image digest in {value!r}")

    last_slash = reference.rfind("/")
    last_colon = reference.rfind(":")
    if last_colon <= last_slash:
        raise RemediationError(f"Image reference must include an explicit tag: {value!r}")

    repository = reference[:last_colon]
    tag = reference[last_colon + 1 :]
    if not repository or not tag:
        raise RemediationError(f"Invalid image reference: {value!r}")

    return ImageReference(repository=repository, tag=tag, digest=digest or None)


def load_policy(config_path: Path, repository: str) -> dict[str, str]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RemediationError(f"Unable to read {config_path}: {error}") from error

    images = config.get("images")
    if not isinstance(images, dict):
        raise RemediationError(f"{config_path} must contain an 'images' object")

    policy = images.get(repository)
    if not isinstance(policy, dict):
        raise RemediationError(f"No remediation policy configured for {repository!r}")

    tag_regex = policy.get("tag_regex")
    version_scheme = policy.get("version_scheme")
    if not isinstance(tag_regex, str) or version_scheme not in {"semver", "numeric"}:
        raise RemediationError(f"Invalid remediation policy for {repository!r}")
    try:
        expression = re.compile(tag_regex)
    except re.error as error:
        raise RemediationError(f"Invalid tag_regex for {repository!r}: {error}") from error
    if "version" not in expression.groupindex:
        raise RemediationError(
            f"tag_regex for {repository!r} must define a named 'version' group"
        )

    return {"tag_regex": tag_regex, "version_scheme": version_scheme}


def version_key(version: str, scheme: str) -> tuple[int, ...]:
    if scheme == "semver":
        parts = version.split(".")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise RemediationError(f"Invalid semantic version {version!r}")
        return tuple(int(part) for part in parts)
    if scheme == "numeric" and version.isdigit():
        return (int(version),)
    raise RemediationError(f"Invalid numeric version {version!r}")


def select_candidates(
    image: ImageReference,
    policy: dict[str, str],
    tag_records: Iterable[dict[str, Any]],
    max_candidates: int,
) -> list[dict[str, str]]:
    expression = re.compile(policy["tag_regex"])
    scheme = policy["version_scheme"]
    current_match = expression.fullmatch(image.tag)
    if current_match is None:
        raise RemediationError(
            f"Current tag {image.tag!r} does not match the configured tag policy"
        )
    current_key = version_key(current_match.group("version"), scheme)

    candidates: list[tuple[tuple[int, ...], dict[str, str]]] = []
    seen_tags: set[str] = set()
    for record in tag_records:
        tag = record.get("name")
        digest = record.get("digest")
        if not isinstance(tag, str) or tag in seen_tags:
            continue
        match = expression.fullmatch(tag)
        if match is None or not isinstance(digest, str) or not DIGEST_PATTERN.fullmatch(digest):
            continue
        candidate_key = version_key(match.group("version"), scheme)
        if candidate_key <= current_key:
            continue
        seen_tags.add(tag)
        candidates.append(
            (
                candidate_key,
                {
                    "repository": image.repository,
                    "tag": tag,
                    "digest": digest,
                    "image": f"{image.repository}:{tag}@{digest}",
                    "released_at": str(record.get("last_updated") or ""),
                },
            )
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in candidates[:max_candidates]]


def fetch_docker_hub_tags(repository: str, max_pages: int = 10) -> list[dict[str, Any]]:
    namespace, name = repository.split("/", 1)
    url = (
        f"{DOCKER_HUB_API}/{urllib.parse.quote(namespace, safe='')}/"
        f"{urllib.parse.quote(name, safe='')}/tags?page_size=100&ordering=last_updated"
    )
    records: list[dict[str, Any]] = []
    for _ in range(max_pages):
        request = urllib.request.Request(url, headers={"User-Agent": "website-container-security/1"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            raise RemediationError(f"Docker Hub tag lookup failed for {repository}: {error}") from error

        page_records = payload.get("results")
        if not isinstance(page_records, list):
            raise RemediationError(f"Docker Hub returned an invalid tag list for {repository}")
        records.extend(record for record in page_records if isinstance(record, dict))

        next_url = payload.get("next")
        if not isinstance(next_url, str) or not next_url:
            break
        url = next_url
    return records


def replace_image_reference(file_path: Path, current: str, candidate: str) -> None:
    if parse_image_reference(current).repository != parse_image_reference(candidate).repository:
        raise RemediationError("Current and candidate image repositories do not match")
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RemediationError(f"Unable to read {file_path}: {error}") from error
    occurrences = content.count(current)
    if occurrences != 1:
        raise RemediationError(
            f"Expected exactly one occurrence of {current!r} in {file_path}, found {occurrences}"
        )
    file_path.write_text(content.replace(current, candidate, 1), encoding="utf-8")


def discover_command(args: argparse.Namespace) -> None:
    image = parse_image_reference(args.image)
    docker_hub_repository = image.docker_hub_repository
    policy = load_policy(args.config, docker_hub_repository)
    records = fetch_docker_hub_tags(docker_hub_repository)
    candidates = select_candidates(image, policy, records, args.max_candidates)
    json.dump(candidates, sys.stdout, indent=2)
    sys.stdout.write("\n")


def replace_command(args: argparse.Namespace) -> None:
    replace_image_reference(args.file, args.current, args.candidate)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="list newer Docker Hub candidates")
    discover.add_argument("--config", type=Path, required=True)
    discover.add_argument("--image", required=True)
    discover.add_argument("--max-candidates", type=int, default=10)
    discover.set_defaults(handler=discover_command)

    replace = subparsers.add_parser("replace", help="replace one pinned image reference")
    replace.add_argument("--file", type=Path, required=True)
    replace.add_argument("--current", required=True)
    replace.add_argument("--candidate", required=True)
    replace.set_defaults(handler=replace_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "max_candidates", 1) < 1:
        parser.error("--max-candidates must be at least 1")
    try:
        args.handler(args)
    except RemediationError as error:
        print(f"container remediation error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
