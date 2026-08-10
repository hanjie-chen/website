import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from container_remediation import (  # noqa: E402
    ImageReference,
    RemediationError,
    load_policy,
    parse_image_reference,
    replace_image_reference,
    select_candidates,
)


class ContainerRemediationTests(unittest.TestCase):
    def test_parse_pinned_reference(self):
        reference = parse_image_reference(
            "amir20/dozzle:v10.6.14@sha256:" + "a" * 64
        )

        self.assertEqual(reference.repository, "amir20/dozzle")
        self.assertEqual(reference.tag, "v10.6.14")
        self.assertEqual(reference.digest, "sha256:" + "a" * 64)
        self.assertEqual(reference.docker_hub_repository, "amir20/dozzle")

    def test_rejects_non_docker_hub_registry(self):
        reference = parse_image_reference("ghcr.io/example/service:v1.0.0")

        with self.assertRaises(RemediationError):
            _ = reference.docker_hub_repository

    def test_selects_only_newer_stable_tags_in_version_order(self):
        image = ImageReference("amir20/dozzle", "v10.6.14", "sha256:" + "1" * 64)
        policy = {
            "tag_regex": r"^v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$",
            "version_scheme": "semver",
        }
        records = [
            {"name": "v10.6.15", "digest": "sha256:" + "2" * 64},
            {"name": "v10.7.1", "digest": "sha256:" + "3" * 64},
            {"name": "v10.7.0-rc1", "digest": "sha256:" + "4" * 64},
            {"name": "v10.6.13", "digest": "sha256:" + "5" * 64},
            {"name": "latest", "digest": "sha256:" + "6" * 64},
        ]

        candidates = select_candidates(image, policy, records, max_candidates=10)

        self.assertEqual([candidate["tag"] for candidate in candidates], ["v10.7.1", "v10.6.15"])
        self.assertEqual(
            candidates[0]["image"],
            "amir20/dozzle:v10.7.1@sha256:" + "3" * 64,
        )

    def test_numeric_version_policy(self):
        image = ImageReference(
            "owasp/modsecurity-crs",
            "4-nginx-alpine-202607160307",
            None,
        )
        policy = {
            "tag_regex": r"^4-nginx-alpine-(?P<version>[0-9]{12})$",
            "version_scheme": "numeric",
        }
        records = [
            {
                "name": "4-nginx-alpine-202608050608",
                "digest": "sha256:" + "7" * 64,
            },
            {
                "name": "4-apache-202608050608",
                "digest": "sha256:" + "8" * 64,
            },
        ]

        candidates = select_candidates(image, policy, records, max_candidates=10)

        self.assertEqual([candidate["tag"] for candidate in candidates], ["4-nginx-alpine-202608050608"])

    def test_replace_requires_exactly_one_matching_reference(self):
        current = "amir20/dozzle:v10.6.14@sha256:" + "1" * 64
        candidate = "amir20/dozzle:v10.7.1@sha256:" + "2" * 64
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(f"services:\n  dozzle:\n    image: {current}\n", encoding="utf-8")

            replace_image_reference(compose_file, current, candidate)

            self.assertIn(candidate, compose_file.read_text(encoding="utf-8"))
            with self.assertRaises(RemediationError):
                replace_image_reference(compose_file, current, candidate)

    def test_load_policy_requires_named_version_group(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "images": {
                            "amir20/dozzle": {
                                "tag_regex": "^v[0-9]+$",
                                "version_scheme": "semver",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(RemediationError):
                load_policy(config_file, "amir20/dozzle")


if __name__ == "__main__":
    unittest.main()
